---
tags: [компонент, ollama]
---

# Ollama

Inference-сервер для запуска LLM на локальном GPU. Обёртка над llama.cpp с REST API, управлением моделей, GPU offload.

## Текущее состояние

| Параметр | Значение |
|----------|----------|
| Версия | **0.18.0** |
| Хост | 192.168.0.128:11434 |
| Управление | systemd (`ollama.service`) |
| Модели | 13 штук, суммарно ~159 ГБ на диске |
| GPU | RTX 3090 (24 ГБ VRAM) + CPU offload в 62 ГБ RAM |

## Ключевые настройки

Файл: [[Ollama override.conf]]

- `OLLAMA_MAX_LOADED_MODELS=2` — две модели в памяти одновременно (FIM + chat/agent)
- `OLLAMA_NUM_PARALLEL=1` — один запрос за раз (Depth over Speed)
- `OLLAMA_FLASH_ATTENTION=1` — экономия VRAM
- `OLLAMA_KV_CACHE_TYPE=q8_0` — KV cache сжимается вдвое
- `GGML_CUDA_NO_GRAPHS=1` — защита от crash при Agent mode

## Архитектура подключения

```
Continue.dev (Chat/Edit/Agent) → gateway.py :8000 → Ollama :11434
Continue.dev (Autocomplete FIM) → Ollama :11434 напрямую
```

## Полезные команды

```bash
# Статус
sudo systemctl status ollama
ollama list                    # загруженные модели
ollama ps                      # активные в памяти

# Логи
sudo journalctl -u ollama -f

# Управление моделями
ollama pull qwen3-coder:30b
ollama rm model-name
ollama stop model-name         # выгрузить из памяти
```

## Известные грабли
- [[08 OLLAMA_HOST формат с портом]]
- [[09 CUDA graph crash]]
- [[02 qwen3.5 tool calling сломан]]

## Связано с
- [[gateway.py]] — проксирует запросы
- [[Роли моделей]] — раскладка по задачам

