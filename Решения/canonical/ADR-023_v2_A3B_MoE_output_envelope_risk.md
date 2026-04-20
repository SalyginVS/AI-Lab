---
tags: [adr, canonical, modeli, moe, a3b, architecture-risk]
дата: 2026-04-17 (initial), 2026-04-19 (v2 model-specific override)
этап: Post-R (initial), v32 (v2)
статус: Accepted, с model-specific override для official Qwen3.6-35B-A3B
компонент: Model architecture assessment
---

# ADR-023 v2: A3B MoE output envelope risk

> **v2 update (2026-04-19):** Добавлен model-specific override для **official Alibaba Qwen3.6-35B-A3B** (passed IDE validation gate, ADR-025). A3B class risk **остаётся активен** для community variants и wave 2. См. §Model-specific override.

---

## Контекст (initial, 2026-04-17)

В сессии 2026-04-17 протестированы две MoE-модели с архитектурой A3B (Active 3B из общих ~30B parameters):

**Qwen3.6-35B-A3B (community `qwen36-35b-a3b-q4km-fix:latest`):**
- Gateway benchmark: 5 из 10 шагов soft FAIL на output envelope (wrong bullet marker, extra fenced blocks, leading whitespace)
- IDE: open-file context failure, thinking stall, format artifacts
- Final: reject for IDE

**Nemotron3-Nano-30B-A3B (`nemotron3-nano-30b-a3b-q4km:latest`):**
- Reasoning leakage (`/no_think` не даёт clean bounded control)
- Format artifact `\n\`\`\`\`\`\`` в ответах
- Отмечена как experimental, не тестировалась дальше

Два независимых релиза от разных вендоров (Alibaba Qwen community fix + NVIDIA Nemotron) с одинаковой архитектурой A3B показали **один и тот же класс проблем**:
- нарушение output envelope (лишние обёртки, неправильные маркеры, whitespace drift)
- слабая дисциплина thinking mode
- нестабильность при strict-format промптах

Это не совпадение двух плохих моделей, это закономерность класса архитектуры под текущим runtime.

Для сравнения, dense-модели схожего размера (gemma4:31b, qwen3-coder:30b) и MoE не-A3B модели (gemma4:26b — MoE 25.8B total, но **не** A3B) таких паттернов не демонстрируют.

## Гипотеза (A — Assumption, не F)

**A3B роутинг в inference time выбирает "не того" эксперта под strict-format промпты.** A3B-архитектура активирует 3B параметров на токен через gating router. Router обучен на общей дистрибуции, в которой markdown fences, bullet points, code-only output встречаются в определённых контекстах. Под strict-format инструкцией router может активировать эксперта, оптимизированного для "пишущего поясняющий код в обёртке", вместо "отдающего raw code без обёртки". Это гипотеза — без доступа к router internals она не верифицируема, но observable behavior pattern согласуется.

Альтернативная гипотеза: проблема в quantization (Q4_K_M) — при агрессивном сжатии MoE router может терять точность распределения. Dense-модели при той же quantization страдают равномерно, а MoE неравномерно теряют по экспертам.

Третья гипотеза (добавлена в v2): проблема в **community post-training tuning** — community "fix" варианты могут применять модификации template/tokenizer config, которые ломают envelope discipline по-разному. Official release от вендора имеет canonical template, что объясняет различие в IDE validation между community fix и official release того же base.

Все три гипотезы согласуются с наблюдениями. Решение не требует различения причин — достаточно факта паттерна.

## Решение (initial, сохранено)

**A3B MoE-модели получают особый протокол валидации**, отличающийся от dense-моделей:

1. **Порядок тестирования инвертирован.** Для dense-моделей: gateway-тест → IDE-тест. Для A3B: **IDE-тест first**, gateway-тест вторым. Причина: если модель не держит output envelope в IDE, дальше тестировать нет смысла.

