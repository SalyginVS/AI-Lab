# ADR-018: Semantic Layer Architecture for Retrieval-Assisted NL-to-SQL

**Статус:** Canonical
**Дата:** 2026-04-10
**Этап:** F-next (Track F: AI-as-Interface)
**Автор:** Vladimir / Claude

---

## Контекст

Text-to-SQL PoC (Этап 11A) достиг SA 90% с монолитным prompt addendum (6 блоков бизнес-семантики в system prompt). Однако обнаружен prompt bleed: точечная правка одного rule вызывала regression на других кейсах (Грабли #36). Монолитный prompt не масштабируется на реальные enterprise-схемы (сотни таблиц).

Нужен архитектурный подход, который:
- динамически подбирает контекст для каждого вопроса;
- устраняет prompt bleed;
- масштабируется без деградации;
- переносим на enterprise.

---

## Рассмотренные варианты

### A. Wren AI — external semantic platform

- **Лицензия:** AGPL-3.0 (ограничивает enterprise-использование без legal review)
- **Runtime:** 6 Docker-контейнеров (wren-engine, wren-ai-service, ibis-server, qdrant, wren-ui, bootstrap)
- **Порт 8000** конфликтует с gateway
- **Qdrant** дублирует ChromaDB
- **LiteLLM** обходит gateway — нарушает ADR-010 (embeddings через gateway) и ADR-015 (audit trail)
- **Ollama support:** open issues с embedding failures, не production-ready для локальных моделей
- **Решение:** Отложен как enterprise-кандидат для отдельного пилота GenBI

### B. Thin owned semantic layer на существующей инфраструктуре ← ПРИНЯТ

- Реиспользует ChromaDB + gateway + qwen3-embedding
- ~200 строк Python, zero new dependencies
- Максимальная портируемость и прозрачность
- Benchmark и evaluator остаются owned

### C. Vanna AI 2.0.2

- Репозиторий archived 2026-03-29 (read-only)
- Dead upstream, нет security patches
- Паттерн заимствован (DDL + docs + SQL pairs → retrieval), код — нет
- **Решение:** Отклонён

### D. Full custom framework

- Over-engineering, highest OPEX, highest bus factor
- **Решение:** Отклонён

---

## Решение

**Вариант B.** Retrieval-assisted SQL через отдельную ChromaDB collection `sql_knowledge` с четырьмя типами карточек знаний. Dynamic prompt assembly на основе similarity search.

### Архитектура

```
Вопрос пользователя
  │
  ├─1─ Embedding вопроса → gateway /v1/embeddings → qwen3-embedding
  │
  ├─2─ Similarity search → ChromaDB collection sql_knowledge (top-k)
  │     Возвращает: DDL + business_doc + sql_example + anti_pattern
  │
  ├─3─ Dynamic prompt assembly
  │     Base system prompt + ТОЛЬКО релевантные карточки
  │     (вопрос про energy НЕ получает карточки про booking)
  │
  ├─4─ SQL generation → gateway /v1/chat/completions → model
  │
  └─5─ Validation + read-only execution → результат
```

### Типы карточек

| Тип | Назначение | Примеры |
|-----|-----------|---------|
| `ddl` | Структура таблицы + описание колонок | CREATE TABLE + комментарии |
| `business_doc` | Бизнес-правила предметной области | «is_active = 1 для текущих сотрудников» |
| `sql_example` | Пары «вопрос → SQL» (few-shot) | «Средняя зарплата по отделам → SELECT...» |
| `anti_pattern` | Частые ошибки моделей | «head_id ≠ department_id» |

### Результат

gemma4:31b: SA 90%, EA 100% — целевая планка достигнута на retrieval-based pipeline.

---

## Enterprise evaluation framework

При оценке enterprise GenBI-платформ (Wren AI, Databricks AI/BI, Azure SQL Copilot и т.д.) использовать:

### Benchmark harness (owned)
- 20+ вопросов с ground truth SQL
- 4 уровня сложности (simple → edge cases)
- Safety test (DML injection reject)
- Hallucination test (out-of-schema question → CANNOT_ANSWER)

### Метрики
- EA (Execution Accuracy) — синтаксическая корректность
- SA (Semantic Accuracy) — правильность результата
- Latency — время генерации
- Prompt bleed resistance — regression при добавлении правил
- Knowledge drift sensitivity — реакция на рассинхрон cards ↔ schema

### Архитектурные критерии
- Gateway integration vs bypass
- Vector store reuse vs duplication
- Audit trail сохранность
- License compatibility с enterprise policy

### Operational
- Service count и port footprint
- Ollama / local model support maturity
- Setup complexity
- Ongoing maintenance burden

---

## Следствия

1. **`sql_knowledge` collection** — owned, versioned, schema-dependent. При изменении БД-схемы карточки ДОЛЖНЫ быть обновлены.
2. **Evaluator (v2)** — owned, tool-independent. Переиспользуется для оценки любого решения.
3. **Benchmark dataset** — owned, expandable. 20 вопросов — baseline; расширяется при добавлении таблиц.
4. **Pipeline pattern** (retrieve → assemble → generate → validate) — enterprise-transferable.
5. **Reasoning-модели предпочтительнее** для semantic layer (gemma4:31b > qwen3-coder:30b). Инверсия по сравнению с plain text-to-sql.
6. **Knowledge drift** — главный операционный риск. Требует процесса синхронизации.

---

## Связанные ADR

- ADR-010: Embeddings через gateway (не напрямую в Ollama)
- ADR-012: Model routing / tier system
- ADR-013: Evaluator separation (strict vs business-aware)
- ADR-015: Mandatory per-user auth + audit trail
