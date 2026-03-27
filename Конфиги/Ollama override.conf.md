---
tags: [конфиг, ollama]
дата: 2026-03-17
---

# Ollama systemd override

Файл: `/etc/systemd/system/ollama.service.d/override.conf`

```ini
[Service]
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
Environment="OLLAMA_MAX_LOADED_MODELS=2"
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="CUDA_VISIBLE_DEVICES=0"
Environment="GGML_CUDA_NO_GRAPHS=1"
```

| Параметр | Значение | Зачем |
|----------|----------|-------|
| FLASH_ATTENTION | 1 | Экономия VRAM |
| KV_CACHE_TYPE | q8_0 | KV cache сжимается вдвое |
| MAX_LOADED_MODELS | 2 | FIM + chat/agent одновременно |
| HOST | 0.0.0.0:11434 | Доступ из LAN |
| CUDA_VISIBLE_DEVICES | 0 | Одна GPU |
| GGML_CUDA_NO_GRAPHS | 1 | Защита от crash при Agent mode |

После изменений: `sudo systemctl daemon-reload && sudo systemctl restart ollama`

