---
tags: [adr]
дата: 2026-03-31
этап: 10A
статус: Accepted
---

# ADR-008: Gateway модуляризация — пакет вместо монолита

## Контекст

gateway.py вырос до 1305 строк (v0.8.0). Добавление новых endpoint-ов (embeddings, metrics, orchestrate) усложняло навигацию и тестирование. Единый файл создавал merge conflicts при параллельной работе.

## Решение

Разбить монолит gateway.py на Python-пакет `gateway/` с отдельными модулями по зоне ответственности: app.py (FastAPI app + middleware), chat.py (POST /v1/chat/completions), embeddings.py (POST /v1/embeddings), listing.py (GET /v1/models), models.py (Pydantic-модели), errors.py (error handlers), upstream.py (httpx client), logging_config.py (structured JSON logging). Точка входа: run.py → uvicorn.

## Альтернативы

- Оставить монолит — отклонено: при >1500 строк работа становится непрактичной, merge risk.
- Разбить на микросервисы — отклонено: overkill для 1 GPU / 1 сервера, усложняет deployment.

## Следствия

gateway/ стал пакетом из 8 модулей (позже расширен до 11: +metrics.py в 10B, +auth.py в 14B, +orchestrate.py в 16). Каждый новый endpoint — отдельный модуль. systemd ExecStart изменён на run.py. Бэкап монолита сохранён как _old_gateway.py.
