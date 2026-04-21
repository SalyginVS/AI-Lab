---
tags: [adr, canonical, routing, модели, instruction-following]
дата: 2026-04-19
этап: v33
статус: Accepted
компонент: Model Routing Policy
связано: [ADR-012, ADR-019, ADR-021 v2, ADR-022, ADR-025, Грабли #77]
---

# ADR-026: qwen3-coder:30b demotion from Agent/Strict Executor roles

## Контекст

**Предшествующее состояние (v32):** qwen3-coder:30b имела роли:
- Primary Agent (после v31)
- Best Strict Executor (code + SQL)
- Best SQL Executor (plain text-to-sql)
- Fast Semantic Agent / Tool Selector (после удаления gemma4:26b)

Эти роли были назначены на основании raw tool calling success rate (26+ tools, function calling PASS), SQL benchmark (SA 75-90%), и предположения о "strict" instruction-following, соответствующей ярлыку "coder".

**Триггер пересмотра (2026-04-19):**

В ежедневной эксплуатации Vladimir обнаружил **систематическое нарушение hard instructions** со стороны qwen3-coder:30b:

1. **Ignored approval gates.** Структурированный prompt с numbered steps + явный "Обязательно!" на шаге "запроси разрешение перед изменениями" → модель переходит к изменениям файлов без запроса.
2. **Scope creep.** Промпт "работать только с Task 2" → модель продолжает с другими задачами без запроса.
3. **Pattern repeatability.** Поведение наблюдается **независимо от промпта** — не единичный случай, не harness-specific.

**Диагностический A/B (2026-04-19, `reasoning_effort: "none"` у всех):**

| Модель | Тот же структурированный промпт | Hard instruction compliance |
|--------|---------------------------------|----------------------------|
| qwen3.6:35b-a3b-q4_K_M | Запрашивает разрешение в Шаге 8, останавливается | **PASS** |
| gemma4:31b | Запрашивает разрешение в Шаге 8, останавливается | **PASS** |
| qwen3-coder:30b | Игнорирует Шаг 8, выполняет изменения | **FAIL** |

Thinking mode отключён для всех трёх — различие не в runtime reasoning, а в model-level instruction-following discipline.

**External confirmation (GitHub issues в QwenLM/qwen-code):**

- Issue #354 "CRITICAL: Qwen Coder agent destroys working builds" — autonomous destructive mode, unauthorized modifications to working code, repeatable pattern
- Issue #494 "Qwen Code CLI Ignores qwen.md Instructions During Task Execution" — systematic failure to follow QWEN.md rules during tasks
- Issue #674 "QWEN CLI ignores rules" — rules in QWEN.md systematically ignored
- Issue #1108 "not following global rules, not listening at all" — global rules ignored
- Issue #1301 "Qwen-Code doesn't respect QWEN.md rules" — instructions in QWEN.md ignored after explicit addition

**Vendor product architecture signal:**

Qwen team сама строит over-the-model **four-tier approval system** в Qwen Code CLI (Plan / Default / Auto-Edit / YOLO). Это **косвенный admission** того, что модель сама по себе approval gates не держит — иначе compensating infrastructure не требовалась бы. См. Грабли #77 (Vendor product architecture as implicit behavioral signal).

## Решение

**qwen3-coder:30b демотируется из следующих ролей:**

| Роль | Прежний carrier (v32) | Новый carrier (v33) | Обоснование |
|------|----------------------|---------------------|-------------|
| Primary Agent | qwen3-coder:30b | **qwen3.6:35b-a3b-q4_K_M + gemma4:31b (tandem)** | Оба PASS на hard instruction compliance, нативные tool calling, distinct strengths (speed/iterative vs quality/reasoning) |
| Best Strict Executor | qwen3-coder:30b | **qwen3.6:35b-a3b-q4_K_M** | qwen3.6 уже Bounded Executor (ADR-025); "strict" без instruction discipline — оксюморон, метка перешла естественно |
| Fast Semantic Agent / Tool Selector | qwen3-coder:30b | **gemma4:31b** | Возврат роли: она была у gemma4:26b до v31, передана qwen3-coder после удаления gemma4:26b, теперь возвращается к gemma4:31b |

**qwen3-coder:30b остаётся Active в narrow non-agent ролях**, где instruction-following discipline не критична:

| Сохраняемая роль | Обоснование safety |
|------------------|-------------------|
| Strict Executor (bounded, code-only, narrow scope, **no tool access**) | Нет tool access → нечего нарушать; scope-locked output ограничивает disobedience до output формата |
| `docs-generate` pipeline executor | Single-shot генерация документации в sandbox; disobedience структурно ограничена scope |
| `commit-msg` pipeline (backup к qwen3.5:9b primary) | Shortform output, scope-locked до commit message |
| Best SQL Executor (plain text-to-sql) | SQL generation — single-shot, SA 75-90% benchmark подтверждён, disobedience структурно ограничена запросом |

**qwen3-coder:30b ЗАПРЕЩЕНО использовать:**

- Agent mode в Continue.dev (любой)
- Pipeline с tool access
- Bounded Executor в IDE path
- Автономная работа с file modifications

## Принцип

**Instruction-following discipline — orthogonal dimension к coding capability.** Модель с высоким coding benchmark score (qwen3-coder: SWE-Bench, function calling success rate) может **не проходить** на hard instruction compliance. Эти два измерения независимы, и routing должен учитывать оба — не только первое.

**Vendor positioning как planning signal:** qwen3-coder positioned как "autonomously executing complex engineering workflows" (Together AI release page). Это **explicit design intent** под autonomous task completion, не под constrained workflow. Модели, позиционированные на iterative coherent workflow (qwen3.6 "stay coherent across steps", Gemma 4 как general-purpose with thinking), имеют другой profile instruction-following.

**Narrow role retention vs full removal:** модель имеет реальные сильные стороны (SQL 75-90%, fast tool calling для bounded use cases). Удаление 18 ГБ не освобождает значимого ресурса при текущем 709 ГБ free. Narrow active retention — более разумный outcome, чем эмоциональное удаление после обнаружения failure mode.

## Следствия

### Паспорт v33

- §5.2 model table: qwen3-coder:30b роль изменяется с "Best Strict Executor / Agent (primary) / Best SQL Executor" на "**Narrow Strict Executor (no tool access, scope-locked) / Best SQL Executor (plain) / docs-generate / commit-msg backup. НЕ Agent, НЕ Bounded Executor, НЕ tool-access workflow.**"
- qwen3.6:35b-a3b-q4_K_M расширяет scope: "Bounded Executor + **Primary Agent** (tandem с gemma4:31b) + **Best Strict Executor**".
- gemma4:31b расширяет scope: "Quality-first Agent / Planner / Reviewer / Primary Reasoner + **Primary Agent tandem** + **Fast Semantic Agent / Tool Selector** (возврат от qwen3-coder)".
- §11 changelog: v33 entry.

### Архитектура v1.19

- §1.3 статусы: carrier updates в Tier 1 table.
- §2.1 Tier 1 routing table: три строки обновлены (gemma4:31b, qwen3.6, qwen3-coder).
- §2.1 ADR-026 блок добавлен.
- §6 open questions: #46 (ADR-027 server-side approval gate — backlog as [Weak Signal]).
- §7.13 новый governance принцип (Vendor product architecture as implicit behavioral signal).
- §8 журнал ревью: v1.19 entry.

### Continue.dev config.yaml

- Новая запись `qwen36-agent` с `roles: [agent, chat]` (qwen3.6 как Primary Agent carrier).
- Существующая запись `qwen36-bounded` с `roles: [edit]` остаётся (Bounded Executor role).
- qwen3-coder:30b запись: `roles: [edit]` только (снимается Agent role) — narrow executor без tool access.
- gemma4:31b запись: сохраняется `roles: [chat, agent]` (Agent tandem).

### 02-coding.md rule

- Новый раздел "Model selection for agent-capable tasks":
  - Agent mode (tool access): **qwen3.6 или gemma4:31b ТОЛЬКО**. qwen3-coder:30b в Agent mode запрещён.
  - Bounded Executor (narrow edit): qwen3.6 или qwen3-coder (narrow, scope-locked).
  - Quality-first review / planning: gemma4:31b.
  - SQL generation: qwen3-coder:30b (single-shot, bounded).
- Явная запись "DO NOT use qwen3-coder:30b in agent mode or with tool access".

### pipelines.yaml

- `plan-execute-review`: planner=gemma4:31b, executor=**qwen3.6:35b-a3b-q4_K_M** (was qwen3-coder:30b), reviewer=gemma4:31b.
- `execute-review`: executor=**qwen3.6:35b-a3b-q4_K_M** (was qwen3-coder:30b), reviewer=gemma4:31b.
- `docs-generate`: executor=qwen3-coder:30b **сохраняется** (single-shot, scope-locked — disobedience ограничена структурно).
- `commit-msg`: executor=qwen3.5:9b (unchanged).
- `review-only`: reviewer=gemma4:31b (unchanged).
- Новый опциональный `bounded-fix`: executor=qwen3.6:35b-a3b-q4_K_M (с v32 plan, carrier подтверждён).

## Tech debt

- **qwen3-coder:30b в SQL роли** — поведение в single-shot plain text-to-sql не должно демонстрировать disobedience (structurally bounded). Но при расширении до agent-based SQL workflow эта allocation требует пересмотра.
- **Continue.dev не имеет нативной approval-mode системы** как Qwen Code CLI. Enforcement через rules — best-effort, не hard barrier. Для enterprise транспозиции — см. Open question #46 (ADR-027 backlog).
- **Автоматизированный instruction-following test** отсутствует в benchmark matrix. Текущий probe — manual (структурированный prompt с numbered steps + explicit approval gate, ручная проверка compliance). Добавление к ADR-022 IDE validation gate — тех. долг. См. Open question #40 (эталонный набор IDE test files).

## Ограничения применения

- Решение основано на **local A/B probe (3 модели, 1 промпт-шаблон) + external bug reports**. Не является large-scale statistical evaluation.
- Применимо к `qwen3-coder:30b` в текущей Ollama сборке (Q4_K_M). Другие квантовки, FP8/FP16 варианты, Qwen3-Coder-Next (80B A3B) — не покрываются этим ADR и должны валидироваться отдельно.
- qwen3.6 и gemma4:31b PASS подтверждён на `reasoning_effort: "none"`. При включении thinking mode поведение может измениться в любом направлении — требует отдельной проверки при любом routing change.

## Связанные

- [[ADR-012 Gemma 4 Model Integration]] — superseded в части role allocation для qwen3-coder:30b
- [[ADR-019 Model retention role-driven]] — governance применяется: qwen3-coder не failure, but role-narrowing
- [[ADR-021 v2 Bounded executor role carrier change]] — context для Bounded Executor role
- [[ADR-022 Mandatory IDE validation gate]] — instruction-following test должен быть добавлен в gate
- [[ADR-025 Replace qwen3.5 with qwen3.6 in Bounded Executor role]] — qwen3.6 compliance evidence
- [[77 Vendor product architecture as implicit behavioral signal]]
- GitHub issues QwenLM/qwen-code: #354, #494, #674, #1108, #1301
- Qwen Code four-tier approval architecture: https://qwenlm.github.io/qwen-code-docs/en/users/features/approval-mode
