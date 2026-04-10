---
tags: [этап, track-f, semantic-layer, text-to-sql, retrieval]
дата: 2026-04-10
этап: F-next
компонент: Semantic Layer
статус: завершён
---

# Этап F-next — Semantic Layer: Retrieval-Assisted SQL

## Суть
Retrieval-based dynamic prompt для Text-to-SQL вместо монолитного prompt addendum.

## Результат
- ChromaDB collection `sql_knowledge`: 34 карточки (DDL + бизнес-правила + SQL-примеры + антипаттерны)
- `text2sql_semantic.py`: thin wrapper над v2 baseline
- gemma4:31b: SA 90%, EA 100%
- Prompt bleed устранён архитектурно

## Ключевые находки
- Reasoning-модели (gemma4:31b) > code generators (qwen3-coder:30b) для semantic layer
- Knowledge drift — главный операционный риск
- Retrieval изолирует контекст: добавление карточек не ломает существующие кейсы

## Связанные документы
- [[ADR-018_Semantic_Layer]]
- [[Этап011A_Text-to-SQL_PoC]]
- [[Этап011_RAG_MCP]]
- [[Грабли065_Knowledge_Layer_Drift]]
- [[Грабли066_Runtime_Bridge]]
- [[Грабли067_Auth_Env_Mismatch]]
- [[Грабли068_Gateway_URL]]
- [[Грабли069_Passport_Drift_Models]]
