#!/usr/bin/env bash
set -euo pipefail
umask 077
state=/var/lib/mbip-strata
control=/opt/mbip-strata/0.2.22/control
archive=$(realpath -- "${1:?usage: install-ink-engine.sh SIGNED_ARCHIVE}")
test "$(id -u)" = 0
test "$(systemctl is-active mbip-strata.service || true)" = inactive
test "$(systemctl is-active ollama.service)" = active
test -z "$(nvidia-smi --query-compute-apps=pid --format=csv,noheader,nounits)"
printf '%s  %s\n' 866798f92e2b0e543ab47dc6212d8ddded7e321100db4fdcb732ff92813b5f3e "$archive" | sha256sum -c -
printf '%s  %s\n' ae984c8874a318155b3279e59b95ef3dbef57ec45b3d5d0f1ff6501b27c4e570 "$state/profile/strata-mbip-qwen36.json" | sha256sum -c -
backup=$(mktemp -d /var/backups/mbip05-v2.XXXXXXXX)
chmod 0700 "$backup"
tar -C / -czf "$backup/baseline.tar.gz" \
 usr/local/sbin/mbip-backend usr/local/libexec/ailab/postboot-check.sh \
 etc/systemd/system/mbip-strata.service etc/systemd/system/mbip-strata.service.d \
 etc/systemd/system/ollama.service etc/systemd/system/ollama.service.d \
 etc/systemd/system/llm-gateway.service etc/systemd/system/llm-gateway.service.d \
 etc/systemd/system/rag-mcp.service etc/systemd/system/rag-mcp.service.d \
 etc/systemd/system/ailab-postboot-check.service etc/systemd/system/ailab-gpu-power.service \
 var/lib/mbip-strata/profile var/lib/mbip-strata/config var/lib/mbip-strata/data \
 var/lib/mbip-strata/components/engine/0.1.69-linux-x86_64-cuda-cuda13/engine-component.json
(cd "$backup"; sha256sum baseline.tar.gz > SHA256SUMS; sha256sum -c SHA256SUMS; tar -tzf baseline.tar.gz > inventory.txt)
for u in ollama llm-gateway rag-mcp mbip-strata ailab-postboot-check ailab-gpu-power; do
 printf '%s ' "$u"; systemctl is-enabled "$u" || true
done > "$backup/unit-enablement.txt"
echo "SERVER_ROLLBACK=$backup"
parent="$state/components/shapes/inkling2/engine"
target="$parent/0.1.69-linux-x86_64-cuda-cuda13"
test ! -e "$target"
install -d -o mbip-strata -g mbip-strata -m 0750 "$state/components/shapes" "$state/components/shapes/inkling2" "$parent"
stage=$(mktemp -d "$parent/.mbip05-incoming.XXXXXXXX")
tar -xzf "$archive" --no-same-owner -C "$stage"
chown -R mbip-strata:mbip-strata "$stage"
chmod 0750 "$stage"
as_strata() {
 runuser -u mbip-strata -- env -u STRATA_UPDATE_TRUSTED_KEYS -u STRATA_INSTALL_TEST_TRUST \
 STRATA_REQUIRE_SIGNED_COMPONENTS=1 STRATA_FEED_MODELS=0 \
 STRATA_INSTALL_DIR="$state/profile" STRATA_DATA_DIR="$state/data" STRATA_COMPONENTS_DIR="$state/components" \
 XDG_CACHE_HOME="$state/cache" XDG_CONFIG_HOME="$state/config" XDG_DATA_HOME="$state/xdg" \
 PYTHONPATH="$control" "$@"
}
as_strata "$control/python/bin/python3.12" -B - "$stage" <<'PY'
from pathlib import Path
import sys
from strata_control import engine_component as ec, signing, shape_engine
p=Path(sys.argv[1])
c=ec.read_manifest(p,"strata-inkling")
assert c.version=="0.1.69" and c.platform=="linux-x86_64" and c.backend=="cuda" and c.variant=="cuda13"
assert signing.ensure_component_verifier()
assert ec.verify_signature(c)=="verified"
ec.verify(c,full=True)
ok,msg=shape_engine._test_start(p/"strata-inkling",shape="inkling2")
assert ok,msg
print("INKLING_ENGINE_SIGNATURE_AND_FILES=PASS")
print("INKLING_ENGINE_VERSION_TEST="+msg)
PY
mv -T "$stage" "$target"
as_strata "$control/python/bin/python3.12" -B - "$state/components" <<'PY'
from pathlib import Path
import sys
from strata_control import shape_engine
c=shape_engine.find("inkling2",Path(sys.argv[1]),backend="cuda",full=True)
assert c.version=="0.1.69" and c.variant=="cuda13"
print("INKLING_ENGINE_RESOLUTION=PASS", c.root)
PY
systemctl is-active ollama llm-gateway rag-mcp
test "$(systemctl is-active mbip-strata.service || true)" = inactive
echo INKLING_ENGINE_INSTALL=PASS
