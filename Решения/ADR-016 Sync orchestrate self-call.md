---
tags: [adr, gateway, orchestration, architecture]
дата: 2026-04-07
этап: 16
статус: принято
---

# ADR-016 Sync orchestrate self-call

## Контекст

Формализация pipeline execution из standalone скрипта (Этап 8C) в gateway API endpoint. Два архитектурных вопроса: (1) синхронный vs async; (2) как pipeline шаги вызывают LLM.

## Варианты

### Execution model

| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| A: Синхронный HTTP | Простота, нет job store | Блокирует HTTP connection 60–90 сек |
| B: Async + polling | Non-blocking, enterprise pattern | Job store, status endpoint, cleanup, overengineering для 2 users |

### LLM call pattern

| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| C: Self-call через gateway | Auth/logging/metrics автоматически, zero code dup | Зависимость от gateway availability, extra HTTP hop |
| D: Прямой httpx к Ollama | Меньше overhead | Дублирование auth, logging, metrics, retry |

## Решение

**A + C: Синхронный HTTP + self-call через gateway localhost.**

## Обоснование

1. `OLLAMA_NUM_PARALLEL=1` — Ollama физически один запрос за раз, async не даёт параллелизма
2. Pipeline 60–90 сек, клиентский timeout 10 мин — запас достаточный
3. Self-call: auth, structured logging, metrics — для каждого pipeline шага без единой строки дублирования
4. Audit trail: caller user_id в `llm_orchestrate`, service user_id `orchestrator` в `llm_completion`

## Последствия

- Третий user `orchestrator` в `.env` (service token)
- `asyncio.to_thread()` для sync OpenAI SDK вызова в async handler
- При масштабировании до `NUM_PARALLEL > 1` или 5+ users — пересмотреть в пользу async

## Связано

- [[Этап016]]
- [[Этап008C]] (orchestrator.py PoC)
- [[ADR-015]] (per-user auth)
