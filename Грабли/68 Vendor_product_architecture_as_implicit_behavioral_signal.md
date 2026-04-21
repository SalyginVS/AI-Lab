---
tags: [grabli, canonical, governance, model-intake, vendor-signals]
дата: 2026-04-19
этап: v33
статус: Active
компонент: Model intake protocol
связано: [ADR-022, ADR-026, §7.13]
---

# Грабли #77: Vendor product architecture as implicit behavioral signal

## Симптом

При оценке модели опираешься на:
- Model card claims (metrics, positioning, capabilities)
- Benchmark scores (SWE-Bench, MMLU, function calling success rate)
- Release announcements

Берёшь модель под целевую роль на основании этих сигналов. Через неделю эксплуатации обнаруживаешь, что модель системно не подчиняется hard instructions — и это документированное поведение, зафиксированное множеством других пользователей.

**Наблюдённый случай (2026-04-19):**

- qwen3-coder:30b имела в паспорте v32 роли: Primary Agent, Best Strict Executor, Fast Semantic Agent.
- Model card и release materials: "autonomously executing complex engineering workflows", "agentic coding supporting for most platform such as Qwen Code, CLINE", "significant performance on agentic coding".
- Benchmark: 26+ tools function calling PASS, SWE-Bench high scores.
- **Реальность в эксплуатации:** игнорирует numbered-step prompts с approval gates, scope creep на соседние задачи, autonomous destructive modifications.

## Root cause

Model cards и benchmarks **не покрывают** instruction-following discipline в agentic workflows. Они измеряют:
- Raw capability (can the model call tools? solve tasks?)
- Task completion quality (does the resulting code work?)

Они **не измеряют**:
- "Does the model stop and ask permission when instructed to?"
- "Does the model stay in scope when explicitly bounded?"
- "Does the model refuse autonomous execution when workflow forbids it?"

Поэтому модель, тренированная под reward signal "complete the task autonomously", будет иметь высокие benchmark scores и при этом системно нарушать workflow constraints.

## Скрытый сигнал в vendor product architecture

**Ключевое наблюдение:** если vendor модели сам строит over-the-model infrastructure для compensation за model behavior — это **implicit admission** того, что модель сама по себе этот класс поведения не держит.

**Конкретный пример: Qwen Code CLI four-tier approval system.**

Qwen team (вендор qwen3-coder:30b) выпустила Qwen Code CLI с четырьмя approval режимами:

1. **Plan Mode** — read-only analysis only. No file editing, no shell commands.
2. **Default Mode** — manual approval required for EVERY file edit and shell command.
3. **Auto-Edit Mode** — file editing auto-approved, shell manual.
4. **YOLO Mode** — everything auto-approved.

**Вопрос:** зачем модели, которая (по model card) корректно выполняет agentic coding workflows, нужна четырёхуровневая approval architecture поверх неё?

**Ответ:** потому что модель **без этой infrastructure** ведёт себя как YOLO по default — выполняет все file changes и shell commands без остановки. Vendor это знает и строит compensating infrastructure, но в model card это не пишет. Наоборот, позиционирует модель как "autonomous execution".

## Правило (new governance principle §7.13)

**Перед назначением модели в роль с instruction-following requirement, проверяй три источника:**

1. **Model card claims** — standard sign.
2. **Independent bug reports** (GitHub issues на vendor repository) — особенно критично, ищи ключевые слова "ignore", "doesn't follow", "autonomous", "without approval", "destroys", "unauthorized".
3. **Vendor product architecture** — если vendor строит multi-tier approval / permission / scoping infrastructure поверх модели, это implicit model-level limitation signal. Читай не только model card, но и documentation для vendor-branded CLI / agent product, если он есть.

**Если источник (3) показывает compensating infrastructure — это red flag**, даже если источники (1) и (2) нейтральны. Infrastructure не строится "на всякий случай" — она строится когда есть operational problem.

## Матрица проверки для active и будущих моделей

**Retrospective audit (v33):**

