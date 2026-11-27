#!/bin/bash
# Actual tmpfiles root ownership test, exclusively in a freshly allocated isolated root.
set -euo pipefail
umask 077
test "$(id -u)" = 0
test "$(id -g)" = 0
P=$(cd "$(dirname "$0")" && pwd)
D=$(mktemp -d /tmp/mbip05-tmpfiles-test.XXXXXXXX)
R="$D/root"
mkdir -p "$R/etc/tmpfiles.d" "$R/run" "$R/etc/mbip05/profiles"
cp "$P/stage/tmpfiles/mbip05.conf" "$R/etc/tmpfiles.d/mbip05.conf"
printf '%s  %s\n' 1ec0d0c9522f514fd99de803f2e9e295a61b54695a80f73c6a9817851cbe4b22 "$R/etc/tmpfiles.d/mbip05.conf" | sha256sum -c -
systemd-tmpfiles --version | head -1
systemd-tmpfiles --root="$R" --create --prefix=/run/mbip05 mbip05.conf
python3 -I - "$R" <<'PY'
import os,pathlib,stat,sys
p=pathlib.Path(sys.argv[1])/"run/mbip05";s=p.stat()
assert (s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode))==(0,0,0o755)
l=p/"active.json";s=l.lstat()
assert stat.S_ISLNK(s.st_mode) and (s.st_uid,s.st_gid)==(0,0)
assert os.readlink(l)=="/etc/mbip05/profiles/strata-mbip-inkling.json"
print("TMPFILES_ROOT_OWNERSHIP=PASS",p.stat().st_uid,p.stat().st_gid,oct(stat.S_IMODE(p.stat().st_mode)),s.st_uid,s.st_gid,os.readlink(l))
PY
echo "ISOLATED_ROOT=$R"
