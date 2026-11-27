#!/usr/bin/env bash
# Non-root stage. Do not run during live inference or other GPU work.
set -euo pipefail
umask 077
base=$(realpath -m -- "${1:?usage: prepare-weights.sh STAGE INK_STAGE q6|ink|mtp|pack-q6|pack-mtp}")
ink=$(realpath -m -- "${2:?INK_STAGE}")
phase="${3:?phase}"
here=$(cd -- "$(dirname -- "$0")" && pwd)
p=/opt/mbip-strata/0.2.22/control
py="$p/python/bin/python3.12"
test "$(id -u)" != 0
mkdir -p "$base/control"
case "$phase" in
 q6|ink)
  if [ "$phase" = q6 ]; then dir="$base/q6"; else dir="$ink"; fi
  mkdir -p "$dir"
  cd "$dir"
  aria2c --input-file="$here/sources/$phase.aria2" --dir="$dir" --continue=true --check-integrity=true --auto-file-renaming=false --allow-overwrite=false --max-concurrent-downloads=1 --max-connection-per-server=4 --split=4 --min-split-size=16M --file-allocation=none --max-tries=12 --retry-wait=10 --timeout=120 --connect-timeout=30 --summary-interval=30 --console-log-level=warn --download-result=full
  sha256sum -c "$here/sources/$phase.sha256"
  ;;
 mtp)
  export STRATA_MTP_REVISION=de4b8e4d43b917e7706784d8bb445c9af86a3540
  unset STRATA_ALLOW_UNPINNED STRATA_SOURCE HF_ENDPOINT
  export PYTHONUNBUFFERED=1
  "$py" -B "$p/tools/mtp_fetch.py" fetch --out "$base/mtp"
  "$py" -B "$p/tools/mtp_fetch.py" verify --out "$base/mtp"
  echo MTP_RAW_VERIFIED
  ;;
 pack-q6)
  grep -q '^EXIT=0$' "$base/control/q6.log"
  "$py" -B "$p/tools/iq_pack.py" --gguf "$base/q6/Qwen3.8-Flash-Next-UD-Q6_K_XL-00001-of-00006.gguf" --out "$base/q6-pack" --compat-bf16
  test ! -e "$base/q6-pack/experts.bin"
  ;;
 pack-mtp)
  grep -q '^MTP_RAW_VERIFIED$' "$base/control/mtp.log"
  m="$base/mtp"
  "$py" -B "$p/tools/mtp_pack.py" --src "$m" --experts q2_0 --out "$m/mtp-q2_0.gguf"
  "$py" -B "$p/tools/mtp_rt.py" --gguf "$m/mtp-q2_0.gguf" --out "$m/rt"
  test -s "$m/rt/experts.bin"; test -s "$m/rt/dense.bin"; test -s "$m/rt/dense.txt"
  (cd "$m/rt"; sha256sum experts.bin dense.bin dense.txt > SHA256SUMS; sha256sum -c SHA256SUMS)
  echo MTP_PACK=PASS
  ;;
 *) exit 2;;
esac
echo EXIT=0
