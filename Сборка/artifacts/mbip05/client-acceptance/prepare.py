import json, pathlib, sys, os, shutil, secrets
root=pathlib.Path(sys.argv[1]);w=pathlib.Path(sys.argv[2]);port=int(sys.argv[3])
models={'flash':'qwen3.8-flash-next-ud-q6_k_xl','inkling':'inkling-2-mini-sq-20'}
for surface in ('cli','ide'):
 for key,mid in models.items():
  p=root/f'{surface}-{key}';p.mkdir(mode=0o700)
  for n in ('agent','workspace','sessions','requests','extension','extensions','user/User'): (p/n).mkdir(mode=0o700,parents=True,exist_ok=True)
  m=json.loads((w/'e01p.DUc5G2Sr/pi-candidate/models.json').read_text());s=json.loads((w/'e01p.DUc5G2Sr/pi-candidate/settings.json').read_text())
  # Only one provider and model, no route to a real API. Keep all model metadata and settings.
  provider=m['providers']['ailab-strata'];provider['baseUrl']=f'http://127.0.0.1:{port}/{surface}-{key}/v1';provider['apiKey']='mock-only';provider['models']=[x for x in provider['models'] if x['id']==mid]
  m={'providers':{'ailab-strata':provider}}
  s.update(defaultProvider='ailab-strata',defaultModel=mid)
  for n,x in [('models.json',m),('settings.json',s)]: (p/'agent'/n).write_text(json.dumps(x,indent=2))
  nonce=secrets.token_hex(8)
  markers=[f'E02_{nonce}_{x}' for x in ('BEGIN','MIDDLE','END')]
  text=markers[0]+'\n'+' a'*115000+'\n'+markers[1]+'\n'+' a'*115000+'\n'+markers[2]
  (p/'workspace/long.txt').write_text(text)
  second=f'NEXT_{nonce}'; final=f'VALUE_{nonce}'
  (p/'workspace/first.txt').write_text(f'next={second}.txt\n')
  (p/'workspace'/f'{second}.txt').write_text(final+'\n')
  e=dict(case=p.name,model=mid,markers=markers,first='first.txt',second=f'{second}.txt',final=final,threshold=249856 if key=='flash' else 253952,maxTokens=8192 if key=='flash' else 4096,fixture_chars=len(text))
  (p/'expected.json').write_text(json.dumps(e,indent=2))
  if surface=='ide':
   orig=pathlib.Path.home()/'.vscode/extensions/pi0.pi-vscode-0.0.9'
   (p/'extensions'/orig.name).symlink_to(orig)
   (p/'user/User/settings.json').write_text(json.dumps({'pi-vscode.path':str(p/'pi-mock'),'extensions.autoUpdate':False,'extensions.autoCheckUpdates':False,'update.mode':'none','telemetry.telemetryLevel':'off','security.workspace.trust.enabled':False,'workbench.startupEditor':'none','workbench.tips.enabled':False}))
   (p/'extension/package.json').write_text(json.dumps({'name':'e02p-probe','publisher':'ailab-local','version':'0.0.1','engines':{'vscode':'^1.90.0'},'main':'./index.js','activationEvents':[]}))
   (p/'extension/index.js').write_text('exports.activate=()=>{};exports.deactivate=()=>{};\n')
   wrapper=f'''#!/bin/bash
set -euo pipefail
if [[ ${{1-}} == --version ]]; then exec "$HOME/.local/bin/pi" "$@"; fi
test -n "${{PI_VSCODE_BRIDGE_URL-}}"; test -n "${{PI_VSCODE_BRIDGE_TOKEN-}}"
export PI_CODING_AGENT_DIR='{p}/agent' PI_OFFLINE=1
exec "$HOME/.local/bin/pi" "$@" --offline --no-skills --no-context-files --no-extensions --approve --model 'ailab-strata/{mid}' --tools read,vscode_get_editor_state --session-dir '{p}/sessions' '@{p}/workspace/long.txt' 'E02_START'
'''
   (p/'pi-mock').write_text(wrapper);(p/'pi-mock').chmod(0o700)
print(root)
