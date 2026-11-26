#!/usr/bin/python3
"""Add only the Strata provider, preserving the existing JSON bytes for rollback."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def add_provider(data, template):
    current = json.loads(data)
    existing = current["providers"]
    if "ailab-strata" in existing:
        if existing["ailab-strata"] != template["ailab-strata"]:
            raise ValueError("Existing ailab-strata differs. Review it before changing.")
        return data
    if "ailab-ollama" not in existing:
        raise ValueError("Accepted ailab-ollama provider missing.")
    text = data.decode("utf-8")
    anchor = re.search(r'(?m)^([ \t]*)"providers"\s*:\s*\{[ \t]*\n', text)
    if not anchor:
        raise ValueError("Unrecognized models.json layout. Review it before changing.")
    indent = anchor[1] + "    "
    cells = json.dumps(template, ensure_ascii=False, indent=4).splitlines()[1:-1]
    entry = "\n".join(indent + line[4:] for line in cells) + ",\n"
    changed = (text[:anchor.end()] + entry + text[anchor.end():]).encode()
    expected = {**current, "providers": {**existing, **template}}
    if json.loads(changed) != expected:
        raise ValueError("Addition changed existing content.")
    return changed


def apply(config_root, backup_root, launcher, template):
    model_file = config_root / "models.json"
    files = (model_file, config_root / "settings.json", launcher)
    if any(not f.is_file() or f.is_symlink() for f in files):
        raise ValueError("Expected regular Pi configuration and launcher files.")
    previous = model_file.read_bytes()
    updated = add_provider(previous, template)
    if previous == updated:
        print("PI_PROVIDER_NOOP",sha(previous))
        return
    backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    prefix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")
    backup = Path(tempfile.mkdtemp(dir=backup_root, prefix=prefix))
    manifest = {"files":{}, "models_deployed_sha256":sha(updated)}
    for f in files:
        data=f.read_bytes()
        copy=backup / f.name
        with copy.open("xb") as stream:
            stream.write(data)
        copy.chmod(0o600)
        manifest["files"][f.name]={"mode": oct(stat.S_IMODE(f.stat().st_mode)), "sha256": sha(data)}
    record=backup/"manifest.json"
    record.write_text(json.dumps(manifest, indent=2)+"\n")
    record.chmod(0o600)
    with tempfile.NamedTemporaryFile(dir=model_file.parent, prefix=".mbip03-", delete=False) as temp:
        temp.write(updated)
        pending=Path(temp.name)
    try:
        if model_file.read_bytes() != previous:
            raise ValueError("models.json changed after snapshot. Apply again after review.")
        pending.chmod(stat.S_IMODE(model_file.stat().st_mode))
        pending.replace(model_file)
    finally:
        pending.unlink(missing_ok=True)
    print("PI_PROVIDER_ADDED", manifest["models_deployed_sha256"], "backup", backup, "original", manifest["files"]["models.json"]["sha256"])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template",type=Path,default=Path(__file__).with_name("pi-provider.json"))
    args=parser.parse_args()
    home=Path.home()
    launcher=shutil.which("pi-q27")
    if not launcher:
        parser.error("pi-q27 not found")
    apply(home/".pi/agent",home/".local/state/mbip03/pi-backups",Path(launcher),json.loads(args.template.read_bytes()))


if __name__=="__main__":
    main()
