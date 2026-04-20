---
tags: [adr, canonical, routing, модели, a3b]
дата: 2026-04-19
этап: v32
статус: Accepted
компонент: Model Routing Policy
связано: [ADR-021, ADR-022, ADR-023, Грабли #76]
---

# ADR-025: Replace qwen3.5:35b with qwen3.6:35b-a3b-q4_K_M in Bounded Executor role

## Контекст

**Предшествующее состояние (v31):**
- Bounded Executor роль — qwen3.5:35b (ADR-021).
- qwen3.6 family: `qwen36-35b-a3b-q4km-fix` (community "fix" вариант) отклонён для IDE-роли в ADR-023 из-за open-file context failure, thinking stall, format artifacts.
- A3B MoE class risk формализован как ex-ante ужесточённый протокол валидации (ADR-023).

**Что изменилось:**

1. **Релиз официального Alibaba Qwen3.6-35B-A3B** (2026-04-16, через Ollama/HuggingFace):
   - Не community "fix" вариант — **official Alibaba post-trained release**.
   - Архитектурные улучшения над Qwen3.5 base: hybrid Gated DeltaNet + MoE layout, native `qwen3_coder` tool-call parser (указан в HF model card), thinking preservation для agent-сценариев.
   - HuggingFace: `Qwen/Qwen3.6-35B-A3B`, Apache-2.0.

2. **Interim agent contour validation (2026-04-19):**
   - Headless bounded agent contour (golden set из 7 сценариев): qwen3.6 = паритет с qwen3.5, 7/7 PASS.
   - Контур и tool discipline подтверждены на двух A3B моделях в одинаковой обвязке.

3. **Knowledge freshness probe (2026-04-19):**
   - qwen3.6 behavioral freshness probe: 1/4 на verified 2025 events (Anora — знает, Leo XIV / PSG / Machado — не знает).
   - Practical horizon ≈ март 2025 для обеих моделей qwen3.5 и qwen3.6 — паритет по свежести знаний, upgrade путь нейтрален по этому параметру.
   - Методика probe формализована в Грабли #76 как обязательный gate для intake.

4. **IDE validation gate re-run (2026-04-19):**
   - Протокол Briefing_qwen36_IDE_Validation_Gate.md v1.0 исполнен через ChatGPT + Vladimir.
   - Первичный вердикт "overall fail" был скорректирован после повторного прогона с нормализованными промптами: часть fail-ов реклассифицирована как contaminated runs, prompt design flaws, mode-specific artifacts.
   - **Normalized verdict:** model viable as Bounded Executor, key checks passed.
   - **Зафиксированный operational nuance:** в одном non-agent current-file path модель вернула "I don't have access to see which file is currently open" — mode-specific inconsistency, не общий reject.

## Решение

**qwen3.5:35b** переводится из Active (Bounded Executor) в **Reserve** с ролью "previous Bounded Executor, replaced by qwen3.6 in ADR-025, disk-retained for rollback".

**qwen3.6:35b-a3b-q4_K_M** (official Alibaba release) переводится из disk-retention в **Active** со **всеми ограничениями Bounded Executor** из ADR-021 v2, плюс дополнительный **operational caveat**: mode-specific inconsistency в non-agent current-file path.

**Роль Bounded Executor переносится на qwen3.6 с сохранением оригинальных границ:**

| Атрибут | Значение (от ADR-021 v2) |
|---------|--------------------------|
| Основной use case | Точечные правки кода по явной инструкции (bug fix, spacing, type hints, boundary conditions) |
| Prompt contract | Narrow, code-only output, без комментариев и объяснений |
| Pipeline pattern | Reviewer → Bounded Executor → Reviewer |
| Correction loop | Supported (после targeted feedback) |
| НЕ делает | Agent mode с `tool_choice: auto`, first-pass review, mixed-format ответы, autonomous execution без supervisor |

**Operational caveat (новое, специфично qwen3.6):**

В одном observed сценарии при non-agent current-file edit path модель вернула "I don't have access to see which file is currently open...". В agent mode аналогичной проблемы не наблюдалось — файл дискаверится штатно.

**Рекомендация для пользователя:** при bounded edit задачах, требующих currentFile context, **если модель не видит файл** — использовать один из обходных путей:
1. Явно передать содержимое выделением и `/edit` (не надеяться на неявный currentFile ingestion)
2. Переключиться в agent mode для file-aware bounded tasks
3. Использовать `@Current File` или `@File` context provider в Chat path

Это **operational nuance**, не блокирующий дефект — модель viable для bounded editor роли при соблюдении этих обходов. Документируется в `02-coding.md` rule.

## Обоснование замены

**Почему upgrade, а не retention обеих:**

1. **OPEX governance.** Две модели в одной роли → confusion при выборе, увеличивает cognitive load оператора.
2. **qwen3.6 — архитектурный upgrade над тем же base.** Hybrid DeltaNet + MoE, native tool-call parser, thinking preservation. Для bounded editor роли эти свойства не критичны, но и не вредят; регрессии нет.
3. **Interim agent contour паритет + IDE validation PASS** — достаточная база для переноса роли.
4. **Freshness probe = паритет** — upgrade не ухудшает knowledge horizon.

**Почему qwen3.5 — Reserve, а не удаление:**

Стандартная политика v31 "no reserve lane for failed models" **не применяется**: qwen3.5 не failed — она замещается по upgrade-пути. Retention на диске (23 ГБ, достаточно свободного места) обеспечивает fast rollback при обнаружении problems с qwen3.6 в эксплуатации. Это **upgrade rollback retention**, не reserve lane for failures.

Формальное прекращение retention qwen3.5 — при наличии 30 дней стабильной эксплуатации qwen3.6 в bounded executor роли без инцидентов, или при необходимости освободить диск для wave 2 evaluation.

**Почему ADR-023 не блокирует:**

ADR-023 был сформулирован на двух observations: (1) community `qwen36-35b-a3b-q4km-fix` с специфичным failure pattern, (2) `nemotron3-nano-30b-a3b-q4km`. Текущая модель — **официальный Alibaba release**, не community "fix" вариант. IDE validation gate (ADR-022) на нормализованных промптах прошёл. Это model-specific override для official Qwen3.6-35B-A3B; A3B class risk **остаётся активным** для wave 2 и community variants — closing note в ADR-023 это фиксирует.

## Принцип

**Mode-aware role assignment.** Предыдущая практика assigning role по бинарному "модель viable для IDE / не viable" оказалась overgeneralizing. При наблюдении mode-specific inconsistency правильная reaction — задокументировать operational nuance и sohранить роль, а не применять blanket reject. Этот принцип согласован с Corrected Report 2026-04-19: "Reliability must be evaluated per invocation mode rather than by a single binary verdict."

**Upgrade path retention semantics.** Модели, замещённые по upgrade-пути, не являются "failed models" под политикой ADR-019 / v31. Их retention в Reserve — это rollback insurance, не reserve lane. Политика "no reserve lane" применяется к моделям, не подтвердившим operational value; qwen3.5 свою value подтвердила ADR-021, поэтому retention корректен.

## Следствия

### Паспорт v32

- §5 model table: qwen3.5:35b Active → Reserve; qwen3.6:35b-a3b-q4_K_M добавляется как Active Bounded Executor.
- §5 freshness probe запись: qwen3.6 behavioral probe 1/4, practical horizon ≈ март 2025.
- Inventory count: 10 → 10 (qwen3.5 остаётся на диске как Reserve).
- §11 changelog: v32 entry.

### Архитектура v1.18

- §2.1 Tier 1 routing table: qwen3.6 в строке Bounded Executor; qwen3.5 → Tier 3 Reserve.
- §2.1 ADR references: ADR-025 добавлен.
- §6 open questions: #44 mode-specific non-agent current-file inconsistency (root cause investigation).
- §7 governance: §7.11 Mode-aware role assignment (new governance principle).
- §8 журнал ревью: v1.18 entry.

### Continue.dev config.yaml

- Удалить модель `qwen35` (qwen3.5:35b) из active entries (или пометить inactive).
- Добавить модель `qwen36-bounded` (qwen3.6:35b-a3b-q4_K_M) с `roles: [edit]`, аналогично предыдущему qwen35.
- `extraBodyProperties.num_ctx`: 131072 (подтверждён для qwen3.6 через gateway).
- `reasoning_effort: "none"` обязателен для bounded output discipline.

### 02-coding.md rule

- Новый раздел: "Bounded Executor invocation contract (qwen3.6-bounded)".
- Явное описание narrow prompt requirements.
- Operational note про mode-specific current-file inconsistency с обходами.

### pipelines.yaml

- Опциональный `bounded-fix` pipeline: executor=qwen3.6:35b-a3b-q4_K_M (вместо qwen3.5:35b).
- Статус: pending implementation (не блокирующее).

### RAG lab_docs reindex

- ADR-021 v2 + ADR-023 v2 + ADR-025 + Грабли #76 → добавить при следующем reindex (canonical corpus: 14 → 18).

### Tech debt

- Root cause mode-specific non-agent current-file inconsistency не установлен. Open question #44 в архитектуре v1.18. Не блокирует operational использование при соблюдении обходов.
- Behavioral freshness probe не автоматизирован (Грабли #76 §Tech debt).

## Ограничения применения

- ADR-025 применяется только к **official Alibaba Qwen3.6-35B-A3B release**. Не распространяется на community "fix" варианты, NVFP4 квантовки, альтернативные GGUF-сборки от других мейнтейнеров без отдельной валидации.
- IDE validation gate результат зафиксирован для **Continue.dev v1.2.22 + Ollama 0.20.7 + gateway v0.12.0+patch**. При major upgrade любого компонента — re-validation обязательна (SOP для upgrade tracking).

## Связанные

- [[ADR-012 Gemma 4 Model Integration]] — routing context
- [[ADR-019 Model retention role-driven]] — governance (upgrade path разъяснён)
- [[ADR-021 Bounded executor role for qwen3.5-35b]] v2 — role definition (supersession)
- [[ADR-022 Mandatory IDE validation gate]] — validation protocol (passed для qwen3.6)
- [[ADR-023 A3B MoE output envelope risk]] v2 — class risk (model-specific override)
- [[76 Knowledge cutoff gate practical vs declared freshness gap]] — intake gate
- Interim report: `Agent_Contour_Validation_Interim_Report_2026-04-19.md`
- IDE validation report: `qwen36_ide_validation_corrected_report_2026-04-19.md`
- Briefing: `Briefing_qwen36_IDE_Validation_Gate.md v1.0`
