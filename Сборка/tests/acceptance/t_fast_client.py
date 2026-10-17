#!/usr/bin/env python3
"""Read client files; never launch npm, pi or code. Run with python3 -I."""
import datetime,hashlib,json,shutil,sys
from pathlib import Path
H=Path.home();Q='qwen3.8-flash-next:125b-a6b-q6_K-ab-262k';R={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tests':{}}
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def test(i,f):
 if '--only' in sys.argv and i!=sys.argv[sys.argv.index('--only')+1]:return
 try:R['tests'][i]=f()
 except Exception as ex:R['tests'][i]={'collection_error':type(ex).__name__,'message':str(ex)}
def pi_root():
 p=Path(shutil.which('pi')).resolve()
 for parent in p.parents:
  f=parent/'package.json'
  if f.exists() and json.loads(f.read_text()).get('name')=='@earendil-works/pi-coding-agent':return parent
 raise ValueError('Pi package root missing')
def c01():
 p=pi_root();return {'version':json.loads((p/'package.json').read_text())['version'],'cli_sha256':sha(p/'dist/bundle/cli.js')}
test('C01',c01)
def c02():
 s=json.loads((H/'.pi/agent/settings.json').read_text());m=json.loads((H/'.pi/agent/models.json').read_text());p=m['providers']['ailab-ollama'];q=next(x for x in p['models'] if x['id']==Q);o=p.get('modelOverrides',{}).get(Q,{})
 values={k:q.get(k) for k in ['contextWindow','maxTokens','thinkingLevelMap']};values.update({k:s.get(k) for k in ['httpIdleTimeoutMs','defaultThinkingLevel']});values.update({k:s['compaction'].get(k) for k in ['reserveTokens','keepRecentTokens']});values['retry_enabled']=s.get('retry',{}).get('enabled');values['override']=o.get('samplingParams',{}).get('reasoning_effort');values['override_contextWindow']=o.get('contextWindow');values['override_maxTokens']=o.get('maxTokens');values['model_compaction_override']=s['compaction'].get('modelOverrides',{}).get('ailab-ollama/'+Q);values['pi_input']=q.get('input');return values
test('C02',c02)
def c03():
 # Read installed application metadata without launching VS Code.
 candidates=[Path('/snap/code/current/usr/share/code/resources/app/package.json'),Path('/usr/share/code/resources/app/package.json')]
 existing=[p for p in candidates if p.is_file()];v=[json.loads(p.read_text())['version'] for p in existing]
 ex=[]
 for p in (H/'.vscode/extensions').glob('pi0.pi-vscode-*/package.json'):
  j=json.loads(p.read_text());ex.append(j['version'])
 return {'vscode_versions':v,'extensions':ex}
test('C03',c03)
def c04():return {name:sha(H/'.pi/agent/bin'/name) for name in ['fd','rg']}
test('C04',c04)
R['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();print(json.dumps(R,ensure_ascii=False))
