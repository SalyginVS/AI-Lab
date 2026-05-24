# Runbook: Ollama 0.24.0 controlled archive upgrade

## Назначение

Процедура controlled upgrade Ollama runtime через официальный release archive `.tar.zst` без pipe-installer.

Используется для перехода:

```text
Ollama 0.23.4 -> 0.24.0
```

## Preconditions

- Runtime host доступен по SSH.
- `ollama.service` работает до начала upgrade.
- `llm-gateway.service` работает до начала upgrade.
- Есть достаточно места на диске.
- Установлены: `aria2c`, `zstd`, `tar`, `curl`, `jq`, `nvidia-smi`.
- Documentation source of truth находится не на runtime host, а в AI-Lab repo.

## Download

```bash
VER="0.24.0"
WORKDIR="$HOME/Downloads/ollama_${VER}_upgrade"
ARCHIVE="$WORKDIR/ollama-linux-amd64.tar.zst"
URL="https://github.com/ollama/ollama/releases/download/v${VER}/ollama-linux-amd64.tar.zst"

mkdir -p "$WORKDIR"
cd "$WORKDIR"

aria2c \
  --continue=true \
  --max-connection-per-server=8 \
  --split=8 \
  --min-split-size=1M \
  --max-tries=0 \
  --retry-wait=5 \
  --timeout=120 \
  --connect-timeout=30 \
  --file-allocation=none \
  -o "$(basename "$ARCHIVE")" \
  "$URL"
```

## Integrity check

```bash
ls -lh "$ARCHIVE"
file "$ARCHIVE"
zstd -t "$ARCHIVE"
tar -I zstd -tf "$ARCHIVE" | sed -n '1,120p'
tar -I zstd -tf "$ARCHIVE" \
  | grep -E '(^|/)bin/ollama$|(^|/)lib/ollama/|cuda_v13|libggml-cuda' \
  | sed -n '1,160p'
```

PASS criteria:

- archive exists;
- `zstd -t` passes;
- archive contains `bin/ollama`;
- archive contains `lib/ollama/cuda_v13/libggml-cuda.so`.

## Controlled replacement

```bash
VER="0.24.0"
ARCHIVE="$HOME/Downloads/ollama_${VER}_upgrade/ollama-linux-amd64.tar.zst"
BACKUP="$HOME/ollama_runtime_backup_before_${VER}_$(date +%Y%m%d_%H%M%S)"

test -f "$ARCHIVE" || exit 1
zstd -t "$ARCHIVE" || exit 1

ollama --version || true
curl -s http://127.0.0.1:11434/api/version || true

sudo systemctl stop ollama.service
sudo systemctl reset-failed ollama.service || true
sleep 2

mkdir -p "$BACKUP"
sudo cp -a /usr/local/bin/ollama "$BACKUP/ollama.binary.before" 2>/dev/null || true
sudo cp -a /usr/local/lib/ollama "$BACKUP/ollama.lib.before" 2>/dev/null || true

sudo rm -rf /usr/local/lib/ollama
sudo tar -I zstd -xpf "$ARCHIVE" -C /usr/local

sudo chown root:root /usr/local/bin/ollama
sudo chmod 755 /usr/local/bin/ollama

sudo systemctl daemon-reload
sudo systemctl restart ollama.service
sleep 8
```

## Post-check

```bash
ollama --version
curl -s http://127.0.0.1:11434/api/version
systemctl is-active ollama.service

journalctl -u ollama.service -n 120 --no-pager \
  | grep -Ei 'version 0.24.0|Listening|inference compute|CUDA|GPU|VRAM|total_vram|cuda_v13|ggml-cuda|error|warn|segv|permission denied' \
  || true

ollama ps || true
nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu --format=csv
```

## Gateway post-check

```bash
systemctl is-active llm-gateway.service || true
sudo systemctl restart llm-gateway.service
sleep 5

curl -sS http://127.0.0.1:8000/health | jq .
```

Then run OpenAI-compatible regression:

- `/v1/models`;
- `/v1/chat/completions`;
- check structured gateway log for `status_code=200` and `error=null`.

## PASS criteria

- `ollama --version` returns `0.24.0`.
- `/api/version` returns `0.24.0`.
- `ollama.service` is active.
- Logs show CUDA backend.
- Direct Ollama generation works.
- `llm-gateway.service` is active.
- gateway `/health` returns `gateway=ok` and `ollama=ok`.
- gateway `/v1/chat/completions` returns valid response with `status_code=200`.

## Rollback note

Rollback backup from the 2026-05-24 upgrade:

```text
/home/vladimir/ollama_runtime_backup_before_0.24.0_20260524_080312
```

Do not delete until the upgraded runtime has several days of stable operation.
