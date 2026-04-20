---
tags: [adr, canonical, routing, модели]
дата: 2026-04-17 (initial), 2026-04-19 (v2 supersession)
этап: Post-R (initial), v32 (v2)
статус: Superseded by ADR-025 (role carrier changed)
компонент: Model Routing Policy
---

# ADR-021 v2: Bounded executor role for qwen3.5-35b → qwen3.6-35b-a3b-q4_K_M

> **v2 update (2026-04-19):** Роль Bounded Executor переносится с qwen3.5:35b на qwen3.6:35b-a3b-q4_K_M (official Alibaba release). См. ADR-025. Оригинальные ограничения роли сохраняются с добавлением mode-specific operational caveat. Closing note для qwen3.5 — в §Closing note.

---

## Контекст (initial, 2026-04-17)

До Ollama 0.20.x у `qwen3.5:35b` tool calling был сломан (GitHub issues #14493, #14745, #14662). Модель находилась в статусе **Legacy** в паспорте v30, с пометкой "кандидат на удаление (wave 2)".

После обновления Ollama до 0.20.7 проведена re-validation (отчёт 2026-04-16, 10-шаговый протокол). Результаты:

| Проверка | Результат |
|----------|-----------|
| Plain chat | PASS |
| Bounded review discipline | PASS (слабо, формат частично удержан) |
| Tool calling smoke | PASS |
| Full tool loop | PASS |
| **Tool obedience under soft constraint** | **FAIL** — модель посчитала сама вместо вызова tool |
| Forced tool_choice | PASS |
| Strict bounded review format | PASS |
| Minimal rewrite | STRONG PASS |
| Minimal bug fix | PASS |

IDE re-validation (отчёт 2026-04-17):
- First-pass review: слабая приоритизация дефектов, упускает главные correctness bugs
- Recoverability after feedback: хорошая
- Bounded execution с narrow prompt (code-only, no refactor, no robustness extras): **стабильно PASS**
- Spacing-only fix, minimal bug fix на реальном файле: PASS
- Mixed-format (bullets + code): drift — formatting artifacts `Javascript` / `Apply`

## Контекст (v2 supersession, 2026-04-19)

Релиз официального Alibaba Qwen3.6-35B-A3B (2026-04-16) предоставил архитектурный upgrade над тем же Qwen3.5 base с native `qwen3_coder` tool-call parser и thinking preservation. Interim agent contour validation (2026-04-19) подтвердила паритет на golden set из 7 сценариев. IDE validation gate (ADR-022 protocol) прошёл после корректировки первоначальных fail-ов как contaminated runs, prompt design flaws, mode-specific artifacts.

Freshness probe показал паритет horizon (≈ март 2025 для обеих моделей) — upgrade нейтрален по знаниям.

**Следствие:** role carrier меняется, но определение роли и её ограничения остаются в силе — они являются архитектурными границами Bounded Executor концепции, не специфичными для qwen3.5.

## Решение (consolidated)

**Bounded Executor role definition (роль, не модель):**

Role: **Bounded Executor** — специализированная узкая роль в routing policy, отличная от "Agent", "Reviewer", "Planner".

**Что делает bounded executor:**
- Точечные правки кода по явной инструкции (bug fix, spacing, type hints, boundary conditions)
- Narrow-scope refactor с явным запретом на robustness/validation extras
- Correction loop после targeted feedback
- Output: code-only, без комментариев и объяснений, если не просят

**Что bounded executor НЕ делает:**
- **First-pass review** — слабая приоритизация дефектов. Reviewer остаётся gemma4:31b или qwen3-coder:30b.
- **Agent mode с tool_choice: auto** — soft tool obedience fail. Agent остаётся qwen3-coder:30b + gemma4:31b.
- **Mixed-format ответы** (bullets + code) — drift формата.
- **Autonomous execution без supervisor** — нужен pass через reviewer.

**Role carrier (current, v2): qwen3.6:35b-a3b-q4_K_M** (official Alibaba release, 2026-04-19).

**Role carrier (superseded, v1): qwen3.5:35b** — Reserve status, disk-retained for rollback (см. ADR-025).

**Routing на уровне pipeline (unchanged):**

```
Schema:     Reviewer → Bounded Executor → Reviewer
            (gemma4:31b → qwen3.6:35b-a3b-q4_K_M → gemma4:31b)
            [ранее v31: qwen3.5:35b в executor позиции]
```

qwen3-coder:30b остаётся primary strict executor и Agent. Bounded Executor — дополнительный executor для случаев, когда qwen3-coder занят или когда нужен более narrow профиль (qwen3-coder склонен к большему output, чем просили).

## Operational caveat (new in v2)

**Specific to qwen3.6:35b-a3b-q4_K_M:**

В одном зафиксированном сценарии при non-agent current-file edit path модель вернула "I don't have access to see which file is currently open...". В agent mode аналогичной проблемы не наблюдалось. Это mode-specific inconsistency, не общая disabling характеристика.

**Обходы при возникновении проблемы:**
1. Явно передать содержимое через selection + `/edit` (не надеяться на неявный currentFile ingestion)
2. Переключиться в agent mode для file-aware bounded tasks
3. Использовать `@Current File` или `@File` context provider в Chat path

**Mitigation в rules (02-coding.md):** раздел "Bounded Executor invocation contract" документирует эти обходы явно.

## Принцип

**Capability retention без исключений governance.** Модель (теперь qwen3.6) имеет подтверждённую уникальную роль через документированный gate. Политика ADR-019 (role-driven retention) применяется: роль уникальна, не дублирует gemma4:31b и не дублирует qwen3-coder:30b.

**Role persistence across carrier changes.** Роль Bounded Executor определена архитектурно (narrow prompt contract, code-only output, correction loop). Model carrier может меняться по upgrade-путям (v1: qwen3.5:35b → v2: qwen3.6-A3B). Определение роли и её ограничения при этом сохраняются.

## Следствия

**Паспорт v32:**
- qwen3.5:35b: Active (Bounded Executor) → Reserve (previous Bounded Executor, disk-retained for rollback).
- qwen3.6:35b-a3b-q4_K_M: добавляется как Active Bounded Executor.
- §11 changelog: v32 entry.

**Архитектура v1.18 §2.1:**
- Tier 1 routing table: qwen3.6 в строке Bounded Executor.
- qwen3.5:35b → Tier 3 Reserve.

**Continue.dev config.yaml:**
- Модель `qwen35` (qwen3.5:35b) удаляется из active entries.
- Добавляется `qwen36-bounded` (qwen3.6:35b-a3b-q4_K_M) с `roles: [edit]`.

**02-coding.md rule:**
- Раздел "Bounded Executor invocation contract" — narrow prompt contract + operational caveat про mode-specific current-file.

**pipelines.yaml:**
- Опциональный pipeline `bounded-fix`: executor=qwen3.6:35b-a3b-q4_K_M (pending implementation).

## Tech debt

- В Continue.dev нет понятия "bounded executor" как отдельной роли. Это контекстная классификация — пользователь должен знать, что `/edit` с qwen36-bounded ожидает narrow prompt, иначе будет drift.
- Раздел "Bounded Executor invocation contract" в `02-coding.md` должен быть добавлен при применении v32 (см. отдельный snippet).
- Root cause mode-specific non-agent current-file inconsistency для qwen3.6 не установлен (Open question #44 в архитектуре v1.18).

## Closing note для qwen3.5 (role vacated)

**Status:** qwen3.5:35b vacates Bounded Executor role, переводится в Reserve.

**Rationale:** замена не из-за failure (ADR-019 "failed models" политика **не применяется**), а по upgrade-пути на архитектурно улучшенный qwen3.6 с passed IDE validation gate.

**Retention semantics:** rollback insurance, не reserve lane для failures. Формальное прекращение retention qwen3.5 — при 30 днях стабильной эксплуатации qwen3.6 в Bounded Executor роли без инцидентов, либо при необходимости освободить диск для wave 2 evaluation.

**Historical context retained:** re-validation отчёты 2026-04-16 и 2026-04-17 сохраняются как архивные свидетельства — они документируют Legacy→Active пересмотр, который был методологически корректен в своё время. Они не invalidate роль Bounded Executor в целом — меняется только carrier.

## Связанные

- [[ADR-012 Gemma 4 Model Integration]] — предшествующая routing policy
- [[ADR-019 Model retention role-driven]] — governance
- [[ADR-022 Mandatory IDE validation gate]] — validation protocol
- [[ADR-023 A3B MoE output envelope risk]] v2 — class risk (model-specific override для официального Qwen3.6)
- [[ADR-025 Replace qwen3_5 with qwen3_6 in Bounded Executor role]] — supersession ADR
- [[73 Tool obedience under soft constraint]]
- [[76 Knowledge cutoff gate practical vs declared freshness gap]]
- Отчёт `report_gemma_qwen35_for_claude_2026-04-16.md`
- Отчёт `today_full_report_for_claude_qwen36_qwen35_ide_gateway.md` §9–10
- IDE validation report: `qwen36_ide_validation_corrected_report_2026-04-19.md`
