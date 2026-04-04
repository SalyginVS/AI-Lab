---
tags: [конфиг, gateway]
дата: 2026-03-15
---

# systemd: llm-gateway.service

Файл: `/etc/systemd/system/llm-gateway.service`

```ini
[Unit]
Description=LLM Gateway
After=ollama.service
Wants=ollama.service

[Service]
Type=simple
User=user
WorkingDirectory=/home/user/llm-gateway
ExecStart=/usr/bin/uvicorn gateway:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Управление:
```bash
sudo systemctl start llm-gateway
sudo systemctl status llm-gateway
sudo journalctl -u llm-gateway -f    # live логи
```

