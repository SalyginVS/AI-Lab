---
tags: [adr]
дата: 2026-04-07
этап: 14B
статус: Accepted
---

# ADR-015: RAG MCP Interim Auth — первый токен из map

## Контекст

После перевода gateway auth на mandatory per-user (14B), RAG MCP server потерял доступ к gateway /v1/embeddings (Грабли #48). RAG MCP server вызывает gateway для получения embedding-векторов при каждом search запросе. Нужен Bearer token для server-to-server вызовов.

## Решение

Interim: RAG MCP server использует первый токен из LLM_GATEWAY_TOKENS map (через shared EnvironmentFile в systemd). Это означает, что server-to-server вызовы логируются под user_id первого пользователя в map, а не под выделенным service account.

## Альтернативы

- Dedicated service token для RAG MCP — отложено: потребует 3-го пользователя в .env и изменения server.py для чтения отдельной env-переменной. Реализуемо, но не критично для 1-user лаборатории.
- Exempt RAG MCP от auth (по IP/path) — отклонено: ослабляет security perimeter, создаёт прецедент.

## Следствия

При добавлении 3+ пользователей или при enterprise-переносе необходимо ввести dedicated service token для server-to-server вызовов. Interim решение допустимо для текущей конфигурации. Обновление: в Этапе 16 добавлен 3-й пользователь `orchestrator` для gateway self-call — аналогичный паттерн можно применить для RAG MCP.