2. **Ужесточённый output-envelope test в gateway-фазе:**
   - Ровно 3 bullet points с маркером `-` (не `*`, не `•`) — PASS только при точном совпадении
   - Raw code без fenced block на явный запрос "return code only, no markdown" — PASS только при отсутствии \`\`\`
   - One-word answer без leading/trailing whitespace — PASS только при exact match
   - Minimum 4 из 4 hard-pass на envelope-тестах

3. **Thinking mode explicit test:** `/no_think` или эквивалент — проверять, что reasoning не leak в финальный ответ. Nemotron показал, что флаг может не работать — это sufficient fail.

4. **Context ingestion test:** дать модели системный промпт с явным блоком "currentFile" + запрос "review this file". Если модель не видит блок — reject for IDE роли. Обходной путь через Continue.dev rules возможен, но должен быть проверен отдельно (см. [[74 Open-file context ingestion failure MoE]]).

5. **Принятие решения:** A3B модель может получить Active статус **только** через passed IDE validation gate (ADR-022) с применением ужесточённого протокола. При FAIL — non-IDE роли или удаление.

## Model-specific override (new in v2, 2026-04-19)

**Applicable to:** `qwen3.6:35b-a3b-q4_K_M` — **official Alibaba Qwen3.6-35B-A3B release** (HuggingFace: `Qwen/Qwen3.6-35B-A3B`, Apache-2.0, 2026-04-16).

**Gate status:** PASSED.

**Evidence:**

1. **Interim agent contour validation (2026-04-19):** 7/7 golden scenarios PASS в headless bounded agent loop, паритет с qwen3.5:35b на том же наборе. Tool discipline, sandbox boundaries, overreach blocking, multi-step repair — все подтверждены.

2. **IDE validation gate (ADR-022 protocol, 2026-04-19):** passed после корректировки первоначальных fail-ов. Первоначальный "overall fail" был переоценён как смесь contaminated runs + prompt design flaws + mode-specific artifacts. Нормализованные повторы prove viability.

3. **Mode-specific operational nuance зафиксирован:** non-agent current-file edit path в одном scenario вернул "I don't have access to see which file is currently open...". В agent mode проблемы не воспроизводится. Это **operational caveat**, не disabling failure — документирован в ADR-025 и ADR-021 v2 с обходами (selection + `/edit`, agent mode switch, `@Current File` context provider).

**Differentiation from initial observations:**

| Атрибут | `qwen36-*-fix` (ADR-023 initial) | `qwen3.6:35b-a3b-q4_K_M` (official, v2) |
|---------|----------------------------------|-----------------------------------------|
| Источник | Community "fix" вариант | Official Alibaba post-trained release |
| GGUF mainтейнер | community | Alibaba Qwen team (реэкспорт через Ollama) |
| Template / tokenizer config | community modifications (подозреваются) | canonical |
| IDE validation gate result | FAIL (5/10 gateway soft FAIL, context failure, stall) | PASS (нормализованные повторы) |
| Решение | Reject, удалена из inventory | Accepted for Bounded Executor role (ADR-025) |

## Остающийся класс риск

**ADR-023 class risk остаётся активен для:**

- Community GGUF variants (bartowski, unsloth, TheBloke, ad-hoc "fix" форки) — каждый требует отдельной валидации через ADR-022 gate, override не транзитивен.
- Other A3B models в wave 2 консолидации: `qwen3-coder-next:q4_K_M` (79.7B, qwen3next arch — **не та же архитектура**, но похожий A3B класс), `gpt-oss:20b` (A3B статус не подтверждён), `nemotron` family.
- Future A3B releases до individual validation.

**Принцип override:** IDE validation gate PASSED для конкретного binary ≠ class risk deactivated. Класс риска меняется только при накоплении **3+ independent A3B releases с PASS** (currently: 1 — Qwen3.6 official). До этого — protocol действует как default, override — per-model.

## Принцип (consolidated)

**Архитектурный класс — это предиктор риска, но не заменяет individual validation.** Класс остаётся предиктором: новая A3B модель по-прежнему проходит ужесточённый протокол. Индивидуальная модель может пройти gate и получить override для своей роли. Класс risk **не деактивируется** прохождением одной модели — это не inductive evidence, а per-instance exemption.

Это согласуется с enterprise подходом к risk management: индивидуальный актив может пройти due diligence и быть принят, но класс assets остаётся в категории elevated scrutiny до накопления статистической базы.

## Следствия

**Паспорт v32 §5:**
- qwen3.6:35b-a3b-q4_K_M добавлен как Active (Bounded Executor, ADR-025) с явной пометкой: A3B class risk — model-specific override действует, individual passed ADR-022 gate.
- §5 classification protocol note дополняется: "A3B models — individual override возможен через passed ADR-022 gate; class risk активен до 3+ PASS в classification protocol".

**Архитектура v1.18 §2.1:**
- Tier 1: qwen3.6 добавлена с пометкой "A3B, individual ADR-023 override".
- §6 open questions: #41 (A3B root cause router vs quantization) остаётся открытым; #44 mode-specific non-agent current-file inconsistency — новый.
- §7.10 governance: формулировка дополнена — "override per-instance, class risk deactivates only at N≥3 independent passes".

**IDE validation gate runner (tech debt):**
- Требуется reference test suite для повторяемости ADR-022 (Open question #40).
- Requires: 5 envelope tests + 2 context ingestion tests + 3 bounded executor tests + 4 freshness probe events.

## Tech debt

- Root cause между A (router mismatch) / B (quantization drift) / C (community template tuning) не различён. Officially released Qwen3.6 PASS vs community "fix" FAIL косвенно указывает на (C) как сильный фактор, но не исключает (A) и (B) — Nemotron community не "fix" вариант и тоже provided class observation.
- Протокол основан на 3 наблюдениях (Qwen3.6 community, Nemotron, Qwen3.6 official). Первое — FAIL, второе — FAIL, третье — PASS. Полезнее было бы иметь FP8/FP16 quants для проверки гипотезы (B), но они не доступны на single RTX 3090 (24 GB VRAM insufficient).
- IDE gate automation отсутствует — manual протокол сейчас. Это Open question #39.

## Ограничения применения (consolidated)

- **НЕ применять к** non-A3B MoE (например, gemma4:26b = MoE 25.8B total без A3B-роутинга, glm-4.7-flash = MoE 30B/3B но не A3B-архитектура в строгом смысле). Они имеют другой routing pattern и свои риски, но не этот класс.
- **НЕ применять к** dense моделям 30B+ — к ним применяется стандартный протокол ADR-022.
- **Override применяется per-instance binary.** Official Qwen3.6-35B-A3B прошёл; community "fix" того же base — нет. Переход на новый quant того же official base (FP8, FP16, другой GGUF source) — re-validation.

## Связанные

- [[ADR-019 Model retention role-driven]]
- [[ADR-022 Mandatory IDE validation gate]] — родительский протокол для всех IDE моделей
- [[ADR-025 Replace qwen3_5 with qwen3_6 in Bounded Executor role]] — первое применение override
- [[74 Open-file context ingestion failure MoE]]
- [[75 Gateway format soft FAIL эквивалентен hard FAIL]]
- Отчёт `today_full_report_for_claude_qwen36_qwen35_ide_gateway.md` §3.1, §8 (initial reject of community fix)
- IDE validation report: `qwen36_ide_validation_corrected_report_2026-04-19.md` (override evidence)
