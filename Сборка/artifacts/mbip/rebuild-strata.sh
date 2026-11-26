#!/usr/bin/env bash
# Clean reconstruction only. Current llm already has these components.
set -euo pipefail
umask 022
bundle=$(cd -- "$(dirname -- "$0")" && pwd)
mode="${1:?usage: rebuild-strata.sh fetch|install STAGING_DIRECTORY}"
stage=$(realpath -m -- "${2:?Provide staging directory}")
release=https://github.com/Niko1221/Strata/releases/download/v0.2.22
control=strata-control-0.1.69-linux-x86_64.tar.gz
engine=strata-engine-0.1.69-linux-x86_64-cuda-cuda13.tar.gz
file=Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf
hf=https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF/resolve/5bc3e238d916f48a861bac2f8a1990a0e9b7e98d
root=/opt/mbip-strata/0.2.22
state=/var/lib/mbip-strata
weights=/srv/ai-test/mbip-strata-models
profile="$state/profile/strata-mbip-qwen36.json"
verify() {
    grep -F "  $1" "$bundle/SHA256SUMS.upstream" | sha256sum -c -
}
fetch() {
    local name=$1 url=$2
    if [[ ! -e "$name" ]]; then
        curl -fsSL --proto '=https' --connect-timeout 20 --retry 5 --speed-time 90 --speed-limit 65536 \
            --continue-at - --output "$name.part" "$url/$name"
        grep -F "  $name" "$bundle/SHA256SUMS.upstream" | sed 's/$/.part/' | sha256sum -c -
        mv -T "$name.part" "$name"
    else
        verify "$name"
    fi
}

if [[ "$mode" == fetch ]]; then
    [[ $(id -u) != 0 ]]
    install -d -m 0700 "$stage"
    cd "$stage"
    fetch "$control" "$release"
    fetch "$engine" "$release"
    fetch "$file" "$hf"
    exit
fi
[[ "$mode" == install && $(id -u) == 0 ]]
cd "$stage"
sha256sum -c "$bundle/SHA256SUMS.upstream"
[[ ! -e "$root" && ! -e "$state" && ! -e "$weights/$file" && ! -e /etc/systemd/system/mbip-strata.service ]]
! getent passwd mbip-strata >/dev/null || exit 3
[[ -z $(ss -Hlt '( sport = :18081 )') ]]
install -d -o root -g root -m 0755 /opt/mbip-strata "$weights"
incoming=$(mktemp -d /opt/mbip-strata/.0.2.22.incoming.XXXXXXXX)
install -d -m 0755 "$incoming/control"
install -m 0644 "$control" "$engine" "$incoming/"
(cd "$incoming"; verify "$control"; verify "$engine")
tar -xzf "$incoming/$control" --no-same-owner -C "$incoming/control"
test -x "$incoming/control/bin/strata"
chmod 0755 "$incoming"
mv -T -- "$incoming" "$root"
useradd --system --user-group --no-create-home --home-dir "$state" --shell /usr/sbin/nologin mbip-strata
install -m 0644 -o root -g root "$file" "$weights/$file"
(cd "$weights"; verify "$file")
install -d -m 0750 -o mbip-strata -g mbip-strata "$state" "$state"/{components,data,cache,config,xdg,profile}
as_strata() {
    runuser -u mbip-strata -- env -u STRATA_UPDATE_TRUSTED_KEYS -u STRATA_INSTALL_TEST_TRUST \
      STRATA_INSTALL_DIR="$state/profile" STRATA_DATA_DIR="$state/data" STRATA_COMPONENTS_DIR="$state/components" \
      STRATA_REQUIRE_SIGNED_COMPONENTS=1 STRATA_FEED_MODELS=0 \
      XDG_CACHE_HOME="$state/cache" XDG_CONFIG_HOME="$state/config" XDG_DATA_HOME="$state/xdg" "$@"
}
cli="$root/control/bin/strata"
as_strata "$cli" --version
as_strata "$cli" update --check --no-engine --feed "$release" --components-dir "$state/components"
as_strata "$cli" components install-file "$root/$engine" --components-dir "$state/components"
as_strata "$cli" components engine --full --components-dir "$state/components"
systemd-run --quiet --wait --collect --pipe --uid=mbip-strata --gid=mbip-strata \
    -p PrivateNetwork=yes -p NoNewPrivileges=yes -p ProtectSystem=strict -p ProtectHome=yes \
    -p "ReadWritePaths=$state" -p "ReadOnlyPaths=$weights" \
    --setenv=STRATA_CONTROL_INSTALL=1 --setenv=STRATA_NEED_ENGINE=1 --setenv=STRATA_REQUIRE_SIGNED_COMPONENTS=1 \
    --setenv=STRATA_FEED_MODELS=0 --setenv=STRATA_INSTALL_DIR="$state/profile" --setenv=STRATA_COMPONENTS_DIR="$state/components" \
    --setenv=STRATA_DATA_DIR="$state/data" --setenv=XDG_DATA_HOME="$state/xdg" --setenv=XDG_CACHE_HOME="$state/cache" \
    --setenv=XDG_CONFIG_HOME="$state/config" "$root/control/python/bin/python3.12" -B "$root/control/setup.py" \
    --setup --no-start --family qwen36 --model UD-Q4_K_XL --gguf-dir "$weights" --data-dir "$state/data" \
    --backend cuda --cuda 13 --context 32768 --vision no --parallel 1 --port 18081 --yes

python3 -IB - "$state" "$weights/$file" "$profile" <<'PY'
from pathlib import Path
import json,os,pwd,sys
state, weights, target=map(Path,sys.argv[1:])
configs=list((state/"profile").glob("strata-qwen36-*.json"))
assert len(configs)==1
p=json.loads(configs[0].read_bytes()); a=p["args"]
assert p["arch"]=="qwen35moe" and a[a.index("--max-context")+1]=="32768"
assert Path(a[a.index("--native")+1]).resolve()==weights and not p.get("vision") and "--pack" not in a
p.update(model_name="qwen3.6-35b-a3b-ud-q4_k_xl",host="127.0.0.1",port=18081,parallel=1,lazy_load=True)
p.pop("api_key",None)
p.pop("api_keys",None)
with target.open("x") as stream: json.dump(p,stream,indent=2); stream.write("\n")
uid=pwd.getpwnam("mbip-strata"); os.chown(target,uid.pw_uid,uid.pw_gid); target.chmod(0o640)
PY
as_strata "$cli" serve --profile "$profile" --host 127.0.0.1 --port 18081 --parallel 1 --offline --plan
systemd-analyze verify "$bundle/systemd/mbip-strata.service"
install -o root -g root -m 0644 "$bundle/systemd/mbip-strata.service" /etc/systemd/system/mbip-strata.service
systemctl daemon-reload
