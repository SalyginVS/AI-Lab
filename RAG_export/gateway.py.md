---
tags: [компонент, gateway]
---

# gateway.py

FastAPI HTTP-шлюз между IDE-клиентами и Ollama. OpenAI-совместимый API. Проксирует, конвертирует форматы, фильтрует reasoning, управляет ошибками.

## Текущее состояние

| Параметр | Значение |
|----------|----------|
| Версия | **v0.7.0** |
| Файл | `~/llm-gateway/gateway.py` |
| Порт | 8000 |
| Сервис | `llm-gateway.service` (systemd) |
| Размер | 994 строки |

## Эндпоинты

| Метод | Путь | Назначение |
|-------|------|-----------|
| POST | /v1/chat/completions | Основной — проксирует в Ollama, стриминг, tool_calls, reasoning |
| GET | /v1/models | Список моделей (OpenAI-формат) |
| GET | /health | Статус: шлюз + Ollama + модели + auth + версия |

Детали: [[gateway.py эндпоинты]]

## Что делает шлюз (чего нет в голой Ollama)

1. **Reasoning policy** — фильтрует thinking из content, отдаёт через `reasoning_content`
2. **Настоящий стриминг** — `client.send(req, stream=True)` вместо буферизации
3. **Tool_calls конвертация** — формат Ollama → формат OpenAI
4. **OOM-детекция** — 8 паттернов, HTTP 503 + Retry-After
5. **Retry при холодном старте** — 3 попытки, exponential backoff
6. **Auth** — опциональный Bearer token
7. **Валидация** — Pydantic, диапазоны параметров, OpenAI-формат ошибок

## Эволюция

| Версия | Этап | Что добавлено |
|--------|------|--------------|
| v0.1.0 | 1 | Базовый проброс (фейковый стриминг) |
| v0.2.0 | 2 | Reasoning policy, /v1/models, /health, systemd |
| v0.3.0 | 3 | Валидация параметров, logging |
| v0.4.0 | 4 | Классификация ошибок, OOM, retry |
| v0.5.0 | 5 | Multimodal messages, tools, auth, SDK-совместимость |
| v0.6.0 | 6 | Настоящий стриминг (TTFT 0.12 сек) |
| v0.7.0 | 7A | Tool_calls конвертация Ollama→OpenAI |

## Планируется
- v0.8.0 — /v1/embeddings (Этап 9A)
- v0.9.0 — Structured logging (Этап 10A)
- v0.10.0 — /metrics (Этап 10B)
- v0.11.0 — /v1/orchestrate (Этап 16)
- Модуляризация в Python-пакет: [[ADR-006 Модуляризация gateway]]

## Известные грабли
- [[01 Фейковый стриминг httpx]] (решено v0.6.0)
- [[07 Ollama tool_calls формат]] (решено v0.7.0)
- [[06 logging uvicorn.error]]
- [[11 nano sed ненадёжен для Python]]

