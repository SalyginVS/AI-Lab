import json,pathlib,sys,subprocess,os,time,queue,threading
p=pathlib.Path(sys.argv[1]);ex=json.loads((p/'expected.json').read_text());env=dict(os.environ,PI_CODING_AGENT_DIR=str(p/'agent'),PI_OFFLINE='1')
cmd=[str(pathlib.Path.home()/'.local/bin/pi'),'--mode','rpc','--offline','--no-skills','--no-context-files','--no-extensions','--approve','--model','ailab-strata/'+ex['model'],'--tools','read','--session-dir',str(p/'sessions')]
def run(resume=False):
 c=cmd+(['--continue'] if resume else [])
 err=(p/('rpc-resume.stderr' if resume else 'rpc.stderr')).open('w')
 proc=subprocess.Popen(c,env=env,cwd=p/'workspace',stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,text=True,bufsize=1)
 q=queue.Queue()
 def reader():
  with (p/('rpc-resume.jsonl' if resume else 'rpc.jsonl')).open('w') as f:
   for l in proc.stdout:
    f.write(l);f.flush()
    try:q.put(json.loads(l))
    except:pass
  q.put(None)
 threading.Thread(target=reader,daemon=True).start()
 def send(x):
  proc.stdin.write(json.dumps(x)+'\n');proc.stdin.flush()
 def wait(pred):
  deadline=time.monotonic()+60
  while time.monotonic()<deadline:
   x=q.get(timeout=max(.01,deadline-time.monotonic()))
   if x is None:raise RuntimeError('RPC ended '+str(proc.poll()))
   if x.get('type')=='response' and x.get('success') is False:raise RuntimeError(str(x))
   if pred(x):return x
  raise TimeoutError()
 def prompt(text):
  send({'type':'prompt','message':text});wait(lambda x:x.get('type')=='agent_settled')
 try:
  send({'id':'state','type':'get_state'});state=wait(lambda x:x.get('id')=='state')['data'];assert state['model']['contextWindow']==262144 and state['model']['maxTokens']==ex['maxTokens'] and state['thinkingLevel']=='low'
  if resume:prompt('E02_AFTER_COMPACT')
  else:
   prompt('E02_START\n'+(p/'workspace/long.txt').read_text())
   prompt('E02_CHAIN')
   prompt('E02_PRESSURE\n'+(' recent'*12500))
  send({'id':'end','type':'get_state'});state=wait(lambda x:x.get('id')=='end')['data'];print(p.name,'resume',resume,'session',state['sessionFile'],'messages',state['messageCount'],flush=True)
 finally:
  proc.stdin.close()
  try:proc.wait(timeout=5)
  except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=5)
  err.close()
run();run(True)
