import json, pathlib, sys, hashlib
root=pathlib.Path(sys.argv[1]);dest=pathlib.Path(sys.argv[2])
dest.mkdir(mode=0o700,parents=True,exist_ok=False)
for case in ('cli-flash','cli-inkling','ide-flash','ide-inkling'):
 p=root/case; q=dest/case; q.mkdir(mode=0o700)
 ws=q/'workspace';ws.mkdir(mode=0o700); prompts=q/'prompts';prompts.mkdir(mode=0o700)
 x=json.loads((p/'expected.json').read_text())
 for name in ('first.txt',x['second']):
  (ws/name).write_bytes((p/'workspace'/name).read_bytes())
 body=(p/'workspace/long.txt').read_text()
 # Initial useful input test. Marker values occur only within the body; do not provide expected answer separately.
 start='This is a synthetic engineering session. Do not summarize the following reference. Preserve its three marker strings exactly. Without tools, reply with a JSON object with keys BEGIN, MIDDLE, END containing the exact corresponding marker strings. Retain them for later tasks.\n\n'+body
 chain='Use read to read ./first.txt. Its contents specify the name of the next file. Only after receiving the first tool result, read that named file. Do not guess its name or value. '
 if case.startswith('ide-'):chain+='After the second read, call vscode_get_editor_state to inspect the current workspace. '
 chain+='Return a JSON object with keys BEGIN, MIDDLE, END (the three original reference markers) and VALUE (the exact second file value).'
 recent='RECENT_'+hashlib.sha256((case+'|'+x['final']+'|independent-recent').encode()).hexdigest()[:20]
 pressure='Treat the following as a new independent recent engineering record. Keep its final marker exactly. Reply only with that marker, without tools.\n'+(' recent'*12500)+'\n'+recent
 after='Using the conversation history and any checkpoint summary, return the exact four original reference values (BEGIN, MIDDLE, END, VALUE) and the recent record marker RECENT. Do not read files again.'
 for name,text in [('01-start.txt',start),('02-chain.txt',chain),('03-pressure.txt',pressure),('04-after.txt',after)]:(prompts/name).write_text(text)
 expected=dict(model=x['model'],contextWindow=262144,maxTokens=x['maxTokens'],compaction_threshold=x['threshold'],markers=dict(zip(('BEGIN','MIDDLE','END'),x['markers'])),value=x['final'],recent=recent,first=x['first'],second=x['second'],fixture_chars=len(body),pressure_chars=len(pressure),notes='Initial and pressure sizes are calibration candidates, not measured tokens. Use actual provider usage and approved guard, do not start automatically.')
 (q/'expected.json').write_text(json.dumps(expected,indent=2)+'\n')
 assert body in start and all(m in start for m in x['markers'])
 assert x['second'] not in chain and x['final'] not in chain
 assert len(set(x['markers']))==3
 assert all(v not in after for v in x['markers']+[x['final']])
 assert (ws/'first.txt').read_text()==f"next={x['second']}\n"
 assert (ws/x['second']).read_text().strip()==x['final']
 print(case,'FIXTURE_PREPARED',len(start),len(pressure))
print('LIVE_FIXTURE_OFFLINE=PASS')