| Модель | Vendor product architecture signal | Conclusion |
|--------|-----------------------------------|-----------|
| qwen3-coder:30b | Qwen Code CLI four-tier approval | **Red flag triggered** → ADR-026 narrow role |
| qwen3.6:35b-a3b-q4_K_M | Qwen Code supports, но модель positioned под "stay coherent across steps, iterative development" | **Neutral** → compliance confirmed in probe |
| gemma4:31b | Google Vertex AI tooling (enterprise-oriented), но no equivalent over-model approval system | **Neutral** → compliance confirmed in probe |
| qwen3.5:9b, qwen2.5-coder:7b | Too small for agent роли, FIM/commit-msg narrow роли | **N/A** — narrow-scope, instruction-following less critical |
| qwen3-coder-next:q4_K_M | Та же vendor infrastructure (Qwen Code), **80B heavy-class** — может быть более агрессивна в autonomous behavior | **Red flag expected** → при wave 2 evaluation ожидать тех же паттернов что qwen3-coder:30b |
| gpt-oss:20b | OpenAI ecosystem — нет over-model approval infrastructure от vendor для этой модели | **Signal missing** — нужен прямой probe |
| glm-4.7-flash | Zhipu ecosystem, нет documented four-tier approval system | **Neutral** → semantic overreach от Post-R tests остаётся основным known issue |
| gemma4:e4b | Google Vertex AI — see gemma4:31b row | **Neutral** |

## Применимость

**Всегда применяется** (дополнение к Грабли #76 knowledge cutoff gate):

Intake protocol теперь требует (ADR-022 расширяется):
1. Model card review (pre-existing)
2. Knowledge cutoff gate (Грабли #76)
3. **Vendor product architecture scan (Грабли #77)** — новый обязательный шаг
4. Hard instruction probe test (новый в ADR-022)
5. IDE validation gate (pre-existing ADR-022)

## Как выполнять vendor product architecture scan

**Для каждой новой модели в intake:**

1. Найти vendor's primary product (CLI / agent / IDE plugin) для этой модели:
   - Qwen → Qwen Code, Qwen-Agent
   - Google → Gemini CLI, Vertex AI tooling
   - OpenAI → Codex, ChatGPT desktop agents
   - Anthropic → Claude Code
   - DeepSeek → DeepSeek agent
   - Zhipu → GLM agent / ChatGLM CLI
2. Прочитать documentation на approval modes, permission systems, scoping mechanisms
3. Зафиксировать результат в intake form:
   - "Vendor имеет multi-tier approval system → red flag для instruction-following discipline"
   - "Vendor имеет single-mode no-approval architecture → нейтральный сигнал"
   - "Нет vendor product → сигнал missing, требуется прямой probe"

## Tech debt

- **Поиск GitHub issues** — manual через web search. Автоматизация через GitHub API возможна, но non-trivial из-за rate limits + pagination.
- **Vendor product documentation discovery** — без каталога vendor product → model mappings. Нужен local registry: vendor → primary product URL → approval architecture summary.
- **Retrospective audit для старых моделей** — провести при следующей ревизии (предположительно wave 2 evaluation).

## Ограничения

- **[A]** Absence of over-model approval infrastructure **не гарантирует** instruction-following compliance. Это **неполный** сигнал. Прямой probe (ADR-022 IDE gate) всё равно обязателен.
- **[A]** Vendor может не релизить product CLI параллельно с model release. Signal отсутствует — не означает что модель безопасна.
- **[F]** Vendor может релизить model без over-model infrastructure **именно потому, что** хочет продать enterprise infrastructure отдельно (upsell). В этом случае отсутствие over-model approval system ≠ позитивный сигнал о модели — это бизнес-решение vendor.

## Связанные

- [[ADR-022 Mandatory IDE validation gate]] — расширяется на vendor scan
- [[ADR-026 qwen3-coder demotion from Agent/Strict Executor roles]] — первое применение принципа
- [[76 Knowledge cutoff gate]] — companion governance gate в intake
- Qwen Code approval modes documentation: https://qwenlm.github.io/qwen-code-docs/en/users/features/approval-mode
- GitHub issues QwenLM/qwen-code #354, #494, #674, #1108, #1301 (external evidence для ADR-026)
