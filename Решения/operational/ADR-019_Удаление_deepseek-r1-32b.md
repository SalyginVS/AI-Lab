---
tags: [adr, governance, модели, reasoning]
дата: 2026-04-14
компонент: Inference/Backend
статус: Accepted
слой: L1-Canonical
---

# ADR-019: Удаление deepseek-r1:32b — reasoning-роль покрыта gemma4:31b

## Решение

Удалить `deepseek-r1:32b` со стенда. Reasoning-роль полностью покрыта `gemma4:31b`.

## Контекст

Role-based head-to-head сравнение (2026-04-13): три теста на заявленном поле deepseek (logical deconstruction, skeptical review, competing hypotheses). Результат: gemma4:31b 9/10 vs deepseek-r1:32b 6/10 по всем критериям.

## Последствия

- 12 → 11 моделей
- Continue config: 10 → 9 моделей
- Tier 2 теряет deepseek-r1:32b
- Long-context fallback: только qwen3-coder:30b
- health-check.sh, setup-check.sh: models_count 12→11

## Governance principle

**Retention = role-driven, not label-driven.** Историческая метка не оправдывает retention без подтверждённой дифференциации.

## Связанные

- [[ADR-012 Gemma 4 Model Integration]]
- [[ADR-018 Semantic Layer Architecture]]
- [[Грабли 70 Label-driven retention]]
