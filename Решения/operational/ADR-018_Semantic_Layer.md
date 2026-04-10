---
tags: [решение, adr, canonical, semantic-layer, text-to-sql]
дата: 2026-04-10
этап: F-next
компонент: Semantic Layer
статус: canonical
---

# ADR-018 — Semantic Layer Architecture for Retrieval-Assisted NL-to-SQL

## Решение
Thin owned semantic layer на существующей инфраструктуре (ChromaDB + gateway + qwen3-embedding). Retrieval-based dynamic prompt вместо монолитного addendum.

## Отклонённые варианты
- **Wren AI:** AGPL-3.0, 6 Docker-контейнеров, Qdrant дубль, LiteLLM мимо gateway. Отложен как enterprise-кандидат.
- **Vanna AI 2.0.2:** Archived 2026-03-29. Паттерн заимствован, код — нет.
- **Full custom framework:** Over-engineering.

## Ключевые следствия
- Reasoning-модели предпочтительнее для semantic layer (gemma4:31b > qwen3-coder:30b)
- Knowledge drift — главный операционный риск
- Enterprise evaluation framework зафиксирован для будущих GenBI-пилотов

## Связано
- [[Этап018_Semantic_Layer]]
- [[ADR-012_Model_Routing]]
- [[ADR-013_Evaluator_Separation]]
- [[ADR-015_Auth_Audit]]
