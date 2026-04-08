---
tags: [adr]
дата: 2026-04-04
этап: 11A
статус: Accepted
---

# ADR-013: Text-to-SQL Evaluator Separation + Prompt Freeze

## Контекст

При разработке Text-to-SQL PoC (Этап 11A) обнаружено, что одновременная оптимизация evaluator-логики и model prompt приводит к неконтролируемым взаимодействиям. Strict evaluator (v1) занижал Semantic Accuracy (SA) в 2–3 раза из-за формальных несовпадений SQL. Prompt bleed (Грабли #36): точечная правка одного rule вызывала regression на других кейсах.

## Решение

1. **Evaluator и prompt — оптимизируются раздельно, последовательно.** Сначала фиксируется evaluator (v2 business-aware), затем оптимизируется prompt при замороженном evaluator.
2. **Prompt freeze:** после достижения SA ~85–90% дальнейший micro-tuning прекращается. Для выхода за 90% SA нужен следующий архитектурный слой (semantic layer / RAG / few-shot retrieval), а не бесконечный prompt polishing.
3. **Baseline truth фиксируется на v2 evaluator:** все future benchmarks сравниваются с ним.

## Альтернативы

- Итеративная совместная оптимизация evaluator+prompt — отклонено: невозможно атрибутировать улучшения/regressions.
- Полностью автоматический evaluator (LLM-as-judge) — отложено: зависимость от второй модели, latency.

## Следствия

Prompt addendum заморожен на v1. Evaluator заморожен на v2 (business-aware). Следующий шаг — semantic layer (retrieval-assisted SQL) в Track F, а не дальнейший prompt engineering.
