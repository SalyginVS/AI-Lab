#!/usr/bin/python3
"""Prepare disposable VS Code Extension Host test of the installed Pi extension."""
import argparse,json,os,secrets,shlex
from pathlib import Path
a=argparse.ArgumentParser();a.add_argument("profile",choices=["flash","inkling"]);a.add_argument("directory",type=Path);args=a.parse_args()
model={"flash":"qwen3.8-flash-next-ud-q6_k_xl","inkling":"inkling-2-mini-sq-20"}[args.profile]
d=args.directory.resolve();d.mkdir(mode=0o700,parents=True,exist_ok=False)
for p in ("workspace","sessions","extension","extensions","user/User"): (d/p).mkdir(mode=0o700,parents=True,exist_ok=True)
original=Path.home()/".vscode/extensions/pi0.pi-vscode-0.0.9"
assert json.loads((original/"package.json").read_text())["version"]=="0.0.9"
(d/"extensions"/original.name).symlink_to(original)
marker="MBIP05_IDE_"+secrets.token_hex(8).upper()
(d/"workspace/probe.txt").write_text(marker+"\n")
(d/"expected.json").write_text(json.dumps(dict(marker=marker,model=model,root=str(d))))
pi=Path.home()/".local/bin/pi"
wrapper=d/"pi-probe"
wrapper.write_text("#!/bin/bash\nset -euo pipefail\n"
    "if [[ ${1-} == --version ]]; then exec "+shlex.quote(str(pi))+" \"$@\"; fi\n"
    "test -n \"${PI_VSCODE_BRIDGE_URL-}\"; test -n \"${PI_VSCODE_BRIDGE_TOKEN-}\"\n"
    "exec "+shlex.quote(str(pi))+" \"$@\" --offline --no-skills --no-context-files --no-extensions --approve --model "+shlex.quote("ailab-strata/"+model)+" --thinking low --tools read,vscode_get_editor_state --session-dir "+shlex.quote(str(d/"sessions"))+"\n")
wrapper.chmod(0o700)
(d/"user/User/settings.json").write_text(json.dumps({"pi-vscode.path":str(wrapper),"extensions.autoUpdate":False,"extensions.autoCheckUpdates":False,"update.mode":"none","telemetry.telemetryLevel":"off","security.workspace.trust.enabled":False,"workbench.startupEditor":"none","workbench.tips.enabled":False}))
(d/"extension/package.json").write_text(json.dumps({"name":"mbip05-probe","publisher":"ailab-local","version":"0.0.1","engines":{"vscode":"^1.90.0"},"main":"./index.js","activationEvents":[]}))
(d/"extension/index.js").write_text("exports.activate=()=>{};exports.deactivate=()=>{};\n")
