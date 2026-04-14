---
tags: [грабли, governance, модели]
дата: 2026-04-14
этап: Post-R
компонент: Model Management
статус: Закрыт
---

# 70 Label-driven retention — историческая метка ≠ оправдание retention

## Суть

`deepseek-r1:32b` удерживалась как «Deep math/reasoning» на основании метки, а не эксперимента. При role-based сравнении с `gemma4:31b` проиграла 6/10 vs 9/10 по всем reasoning-критериям.

## Правило

**Retention = role-driven, not label-driven.** Каждая Active-модель должна иметь подтверждённую уникальную роль. При wave cleanup — эксперимент предшествует решению.

## Связанные

- [[ADR-019 Удаление deepseek-r1-32b]]
