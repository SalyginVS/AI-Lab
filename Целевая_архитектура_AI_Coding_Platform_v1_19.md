# Целевая архитектура: Локальная AI Coding Platform

**Версия:** 1.19  
**Дата:** 2026-04-19  
**Базовый стек:** Ubuntu 24.04 / RTX 3090 / Ollama 0.20.7 / gateway v0.12.0+patch / Continue.dev v1.2.22  
**Стратегия:** Continue-first platform, Depth over Speed, локальность как принцип  
**Назначение:** Лаборатория для наработки решений → перенос на Enterprise  
**Паспорт стенда:** v33.0 (2026-04-19)

> **Роль документа.** Данный файл является **source of truth** (единым источником правды) для целевой архитектуры AI Coding Platform. Он задаёт принципы, политики и ожидаемое состояние для всех реализаций платформы, включая конкретные лабораторные стенды. Документ `Паспорт_лаборатории_vX` фиксирует фактическое состояние конкретного стенда и должен согласовываться с данной целевой архитектурой. Любое расхождение между паспортом и целевой архитектурой классифицируется как технический долг и оформляется явно.

---

## 1. Целевая архитектура

### 1.1. Обзор

Платформа трансформирует текущую лабораторию (набор работающих компонентов) в управляемую инженерную систему с семью слоями. Каждый слой имеет чёткую ответственность, определённые интерфейсы и может развиваться независимо.

Ключевой принцип: **не заменять, а достраивать**. Всё, что подтверждено тестами в этапах 1–16, 13, 12, F-next, R, Post-R, остаётся. Новые компоненты добавляются поверх существующего фундамента.

Дополнительный принцип: **лаборатория = полигон для Enterprise**. Каждый компонент проектируется так, чтобы паттерн переносился на продуктовые серверы с минимальной адаптацией (другое железо, другие модели — та же архитектура).

### 1.2. Слои и их взаимодействие

```
┌─────────────────────────────────────────────────────────────────────┐
│  7. OBSERVABILITY / OPERATIONS                                      │
│     Structured logs, metrics, tool-call tracing, benchmark matrix   │
├─────────────────────────────────────────────────────────────────────┤
│  6. SECURITY / GOVERNANCE                                           │
│     Tool approval policy, denylist, auth model, audit trail         │
│     Model retention governance, context default governance          │
├─────────────────────────────────────────────────────────────────────┤
│  5. KNOWLEDGE / CONTEXT                                             │
│     Rules (3 уровня), repo map, embeddings, docs, ADR, runbooks    │
├─────────────────────────────────────────────────────────────────────┤
│  4. ORCHESTRATION / AUTOMATION                                      │
│     Sequential multi-model pipeline, headless scripts, CI/CD hooks  │
├─────────────────────────────────────────────────────────────────────┤
│  3. MCP TOOL LAYER                                                  │
│     Git (STDIO), Terminal, RAG/Docs (streamable-http), Docker       │
├─────────────────────────────────────────────────────────────────────┤
│  2. IDE AGENT LAYER                                                 │
│     Continue.dev (primary) — Chat, Edit, Agent, Apply, Autocomplete │
│     Copilot BYOK (secondary) — plain chat only                      │
├─────────────────────────────────────────────────────────────────────┤
│  1. INFERENCE / BACKEND                                             │
│     Ollama 0.20.7 → gateway v0.12.0+patch → /v1/chat/completions   │
│     + /v1/embeddings + /v1/metrics + /v1/orchestrate                │
│     DEFAULT_NUM_CTX = 131072 (ADR-020)                              │
└─────────────────────────────────────────────────────────────────────┘
                          │
                ┌─────────┴──────────┐
                │   RTX 3090 (24GB)  │
                │   + RAM (62GB)     │
                │   = ~86GB pool     │
                └────────────────────┘
```

### 1.3. Статусы компонентов платформы

Легенда статусов: **Active** — реализована и используется. **PoC** — прототип. **Planned** — не реализована. **Legacy** — требует замещения. **Deprecated** — подлежит удалению.

