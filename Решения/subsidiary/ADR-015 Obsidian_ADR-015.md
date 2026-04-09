---
tags: [решение, adr, security, auth]
дата: 2026-04-07
этап: 14B
компонент: gateway
статус: принято
---

# ADR-015 Per-user token storage — ENV-based JSON

## Контекст

Этап 14B: переход от optional single-token auth к mandatory per-user tokens. Нужно хранить маппинг token → user_id для 2–3 пользователей лаборатории.

## Варианты

**A. ENV-based JSON** — `LLM_GATEWAY_TOKENS='{"token": "user_id"}'` в `.env` файле, подключение через systemd `EnvironmentFile=`.

**B. YAML config file** — отдельный `tokens.yaml` с маппингом.

## Решение

Вариант A — ENV-based JSON.

## Обоснование

- Ноль новых файлов конфигурации (кроме .env)
- Secret isolation через chmod 600 + systemd EnvironmentFile
- Достаточно для 2–3 пользователей
- Shared между llm-gateway и rag-mcp через один EnvironmentFile
- Ротация токенов: заменить .env → restart оба сервиса

## Ограничения

- При 5+ пользователях — неудобно. Миграция на config file или secrets manager.
- Первый токен из map используется для rag-mcp server-to-server calls (interim решение, не dedicated service token).

## Последствия

- `~/llm-gateway/.env` (chmod 600) — единое хранилище токенов
- `EnvironmentFile=` в systemd override для `llm-gateway.service` и `rag-mcp.service`
- Gateway отказывается стартовать без `LLM_GATEWAY_TOKENS` (mandatory)
