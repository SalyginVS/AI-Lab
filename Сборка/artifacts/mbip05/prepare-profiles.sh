#!/usr/bin/env bash
set -euo pipefail
umask 027
test "$(id -u)" = 0
state=/var/lib/mbip-strata
control=/opt/mbip-strata/0.2.22/control
base=$(realpath -- "${1:?usage: prepare-profiles.sh STAGE INK_STAGE}")
ink_stage=$(realpath -- "${2:?provide INK_STAGE}")
q=/srv/mbip05-models/flash-q6
i=/srv/ai-test/mbip-strata-models/inkling-sq20
data="$state/data"
stage="$state/mbip05-setup"
test "$(systemctl is-active ollama)" = active
test "$(systemctl is-active mbip-strata || true)" = inactive
test -z "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits)"
grep -q '^EXIT=0$' "$base/control/q6.log"
grep -q '^EXIT=0$' "$base/control/ink.log"
grep -q '^EXIT=0$' "$base/control/pack-q6.log"
grep -q '^MTP_PACK=PASS$' "$base/control/pack-mtp.log"
test ! -e "$q"; test ! -e "$i"; test ! -e "$data/packs/unsloth-ud-q6_k_xl"; test ! -e "$data/mtp"; test ! -e "$stage"
install -d -o root -g mbip-strata -m 0750 /srv/mbip05-models "$q" "$i"
# Hard links preserve staged source paths and allocate no second copy of weights.
for f in "$base"/q6/*.gguf; do
  ln -- "$f" "$q/"
  chgrp mbip-strata "$f"
  chmod 0640 "$f"
done
for n in Inkling-2-Mini-SQ-20.strata tokenizer.json chat_template.jinja; do
  f="$ink_stage/$n"
  ln -- "$f" "$i/"
  chgrp mbip-strata "$f"
  chmod 0640 "$f"
done
test "$(find "$q" -maxdepth 1 -name '*.gguf' -type f -links +1 | wc -l)" = 6
test "$(stat -c %i "$i/Inkling-2-Mini-SQ-20.strata")" = "$(stat -c %i "$ink_stage/Inkling-2-Mini-SQ-20.strata")"
# Link derived files; preserve source staging and avoid redundant disk allocations.
link_tree() {
  local src="$1" dst="$2"
  install -d -o mbip-strata -g mbip-strata -m 0750 "$dst"
  while IFS= read -r -d '' rel; do
    install -d -o mbip-strata -g mbip-strata -m 0750 "$dst/$rel"
  done < <(cd "$src"; find . -mindepth 1 -type d -printf '%P\0')
  while IFS= read -r -d '' rel; do
    ln -- "$src/$rel" "$dst/$rel"
    chgrp mbip-strata "$src/$rel"
    chmod 0640 "$src/$rel"
  done < <(cd "$src"; find . -type f ! -name '.mtp_fetch.lock' -printf '%P\0')
}
link_tree "$base/q6-pack" "$data/packs/unsloth-ud-q6_k_xl"
link_tree "$base/mtp" "$data/mtp"
# Keep the generated draft vocab separate so setup can update it normally.
install -o mbip-strata -g mbip-strata -m 0640 "$control/data/draft_vocab_cyrillic.bin" "$data/mtp/rt/draft_vocab.bin"
install -d -o mbip-strata -g mbip-strata -m 0750 "$stage" "$stage"/{profile,cache,config,xdg}
for f in "$q"/*.gguf "$i/Inkling-2-Mini-SQ-20.strata"; do runuser -u mbip-strata -- test -r "$f"; done
echo STORAGE_LINKS=PASS
setup() {
 systemd-run --quiet --wait --collect --pipe --uid=mbip-strata --gid=mbip-strata \
 -p PrivateNetwork=yes -p NoNewPrivileges=yes -p ProtectSystem=strict -p ProtectHome=yes \
 -p "ReadWritePaths=$state" -p "ReadOnlyPaths=$q $i" \
 --setenv=STRATA_CONTROL_INSTALL=1 --setenv=STRATA_NEED_ENGINE=1 --setenv=STRATA_REQUIRE_SIGNED_COMPONENTS=1 \
 --setenv=STRATA_FEED_MODELS=0 --setenv=STRATA_NO_ACQUIRE=1 --setenv=STRATA_INSTALL_DIR="$stage/profile" \
 --setenv=STRATA_COMPONENTS_DIR="$state/components" --setenv=STRATA_DATA_DIR="$data" \
 --setenv=XDG_DATA_HOME="$stage/xdg" --setenv=XDG_CACHE_HOME="$stage/cache" --setenv=XDG_CONFIG_HOME="$stage/config" \
 "$control/python/bin/python3.12" -B "$control/setup.py" --setup --no-start --data-dir "$data" \
 --backend cuda --cuda 13 --vision no --parallel 1 --host 127.0.0.1 --port 18081 --yes "$@"
}
setup --family inkling-2-mini --model SQ-20 --gguf-dir "$i" --context 32768
echo INK_SETUP=PASS
setup --family unsloth --model UD-Q6_K_XL --gguf-dir "$q" --context 8192 --resident-budget-gib 40 --mtp on --draft-vocab cyrillic
echo FLASH_SETUP=PASS
python3 -IB - "$stage/profile" "$state/profile" "$q" "$i" <<'PY'
import json,sys,os,pwd
from pathlib import Path
src,dst,q,i=map(Path,sys.argv[1:])
print("generated",[(p.name) for p in src.glob("strata-*.json")])
for name, expected, source, ctx in (
 ("inkling", "inkling-2-mini-sq-20",i/"Inkling-2-Mini-SQ-20.strata",32768),
 ("flash","qwen3.8-flash-next-ud-q6_k_xl",q/"Qwen3.8-Flash-Next-UD-Q6_K_XL-00001-of-00006.gguf",8192)):
 matches=[]
 for p in src.glob("strata-*.json"):
  x=json.loads(p.read_text())
  a=x.get("args",[])
  if "--native" in a and Path(a[a.index("--native")+1])==source: matches.append(x)
 assert len(matches)==1,(name,len(matches))
 x=matches[0]; a=x["args"]
 assert a[a.index("--max-context")+1]==str(ctx)
 assert not x.get("vision") and "--vision" not in a
 if name=="flash":
  assert a[a.index("--resident-budget-gib")+1]=="40"
  assert "--mtp" in a and "--pack" in a
  assert not (Path(a[a.index("--pack")+1])/"experts.bin").exists()
 x.update(model_name=expected,host="127.0.0.1",port=18081,parallel=1,lazy_load=True,log=str(dst/f"mbip05-{name}.log"))
 for k in ("api_key","api_keys"): x.pop(k,None)
 p=dst/f"strata-mbip-{name}.json"
 with p.open("x") as f:json.dump(x,f,indent=2);f.write("\n")
 os.chown(p,0,pwd.getpwnam("mbip-strata").pw_gid);p.chmod(0o640)
 print("PROFILE",name,x["exe"],x.get("arch"),x["args"])
PY
echo MBIP05_PROFILES=PASS
