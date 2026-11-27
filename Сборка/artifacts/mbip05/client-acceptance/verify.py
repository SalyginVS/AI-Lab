import pathlib,json,hashlib,sys
root=pathlib.Path(sys.argv[1])
def text(m):
 c=m.get('content') or ''
 return c if isinstance(c,str) else '\n'.join(x.get('text','') for x in c if isinstance(x,dict))
def load(p):return json.loads(p.read_text())
def lines(p):return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
results=[]
for surface in ('cli','ide'):
 for key in ('flash','inkling'):
  p=root/f'{surface}-{key}';ex=load(p/'expected.json');fixture=(p/'workspace/long.txt').read_text();recent=' recent'*12500
  assert not (p/'mock-errors.log').exists()
  rows=lines(p/'mock-events.jsonl');phases=['start','first','second']+(['bridge'] if surface=='ide' else [])+['chain-final','pressure','summary','after']
  assert [x['phase'] for x in rows]==phases,(p.name,rows)
  assert len(list((p/'requests').glob('*.json')))==len(rows)
  for e in rows:
   raw=(p/'requests'/f"{e['request']:03}.json").read_bytes();assert hashlib.sha256(raw).hexdigest()==e['payload_sha256']
   r=json.loads(raw);assert r['model']==ex['model'] and r['reasoning_effort']=='low'
   assert 20<=r['max_tokens']<=ex['maxTokens'] and e['input_usage_synthetic']+r['max_tokens']<=262144
   msgs=r['messages'];alltext='\n'.join(text(m) for m in msgs)
   if e['phase']!='after':assert fixture in alltext
   if e['phase'] in ('pressure','after'):assert recent in alltext,(p.name,e['phase'],'recent tail missing')
   if e['phase']=='after':assert fixture not in alltext and all(x in alltext for x in ex['markers']) and 'E02_CHECKPOINT' in alltext and ex['final'] in alltext
   if e['phase'] in ('start','first','second','bridge','chain-final','summary','after'):assert r['max_tokens']==ex['maxTokens']
  fs=list((p/'sessions').rglob('*.jsonl'));assert len(fs)==1
  entries=lines(fs[0]);msgs=[e['message'] for e in entries if e['type']=='message']
  a=[m for m in msgs if m['role']=='assistant'];assert all(m.get('stopReason') in ('toolUse','stop') and m.get('model')==ex['model'] and m.get('provider')=='ailab-strata' for m in a)
  assert any(fixture in text(m) for m in msgs if m['role']=='user')
  assert any(recent in text(m) for m in msgs if m['role']=='user')
  calls=[c for m in a for c in m.get('content',[]) if c.get('type')=='toolCall'];tr=[m for m in msgs if m['role']=='toolResult'];assert len(calls)==len(tr)==(3 if surface=='ide' else 2)
  assert len({c['id'] for c in calls})==len(calls)
  assert all(not m.get('isError') and any(c['id']==m['toolCallId'] and c['name']==m['toolName'] for c in calls) for m in tr)
  assert calls[0]['name']==calls[1]['name']=='read' and calls[0]['arguments']['path']==ex['first'] and calls[1]['arguments']['path']==ex['second']
  assert ex['second'] in text(tr[0]) and ex['final'] in text(tr[1])
  if surface=='ide':assert calls[2]['name']=='vscode_get_editor_state' and str(p/'workspace') in text(tr[2]);assert any(e['event']=='IDE_MOCK_PASS' for e in lines(p/'ide-events.jsonl'))
  assert 'E02_CHAIN_OK '+ex['final'] in [text(m) for m in a]
  cs=[e for e in entries if e['type']=='compaction'];assert len(cs)==1 and all(x in cs[0]['summary'] for x in ex['markers']) and ex['final'] in cs[0]['summary']
  assert cs[0]['firstKeptEntryId'] in {e.get('id') for e in entries}
  assert cs[0]['tokensBefore']>ex['threshold']
  assert text(a[-1])=='E02_AFTER_OK'
  if surface=='cli':
   ev=lines(p/'rpc.jsonl');resume=lines(p/'rpc-resume.jsonl')
   assert any(e.get('type')=='compaction_end' and e.get('reason')=='threshold' and not e.get('errorMessage') for e in ev), [e for e in ev if 'compaction' in e.get('type','')]
   s1=next(e['data'] for e in ev if e.get('id')=='state');s2=next(e['data'] for e in resume if e.get('id')=='state');assert s1['sessionId']==s2['sessionId'] and s1['sessionFile']==s2['sessionFile']
  record=dict(case=p.name,requests=len(rows),fixture_chars=len(fixture),pressure_payload_chars=next(x['chars'] for x in rows if x['phase']=='pressure'),pressure_output_cap=next(x['max_tokens'] for x in rows if x['phase']=='pressure'),tokens_before_compaction=cs[0]['tokensBefore'],summary_output_cap=next(x['max_tokens'] for x in rows if x['phase']=='summary'),recent_tail_chars=len(recent),correlated_tools=len(calls),session_entries=len(entries),persisted_file=str(fs[0].relative_to(root)),result='MOCK_PASS')
  results.append(record);print(json.dumps(record))
(root/'verification.json').write_text(json.dumps(results,indent=2)+'\n')
print('E02P_PRIMARY_VERIFICATION=PASS')
