#!/bin/bash
# Runs exclusively in a fresh private staging root, never on the active manager.
set -euo pipefail
umask 077
S="$(realpath -- "$1")"
R="$(mktemp -d "$HOME/mbip05-downloads/control/context/e03p-systemd.XXXXXXXX")"
echo "OFFLINE_ROOT=$R"
U="$R/etc/systemd/system"
mkdir -p "$U" "$R/etc/tmpfiles.d" "$R/run" "$R/etc/mbip05/profiles" "$R/usr/local/libexec/ailab"
for u in mbip-strata ollama llm-gateway rag-mcp ailab-postboot-check ailab-gpu-power; do
  cp -a "/etc/systemd/system/$u.service" "$U/"
  if [[ -d "/etc/systemd/system/$u.service.d" ]]; then cp -a "/etc/systemd/system/$u.service.d" "$U/"; fi
done
for u in default.target multi-user.target; do printf '[Unit]\nDescription=Offline fixture %s\n' "$u" > "$U/$u"; done
ctl(){ systemctl --root="$R" "$@"; }
links(){ find "$U" -type l -printf '%P -> %l\n' | sort; }
for u in ollama llm-gateway rag-mcp ailab-postboot-check ailab-gpu-power; do ctl enable "$u.service"; done
links > "$R/links.before"
cp -a "$U" "$R/original-systemd"
test "$(ctl is-enabled mbip-strata.service || :)" = static
mkdir -p "$U/mbip-strata.service.d" "$U/ailab-postboot-check.service.d"
cp "$S/systemd/mbip-strata.service.d/97-mbip05-boot.conf" "$U/mbip-strata.service.d/"
cp "$S/systemd/ailab-postboot-check.service.d/95-mbip05-mode.conf" "$U/ailab-postboot-check.service.d/"
cp "$S/tmpfiles/mbip05.conf" "$R/etc/tmpfiles.d/"
cp "$S/profiles/"*.json "$R/etc/mbip05/profiles/"
cp "$S/mbip05-postboot-readiness" "$R/usr/local/libexec/ailab/"
ctl enable mbip-strata.service
ctl disable ollama.service llm-gateway.service rag-mcp.service
test "$(ctl is-enabled mbip-strata.service)" = enabled
for u in ollama llm-gateway rag-mcp; do test "$(ctl is-enabled "$u.service" || :)" = disabled; done
for u in ailab-postboot-check ailab-gpu-power; do test "$(ctl is-enabled "$u.service")" = enabled; done
links > "$R/links.after"
echo SYSTEMD_ENABLEMENT_OFFLINE=PASS
# tmpfiles rule must recreate the exact default pointer in a fresh /run.
# Execute real tmpfiles only inside private root. Root ownership may be refused on unprivileged run.
set +e
systemd-tmpfiles --root="$R" --create --prefix=/run/mbip05 mbip05.conf > "$R/tmpfiles.log" 2>&1
rc=$?
set -e
cat "$R/tmpfiles.log"
echo TMPFILES_EXIT="$rc"
if [[ -L "$R/run/mbip05/active.json" ]]; then
  test "$(readlink "$R/run/mbip05/active.json")" = /etc/mbip05/profiles/strata-mbip-inkling.json
  echo TMPFILES_POINTER=PASS
else
  echo TMPFILES_POINTER=NOT_VERIFIED
fi
# Revert only planned new artifacts, and restore original enablement.
ctl disable mbip-strata.service
rm -- "$U/mbip-strata.service.d/97-mbip05-boot.conf" "$U/ailab-postboot-check.service.d/95-mbip05-mode.conf"
rmdir "$U/ailab-postboot-check.service.d" 2>/dev/null || :
rm -- "$R/etc/tmpfiles.d/mbip05.conf" "$R/usr/local/libexec/ailab/mbip05-postboot-readiness"
for u in ollama llm-gateway rag-mcp; do ctl enable "$u.service"; done
test "$(ctl is-enabled mbip-strata.service || :)" = static
links > "$R/links.rollback"
cmp "$R/links.before" "$R/links.rollback"
diff -r --no-dereference "$R/original-systemd" "$U"
echo SYSTEMD_ROLLBACK_OFFLINE=PASS
