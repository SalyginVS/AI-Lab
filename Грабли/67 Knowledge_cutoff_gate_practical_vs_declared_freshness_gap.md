---
tags: [grabli, canonical, governance, model-intake, freshness]
дата: 2026-04-19
этап: Post-R / v32
статус: Active
компонент: Model intake protocol
связано: [ADR-022, ADR-025]
---

# Грабли #76: Knowledge cutoff gate + practical vs declared freshness gap

## Симптом

При intake новой модели неявно считается, что vendor-заявленная дата релиза ≈ freshness знаний. По факту:

1. Многие vendor-ы (Qwen, Alibaba — в частности Qwen3.5 и Qwen3.6 family) не публикуют knowledge cutoff в model card вообще.
2. Даже когда cutoff публикуется (Qwen3-Coder-30B-A3B-Instruct: cutoff 2025-06-30, OpenRouter model card), **практически наблюдаемый horizon свежести знаний на 2-3 месяца раньше** официальной даты.
3. Разрыв возникает из-за pipeline свойств: последние месяцы перед training cutoff underrepresented в данных (меньше индексированных страниц, меньше производных обсуждений).

**Наблюдённый случай (2026-04-19):**
- `qwen3.6:35b-a3b-q4_K_M` (релиз 2026-04-16): cutoff **не опубликован** ни в HuggingFace model card, ни в Qwen blog post.
- Behavioral freshness probe (4 verified 2025 events): 1/4 — знает Anora (март 2025), не знает Leo XIV (май 2025), PSG Champions League (май 2025), Machado Nobel (октябрь 2025).
- Практический horizon ≈ **март 2025**, то есть на 13 месяцев раньше даты релиза модели.

## Root cause

**Два независимых источника drift между заявленной и фактической свежестью:**

1. **Training data curation lag.** Training corpus собирается не непрерывно; последний сбор → cleanup → training → post-training → release занимает 6-12 месяцев. Модели, выпущенной в апреле 2026, training data cutoff типично в диапазоне июнь 2025 — сентябрь 2025.
2. **Underrepresentation tail.** Даже если cutoff формально декабрь 2025, объём уникального контента, проиндексированного из **последних** месяцев перед cutoff, заметно меньше, чем из более ранних. События последних 1-3 месяцев представлены слабо.

Следствие: behavioral probe даёт более честную оценку, чем vendor-заявленная дата.

## Влияние

**Безопасность/GRC:** модель с неизвестным cutoff может давать устаревшие советы по API/библиотекам/CVE. Для production в энергетике/производстве это дисквалифицирующий фактор.

**Bits/интеграции:** выбор модели под задачу без знания horizon = слепой выбор. Вопрос "эта модель знает про Python 3.13 / PostgreSQL 17 / Kubernetes 1.31" должен иметь ответ до назначения роли.

**Money/OPEX:** модели с unknown horizon создают cognitive load при routing ("знает ли она?") — это скрытый OPEX на единицу использования.

## Решение (governance fix для ADR-022)

**ADR-022 intake protocol получает обязательный gate:**

Ни одна модель не проходит intake без одного из трёх:

1. **(F) Confirmed vendor cutoff** — ссылка на vendor model card / blog post с явной датой.
2. **(A) Behavioral freshness probe result** — минимум 4-5 вопросов о событиях с известными датами за последние 12 месяцев до предполагаемого cutoff. Зафиксировать результат в паспорте (score X/N) и вывести practical horizon.
3. **(U-accepted, conditional)** — формально документированный Unknown с явным operational caveat: "модель не рекомендуется для задач, требующих знаний после <дата> — использовать только в narrow/bounded сценариях, где historical knowledge достаточно".

### Template записи в паспорт

```
Knowledge cutoff: [F/A/U] <formulation>
Behavioral freshness probe (verified <N> events): <score>
Interpretation: <practical horizon approximation or gap rationale>
```

### Практический horizon правило

**[A]** Поскольку behavioral probe по природе ограничен (4-5 вопросов ≠ full coverage), practical horizon = **last verified event date** с пометкой "approximate, probe-based". Не путать с training cutoff — это разные величины, и для lab governance важна первая.

## Применимость

Этот gate применяется к:
- Всем intake процессам новых моделей (дополнение ADR-022)
- Пересмотру существующих моделей, если role требует freshness (например, инструкции по текущим API, security advisories)
- Wave 2 кандидатам (qwen3-coder-next:q4_K_M, gpt-oss:20b): до prom‍оции обязательно зафиксировать cutoff [F/A/U]

Gate **не применяется**:
- К моделям с ролями, где knowledge freshness не критичен (autocomplete FIM, embeddings — там важен алгоритмический profile, не event knowledge)
- К моделям в PoC статусе без назначенной operational роли

## Следствия для действующих моделей

**Retroactive application к v32:**

| Модель | Cutoff статус | Источник | Действие |
|--------|---------------|----------|----------|
| qwen3-coder:30b | [F] 2025-06-30 | OpenRouter model card | Документировать в паспорте |
| gemma4:31b | [U] Unknown | — | Probe при следующей ревизии |
| qwen3.6:35b-a3b-q4_K_M | [A] ≈ март 2025 | Behavioral probe 2026-04-19, 1/4 | Записано в v32 §5 |
| qwen3.5:35b | [A] ≈ март 2025 | Inferred (общий base с qwen3.6, probe 1/4 на qwen3.6) | Documented in v32 as Reserve |
| qwen3.5:9b | [U] | — | Probe при следующей ревизии |
| qwen2.5-coder:7b | [F] end of 2023 | Qwen2.5 family cutoff | Документировать |
| qwen3-embedding | N/A | Embeddings — freshness не критичен | Gate не применяется |
| gemma4:e4b | [U] | — | PoC, deferred |

## Tech debt

- **Behavioral probe не формализован** как test suite. Сейчас — ad-hoc 4 вопроса per model. Нужна reference corpus из 10-15 verified events 2024-2025 для повторяемости.
- **Gateway probe tool** отсутствует. Manual `curl` per model per test. Может быть автоматизирован в `scripts/probe-freshness.sh`.
- **Периодическая реоценка** probe-результатов при обновлении reference corpus (новые события 2026 добавляются → probe становится строже).

## Связанные

- [[ADR-022 Mandatory IDE validation gate]] — родительский protocol, расширяется данным gate
- [[ADR-025 Replace qwen3.5 with qwen3.6 in Bounded Executor role]] — первое применение gate в intake
- Paspotr v32 §5.2 (model table с cutoff записями)
- Архитектура v1.18 §7.11 (governance принцип: freshness awareness)
