# Грабли #70: Label-driven retention — историческая метка ≠ оправдание retention

**Дата:** 2026-04-14  
**Этап:** Post-R (эксперимент deepseek-r1:32b vs gemma4:31b)  
**Компонент:** Governance / Model Management  
**Severity:** Medium (governance noise, не runtime failure)

---

## Суть

Модель `deepseek-r1:32b` удерживалась на стенде как «Deep math/reasoning» (Tier 2, Active) на основании **исторической метки**, а не подтверждённой дифференциации. При role-based head-to-head сравнении с gemma4:31b она проиграла по всем пяти критериям reasoning (6/10 vs 9/10), включая handling of ambiguity, skeptical review и logical deconstruction.

## Почему это грабли

- Метка «specialized reasoner» создавала **ложное ощущение уникальной ценности**
- Модель занимала место в Tier 2, влияя на routing decisions и документацию
- Отсутствие периодической re-evaluation привело к тому, что модель пережила ревизию R без проверки своей заявленной роли
- На single-GPU стенде каждая лишняя модель — routing noise и governance overhead

## Правило

**Retention = role-driven, not label-driven.** Каждая модель со статусом Active должна иметь подтверждённую уникальную роль, верифицированную экспериментом. Историческая метка — не основание для retention. При wave cleanup первый вопрос: «есть ли у модели distinct value, не покрытая другой Active-моделью?»

## Связанные артефакты

- ADR-019: Удаление deepseek-r1:32b
- Эксперимент: `DeepSeekR1_vs_Gemma4_31B_Reasoning_Report_for_Claude_2026-04-13.md`
