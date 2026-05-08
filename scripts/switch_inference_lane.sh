#!/usr/bin/env bash
set -euo pipefail

TARGET_HOST="${TARGET_HOST:-vladimir@192.168.0.128}"
MODE="${1:-}"

usage() {
  cat <<'EOF'
Usage:
  scripts/switch_inference_lane.sh status
  scripts/switch_inference_lane.sh ollama-heavy
  scripts/switch_inference_lane.sh vllm-mtp-128k

Environment:
  TARGET_HOST=vladimir@192.168.0.128

Meaning:
  status          Show GPU, Ollama, vLLM and gateway status.
  ollama-heavy    Stop vLLM MTP 128K and restore Ollama default/heavy lane.
  vllm-mtp-128k   Restart Ollama to unload heavy models and start vLLM MTP 128K.
EOF
}

remote_status() {
  ssh "$TARGET_HOST" 'bash -s' <<'REMOTE'
echo "=== host ==="
hostname
date

echo
echo "=== gpu ==="
nvidia-smi || true

echo
echo "=== vLLM MTP service ==="
systemctl is-active vllm-qwen36-mtp.service || true
systemctl status vllm-qwen36-mtp.service --no-pager -l | head -60 || true

echo
echo "=== vLLM models on 8027 ==="
curl -s --max-time 10 http://127.0.0.1:8027/v1/models | python3 -m json.tool || true

echo
echo "=== Ollama loaded models ==="
ollama ps || true

echo
echo "=== gateway health ==="
curl -s --max-time 10 http://127.0.0.1:8000/health | python3 -m json.tool | head -80 || true
REMOTE
}

remote_ollama_heavy() {
  ssh -t "$TARGET_HOST" 'bash -s' <<'REMOTE'
set -euo pipefail

echo "=== switch to Ollama heavy/default lane ==="
sudo systemctl stop vllm-qwen36-mtp.service || true
sudo systemctl restart ollama

sleep 10

echo
echo "=== gpu ==="
nvidia-smi

echo
echo "=== ollama ps ==="
ollama ps || true

echo
echo "=== gateway health ==="
curl -s --max-time 10 http://127.0.0.1:8000/health | python3 -m json.tool | head -80 || true

echo
echo "LANE=ollama-heavy"
REMOTE
}

remote_vllm_mtp_128k() {
  ssh -t "$TARGET_HOST" 'bash -s' <<'REMOTE'
set -euo pipefail

echo "=== switch to vLLM MTP 128K lane ==="
sudo systemctl restart ollama
sudo systemctl start vllm-qwen36-mtp.service

echo
echo "=== wait for vLLM readiness, max 5 min ==="
READY=NO
for i in $(seq 1 60); do
  RAW="$(curl -s --max-time 5 http://127.0.0.1:8027/v1/models || true)"
  if echo "$RAW" | python3 -m json.tool >/tmp/vllm_models.json 2>/dev/null; then
    cat /tmp/vllm_models.json
    READY=YES
    break
  fi
  sleep 5
done
rm -f /tmp/vllm_models.json
echo "READY=$READY"

echo
echo "=== gpu ==="
nvidia-smi

echo
echo "=== service ==="
systemctl status vllm-qwen36-mtp.service --no-pager -l | head -60 || true

echo
echo "LANE=vllm-mtp-128k"
REMOTE
}

case "$MODE" in
  status)
    remote_status
    ;;
  ollama-heavy)
    remote_ollama_heavy
    ;;
  vllm-mtp-128k)
    remote_vllm_mtp_128k
    ;;
  -h|--help|help|"")
    usage
    ;;
  *)
    echo "Unknown mode: $MODE" >&2
    usage
    exit 2
    ;;
esac
