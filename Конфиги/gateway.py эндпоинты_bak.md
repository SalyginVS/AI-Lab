---
tags: [конфиг, gateway]
дата: 2026-03-19
---

# gateway.py v0.7.0 — эндпоинты и параметры

Файл: `~/llm-gateway/gateway.py`
Сервис: `llm-gateway.service`
Порт: 8000

## Эндпоинты

| Метод | Путь | Назначение |
|-------|------|-----------|
| POST | /v1/chat/completions | Основной — проксирует в Ollama |
| GET | /v1/models | Список моделей (OpenAI-формат) |
| GET | /health | Статус шлюза, Ollama, моделей |

## Ключевые параметры

- **reasoning_effort**: none/low/medium/high → think: true/false
- **num_ctx**: 1–32768 (дефолт 8192)
- **tools/tool_choice**: проброс для function calling
- **Auth**: Bearer token через env `LLM_GATEWAY_API_KEY` (опционально)
- **Retry**: 3 попытки при connection errors, exponential backoff
- **OOM**: 8 паттернов, HTTP 503 + Retry-After: 30
