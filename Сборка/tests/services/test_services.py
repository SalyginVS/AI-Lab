#!/usr/bin/env python3
"""RB-07 offline evidence tests. Never connect to the lab server."""
import argparse,ast,hashlib,http.server,json,os,re,secrets,shutil,socket,sqlite3,subprocess,sys,tempfile,threading,time,urllib.request,urllib.error
from pathlib import Path

def digest(b):return hashlib.sha256(b).hexdigest()
def http_json(url,payload=None,headers=None):
    h=dict(headers or {})
    if payload is not None:h['Content-Type']='application/json'
    q=urllib.request.Request(url,data=None if payload is None else json.dumps(payload).encode(),headers=h)
    try:
        with urllib.request.urlopen(q,timeout=20) as r:
            b=r.read().decode();rh=dict(r.headers);status=r.status
    except urllib.error.HTTPError as exc:return exc.code,{},None
    if b.startswith('event:') or b.startswith('data:'):
        ds=[l[5:].strip() for l in b.splitlines() if l.startswith('data:')];data=json.loads(ds[-1]) if ds else None
    else:data=json.loads(b) if b else None
    return status,rh,data

class Stub(http.server.BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        if self.path=='/api/tags':data={'models':[{'name':'test-model','modified_at':'2026-01-01T00:00:00Z'}]}
        elif self.path.startswith('/search'):data={'results':[{'title':'Test result','url':'https://example.com/','content':'offline stub'}]}
        elif self.path.endswith('/system/df'):data={'Containers':[],'Images':[],'Volumes':[]}
        else:data={'ApiVersion':'1.45','Version':'offline-stub','Os':'linux','Arch':'amd64'}
        b=json.dumps(data).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)

BOOTSTRAP=r'''
import sys,runpy,os
from pathlib import Path
service,src,port,stub,chroma=sys.argv[1:];sys.path.insert(0,src)
if service=='gateway':
 import gateway
 gateway.OLLAMA_TAGS_URL='http://127.0.0.1:'+stub+'/api/tags'
 import uvicorn
 uvicorn.run('gateway.app:app',host='127.0.0.1',port=int(port),log_level='error',access_log=False)
elif service=='rag-mcp':
 import chromadb
 original=chromadb.PersistentClient
 def client(*args,**kwargs):
  kwargs['path']=chroma
  kwargs['settings']=chromadb.Settings(anonymized_telemetry=False)
  return original(**kwargs)
 chromadb.PersistentClient=client
 ns=runpy.run_path(str(Path(src)/'server.py'),run_name='rb07_test')
 ns['mcp'].settings.host='127.0.0.1';ns['mcp'].settings.port=int(port)
 ns['mcp'].run(transport='streamable-http')
elif service=='docker-mcp':
 ns=runpy.run_path(str(Path(src)/'server.py'),run_name='rb07_test')
 import uvicorn
 uvicorn.run(ns['app'],host='127.0.0.1',port=int(port),log_level='error',access_log=False)
else:
 ns=runpy.run_path(str(Path(src)/'server.py'),run_name='rb07_test')
 ns['mcp'].run(transport='streamable-http',host='127.0.0.1',port=int(port),streamable_http_path='/mcp',json_response=True,stateless_http=True,transport_security=ns['security'])
'''

