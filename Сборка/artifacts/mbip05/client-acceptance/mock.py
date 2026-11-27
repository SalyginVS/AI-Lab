import http.server,json,pathlib,sys,threading,time,hashlib,traceback
root=pathlib.Path(sys.argv[1]);port=int(sys.argv[2]); lock=threading.Lock()
def txt(m):
 c=m.get('content') or ''
 return c if isinstance(c,str) else '\n'.join(x.get('text','') for x in c if isinstance(x,dict))
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_POST(self):
  p=None
  try:
   case,_,endpoint=self.path.strip('/').split('/',2);p=root/case
   assert case in ('cli-flash','cli-inkling','ide-flash','ide-inkling') and endpoint=='chat/completions'
   ex=json.loads((p/'expected.json').read_text());raw=self.rfile.read(int(self.headers['Content-Length']));req=json.loads(raw)
   with lock:
    n=len(list((p/'requests').glob('*.json')))+1
    (p/'requests'/f'{n:03}.json').write_bytes(raw)
   assert req['model']==ex['model'],req['model']
   assert req.get('stream') is True
   assert 0<req['max_tokens']<=ex['maxTokens'],req.get('max_tokens')
   ms=req['messages'];us=[txt(m) for m in ms if m['role']=='user'];last=us[-1];alltext='\n'.join(txt(m) for m in ms)
   fixture=(p/'workspace/long.txt').read_text()
   tools=[x['function']['name'] for x in req.get('tools',[])]
   calls=[x for m in ms for x in m.get('tool_calls',[])]
   results={m.get('tool_call_id'):txt(m) for m in ms if m['role']=='tool'}
   call=None; summary=False; phase=''; inputn=230700; result=''
   if '<conversation>' in last or '# Conversation\n' in last and '# Instructions' in last:
    phase='summary';summary=True
    assert all(x in alltext for x in ex['markers']), 'summary lost markers'
    assert fixture in alltext, 'summary lost fixture'
    result='E02_CHECKPOINT '+ ' '.join(ex['markers'])+' '+ex['final'];inputn=ex['threshold']-500
   elif 'E02_AFTER_COMPACT' in last:
    phase='after';assert 'E02_CHECKPOINT' in alltext and all(x in alltext for x in ex['markers'])
    assert fixture not in alltext,'old history was not compacted'
    result='E02_AFTER_OK';inputn=1000
   else:
    assert fixture in alltext, 'full long fixture missing from outbound request'
    assert all(x in alltext for x in ex['markers'])
    if 'E02_PRESSURE' in last:
     phase='pressure';result='E02_PRESSURE_OK';inputn=ex['threshold']+100
    elif 'E02_CHAIN' in last:
     inputn=230700
     if 'e02_first' not in results:
      phase='first';assert 'read' in tools;call=('e02_first','read',{'path':ex['first']})
     elif 'e02_second' not in results:
      phase='second';assert ex['second'] in results['e02_first'];call=('e02_second','read',{'path':ex['second']})
     elif case.startswith('ide-') and 'e02_bridge' not in results:
      phase='bridge';assert ex['final'] in results['e02_second'];assert 'vscode_get_editor_state' in tools;call=('e02_bridge','vscode_get_editor_state',{})
     else:
      phase='chain-final';assert ex['second'] in results['e02_first'] and ex['final'] in results['e02_second']
      if case.startswith('ide-'):assert str(p/'workspace') in results['e02_bridge']
      result='E02_CHAIN_OK '+ex['final']
    elif 'E02_START' in last:
     phase='start';result='E02_START_OK'
    else:raise AssertionError('unrecognized request '+last[:100])
   output=20
   assert req['max_tokens']>=output, 'output budget starvation'
   record={'request':n,'phase':phase,'input_usage_synthetic':inputn,'max_tokens':req['max_tokens'],'reasoning_effort':req.get('reasoning_effort'),'chars':len(alltext),'payload_sha256':hashlib.sha256(raw).hexdigest(),'fixture_exact':fixture in alltext,'tool_result_ids':list(results),'call':call}
   with lock:
    with (p/'mock-events.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
   self.send_response(200);self.send_header('Content-Type','text/event-stream');self.send_header('Cache-Control','no-cache');self.end_headers()
   def emit(delta,finish=None,usage=None):
    x={'id':f'chatcmpl-e02-{n}','object':'chat.completion.chunk','created':int(time.time()),'model':ex['model'],'choices':[{'index':0,'delta':delta,'finish_reason':finish}] if usage is None else []}
    if usage is not None:x['usage']=usage
    self.wfile.write(('data: '+json.dumps(x)+'\n\n').encode());self.wfile.flush()
   emit({'role':'assistant','content':''})
   if call:
    cid,name,args=call;emit({'tool_calls':[{'index':0,'id':cid,'type':'function','function':{'name':name,'arguments':json.dumps(args)}}]});emit({},'tool_calls')
   else:
    emit({'content':result});emit({},'stop')
   emit({},usage={'prompt_tokens':inputn,'completion_tokens':output,'total_tokens':inputn+output})
   self.wfile.write(b'data: [DONE]\n\n');self.wfile.flush()
  except Exception as e:
   if p and p.is_dir():
    with (p/'mock-errors.log').open('a') as f:f.write(traceback.format_exc()+'\n')
   try:self.send_error(400,str(e))
   except:pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',port),Handler);print('MOCK_READY',flush=True);server.serve_forever()
