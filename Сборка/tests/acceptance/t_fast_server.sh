#!/usr/bin/env bash
set -euo pipefail
RB10_ONLY="${1-}" python3 -I - <<'PY'
import base64,datetime,hashlib,json,os,re,shlex,subprocess,urllib.request
from pathlib import Path
Q='qwen3.8-flash-next:125b-a6b-q6_K-ab-262k'
start=datetime.datetime.now(datetime.timezone.utc).isoformat();result={'started_at':start,'tests':{}}
def cmd(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=30)
 return {'rc':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
def http(path,body=None):
 data=None if body is None else json.dumps(body).encode()
 with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:11434'+path,data=data,headers={'Content-Type':'application/json'}),timeout=30) as r:return json.load(r)
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def test(i,fn):
 if os.environ.get('RB10_ONLY') and i!=os.environ['RB10_ONLY']:return
 try:result['tests'][i]=fn()
 except Exception as ex:result['tests'][i]={'collection_error':type(ex).__name__,'message':str(ex)}
def f01():
 v=http('/api/version')['version'];return {'version':v,'ollama_sha256':sha('/usr/local/bin/ollama'),'runner_sha256':sha('/usr/local/lib/ollama/llama-server.real-'+v)}
test('F01',f01)
def f02():
 raw=cmd(['systemctl','show','ollama.service','-p','Environment','--value']);env=dict(x.split('=',1) for x in shlex.split(raw['stdout']) if '=' in x)
 # Keep only accepted model-runtime invariants; no site binding/topology in public output.
 allowed=['OLLAMA_CONTEXT_LENGTH','OLLAMA_KV_CACHE_TYPE','OLLAMA_FLASH_ATTENTION','OLLAMA_NUM_PARALLEL','OLLAMA_MAX_LOADED_MODELS','OLLAMA_KEEP_ALIVE','CUDA_VISIBLE_DEVICES','GGML_CUDA_NO_GRAPHS']
 return {'environment':{k:env.get(k) for k in allowed},'rc':raw['rc']}
test('F02',f02)
tags=http('/api/tags');digests={m['name']:m['digest'] for m in tags['models']};qid=digests.get(Q,'')[:12]
def f03():
 v=result['tests']['F01']['version'];p=Path('/usr/local/lib/ollama/llama-server');real=Path(str(p)+'.real-'+v)
 return {'qid':qid,'version':v,'wrapper_sha256':sha(p),'wrapper_b64':base64.b64encode(p.read_bytes()).decode(),'chat_sha256':sha('/usr/local/share/ollama/templates/q6-'+qid+'-reasoning-compat.jinja'),'real_present':real.is_file()}
test('F03',f03)
def f04():
 shown=http('/api/show',{'model':Q});mod=cmd(['ollama','show','--modelfile',Q]);m=re.search(r'^PARAMETER\s+num_ctx\s+(\d+)',mod['stdout'],re.M)
 return {'models':digests,'num_ctx':int(m[1]) if m else None,'capabilities':shown.get('capabilities',[]),'modelfile_rc':mod['rc']}
test('F04',f04)
def f05():return cmd(['journalctl','-b','-t','ollama-q6-profile','--no-pager','-o','cat'])
test('F05',f05)
def f06():
 services={n:{k:cmd(['systemctl','is-'+k,n+'.service']) for k in ['active','enabled']} for n in ['ollama','llm-gateway','rag-mcp','docker-mcp','searxng-mcp','docker']}
 with urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=15) as r:health=json.load(r)
 p=cmd(['docker','compose','--project-directory',str(Path.home()/'searxng'),'ps','--format','json']);lines=p['stdout'].strip();containers=json.loads(lines) if lines.startswith('[') else [json.loads(l) for l in lines.splitlines() if l]
 return {'services':{n:{k:{'rc':v['rc'],'value':v['stdout'].strip()} for k,v in d.items()} for n,d in services.items()},'health':{k:health.get(k) for k in ['version','auth_enabled','pipelines_count']},'compose_rc':p['rc'],'compose':[{'service':c.get('Service'),'state':c.get('State'),'health':c.get('Health')} for c in containers]}
test('F06',f06)
def f07():
 p=cmd(['dpkg-query','-W','-f=${binary:Package}\t${Version}\t${db:Status-Status}\n']);packages={}
 for l in p['stdout'].splitlines():
  name,v,status=l.split('\t');
  if status=='installed':packages[name]=v
 return {'packages':packages,'kernel':cmd(['uname','-r'])['stdout'].strip(),'nvidia':cmd(['nvidia-smi','--query-gpu=driver_version','--format=csv,noheader'])['stdout'].strip(),'python':cmd(['python3','--version'])['stdout'].strip(),'rc':p['rc']}
test('F07',f07)
def f09():
 power=cmd(['nvidia-smi','--query-gpu=power.limit','--format=csv,noheader,nounits'])
 status=cmd(['systemctl','show','ailab-gpu-power.service','-p','ActiveState','-p','SubState','-p','Result','-p','ExecMainStatus','--no-pager'])
 enabled=cmd(['systemctl','is-enabled','ailab-gpu-power.service'])
 fields=dict(line.split('=',1) for line in status['stdout'].splitlines() if '=' in line)
 try:watts=float(power['stdout'].strip())
 except (TypeError,ValueError):watts=None
 return {'power_limit_w':watts,'power_rc':power['rc'],'unit_rc':status['rc'],
         'active':fields.get('ActiveState'),'substate':fields.get('SubState'),
         'result':fields.get('Result'),'exec_main_status':fields.get('ExecMainStatus'),
         'enabled':enabled['stdout'].strip(),'enabled_rc':enabled['rc']}
test('F09',f09)
result['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();print(json.dumps(result,ensure_ascii=False))
PY
