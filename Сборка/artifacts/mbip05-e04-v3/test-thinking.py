#!/usr/bin/env python3
"""Short E02-P-style loopback SSE probe; no model generation or live provider."""
import http.server, json, pathlib, sys, threading, subprocess, os, queue, time, copy
root=pathlib.Path(sys.argv[1]);src=pathlib.Path(sys.argv[2]);root.mkdir(mode=0o700)
m=json.loads((src/'models.json').read_text());s=json.loads((src/'settings.json').read_text())
cases={
 'inkling':('ailab-strata','inkling-2-mini-sq-20','max',{'off':'none','minimal':'minimal','low':'low','medium':'medium','high':'high','xhigh':'xhigh','max':'max'}),
 'flash':('ailab-strata','qwen3.8-flash-next-ud-q6_k_xl','high',{'off':'none','low':'low','medium':'medium','high':'xhigh'}),
 'q27':('ailab-ollama','qwen3.8-27b-gsq-rco:iq3s-mtp-262k','medium',None)}
requests={k:[] for k in cases}
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_POST(self):
  try:
   key,_,endpoint=self.path.strip('/').split('/',2);assert endpoint=='chat/completions' and key in cases
   raw=self.rfile.read(int(self.headers['Content-Length']));req=json.loads(raw);assert req['model']==cases[key][1] and req['stream'] is True
   assert 0<req['max_tokens']<=262144
   requests[key].append(req);(root/key/('request-%02d.json'%len(requests[key]))).write_bytes(raw)
   self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Cache-Control','no-cache');self.end_headers()
   def emit(delta,finish=None,usage=None):
    x={'id':'chatcmpl-thinking','object':'chat.completion.chunk','created':int(time.time()),'model':req['model'],'choices':[{'index':0,'delta':delta,'finish_reason':finish}] if usage is None else []}
    if usage is not None:x['usage']=usage
    self.wfile.write(('data: '+json.dumps(x)+'\n\n').encode());self.wfile.flush()
   emit({'role':'assistant','content':''});emit({'content':'MOCK_OK'});emit({},'stop');emit({},usage={'prompt_tokens':1000,'completion_tokens':2,'total_tokens':1002});self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush()
  except Exception as ex:
   self.send_error(400,str(ex))
srv=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);port=srv.server_address[1];threading.Thread(target=srv.serve_forever,daemon=True).start()
try:
 for key,(provider,mid,default,expected) in cases.items():
  p=root/key;p.mkdir(mode=0o700);agent=p/'agent';agent.mkdir(mode=0o700);workspace=p/'workspace';workspace.mkdir();sessions=p/'sessions';sessions.mkdir()
  prov=copy.deepcopy(m['providers'][provider]);prov['baseUrl']=f'http://127.0.0.1:{port}/{key}/v1';prov['apiKey']='mock-only';prov['models']=[v for v in prov['models'] if v['id']==mid];settings=copy.deepcopy(s)
  # Retain actual global and per-model defaults; use explicit --model exactly as launcher.
  for n,v in [('models.json',{'providers':{provider:prov}}),('settings.json',settings)]: (agent/n).write_text(json.dumps(v))
  env=dict(os.environ,PI_CODING_AGENT_DIR=str(agent),PI_OFFLINE='1')
  with (p/'stderr.log').open('w') as err,(p/'rpc.jsonl').open('w') as log:
   proc=subprocess.Popen([str(pathlib.Path.home()/'.local/bin/pi'),'--mode','rpc','--offline','--model',provider+'/'+mid,'--no-skills','--no-context-files','--no-extensions','--session-dir',str(sessions)],env=env,cwd=workspace,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,text=True,bufsize=1)
   q=queue.Queue()
   def read():
    for line in proc.stdout:
     log.write(line);log.flush()
     try:q.put(json.loads(line))
     except ValueError:pass
    q.put(None)
   threading.Thread(target=read,daemon=True).start()
   counter=0
   def wait(pred):
    end=time.monotonic()+15
    while time.monotonic()<end:
     x=q.get(timeout=max(.01,end-time.monotonic()))
     if x is None:raise RuntimeError('Pi ended')
     if x.get('type')=='response' and x.get('success') is False:raise RuntimeError(str(x))
     if pred(x):return x
    raise TimeoutError()
   def cmd(t,**kw):
    nonlocal_dummy=None
    global counter
    counter+=1;ident=str(counter);proc.stdin.write(json.dumps(dict(type=t,id=ident,**kw))+'\n');proc.stdin.flush();return wait(lambda x:x.get('id')==ident and x.get('type')=='response').get('data')
   try:
    state=cmd('get_state');assert state['thinkingLevel']==default,(key,state['thinkingLevel'],default)
    levels=cmd('get_available_thinking_levels')['levels'];print(key,'startup',default,'levels',levels,flush=True)
    if expected is not None:assert set(levels)==set(expected),(key,levels,expected)
    else:expected={k:v for k,v in prov['models'][0]['thinkingLevelMap'].items() if v is not None}
    # Default request and a complete native cycle using the same session method as Shift+Tab.
    seen=[];level=default
    for i in range(len(levels)):
     assert cmd('get_state')['thinkingLevel']==level
     cmd('prompt',message='E04_THINKING '+level);wait(lambda x:x.get('type')=='agent_settled')
     assert len(requests[key])==i+1
     req=requests[key][-1];actual=req.get('reasoning_effort')
     # For unsupported/off without mapping, omission is the existing Q27 behavior.
     assert actual==expected.get(level),(key,level,actual,expected.get(level))
     seen.append(dict(level=level,reasoning_effort=actual,max_tokens=req['max_tokens']))
     level=cmd('cycle_thinking_level')['level']
    assert level==default and len(set(x['level'] for x in seen))==len(levels)
    (p/'summary.json').write_text(json.dumps(seen,indent=2)+'\n');print(key,'PASS',json.dumps(seen),flush=True)
   finally:
    proc.stdin.close()
    try:proc.wait(timeout=5)
    except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=5)
 print('THINKING_MOCK_PASS',sum(map(len,requests.values())),flush=True)
finally:srv.shutdown();srv.server_close()
