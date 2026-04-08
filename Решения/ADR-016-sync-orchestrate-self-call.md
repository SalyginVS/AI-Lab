---
tags: [adr]
дата: 2026-04-07
этап: 16
статус: Accepted
---

# ADR-016: Sync Orchestrate + Self-Call Pattern

## Контекст

Формализация orchestrator паттерна (Этап 8C standalone CLI → Этап 16 gateway API). Нужно решить: реализовать pipeline execution внутри gateway как собственную логику, или переиспользовать существующий /v1/chat/completions endpoint.

## Решение

**Self-call pattern:** каждый шаг pipeline выполняется через POST /v1/chat/completions на localhost:8000 с service token пользователя `orchestrator`. Это обеспечивает прохождение каждого шага через auth middleware, structured logging и metrics автоматически — без дублирования кода chat.py.

**Sync execution:** pipeline выполняется синхронно (sequential steps), результат возвращается целиком в одном HTTP response. Async/streaming pipeline — будущая доработка при необходимости.

## Альтернативы

- Прямой вызов Ollama из orchestrate.py (минуя gateway) — отклонено: дублирование auth/logging/metrics логики, нарушение принципа «единый ingress через gateway».
- Async pipeline с WebSocket/SSE стримингом шагов — отложено: усложняет клиентский контракт, не требуется для текущих 6 pipeline.
- Вызов chat.py функций напрямую (import) — отклонено: tight coupling, обходит middleware stack.

## Следствия

3-й пользователь `orchestrator` добавлен в .env (LLM_GATEWAY_TOKENS + LLM_ORCHESTRATOR_TOKEN). В audit trail видна полная цепочка: кто вызвал pipeline (user_id из внешнего запроса) → какие модели отработали (user_id=orchestrator для каждого шага). API-контракт (POST pipeline+task → structured result) переносится на enterprise gateway без изменений.
