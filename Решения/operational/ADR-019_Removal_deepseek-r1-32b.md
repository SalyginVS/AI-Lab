# ADR-019: Удаление deepseek-r1:32b — reasoning-роль покрыта gemma4:31b

**Дата:** 2026-04-14  
**Статус:** Accepted  
**Слой:** L1 — Canonical  
**Компоненты:** Inference/Backend (Layer 1), Model Routing (ADR-012)  
**Связанные ADR:** ADR-012 (Gemma 4 Model Integration), ADR-018 (Semantic Layer Architecture)

---

## Контекст

`deepseek-r1:32b` исторически занимала роль **Deep math/reasoning** (Tier 2, статус Active) в лаборатории. После интеграции Gemma 4 (ADR-012) и подтверждения gemma4:31b как Quality-first Agent / Planner / Reviewer / Best Semantic SQL возник вопрос: сохраняет ли deepseek-r1:32b уникальную reasoning-ценность, которую gemma4:31b не закрывает?

Вопрос не «какая модель лучше вообще», а governance-вопрос: оправдывает ли deepseek-r1:32b отдельную системную роль в лаборатории?

## Эксперимент

Проведено **role-based head-to-head сравнение** (2026-04-13), намеренно смещённое в пользу deepseek-r1:32b — на её заявленном поле (specialized reasoning), без сравнения по chat, coding, agent, planning.

**Три теста:**
1. **Destroy-the-logic** — разбор утверждения как логической конструкции
2. **Adversarial second-opinion** — skeptical review чужого вывода
3. **Competing hypotheses under ambiguity** — reasoning при неполных данных

**Результаты (оценки по 10-балльной шкале):**

| Критерий | gemma4:31b | deepseek-r1:32b |
|----------|:----------:|:---------------:|
| Logical deconstruction | 9 | 6 |
| Skeptical review quality | 9 | 6 |
| Handling of ambiguity | 9.5 | 5.5 |
| Discipline / structure | 9 | 6 |
| Distinct value as specialized reasoner | 8.5 | 5.5 |

## Решение

**Удалить deepseek-r1:32b со стенда (Variant C — strict cleanup).**

Обоснование:
- gemma4:31b перекрывает reasoning-роль, ради которой deepseek-r1:32b могла быть сохранена
- deepseek-r1:32b не показала distinct reasoning differentiation даже на своём заявленном поле
- сохранение модели без уникальной роли создаёт routing noise, retention ambiguity, ложное ощущение richness
- лаборатория на single RTX 3090 требует строгой role discipline

## Последствия

### Модельный контур
- 12 → 11 моделей на сервере
- Tier 2 теряет deepseek-r1:32b, остаётся: qwen3.5:9b, gemma4:e4b
- Continue config: 10 → 9 моделей (удалить deepseek-r1 из config.yaml)
- setup-check.sh, health-check.sh: обновить ожидаемое количество моделей (12→11)
- health endpoint /health: models_count=11

### Архитектурные ссылки
- Long-context fallback (Грабли #43): ранее упоминалось «non-Gemma модели (qwen3-coder, deepseek-r1)». Теперь fallback — только qwen3-coder:30b.
- Открытый вопрос #35 (wave 2): deepseek-r1:32b больше не в списке кандидатов — решение принято.

### Governance principle (новый)
**Retention = role-driven, not label-driven.** Историческая метка («Deep reasoner») не оправдывает retention без подтверждённой дифференциации через эксперимент.

## Альтернативы (отклонены)

- **Variant A (Conservative):** оставить как архивный / резервный слой. Отклонено — размывает governance дисциплину.
- **Variant B (Demote):** перевести в Demoted. Отклонено — промежуточный статус без добавленной ценности при 675 ГБ свободного диска.

## Риски

- При появлении задач, требующих специфической DeepSeek R1 архитектуры (chain-of-thought с explicit reasoning trace), модель придётся скачать заново (~19 ГБ, ~5 мин). Риск оценивается как низкий: gemma4:31b с thinking mode закрывает этот класс задач.