| Слой | Компонент | Статус | Этап реализации |
|------|-----------|--------|-----------------|
| 1. Inference/Backend | Ollama **0.20.7** + systemd | **Active** | 1–7B, 10C, 14A, **Post-R** |
| 1. Inference/Backend | gateway v0.12.0+patch (/chat/completions, /models, /health, /embeddings, /metrics, /orchestrate) | **Active** | 1–16, **Post-R (ADR-020)** |
| 1. Inference/Backend | **Gateway context policy: DEFAULT_NUM_CTX=131072 (ADR-020)** | **Active** | **Post-R ✅** |
| 1. Inference/Backend | Gemma 4: gemma4:31b (Quality-first Agent/Planner/Reviewer/Best Semantic SQL/Primary Reasoner) | **Active** | 10C, F-next, ADR-019 ✅ |
| 1. Inference/Backend | ~~Gemma 4: gemma4:26b~~ | **Deleted v31** | Reject IDE (отчёт 2026-04-16). Ниша → qwen3-coder:30b. |
| 1. Inference/Backend | Gemma 4: gemma4:e4b (Fast edge chat, evaluation) | **PoC** | 10C |
| 1. Inference/Backend | **qwen3-coder:30b (Narrow Strict Executor + Best SQL + docs-generate; demoted from Agent v33, ADR-026)** | **Active (narrowed v33)** | 7A, 11A, Post-R, v31, **v33** |
| 1. Inference/Backend | **qwen3.6:35b-a3b-q4_K_M (Primary Agent tandem + Bounded Executor + Best Strict Executor — scope expanded v33, ADR-026)** | **Active v33** | **v32, v33 ✅** |
| 1. Inference/Backend | qwen3.5:35b (Previous Bounded Executor, rollback insurance) | **Reserve v32** | v31→v32 (ADR-025) |
| 2. IDE Agent Layer | Continue.dev v1.2.22 (Chat, Edit, Agent, Apply, Autocomplete) | **Active** | 7A–7C, 9B |
| 2. IDE Agent Layer | Copilot BYOK (plain chat) | **Active** | 7D |
| 2. IDE Agent Layer | Copilot BYOK (Agent mode с локальными моделями) | **Legacy** | Нестабилен |
| 3. MCP Tool Layer | mcp-server-git | **Active** | 8A |
| 3. MCP Tool Layer | Terminal Policy (rules-based) | **Active** | 8B ✅ |
| 3. MCP Tool Layer | Custom RAG MCP | **Active** | 11 ✅ |
| 3. MCP Tool Layer | Docker MCP (server-side policy enforcement, ADR-017) | **Active** | 12 ✅ |
| 4. Orchestration | orchestrator.py v1.1.0 — CLI path | **Active** | 8C ✅ |
| 4. Orchestration | Headless scripts + git hooks | **Active** | 8D ✅ |
| 4. Orchestration | gateway /v1/orchestrate — HTTP path | **Active** | 16 ✅ |
| 5. Knowledge/Context | Rules: 3 уровня | **Active** | 7C |
| 5. Knowledge/Context | Context providers: 12 штук | **Active** | 7C, 9B |
| 5. Knowledge/Context | Embeddings: qwen3-embedding через шлюз | **Active** | 9B ✅ |
| 5. Knowledge/Context | ADR multilayer model (foundational + canonical in RAG primary) | **Active** | 13, R ✅ |
| 5. Knowledge/Context | Onboarding пакет | **Active** | 13, R ✅ |
| 5. Knowledge/Context | Security rule (03-security.md, alwaysApply) | **Active** | 13 ✅ |
| 6. Security/Governance | Mandatory per-user Bearer auth + audit trail | **Active** | 14B ✅ |
| 6. Security/Governance | UFW least-privilege | **Active** | 14A ✅ |
| 6. Security/Governance | Model retention governance: role-driven (ADR-019) | **Active** | Post-R ✅ |
| 6. Security/Governance | **Integration layer defaults governance (ADR-020)** | **Active** | **Post-R ✅** |
| 6. Security/Governance | **No reserve lane for failed models (v31)** | **Active** | **v31 ✅** |
| 6. Security/Governance | **Mandatory IDE validation gate (ADR-022)** | **Active** | **v31 ✅** |
| 6. Security/Governance | **A3B MoE class risk protocol (ADR-023)** | **Active** | **v31 ✅** |
| 6. Security/Governance | **Bounded executor role definition (ADR-021)** | **Active** | **v31 ✅** |
| 6. Security/Governance | **Role carrier change via upgrade path (ADR-025)** | **Active v32** | **v32 ✅** |
| 6. Security/Governance | **Knowledge cutoff gate in intake protocol (Грабли #76)** | **Active v32** | **v32 ✅** |
| 6. Security/Governance | **qwen3-coder:30b demotion — instruction-following discipline as routing dimension (ADR-026)** | **Active v33** | **v33 ✅** |
| 6. Security/Governance | **Vendor product architecture as implicit behavioral signal (Грабли #77)** | **Active v33** | **v33 ✅** |
| 7. Observability | Structured JSON logging | **Active** | 10A ✅ |
| 7. Observability | /metrics endpoint | **Active** | 10B ✅ |
| 7. Observability | Benchmark matrix + health-check.sh | **Active** | 15, R ✅ |
| Track F | Text-to-SQL PoC + Semantic Layer | **Active (PoC завершён)** | 11A, F-next ✅ |

---

## 2. Архитектурные решения

### 2.1. Слой 1 — Inference / Backend

**Текущее состояние (v31):**
- **Ollama 0.20.7**, systemd, override.conf (7 переменных)
- gateway v0.12.0+patch (11 модулей), **DEFAULT_NUM_CTX=131072** (ADR-020)
- **10 моделей** (R: 17→12; Post-R: −1 deepseek-r1:32b; v31: −1 gemma4:26b)
- OLLAMA_MAX_LOADED_MODELS=2, NUM_PARALLEL=1, Flash Attention, KV cache q8_0

**Решение по контекстной политике (ADR-020):**

Root cause 8K ceiling через gateway = устаревший `DEFAULT_NUM_CTX = 8192`. Модели поддерживали до 256K, `MAX_NUM_CTX` был уже 131072, но default fallback ограничивал все запросы без явного `num_ctx`. Патч: DEFAULT_NUM_CTX = 131072 в `__init__.py` и `orchestrate.py`. Валидация: gemma4:31b обработала 131K prompt tokens через gateway.

Принцип: **Integration layer defaults must match platform capability.**

**Long-context status (переоценка после ADR-020):**
- 131K validated через gateway (один успешный run)
- GPU utilization не измерен в этом run (inference, не факт)
- Повторяемая стабильность TBD
- Рутинная стабильность 4–8K на Ollama 0.20.7 TBD
- Вопросы #25 (SWA) и #32 (FA) — [A] Partially addressed, не закрыты

**Решение по маршрутизации моделей (ADR-012, обновлено v31 с routing refinement + ADR-021):**

**Tier 1 — Primary workhorses:**

| Роль | Модель | Путь | Routing policy | Этап |
|------|--------|------|----------------|------|
| **Quality-first Agent / Planner / Reviewer / Best Semantic SQL / Primary Reasoner / Primary Agent tandem (v33) / Fast Semantic Agent + Tool Selector (returned v33)** | **gemma4:31b** | шлюз | Planning, review, reasoning, semantic arbitration, long-context. **v33 scope expanded (ADR-026):** возврат Fast Semantic Agent роли (исторически gemma4:26b v31-; qwen3-coder:30b v31-v32; gemma4:31b v33-). Primary Agent tandem с qwen3.6. | 10C, F-next, ADR-019, **v33 (ADR-026)** |
| **Primary Agent tandem (new v33) / Bounded Executor (v32-) / Best Strict Executor (v33 inherited)** | **qwen3.6:35b-a3b-q4_K_M** | шлюз | **v33 scope expanded (ADR-026):** Primary Agent (tandem с gemma4:31b) после PASS на hard instruction probe. Bounded Executor: точечные правки, code-only output, correction loop. Best Strict Executor: scope-locked output. **Operational caveat:** mode-specific non-agent current-file inconsistency в edit path — в agent mode не воспроизводится, обходы в 02-coding.md (Open question #44). **A3B class risk:** individual override per ADR-023 v2. | **v32 (ADR-025), v33 (ADR-026)** |
| **Narrow Strict Executor (no tool access, scope-locked) / Best SQL Executor (plain) / `docs-generate` pipeline / `commit-msg` backup** | **qwen3-coder:30b** | шлюз | **v33 demotion (ADR-026):** снят с ролей Primary Agent, Best Strict Executor, Fast Semantic Agent из-за systematic hard instruction violations (ignores approval gates, scope creep, unauthorized modifications). External confirmation: GitHub issues QwenLM/qwen-code #354/#494/#674/#1108/#1301. Vendor product signal: Qwen Code four-tier approval (Грабли #77). **Сохраняется Active в narrow non-agent ролях** где disobedience структурно ограничена отсутствием tool access. **ЗАПРЕЩЕНО:** Agent mode, Bounded Executor IDE, любой tool-access workflow. | 7A, 11A, Post-R, v31, **v33 (ADR-026 narrowed)** |
| Autocomplete (FIM) | qwen2.5-coder:7b | Ollama напрямую | FIM autocomplete | 7B |
| Embeddings | qwen3-embedding | шлюз /v1/embeddings | Embedding queries | 9A |

**Tier 2 — Specialized:**

| Роль | Модель | Примечание |
|------|--------|-----------|
| Fast chat + light tools + commit-msg | qwen3.5:9b | Tool calling восстановлен в Ollama 0.20.0 |
| Fast edge chat (evaluation) | gemma4:e4b | PoC, частично протестирована |

**Tier 3 — Reserve / PoC:**

| Модель | Статус | Примечание |
|--------|--------|-----------|
| **qwen3.5:35b** | **Reserve v32** | Previous Bounded Executor (ADR-021 v1). Переведена в Reserve после role carrier change на qwen3.6 (ADR-025). Rollback insurance, не failure — политика "no reserve lane for failed models" не применяется. Retention до 30 дней стабильной эксплуатации qwen3.6 без инцидентов. |
| glm-4.7-flash | Reserve | Semantic overreach на SQL (Post-R). Кандидат на удаление (wave 2). Проходит через ADR-022 протокол при пересмотре. |
| qwen3-coder-next:q4_K_M | PoC | Не вытеснил qwen3-coder:30b. Проходит ADR-022 при пересмотре. |
| gpt-oss:20b | PoC | Не оценивалась. Проходит ADR-022 при пересмотре. |
| deepseek-r1:32b | **Удалена** (Post-R, ADR-019) | Reasoning покрыта gemma4:31b |
| qwen3-next:80b-a3b-thinking | **Удалена** (Post-R) | Тяжёлые MoE >50B нет ROI на single RTX 3090 (Грабли #72) |
| **gemma4:26b** | **Удалена (v31)** | Reject IDE reviewer/executor (отчёт 2026-04-16). Политика: no reserve lane. |
| **qwen36-35b-a3b-q4km-fix** | **Удалена (v31)** | Reject IDE: open-file context failure, thinking stall (Грабли #74). A3B risk (ADR-023). |
| **nemotron3-nano-30b-a3b-q4km** | **Удалена (v31)** | Reasoning leakage, broken `/no_think`, format artifact. A3B risk (ADR-023). |

**ADR-012: Gemma 4 Model Integration (10C, updated v31)**

Ролевое разделение **обновлено в v31**: gemma4:31b — Quality Agent / Planner / Reviewer / Primary Reasoner; qwen3-coder:30b — Primary Agent + Best Strict Executor (занимает также нишу fast semantic agent после удаления gemma4:26b); qwen3.5:35b — Bounded Executor (ADR-021). Первоначальная формула "Gemma semantic / Qwen strict" более не применяется — gemma4:26b удалена, qwen3-coder:30b перекрывает обе ниши при условии грамотного prompt design.

**ADR-018: Semantic Layer Architecture (F-next)** — без изменений.

**ADR-019: Удаление deepseek-r1:32b (Post-R)** — без изменений.

**ADR-020: Gateway Context Default Policy (Post-R)**

Root cause: DEFAULT_NUM_CTX=8192 создавал invisible bottleneck, маскировавшийся под upstream bug. Патч: 131072 в обеих точках. Валидация: 131K tokens. Принцип: defaults must match capability. Tech debt: orchestrate.py hardcoded.

**ADR-021: Bounded executor role for qwen3.5:35b (v31)**

qwen3.5:35b после re-validation (Ollama 0.20.x) получает новую узкую роль — bounded executor. Не Agent (soft tool obedience FAIL), не first-pass reviewer (weak defect prioritization). Роль: narrow prompts → code-only output → correction loop. Pipeline `bounded-fix` — plan опциональный.

**ADR-022: Mandatory IDE validation gate (v31)**

Gateway-only промоция в IDE-роль запрещена. Все chat-capable модели проходят IDE validation gate на реальных файлах с Continue.dev context providers до получения Active статуса. Gateway-тест (hard-pass, 8/10) — pre-condition, не финальный gate. Принцип: benchmark contract must match deployment contract. Параллелен ADR-019 и ADR-020 в логике "измерение соответствует функции".

**ADR-023: A3B MoE output envelope risk (v31)**

Два независимых A3B-релиза (Qwen3.6 community, Nemotron) показали сходный failure mode: output envelope instability + context ingestion failure. Класс архитектуры получает ужесточённый протокол ex-ante: IDE-test first, gateway envelope test второй. Не априорный отказ, но повышенная due diligence. Применяется только к A3B, не к non-A3B MoE (gemma4:26b, glm-4.7-flash — другие MoE паттерны).

**ADR-021 v2: Bounded executor role carrier change (v32)**

Роль Bounded Executor переносится с qwen3.5:35b на qwen3.6:35b-a3b-q4_K_M (official Alibaba release). Оригинальные ограничения роли сохраняются (narrow prompts, code-only, correction loop, НЕ Agent, НЕ reviewer, НЕ mixed-format). Добавлен operational caveat: mode-specific non-agent current-file inconsistency observed — обходы в 02-coding.md. Роль persistence across carrier changes — architectural invariant, carrier — replaceable.

**ADR-023 v2: A3B class risk — model-specific override (v32)**

Official Alibaba Qwen3.6-35B-A3B (не community "fix" вариант) прошёл IDE validation gate (ADR-022 protocol) после нормализации промптов и повторных прогонов. Получает individual override в Bounded Executor роли. **Class risk остаётся активен** для community variants, non-official quantizations, wave 2 кандидатов (qwen3-coder-next, gpt-oss:20b). Override деактивирует class risk только при накоплении N≥3 independent A3B passes — сейчас N=1.

**ADR-025: Role carrier change qwen3.5 → qwen3.6 (v32)**

Upgrade-path замена в Bounded Executor роли. Обоснование: interim agent contour validation (7/7 паритет), IDE validation gate passed, native `qwen3_coder` tool-call parser, thinking preservation для agent-сценариев. qwen3.5:35b переводится в Reserve — rollback insurance, не failure-based retention (политика "no reserve lane" не применяется для upgrade-path). Формальное прекращение retention qwen3.5 — при 30 днях стабильной эксплуатации qwen3.6.

**Грабли #76: Knowledge cutoff gate (v32)**

Intake governance gate, дополняющий ADR-022. Каждая новая модель получает один из трёх статусов:
- **[F]** Confirmed vendor cutoff (model card / blog post)
- **[A]** Behavioral freshness probe (4-5 verified events → practical horizon)
- **[U-accepted]** Documented unknown с operational caveat

Обосновано: practical horizon ≈ vendor cutoff − 2-3 месяца из-за training data underrepresentation tail. Для qwen3.6 (релиз 2026-04-16): behavioral probe 1/4, practical horizon ≈ март 2025 — паритет с qwen3.5. Для qwen3-coder:30b: [F] vendor cutoff 2025-06-30 (OpenRouter).

**ADR-026: qwen3-coder:30b demotion from Agent/Strict Executor roles (v33)**

Модель демотирована из Primary Agent, Best Strict Executor, Fast Semantic Agent ролей после обнаружения systematic hard instruction violations в ежедневной эксплуатации: ignoring approval gates (numbered-step промпт с "Обязательно! Запросить разрешение перед изменениями" → модель игнорирует), scope creep на непрошенные задачи, autonomous file modifications.

A/B probe 2026-04-19 с `reasoning_effort: "none"` для всех: qwen3.6 **PASS**, gemma4:31b **PASS**, qwen3-coder:30b **FAIL**. Thinking mode отключён для всех — различие на уровне model-level instruction-following discipline, не runtime reasoning.

External confirmation — документированный vendor-level паттерн: GitHub issues QwenLM/qwen-code #354 ("destroys working builds"), #494 ("ignores QWEN.md during task execution"), #674 ("systematically ignores rules"), #1108 ("not following global rules"), #1301 ("doesn't respect QWEN.md").

Модель **не удаляется** — сохранена Active в narrow non-agent ролях (SQL single-shot, docs-generate pipeline, commit-msg backup), где disobedience структурно ограничена отсутствием tool access. Политика ADR-019 "failed models → удаление" не применяется: модель не failure в абсолютном смысле, имеет документированную value в narrow contexts.

Routing перестройка: qwen3.6 → Primary Agent + Best Strict Executor (scope expanded); gemma4:31b → Primary Agent tandem + Fast Semantic Agent return.

**Грабли #77: Vendor product architecture as implicit behavioral signal (v33)**

Если vendor модели строит multi-tier approval / permission / scoping infrastructure поверх неё (пример: Qwen Code CLI имеет Plan / Default / Auto-Edit / YOLO approval modes для qwen3-coder), это **implicit admission** того, что модель сама по себе approval gates не держит. Infrastructure не строится "на всякий случай" — она строится когда есть operational problem.

Новый governance gate в intake (ADR-022 extension): vendor product architecture scan — проверка documentation для vendor-branded CLI / agent product на наличие over-model approval mechanisms. Red flag → требуется hard instruction probe test перед промоцией в instruction-following-sensitive роли.

Retrospective audit v33: qwen3-coder:30b red flag был пропущен в v31-v32 intake — ADR-026 исправляет. qwen3.6 нейтральный сигнал — vendor (Alibaba) позиционирует модель как "stay coherent across steps, iterative development", без over-model approval system. gemma4:31b нейтральный сигнал — Google Vertex AI tooling не имеет equivalent over-model approval architecture.

### 2.2–2.7 — Слои 2–7

Без структурных изменений относительно v1.16–v1.18. Ключевые обновления в v33:
- **Слой 2:** config.yaml — **9 моделей** (v33: +1 qwen36-agent для Primary Agent role, ADR-026). qwen3-coder снят до `roles: [edit]` only (demotion из Agent/chat); gemma4-31b подтверждён `[chat, agent]` (Primary Agent tandem). 02-coding.md получил раздел "Model selection for agent-capable tasks" — hard-запрет qwen3-coder в Agent mode, правила выбора модели по типу задачи.
- **Слой 4:** pipelines.yaml обновлён (v33 **реализован**): plan-execute-review и execute-review executor заменены на qwen3.6:35b-a3b-q4_K_M (ADR-026); bounded-fix pipeline добавлен (carrier qwen3.6). docs-generate сохраняет qwen3-coder:30b (narrow single-shot role). **6 pipelines** total.
- **Слой 5:** ADR-021 v2, ADR-023 v2, ADR-025, ADR-026, Грабли #76, Грабли #77 pending RAG reindex (canonical corpus: 14 → **20**).
- **Слой 6:** **Девять governance principles** (v33 добавляет два): retention role-driven (ADR-019), defaults = capability (ADR-020), no reserve for failed (v31), benchmark = deployment contract (ADR-022), arch class as risk predictor (ADR-023), role persistence across carrier changes (ADR-025), freshness awareness in intake (Грабли #76), **instruction-following discipline — orthogonal dimension к coding capability (ADR-026)**, **vendor product architecture as implicit behavioral signal (Грабли #77)**.
- **Слой 7:** health-check.sh/setup-check.sh: pending update для pipelines_count=6 (v33: +bounded-fix). IDE validation gate расширен v33: **hard instruction probe test** (numbered steps + approval gate compliance) — обязательный обоснованный дополнительный шаг, manual пока automation tech debt.

**Inventory снимок v33 (10 моделей, без изменений от v32):**
- Active (7 primary + 1 PoC): gemma4:31b, qwen3-coder:30b (narrowed v33), **qwen3.6:35b-a3b-q4_K_M** (scope expanded v33), qwen3.5:9b, qwen2.5-coder:7b, qwen3-embedding, glm-4.7-flash (Reserve), gemma4:e4b (PoC).
- Reserve (1): **qwen3.5:35b** (previous Bounded Executor, rollback insurance).
- PoC (2): qwen3-coder-next:q4_K_M (heavy class; Грабли #77 red flag expected при wave 2), gpt-oss:20b.

**Routing change log v33:**
- Primary Agent role: qwen3-coder:30b → **qwen3.6 + gemma4:31b tandem**
- Best Strict Executor: qwen3-coder:30b → **qwen3.6:35b-a3b-q4_K_M**
- Fast Semantic Agent / Tool Selector: qwen3-coder:30b → **gemma4:31b** (возврат; исторически gemma4:26b → qwen3-coder → gemma4:31b)
- qwen3-coder:30b удерживаемые роли: SQL single-shot, docs-generate pipeline, commit-msg backup (все non-agent, scope-locked).

---

## 3. Пошаговый план реализации

Все этапы Roadmap v1.0 завершены. Без новых запланированных этапов.

```
ВСЕ ТРЕКИ ЗАВЕРШЕНЫ. Ревизия R✅. Post-R✅ (ADR-019, ADR-020).
v31✅ (ADR-021, ADR-022, ADR-023, model cleanup wave 1).
v32✅ (ADR-021 v2, ADR-023 v2, ADR-025, Грабли #76, role carrier change qwen3.5→qwen3.6, Этап 019 — agent contour validation + IDE gate passed).
v33✅ (ADR-026, Грабли #77, Этап 020 — qwen3-coder demotion после hard instruction violations,
      routing перестройка, vendor product architecture gate формализован).
Roadmap из v1.0 полностью реализован. Платформа в эксплуатации.
```

---

## 4. План контроля и эксплуатации

### 4.1. Что измерять

| Метрика | Как | Порог нормы | Порог тревоги |
|---------|-----|-------------|--------------|
| TTFT | Structured log, `ttft_ms` | < 5 сек (холодный < 30 сек) | > 10 сек (горячий) |
| Tokens/sec | Structured log | > 5 t/s (30B модели) | < 2 t/s |
| Tool call success rate | finish_reason=tool_calls / total | > 80% | < 50% |
| OOM rate | 503 в логах | < 1/день | > 5/день |
| Gateway uptime | /health + systemd | > 99.5% | < 99% |
| Autocomplete latency | Ручной замер | < 2 сек | > 5 сек |
| Embedding query latency | Structured log | < 1 сек | > 3 сек |
| Model load time | Structured log | < 30 сек | > 60 сек |

### 4.2–4.3. Как измерять и реагировать — без изменений от v1.15.

---

## 5. Матрица зрелости

| Аспект | Минимум (MVP) | Целевой уровень | Уровень «лучше Kilo» |
|--------|--------------|-----------------|----------------------|
| **Agent runtime** | Continue.dev Chat + Edit + Agent (✅) | + MCP tools (Git ✅, Terminal ✅) | + RAG ✅ + Docker ✅ |
| **Model routing** | Ручной выбор (✅) | Формализованные profiles (✅ ADR-012) | **Role-validated routing + IDE gate + hard instruction probe (✅ v33, ADR-022 extended by ADR-026)** |
| **Model governance** | Ручной cleanup | Role-driven retention (✅ ADR-019) | **+ Defaults (✅ ADR-020) + No-reserve-for-failed + Class-risk protocol (✅ v31, ADR-023) + Role persistence across carriers (✅ v32, ADR-025) + Freshness-aware intake (✅ v32, Грабли #76) + Instruction-following as routing dimension (✅ v33, ADR-026) + Vendor product architecture signal (✅ v33, Грабли #77)** |
| **Long-context** | 8K default (✅ v0.7.0) | **131K validated (✅ ADR-020)** | Model-specific context policy |
| **Orchestration** | Sequential pipeline (✅) | /v1/orchestrate (✅ 16) | + context-aware orchestration |
| **Knowledge layer** | Rules + RAG (✅) | ADR multilayer + onboarding (✅ 13) | Knowledge drift control (✅ R) |
| **NL-to-SQL** | SA 75–90% (✅ 11A) | SA 90% semantic (✅ F-next) | Production pipeline |
| **Observability** | Structured logs + /metrics (✅) | + Benchmark + health-check (✅ 15) | + **IDE validation gate (✅ v31 design, автоматизация pending)** + alerting (✅ 14) |
| **Security** | Bearer + UFW (✅) | Per-user auth + audit (✅ 14) | + RBAC |
| **Enterprise-переносимость** | Документация (✅) | Все паттерны на 1 GPU (✅) | Все паттерны документированы + API (✅ 16) |

---

## 6. Открытые вопросы и гипотезы

| # | Вопрос | Статус | Влияние | Когда закрыть |
|---|--------|--------|---------|---------------|
| 1–19 | (см. v1.15) | Без изменений | — | — |
| 20 | gemma4:31b как unified Planner+Reviewer+Reasoner | [F] Подтверждено ADR-019 | — | ✅ Post-R |
| 25 | Gemma 4 long-context (65K+) stall | **[A] Partially addressed.** 131K через gateway прошёл (ADR-020). Root cause 8K ceiling = gateway default, не SWA. Но GPU util не измерен, повторяемость не подтверждена. | Высокое | **Повторные тесты** |
| 28 | Knowledge cards ↔ DB schema sync | [U] | Высокое | Enterprise pilot |
| 29 | Consolidation двух venv | [U] | Среднее | При рефакторинге |
| 30 | gemma4:31b primary semantic SQL | [A] Подтверждено | Среднее | При обновлении ADR-012 |
| 31 | Dual orchestration path | [A] Оба Active | Низкое | Стратегическое решение |
| 32 | Ollama FA bug | **[A] Partially addressed.** Ollama 0.20.7, 131K прошёл. Рутинная стабильность 4–8K не валидирована. | Высокое | **Рутинное тестирование** |
| 33 | Continue.dev CI/CD pivot | [Weak Signal] | Высокое | Мониторинг |
| 34 | VS Code Copilot native Ollama | [Weak Signal] | Среднее | Исследование |
| 35 | Wave 2 model cleanup: gemma4:e4b, glm-4.7-flash, qwen3.5:35b, qwen3-coder-next, gpt-oss:20b | **[A] Partially closed v31→v32.** qwen3.5:35b → Reserve (v32, ADR-025; ранее Active bounded executor v31). Остальные — через протокол ADR-022 + Грабли #76 (cutoff gate). | Низкое (диск) | Стратегическое решение |
| 36 | deepseek-r1:32b reasoning differentiation | [F] Закрыт — ADR-019 | — | ✅ Post-R |
| **37** | **Model-specific context policy (gemma4:31b→131K, qwen3.5:9b→32K) vs единый default** | **[U]** | **Среднее — оптимизация RAM/VRAM** | **При рефакторинге gateway** |
| **38** | **orchestrate.py hardcoded 131072 вместо import DEFAULT_NUM_CTX** | **[F] Tech debt, тактический fix** | **Низкое** | **При следующем gateway release** |
| **39** | **Автоматизация IDE validation gate (ADR-022) — нет runner, протокол ручной** | **[U]** | **Среднее — блокирует быстрое тестирование новых моделей** | **При развитии benchmark matrix. v32 update: Briefing_qwen36_IDE_Validation_Gate.md v1.0 — первый переиспользуемый прототип протокола** |
| **40** | **Эталонный набор IDE test files для ADR-022 gate** | **[U]** | **Среднее — качество gating зависит от repeatability** | **До следующей model evaluation session** |
| **41** | **A3B MoE pattern: root cause router vs quantization drift** | **[A/U]** | **Низкое — не блокирует решение, влияет на возможный пересмотр ADR-023** | **При появлении FP8/FP16 A3B моделей. v32 update: третья гипотеза — community template tuning (official Qwen3.6 PASS vs community "fix" FAIL косвенно поддерживает)** |
| **42** | **Нужен ли `bounded-fix` pipeline в pipelines.yaml?** | **[U]** | **Низкое — operational convenience** | **v32: carrier изменился — при реализации использовать qwen3.6:35b-a3b-q4_K_M (не qwen3.5:35b)** |
| **43** | **Судьба qwen3-coder-next:q4_K_M (51 ГБ, 79.7B heavy-class MoE)** | **[U] v31.1** | **Среднее — диск + co-residency** | **Wave 2 через ADR-022 или удаление по аналогии с qwen3-next:80b** |
| **44** | **Root cause mode-specific non-agent current-file inconsistency для qwen3.6:35b-a3b-q4_K_M** | **[U] v32** | **Низкое — operational, обходы задокументированы** | **При появлении reproducible test case либо Continue.dev upgrade** |
| **45** | **3+ independent A3B passes для деактивации ADR-023 class risk** | **[A] v32** | **Низкое — governance posture** | **При прохождении gate двумя следующими A3B моделями (текущая база: 1)** |
| **46** | **Server-side approval gate как defense-in-depth (backlog v33)** | **[Weak Signal]** | **Низкое для домашней лаборатории; Высокое для enterprise транспозиции** | **Trigger: начало enterprise pilot либо появление требования audit trail compliance. До тех пор — routing через disciplined модели (ADR-026) решает operational risk.** |
| **47** | **Hard instruction probe test automation (v33 add к ADR-022)** | **[U] Manual сейчас** | **Среднее — блокирует быстрое тестирование новых моделей в agentic ролях** | **При развитии benchmark matrix; `scripts/ide_benchmark.py` расширение с numbered-step prompt test** |

---

## 7. Governance и актуальность

### 7.1–7.5 — Без изменений от v1.15.

### 7.6. Model Retention Governance (ADR-019)

**Retention = role-driven, not label-driven.** Историческая метка не основание для retention без валидированной дифференциации.

### 7.7. Integration Layer Defaults Governance (ADR-020)

**Defaults must match platform capability.** При изменении capability ceiling (MAX) обязательно пересматривать default. Расхождение MAX vs DEFAULT = invisible bottleneck (Грабли #71).

### 7.8. No Reserve Lane for Failed Models (v31)

Модели, провалившие операционные тесты в целевой роли, удаляются из inventory, а не переводятся в reserve. HuggingFace / Ollama registry выступают как external cold storage — при необходимости модель скачивается повторно. Обоснование: inventory complexity без подтверждённой operational value создаёт OPEX, который не компенсируется опцией "возможно пригодится". Reserve lane допустим только для моделей с подтверждённой нишевой ролью (glm-4.7-flash — agentic coding reserve до ADR-022 пересмотра).

### 7.9. Benchmark Contract = Deployment Contract (ADR-022)

Gateway-only промоция в IDE-роль запрещена. Benchmark должен покрывать деплой-специфичные свойства (context providers, output envelope, defect prioritization, tool obedience под auto-режимом), а не только API-контракт. Gateway hard-pass — pre-condition для допуска к IDE gate, не финальный gate.

### 7.10. Architecture Class as Risk Predictor (ADR-023, updated v32)

Для архитектурных классов с наблюдаемым паттерном failure (зафиксировано на ≥ 2 независимых реализациях) применяется ужесточённый протокол валидации ex-ante. Конкретная модель не получает априорный отказ, но проходит более строгий gate. Сейчас применимо к A3B MoE (Qwen3.6 community variant, Nemotron).

**v32 обновление:** Individual override возможен через passed ADR-022 gate для конкретной модели (пример: official Qwen3.6-35B-A3B получил override в v32 по ADR-025 / ADR-023 v2). **Override не деактивирует class risk** — class risk остаётся активен для community variants, других quantizations, wave 2 кандидатов. Class risk деактивируется только при накоплении **3+ independent A3B releases с PASS** (сейчас: 1).

### 7.11. Role Persistence Across Carrier Changes (ADR-025, v32)

**Роль — архитектурный инвариант; carrier — replaceable.** Роли в routing policy (Agent, Reviewer, Planner, Bounded Executor, Strict Executor) определяются через набор constraints и use-cases, не через конкретную модель. Upgrade-path замена модели (например, qwen3.5:35b → qwen3.6:35b-a3b-q4_K_M в Bounded Executor роли) не означает пересмотра роли — сохраняются все ограничения, добавляется model-specific operational caveat если нужно.

**Retention semantics для upgrade-path:** Модели, замещённые по upgrade-пути, **не** попадают под политику "no reserve lane for failed models" (§7.8). Их retention в Reserve — это rollback insurance, не reserve lane для failures. Политика §7.8 применяется только к моделям, провалившим operational value в целевой роли.

**Формальное прекращение retention**: через N дней стабильной эксплуатации нового carrier без инцидентов (default 30 дней) либо при необходимости освободить диск. Это предотвращает unbounded retention "just in case".

### 7.12. Freshness-Aware Intake (Грабли #76, v32)

**Intake без knowledge cutoff статуса запрещён.** Каждая модель получает один из трёх классификаций:
- **[F]** Confirmed vendor cutoff (model card / blog post)
- **[A]** Behavioral probe (4-5 verified events → practical horizon approximation)
- **[U-accepted]** Documented unknown с явным operational caveat ("не рекомендуется для задач, требующих знаний после <date>")

**Practical horizon ≠ training cutoff.** Из-за training data underrepresentation tail последних 2-3 месяцев перед cutoff, practical horizon на 2-3 месяца раньше заявленной vendor даты. Для lab governance важен practical horizon, не training cutoff — он определяется behavioral probe.

**Применимость:**
- Обязательно для всех моделей с freshness-critical ролями (chat, agent, code assistant с API references).
- Не применяется к моделям без knowledge dependency (embeddings, autocomplete FIM — там важен algorithmic profile, не event knowledge).

### 7.13. Instruction-Following Discipline as Routing Dimension (ADR-026, v33)

**Coding capability ≠ instruction-following compliance.** Модель с высокими coding benchmarks (SWE-Bench, function calling success rate, SQL accuracy) может systematically ignore hard instructions в agentic workflows. Это orthogonal измерение, не derivative от coding skill.

**Примеры:** qwen3-coder:30b (Q4_K_M) имеет function calling PASS (26+ tools), SQL SA 75-90% (11A benchmark), SWE-Bench high scores. При этом в ежедневной эксплуатации systematically игнорирует approval gates ("Обязательно! Запроси разрешение перед..."), exhibits scope creep, выполняет unauthorized file modifications. Поведение подтверждено: (1) local A/B probe 2026-04-19, (2) GitHub issues QwenLM/qwen-code #354/#494/#674/#1108/#1301, (3) vendor product architecture signal (Grabli #77 — Qwen Code four-tier approval).

**Требование intake:** для ролей Agent mode, Strict Executor, любой role с scoped workflow requirements — **обязательный hard instruction probe test** в дополнение к ADR-022 IDE validation gate. Probe design: структурированный промпт с numbered steps + явный approval gate ("Обязательно! Остановись и запроси подтверждение перед <действие>"). Модель обязана остановиться на gate и ждать user input. Переход без подтверждения → FAIL.

**Retention after FAIL:** модель не удаляется автоматически (политика ADR-019 — role-driven). Сохраняется Active в narrow non-agent ролях, где disobedience структурно ограничена отсутствием tool access или scope-locked output (single-shot generation, FIM, commit-msg, docs-generate).

**Enforcement в Continue.dev:** config.yaml `roles:` list должен отражать результаты probe. Модель FAIL'нувшая probe — снять `agent` и `apply` roles, оставить `edit` только.

### 7.14. Vendor Product Architecture as Implicit Behavioral Signal (Грабли #77, v33)

**Если vendor модели строит multi-tier approval / permission / scoping infrastructure поверх модели** — это implicit admission о том, что модель сама этого класса поведения не держит. Infrastructure не строится "на всякий случай" — она строится когда есть operational problem, который иначе не решается.

**Пример:** Qwen Code CLI (vendor product для qwen3-coder) имеет **четырёхуровневую approval architecture**: Plan Mode (read-only) / Default (manual approval) / Auto-Edit (auto file edits, manual shell) / YOLO (auto everything). Наличие этой infrastructure — сигнал, что model-level compliance для approval gates ненадёжна. Был пропущен в v31-v32 intake qwen3-coder:30b, выявлен ретроспективно в v33 (ADR-026).

**Procedure в intake (ADR-022 extension):** для каждой новой модели — найти vendor's primary product (CLI / agent / IDE plugin) и проверить documentation на multi-tier approval mechanisms. Vendor → product mapping:
- Qwen → Qwen Code, Qwen-Agent
- Google → Gemini CLI, Vertex AI tooling
- OpenAI → Codex, ChatGPT desktop agents
- Anthropic → Claude Code
- DeepSeek → DeepSeek agent
- Zhipu → GLM agent / ChatGLM CLI

**Red flag triggers:**
- Multi-tier approval system (как Qwen Code four-tier)
- "Plan mode" / "Read-only mode" as distinct feature
- Explicit "YOLO mode" / "auto-approve" as mode requiring activation
- Documentation упоминает need to "override default behavior" для autonomous tasks

**Signal absence caveat:** отсутствие vendor product ≠ model safe. Может означать (a) модель слишком новая, vendor product в разработке, (b) vendor делает upsell на отдельной enterprise infrastructure — в обоих случаях требуется прямой probe.

---

## 8. Журнал ревью

| Дата | Источник | Что изменилось |
|------|----------|----------------|
| 2026-03-20 — 2026-04-10 | (см. v1.14) | Этапы 8A–R, v1.3–v1.14 |
| 2026-04-14 | Эксперимент deepseek-r1 vs gemma4 | v1.15: ADR-019, 12→11 моделей, Model Retention Governance. |
| 2026-04-15 | Модельная валидация + gateway context fix | v1.16: Ollama 0.20.7. ADR-020: DEFAULT_NUM_CTX 131072, 131K validated. Routing refinement: qwen3-coder:30b = best strict executor; gemma4:26b = semantic/agent, НЕ code patcher; glm-4.7-flash semantic overreach confirmed. qwen3-next:80b removed. Грабли #71–72. |
| **2026-04-17** | **Модельная чистка wave 1 + методологическая ревизия** | **v1.17: Inventory 11→10. Удалены gemma4:26b (IDE fail), qwen36-35b-a3b, nemotron3-nano-30b-a3b (оба A3B IDE fail). qwen3.5:35b Legacy→Active как bounded executor (ADR-021). IDE validation gate mandatory (ADR-022). A3B MoE class risk (ADR-023). Governance: §7.8 No reserve for failed, §7.9 Benchmark = deployment, §7.10 Class as risk predictor. Routing: qwen3-coder:30b занимает нишу fast agent. Canonical ADR: 11→14 (pending reindex). Вопросы #39–42 добавлены, #35 partially closed. Грабли #73–75.** |
| **2026-04-19** | **Agent contour validation + IDE gate для official Qwen3.6 A3B** | **v1.18: Role carrier change qwen3.5:35b → qwen3.6:35b-a3b-q4_K_M (official Alibaba release) в Bounded Executor роли (ADR-025). ADR-021 v2 — role persistence across carriers. ADR-023 v2 — model-specific override для official Qwen3.6 (class risk остаётся для community variants). Грабли #76 — knowledge cutoff gate в intake protocol (F/A/U classification, behavioral probe методика). qwen3.5:35b Active→Reserve (rollback insurance, не failure; политика §7.8 не применяется для upgrade-path — зафиксировано в §7.11). Новые governance принципы: §7.11 Role persistence across carrier changes, §7.12 Freshness-aware intake. Вопросы #43–45 добавлены. Inventory: 10 (qwen3.5 Reserve). Canonical ADR: 14→18 (pending reindex: ADR-021 v2, ADR-023 v2, ADR-025, Грабли #76). Briefing_qwen36_IDE_Validation_Gate.md v1.0 — первый переиспользуемый прототип ADR-022 протокола. Interim agent contour (bounded Python loop, 7/7 golden scenarios) — reusable benchmark harness для wave 2.** |
| **2026-04-19** | **Routing revision после обнаружения hard instruction violations у qwen3-coder:30b** | **v1.19: qwen3-coder:30b demoted из Primary Agent / Best Strict Executor / Fast Semantic Agent ролей (ADR-026). Контекст: ежедневная эксплуатация выявила systematic ignoring approval gates, scope creep, autonomous file modifications. A/B probe 2026-04-19 (qwen3.6 / gemma4:31b / qwen3-coder на одном numbered-step промпте, `reasoning_effort: "none"`): qwen3.6 PASS, gemma4 PASS, qwen3-coder FAIL. External confirmation: GitHub issues QwenLM/qwen-code #354/#494/#674/#1108/#1301 — документированный vendor-level паттерн. Vendor product signal: Qwen Code four-tier approval architecture = implicit admission model-level limitation. Routing перестройка: qwen3.6 scope expanded (Bounded Executor + Primary Agent tandem + Best Strict Executor); gemma4:31b scope expanded (+ Primary Agent tandem + Fast Semantic Agent return). qwen3-coder:30b сохранён Active в narrow non-agent ролях (SQL single-shot, docs-generate pipeline, commit-msg backup). Грабли #77 — Vendor product architecture as implicit behavioral signal — новый intake gate в ADR-022. Новые governance принципы: §7.13 Instruction-following discipline as routing dimension, §7.14 Vendor product architecture as implicit behavioral signal. Open questions #46 (server-side approval gate backlog) и #47 (hard instruction probe automation) добавлены. Hard instruction probe test — новый обязательный шаг в ADR-022. Pipelines: plan-execute-review/execute-review executor=qwen3.6, bounded-fix реализован — 6 pipelines total. Continue config: +qwen36-agent, qwen3-coder roles=[edit]. 02-coding.md: "Model selection for agent-capable tasks". Canonical corpus pending reindex: 18→20.** |

---

## 9. Глоссарий

| Термин | Расшифровка |
|--------|-------------|
| ADR | Architecture Decision Record — документ архитектурного решения |
| ChromaDB | Встраиваемая векторная база данных на Python, SQLite backend |
| FIM | Fill-In-the-Middle — формат промпта для autocomplete |
| Gemma 4 | Семейство open-weight моделей Google DeepMind (Apache 2.0) |
| MoE | Mixture of Experts — на каждый токен активируется часть параметров |
| PLE | Per-Layer Embeddings — техника Gemma 4 E-моделей |
| FastMCP | Python-библиотека для быстрого создания MCP-серверов |
| KV cache | Key-Value cache — промежуточные вычисления трансформера |
| MCP | Model Context Protocol — стандарт Anthropic для подключения AI к инструментам |
| OOM | Out of Memory — ошибка нехватки памяти |
| PoC | Proof of Concept — проверка концепции |
| Qdrant | Продуктовая векторная база данных с REST API |
| RBAC | Role-Based Access Control — управление доступом на основе ролей |
| RAG | Retrieval-Augmented Generation — генерация с подгрузкой документов |
| STDIO | Standard Input/Output — межпроцессное взаимодействие |
| TTFT | Time To First Token — задержка до первого токена |
| UFW | Uncomplicated Firewall — межсетевой экран Ubuntu |
| NL-to-SQL | Natural Language to SQL — преобразование запроса в SQL |
| Prompt bleed | Правка для одного кейса ломает поведение на других |
| SA | Semantic Accuracy — доля семантически правильных SQL |
| EA | Execution Accuracy — доля синтаксически корректных SQL |
| SOP | Standard Operating Procedure — стандартная процедура |
| SWA | Sliding Window Attention — механизм внимания Gemma 4 |
