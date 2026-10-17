#!/usr/bin/env python3
"""Sequential live reference probes. No pulls, updates or service changes."""
import argparse,datetime,hashlib,json,math,os,re,runpy,signal,subprocess,tempfile,time,urllib.error,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
ssh_script=runpy.run_path(str(HERE/'transport.py'))['ssh_script']

def main():
 p=argparse.ArgumentParser();p.add_argument('--ssh-target',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--private-output',type=Path,required=True);p.add_argument('--only',default='');a=p.parse_args()
 credential=input();b=json.loads((HERE/'baseline.json').read_text())['tests'];get=lambda i,k:b[i][k]['value'];Q=get('M01','model')
 live=Path.home()/'.pi/agent';provider=json.loads((live/'models.json').read_text())['providers'][get('M09','provider')];base=provider['baseUrl'].removesuffix('/v1')
 a.output.mkdir(parents=True,exist_ok=True);a.private_output.mkdir(parents=True,exist_ok=True)
 report={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tests':{}};began=time.monotonic();selected=set(a.only.split(',')) if a.only else None
 def deadline(sig,frame):raise TimeoutError('test deadline exceeded')
 signal.signal(signal.SIGALRM,deadline)
 def request(path,body=None,stream=False):
  data=None if body is None else json.dumps(body,ensure_ascii=False).encode();start=time.monotonic();req=urllib.request.Request(base+path,data=data,headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=min(900,max(1,3600-(time.monotonic()-began)))) as r:
   if not stream:return {'http_status':r.status,'body':json.load(r),'total_s':time.monotonic()-start}
   events=[];content='';ttft=None;finish=None
   for line in r:
    if not line.startswith(b'data:'):continue
    raw=line[5:].strip()
    if raw==b'[DONE]':break
    event=json.loads(raw);events.append(event)
    for c in event.get('choices',[]):
     delta=c.get('delta',{});token=delta.get('content') or delta.get('reasoning') or delta.get('reasoning_content')
     if token and ttft is None:ttft=time.monotonic()-start
     content+=delta.get('content') or ''
     if c.get('finish_reason'):finish=c['finish_reason']
   return {'http_status':r.status,'events':events,'content':content,'ttft_s':ttft,'total_s':time.monotonic()-start,'finish_reason':finish}
 def remote(code,timeout=120,sudo=False):
  out=ssh_script(a.ssh_target,"python3 -I - <<'RB10REMOTE'\n"+code+"\nRB10REMOTE",credential,timeout=timeout,with_sudo=sudo)
  if out['rc']!=0:raise RuntimeError('remote probe returned nonzero status')
  return json.loads(out['stdout'])
 def save():
  report['duration_min']=(time.monotonic()-began)/60
  (a.output/'t_med.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 def run(i,fn,limit=900):
  if selected and i not in selected:return
  remaining=3600-(time.monotonic()-began)
  if remaining<=0:raise TimeoutError('T-MED budget exhausted')
  print(i+' START',flush=True);start=time.monotonic();stamp=datetime.datetime.now(datetime.timezone.utc).isoformat();signal.alarm(max(1,int(min(limit,remaining))))
  try:
   result=fn();report['tests'][i]=result
  except Exception as ex:
   # URLs, tokens and traceback contents never enter public errors.
   report['tests'][i]={'probe_error':type(ex).__name__,'http_status':getattr(ex,'code',None)}
   if isinstance(ex,(TimeoutError,urllib.error.URLError)):
    signal.alarm(0)
    try:request('/api/version')
    except Exception:
     report['tests'][i]['stop']='Ollama unavailable; no restart attempted';save();raise SystemExit('STOP: Ollama unavailable')
  finally:signal.alarm(0)
  report['tests'][i]['started_at']=stamp;report['tests'][i]['elapsed_s']=time.monotonic()-start;save();print(i+' DONE',flush=True)
 m01_since=datetime.datetime.now(datetime.timezone.utc).isoformat()
 def m01():return request('/v1/chat/completions',{'model':Q,'messages':[{'role':'user','content':get('M01','prompt')}],'reasoning_effort':get('M01','reasoning_effort'),'max_tokens':get('M01','max_tokens'),'stream':True},True)
 run('M01',m01)
 run('M02',lambda:request('/api/ps'))
 def journal(since):
  return remote('import json,subprocess,os\np=subprocess.run(["sudo","-S","-p","","journalctl","-t","ollama-q6-profile","--since",'+repr(since)+',"--no-pager","-o","cat"],input=os.environ["RB10_CREDENTIAL"]+"\\n",capture_output=True,text=True)\nprint(json.dumps({"rc":p.returncode,"stdout":p.stdout}))',sudo=True)
 run('M03',lambda:journal(m01_since),60)
 run('M04',lambda:{effort:request('/v1/chat/completions',{'model':Q,'messages':[{'role':'user','content':'Ответь только: OK'}],'reasoning_effort':effort,'max_tokens':1,'stream':False,'_debug_render_only':True}) for effort in get('M04','efforts')})
 m05_since=datetime.datetime.now(datetime.timezone.utc).isoformat()
 def m05():
  strings=(HERE/'embedding_strings.json').read_bytes();values=json.loads(strings)
  code='''import json,urllib.request
from pathlib import Path
env={}
for line in (Path.home()/"llm-gateway/.env").read_text().splitlines():
 line=line.strip()
 if line and not line.startswith("#") and "=" in line:
  k,v=line.split("=",1);env[k]=v.strip().strip("\\\"").strip("'")
tokens=json.loads(env["LLM_GATEWAY_TOKENS"]);selected=[k for k,v in tokens.items() if v=="vladimir"]
assert len(selected)==1
body=json.dumps({"model":"qwen3-embedding","input":STRINGS}).encode()
results=[]
for _ in range(2):
 req=urllib.request.Request("http://127.0.0.1:8000/v1/embeddings",data=body,headers={"Content-Type":"application/json","Authorization":"Bearer "+selected[0]})
 with urllib.request.urlopen(req,timeout=600) as r:results.append({"http_status":r.status,"body":json.load(r)})
print(json.dumps({"runs":results}))
'''.replace('STRINGS',repr(values))
  result=remote(code,timeout=800);vectors=[]
  for r in result['runs']:
   data=sorted(r['body']['data'],key=lambda row:row['index']);assert [x['index'] for x in data]==list(range(len(values)));v=[x['embedding'] for x in data];assert len(v)==len(values) and all(len(x)==get('M05','dimension') for x in v) and all(math.isfinite(n) for row in v for n in row);vectors.append(v)
  diff=max(abs(x-y) for aa,bb in zip(*vectors) for x,y in zip(aa,bb));reference={'strings_sha256':hashlib.sha256(strings).hexdigest(),'model':get('M05','model'),'dimension':get('M05','dimension'),'runs':vectors,'run_to_run_max_abs_diff':diff,'comparison_atol':diff,'tolerance_policy':'Measured max_abs_diff, no silently added margin; zero means exact equality. Any later enlargement requires review.'}
  (a.output/'embedding_reference.json').write_text(json.dumps(reference,ensure_ascii=False,indent=2)+'\n');result['reference']={k:v for k,v in reference.items() if k!='runs'};return result
 run('M05',m05)
 run('M06',lambda:journal(m05_since),60)
 run('M07',lambda:request('/v1/chat/completions',{'model':Q,'messages':[{'role':'system','content':get('M07','system_prompt')},{'role':'user','content':'Ответь одним словом: OK'}],'temperature':get('M07','temperature'),'max_tokens':get('M07','max_tokens'),'stream':False}))
 probe=(HERE.parents[1]/'artifacts/services/probe_mcp.py').read_text()
 def mcp(tool,url,args):
  code='import sys\nsys.argv='+repr(['probe_mcp.py','--url',url,'--tool',tool,'--arguments',json.dumps(args,ensure_ascii=False)])+'\n'+probe
  return remote(code,180)
 run('M08',lambda:{'collections':mcp('list_collections','http://127.0.0.1:8100/mcp',{}),'search':mcp('search_docs','http://127.0.0.1:8100/mcp',{'query':get('M08','query'),'top_k':3})},450)
 def m09():
  config_before={name:hashlib.sha256((live/name).read_bytes()).hexdigest() for name in ['settings.json','models.json']}
  executable=__import__('shutil').which('pi')
  with tempfile.TemporaryDirectory(prefix='rb10-pi-') as name:
   home=Path(name);agent=home/'.pi/agent';agent.mkdir(parents=True)
   for f in config_before:(agent/f).write_bytes((live/f).read_bytes())
   auth_copied=False
   auth_path=live/'auth.json'
   if auth_path.is_file():
    entry=json.loads(auth_path.read_text()).get(get('M09','provider'))
    if entry is not None:
     auth=agent/'auth.json';auth.write_text(json.dumps({get('M09','provider'):entry}));auth.chmod(0o600);auth_copied=True
   env={k:v for k,v in os.environ.items() if not re.search(r'(TOKEN|SECRET|PASSWORD|API_KEY|^PI_|^XDG_)',k)};env.update({'HOME':str(home),'XDG_CONFIG_HOME':str(home/'.config'),'XDG_CACHE_HOME':str(home/'.cache'),'XDG_DATA_HOME':str(home/'.local/share'),'PI_CODING_AGENT_DIR':str(agent),'PI_OFFLINE':'1','NO_COLOR':'1'})
   args=[executable,'--offline','--no-session','--no-tools','--no-extensions','--no-skills','--no-prompt-templates','--no-context-files','--provider',get('M09','provider'),'--model',Q,'-p','Ответь одним словом: OK']
   proc=subprocess.run(args,cwd=home,env=env,capture_output=True,text=True,timeout=850)
   output={'rc':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr,'config_copies_sha256':config_before,'auth_copied':auth_copied,'temporary_home':True}
  output['live_configs_unchanged']=config_before=={name:hashlib.sha256((live/name).read_bytes()).hexdigest() for name in config_before};return output
 run('M09',m09)
 def health(i,script):
  raw=ssh_script(a.ssh_target,script,credential,timeout=400)
  (a.private_output/(i+'-raw.txt')).write_text(raw['stdout'])
  lines=[l for l in raw['stdout'].splitlines() if re.match(r'^\[(OK|FAIL)\]',l)];checks=[{'index':n+1,'status':'FAIL' if l.startswith('[FAIL]') else 'PASS'} for n,l in enumerate(lines)]
  return {'rc':raw['rc'],'checks':checks,'passed':sum(x['status']=='PASS' for x in checks),'failed':sum(x['status']=='FAIL' for x in checks),'total':len(checks),'full_receipt':'private companion'}
 services=HERE.parents[1]/'artifacts/services/gateway'
 run('M10',lambda:health('M10',(services/'revisions/rb07.1/scripts/health-check.sh').read_text()),450)
 run('M11',lambda:health('M11',(services/'src/scripts/health-check.sh').read_text()),450)
 run('M12',lambda:mcp('web_search','http://127.0.0.1:8300/mcp',{'query':'Ollama documentation','max_results':3}),180)
 report['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();save();print('T-MED COMPLETE minutes='+str(round(report['duration_min'],3)),flush=True)
if __name__=='__main__':main()
