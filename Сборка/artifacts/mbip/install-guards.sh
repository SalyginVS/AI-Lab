#!/usr/bin/env bash
set -euo pipefail
umask 077
cd -- "$(dirname -- "$0")"
[[ $(id -u) == 0 ]]
exec 9>/run/lock/mbip-strata-smoke.lock
flock -n 9
sha256sum -c SHA256SUMS.live
for service in ollama llm-gateway rag-mcp; do systemctl is-active --quiet "$service.service"; done
if systemctl is-active --quiet mbip-strata.service; then echo 'Strata is running'; exit 2; fi
profile=/var/lib/mbip-strata/profile/strata-mbip-qwen36.json
printf '%s  %s\n' ae984c8874a318155b3279e59b95ef3dbef57ec45b3d5d0f1ff6501b27c4e570 "$profile" | sha256sum -c -
runuser -u mbip-strata -- test -r /srv/ai-test/mbip-strata-models/Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf
printf '%s\n' 'PROFILE_EFFECTIVE'
python3 -IB - "$profile" <<'PY'
import json,sys
d=json.load(open(sys.argv[1])); a=d["args"]
print(json.dumps({"model":d["model_name"],"arch":d["arch"],"host":d["host"],"port":d["port"],"parallel":d["parallel"],"context":a[a.index("--max-context")+1],"mtp":a[a.index("--mtp")+1],"api_key_configured":bool(d.get("api_key") or d.get("api_keys"))}))
PY

units=(ollama.service llm-gateway.service rag-mcp.service mbip-strata.service)
target=/usr/local/sbin/mbip-backend
snap=$(mktemp -d /var/backups/mbip03-guard.XXXXXXXX)
added=()
done_install=false
cleanup() {
    if [[ "$done_install" == false ]]; then
        for path in "${added[@]}"; do rm -f -- "$path"; done
        if ((${#added[@]})); then systemctl daemon-reload; fi
    fi
}
trap cleanup EXIT
trap 'printf "INSTALL_ERROR line=%s rc=%s\n" "$LINENO" "$?" >&2' ERR

if [[ -e "$target" ]]; then cmp -s mbip-backend "$target"; fi
for service in "${units[@]}"; do
    d="/etc/systemd/system/$service.d/95-mbip-mode-guard.conf"
    if [[ -e "$d" ]]; then cmp -s "systemd/$service.d/95-mbip-mode-guard.conf" "$d"; fi
    f="/etc/systemd/system/$service"
    cp -p -- "$f" "$snap/$service"
    stat -c '%a %U:%G %n' "$f"
    sha256sum "$f"
done
cp -p -- "$profile" "$snap/"
stat -c '%a %U:%G %n' "$profile"
printf 'SNAPSHOT_DIR=%s\n' "$snap"

if [[ ! -e "$target" ]]; then
    install -o root -g root -m 0755 mbip-backend "$target"
    added+=("$target")
fi
for service in "${units[@]}"; do
    d="/etc/systemd/system/$service.d/95-mbip-mode-guard.conf"
    if [[ ! -e "$d" ]]; then
        install -D -o root -g root -m 0644 "systemd/$service.d/95-mbip-mode-guard.conf" "$d"
        added+=("$d")
    fi
    sha256sum "$d"
done
systemd-analyze --man=no verify "${units[@]/#//etc/systemd/system/}"
systemctl daemon-reload
sha256sum "$target"
for service in "${units[@]}"; do
    systemctl show "$service" --no-pager -p Id,ActiveState,UnitFileState,DropInPaths
done
done_install=true
printf 'MBIP03_GUARDS_INSTALLED=PASS\n'
