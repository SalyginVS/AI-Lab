# Runbook: Ollama 0.23.4 manual archive repair

## Назначение

Процедура ручного восстановления Ollama runtime из полного release archive после повреждённой или прерванной установки.

## Preconditions

- Есть rollback snapshot.
- `ollama.service` можно временно остановить.
- Архив скачан полностью:
  - `ollama-linux-amd64.tar.zst`.

## Download через aria2c

```bash
mkdir -p ~/Downloads/ollama_0234_repair
cd ~/Downloads/ollama_0234_repair

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
  -o ollama-linux-amd64.tar.zst \
  "https://github.com/ollama/ollama/releases/download/v0.23.4/ollama-linux-amd64.tar.zst"
```

## Integrity check

```bash
cd ~/Downloads/ollama_0234_repair
ls -lh ollama-linux-amd64.tar.zst
zstd -t ollama-linux-amd64.tar.zst
tar -I zstd -tf ollama-linux-amd64.tar.zst | sed -n '1,80p'
```

## Manual extract

```bash
ARCHIVE="$HOME/Downloads/ollama_0234_repair/ollama-linux-amd64.tar.zst"
REPAIR_BACKUP="$HOME/ollama_0234_broken_runtime_backup_$(date +%Y%m%d_%H%M%S)"

sudo systemctl stop ollama.service || true
sudo systemctl reset-failed ollama.service || true

mkdir -p "$REPAIR_BACKUP"
sudo cp -a /usr/local/bin/ollama "$REPAIR_BACKUP/ollama.binary.broken" 2>/dev/null || true
sudo cp -a /usr/local/lib/ollama "$REPAIR_BACKUP/ollama.lib.broken" 2>/dev/null || true

sudo rm -rf /usr/local/lib/ollama
sudo tar -I zstd -xpf "$ARCHIVE" -C /usr/local

sudo chown root:root /usr/local/bin/ollama
sudo chmod 755 /usr/local/bin/ollama

/usr/local/bin/ollama --version

sudo systemctl daemon-reload
sudo systemctl restart ollama.service
sleep 8
```

## Post-check

```bash
ollama --version
curl -s http://127.0.0.1:11434/api/version
systemctl is-active ollama.service

journalctl -u ollama.service -n 160 --no-pager \
  | grep -Ei 'version 0.23.4|inference compute|CUDA|GPU|VRAM|total_vram|ggml-cuda|offload|offloaded|runner started|error|warn' \
  || true

ollama ps
nvidia-smi
```

## PASS criteria

- `ollama --version` returns `0.23.4`.
- `/api/version` returns `0.23.4`.
- `ollama.service` is `active`.
- Logs show CUDA backend.
- `ollama ps` shows test model as `100% GPU`.
- No fresh `SEGV`, `Permission denied`, `total_vram="0 B"`.
