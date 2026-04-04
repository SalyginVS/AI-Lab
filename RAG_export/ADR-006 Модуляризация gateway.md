---
tags: [adr, решение]
дата: 2026-03-20
статус: принято
---

# ADR-006: Модуляризация gateway.py при первом расширении

## Контекст
gateway.py v0.7.0 — 994 строки. При добавлении embeddings, logging, metrics, orchestrate вырастет до 2000+.

## Решение
При первом расширении (Этап 9A/10A) разбить на Python-пакет `~/llm-gateway/gateway/`. Модули в одном процессе (один systemd unit, один порт), логически разделённые: app.py, router.py, streaming.py, embeddings.py, metrics.py, auth.py, logging_config.py, models.py, orchestrator.py.

## Последствия
- Можно обновлять embeddings не трогая streaming
- Тестировать orchestrator изолированно
- При переносе на Enterprise — вынести модули в отдельные сервисы если нужно
