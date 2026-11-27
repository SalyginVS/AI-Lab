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
 import pexpect
 key='inkling';provider,mid,default,expected=cases[key];p=root/key;p.mkdir(mode=0o700);agent=p/'agent';agent.mkdir(mode=0o700);workspace=p/'workspace';workspace.mkdir();sessions=p/'sessions';sessions.mkdir()
 prov=copy.deepcopy(m['providers'][provider]);prov['baseUrl']=f'http://127.0.0.1:{port}/{key}/v1';prov['apiKey']='mock-only';prov['models']=[v for v in prov['models'] if v['id']==mid]
 for n,v in [('models.json',{'providers':{provider:prov}}),('settings.json',s)]: (agent/n).write_text(json.dumps(v))
 env=dict(os.environ,PI_CODING_AGENT_DIR=str(agent),PI_OFFLINE='1',TERM='xterm-256color')
 args=['--offline','--model',provider+'/'+mid,'--no-skills','--no-context-files','--no-extensions','--session-dir',str(sessions)]
 with (p/'tui.log').open('w') as log:
  child=pexpect.spawn(str(pathlib.Path.home()/'.local/bin/pi'),args,env=env,cwd=str(workspace),encoding='utf-8',dimensions=(35,120),timeout=12);child.logfile_read=log
  try:
   child.expect('max',timeout=12)
   child.send('E04_TUI_FIRST');child.send('\r');child.expect('MOCK_OK',timeout=12);time.sleep(.3)
   assert len(requests[key])==1 and requests[key][0].get('reasoning_effort')=='max',requests[key]
   child.send('\x1b[Z');child.expect('Thinking level: off',timeout=12);child.send('E04_TUI_SECOND');child.send('\r');child.expect('MOCK_OK',timeout=12);time.sleep(.3)
   assert len(requests[key])==2 and requests[key][1].get('reasoning_effort')=='none',requests[key]
   print('SHIFT_TAB_TUI_MOCK_PASS max -> off; wire max -> none',flush=True)
  finally:
   child.close(force=True)
finally:srv.shutdown();srv.server_close()
