#!/bin/bash
set -euo pipefail
umask 077
SRC="$(cd "$(dirname "$0")" && pwd)"
W="$(dirname "$SRC")"
PORT=18762
if [[ $# -ne 0 ]]; then echo "Usage: $0 (creates fresh private run under $W)" >&2; exit 2; fi
(cd "$W/e01p.DUc5G2Sr" && sha256sum -c SHA256SUMS >/dev/null)
test "$(pi --version)" = 1.0.3
test "$(code --version | head -n 1)" = 1.148.0
test -z "$(ss -H -ltn "( sport = :$PORT )")"
R="$(mktemp -d "$W/e02p-replay.XXXXXXXX")"
echo "E02P_REPLAY=$R"
sha256sum "$HOME/.pi/agent/models.json" "$HOME/.pi/agent/settings.json" > "$R/client-before.sha256"
python3 -IB "$SRC/prepare.py" "$R" "$W" "$PORT"
for c in ide-flash ide-inkling; do cp "$SRC/ide-test.js" "$R/$c/extension/test.js"; bash -n "$R/$c/pi-mock"; done
while IFS='=' read -r k v; do export "$k=$v"; done < <(systemctl --user show-environment | grep -E '^(DISPLAY|WAYLAND_DISPLAY|XAUTHORITY|XDG_RUNTIME_DIR|DBUS_SESSION_BUS_ADDRESS)=')
test -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}"
python3 -IB "$SRC/mock.py" "$R" "$PORT" > "$R/mock.log" 2>&1 &
M=$!
trap 'kill "$M" 2>/dev/null || true; wait "$M" 2>/dev/null || true' EXIT
for ((i=0;i<50;i++)); do grep -q MOCK_READY "$R/mock.log" && break; kill -0 "$M"; sleep .1; done
grep -q MOCK_READY "$R/mock.log"
for c in cli-flash cli-inkling; do
 python3 -IB "$SRC/run-cli.py" "$R/$c" > "$R/$c/run.log" 2>&1
 test ! -f "$R/$c/mock-errors.log"
 cat "$R/$c/run.log"
done
for c in ide-flash ide-inkling; do
 P="$R/$c"
 code --new-window --user-data-dir "$P/user" --extensions-dir "$P/extensions" --extensionDevelopmentPath="$P/extension" --extensionTestsPath="$P/extension/test.js" "$P/workspace" > "$P/host.log" 2>&1
 for ((i=0;i<110;i++)); do
  if test -f "$P/ide-events.jsonl" && grep -Eq 'IDE_MOCK_(PASS|FAIL)' "$P/ide-events.jsonl"; then break; fi
  sleep 1
 done
 test -f "$P/ide-events.jsonl"; cat "$P/ide-events.jsonl"
 grep -q IDE_MOCK_PASS "$P/ide-events.jsonl"; test ! -f "$P/mock-errors.log"
done
python3 -IB "$SRC/verify.py" "$R" | tee "$R/verify.log"
sha256sum -c "$R/client-before.sha256"
echo E02P_REPLAY_PASS