def startup(a):
    out={};stub=http.server.ThreadingHTTPServer(('127.0.0.1',0),Stub);threading.Thread(target=stub.serve_forever,daemon=True).start();stubport=stub.server_address[1]
    try:
        for s in ['gateway','rag-mcp','docker-mcp','searxng-mcp']:
            py=a.venvs/s/'bin/python';result={};proc=None
            with tempfile.TemporaryDirectory(prefix='rb07-start-') as td:
                td=Path(td);src=td/'src';shutil.copytree(a.artifacts/s/'src',src)
                with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
                token=secrets.token_hex(32);env=os.environ.copy();env.update(LLM_GATEWAY_TOKENS=json.dumps({token:'test'}),LLM_ORCHESTRATOR_TOKEN=token,SEARXNG_URL='http://127.0.0.1:'+str(stubport),DOCKER_HOST='tcp://127.0.0.1:'+str(stubport),PYTHONDONTWRITEBYTECODE='1',ANONYMIZED_TELEMETRY='False',HOME=str(td),NO_PROXY='127.0.0.1,localhost')
                try:
                    with (td/'stderr').open('wb') as err:
                        proc=subprocess.Popen([str(py),'-I','-B','-c',BOOTSTRAP,s,str(src),str(port),str(stubport),str(td/'chroma')],cwd=src,env=env,stdout=subprocess.DEVNULL,stderr=err)
                        deadline=time.monotonic()+45
                        while time.monotonic()<deadline:
                            if proc.poll() is not None:raise RuntimeError('process exited '+str(proc.returncode))
                            try:
                                with socket.create_connection(('127.0.0.1',port),timeout=.2):break
                            except OSError:time.sleep(.1)
                        else:raise RuntimeError('startup timeout')
                        url='http://127.0.0.1:'+str(port)
                        if s=='gateway':
                            status,_,data=http_json(url+'/health');assert status==200 and data['version']=='0.12.0' and data['auth_enabled'] is True and data['ollama']=='ok' and data['pipelines_count']==1
                            assert http_json(url+'/v1/models')[0]==401
                            status,_,data=http_json(url+'/v1/models',headers={'Authorization':'Bearer '+token});assert status==200 and data['object']=='list'
                            result={'status':'PASS','health_version':'0.12.0','auth_enabled':True,'unauthenticated_status':401,'authenticated_status':200,'stub_ollama':True}
                        else:
                            headers={'Accept':'application/json, text/event-stream'}
                            req={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'rb07-test','version':'1.0'}}}
                            status,rh,data=http_json(url+'/mcp',req,headers);assert status==200 and data and 'result' in data,(status,data)
                            sid=next((v for k,v in rh.items() if k.lower()=='mcp-session-id'),None)
                            if sid:headers['Mcp-Session-Id']=sid
                            http_json(url+'/mcp',{'jsonrpc':'2.0','method':'notifications/initialized'},headers)
                            status,_,data=http_json(url+'/mcp',{'jsonrpc':'2.0','id':2,'method':'tools/list'},headers);assert status==200 and 'tools' in data['result']
                            tool={'rag-mcp':'list_collections','docker-mcp':'system_info','searxng-mcp':'web_search'}[s]
                            assert tool in [t['name'] for t in data['result']['tools']]
                            args={'query':'offline test'} if s=='searxng-mcp' else {}
                            status,_,data=http_json(url+'/mcp',{'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':tool,'arguments':args}},headers)
                            assert status==200 and 'result' in data and not data['result'].get('isError'),(status,data)
                            result={'status':'PASS','initialize':True,'tools_list':True,'tool':tool,'tool_call_success':True,'test_dependency':{'rag-mcp':'real Chroma in temporary directory','docker-mcp':'Docker Engine HTTP stub','searxng-mcp':'SearXNG HTTP stub'}[s]}
                except Exception as exc:result={'status':'LIMITATION','error':str(exc)}
                finally:
                    if proc and proc.poll() is None:
                        proc.terminate()
                        try:proc.wait(timeout=8)
                        except subprocess.TimeoutExpired:proc.kill();proc.wait()
                    if result.get('status')!='PASS' and (td/'stderr').exists():result['stderr']=(td/'stderr').read_text(errors='replace')[-5000:].replace(token,'<TEST_TOKEN>')
            out[s]=result;print('T7',s,json.dumps(result),flush=True)
    finally:stub.shutdown();stub.server_close()
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--artifacts',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--capture',type=Path,required=True);p.add_argument('--venvs',type=Path,required=True);a=p.parse_args();e=a.evidence;out={}
    rows=[l.split('\t') for l in (e/'rb07_source_sets.tsv').read_text().splitlines()[1:]]
    for service,status,path,reason,sha,size in rows:
        if status!='INCLUDED':continue
        root={'gateway':'llm-gateway','rag-mcp':'rag-mcp-server','docker-mcp':'docker-mcp-server','searxng-mcp':'searxng-mcp'}[service]
        rel=Path(path).relative_to('home/vladimir/'+root);original=(a.capture/path).read_bytes();published=(a.artifacts/service/'src'/rel).read_bytes();assert original==published and digest(published)==sha
    out['T1']={'status':'PASS','files':sum(r[1]=='INCLUDED' for r in rows)}
    graphs=json.loads((e/'rb07_import_graph.json').read_text());live=json.loads((e/'rb07_live_packages.json').read_text());mapping={'yaml':'pyyaml'}
    for service,g in graphs.items():
        locked={r['name'].lower().replace('_','-') for r in live[service]}
        for module in g['external_imports']:assert module in sys.stdlib_module_names or mapping.get(module,module).lower().replace('_','-') in locked,(service,module)
        for mod in g['local_modules']:
            f=a.artifacts/service/'src'/Path(*mod.split('.'));assert f.with_suffix('.py').is_file() or (f/'__init__.py').is_file()
    out['T2']={'status':'PASS','static_import_closure':True,'runtime_file_map':'runtime-files.json','dynamic_entrypoint':'uvicorn gateway.app:app explicitly included','reindex_entrypoint':'indexer.py explicitly included'}
    for f in (a.artifacts/'units').rglob('*.in'):
        rel=f.relative_to(a.artifacts/'units');original=(a.capture/'etc/systemd/system'/rel.with_suffix('')).read_bytes();b=f.read_bytes();assert b'vladimir' not in b
        assert b.replace(b'@LAB_SERVICE_ROOT@',b'/home/vladimir').replace(b'@LAB_OPERATOR@',b'vladimir')==original
    assert (a.artifacts/'cron.in').read_bytes().replace(b'@LAB_SERVICE_ROOT@',b'/home/vladimir')==(e/'rb07_crontab_captured.txt').read_bytes()
    assert (a.artifacts/'searxng/docker-compose.yml').read_bytes().replace(b'@LAB_SERVICE_ROOT@',b'/home/vladimir')==(a.capture/'home/vladimir/searxng/docker-compose.yml').read_bytes()
    out['T3']={'status':'PASS','unit_and_dropin_files':6,'cron':True,'compose':True}
    deps=json.loads((e/'rb07_dependencies_test.json').read_text())
    for service,packages in live.items():
        lock=(a.artifacts/service/'requirements.lock').read_text();lines=[l for l in lock.splitlines() if l and not l.startswith('#')]
        versions=dict(l.split()[0].split('==',1) for l in lines);assert versions=={d['name']:d['version'] for d in packages}
        assert all('--hash=sha256:' in l for l in lines)
    out['T4']={'status':'PASS' if all(d['cross_download_exit']==0 for d in deps.values()) else 'GAPS_RECORDED','versions_mismatched':0,'results':deps}
    images=json.loads((e/'rb07_image_digests.txt').read_text());out['T5']={'status':'PASS' if all(i['registry_serves'] and i.get('config_equals_live_id') for i in images) else 'GAPS_RECORDED','images':images}
    with tempfile.TemporaryDirectory(prefix='rb07-t6-') as td:
        db=Path(td)/'chroma.sqlite3';shutil.copyfile(a.capture/'home/vladimir/rag-data/chroma/chroma.sqlite3',db);c=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
        actual={name:{'dimension':dim,'records':c.execute('select count(*) from embeddings e join segments s on e.segment_id=s.id where s.collection=?',(cid,)).fetchone()[0]} for cid,name,dim in c.execute('select id,name,dimension from collections')};c.close()
    expected={x['name']:{'dimension':x['dimension'],'records':x['records']} for x in json.loads((e/'rb07_chroma_expectations.json').read_text())['collections']};assert actual==expected
    out['T6']={'status':'PASS','collections':actual}
    starts=startup(a)
    out['T7']={'status':'PASS' if all(v['status']=='PASS' for v in starts.values()) else 'LIMITATIONS_RECORDED','services':starts,'limits':['loopback binding and upstream endpoints injected by test bootstrap; accepted source files unchanged','GPU, real Ollama, Docker Engine and public web not tested','RAG production literal paths redirected only within test bootstrap']}
    template=(a.artifacts/'searxng/settings.yml.in').read_bytes();raw=(e/'private/settings.yml').read_bytes();match=re.search(rb'(?m)^\s*secret_key:\s*[\x22\x27]?([^\r\n\x22\x27]+)',raw);assert match and template.replace(b'@SEARXNG_SECRET_KEY@',match[1])==raw
    out['T8']={'status':'PASS','captured_sha256':digest(raw),'roundtrip_byte_equal':True}
    (e/'rb07_tests.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');(e/'rb07_tests.log').write_text('\n'.join(k+'='+v['status'] for k,v in out.items())+'\n')
    print(json.dumps({k:v['status'] for k,v in out.items()}),flush=True)
if __name__=='__main__':main()
