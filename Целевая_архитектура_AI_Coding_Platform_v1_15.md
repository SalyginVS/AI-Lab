# Целевая архитектура: Локальная AI Coding Platform

**Версия:** 1.15  
**Дата:** 2026-04-14  
**Базовый стек:** Ubuntu 24.04 / RTX 3090 / Ollama 0.20.2 / gateway v0.12.0 / Continue.dev v1.2.22  
**Стратегия:** Continue-first platform, Depth over Speed, локальность как принцип  
**Назначение:** Лаборатория для наработки решений → перенос на Enterprise  
**Паспорт стенда:** v29.0 (2026-04-14)

> **Роль документа.** Данный файл является **source of truth** (единым источником правды) для целевой архитектуры AI Coding Platform. Он задаёт принципы, политики и ожидаемое состояние для всех реализаций платформы, включая конкретные лабораторные стенды. Документ `Паспорт_лаборатории_vX` фиксирует фактическое состояние конкретного стенда и должен согласовываться с данной целевой архитектурой. Любое расхождение между паспортом и целевой архитектурой классифицируется как технический долг и оформляется явно.

---

## 1. Целевая архитектура

### 1.1. Обзор

Платформа трансформирует текущую лабораторию (набор работающих компонентов) в управляемую инженерную систему с семью слоями. Каждый слой имеет чёткую ответственность, определённые интерфейсы и может развиваться независимо.

Ключевой принцип: **не заменять, а достраивать**. Всё, что подтверждено тестами в этапах 1–16, 13, 12, F-next, R, остаётся. Новые компоненты добавляются поверх существующего фундамента.

Дополнительный принцип: **лаборатория = полигон для Enterprise**. Каждый компонент проектируется так, чтобы паттерн переносился на продуктовые серверы с минимальной адаптацией (другое железо, другие модели — та же архитектура).

### 1.2. Слои и их взаимодействие

```
┌─────────────────────────────────────────────────────────────────────┐
│  7. OBSERVABILITY / OPERATIONS                                      │
│     Structured logs, metrics, tool-call tracing, benchmark matrix   │
├─────────────────────────────────────────────────────────────────────┤
│  6. SECURITY / GOVERNANCE                                           │
│     Tool approval policy, denylist, auth model, audit trail         │
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
│     Ollama 0.20.2 → gateway v0.12.0 → /v1/chat/completions         │
│     + /v1/embeddings + /v1/metrics + /v1/orchestrate                │
└─────────────────────────────────────────────────────────────────────┘
                          │
                ┌─────────┴──────────┐
                │   RTX 3090 (24GB)  │
                │   + RAM (62GB)     │
                │   = ~86GB pool     │
                └────────────────────┘
```

### 1.3. Статусы компонентов платформы

Легенда статусов:
- **Active** — часть целевой архитектуры, реализована и используется в продуктивных сценариях.
- **PoC** (Proof of Concept — проверка концепции) — прототип; не обязателен для основного контура, но ценен как паттерн.
- **Planned** — целевая функция, ещё не реализованная.
- **Legacy** — унаследованный компонент, требующий замещения.
- **Deprecated** — устаревший компонент, подлежащий удалению.

| Слой | Компонент | Статус | Этап реализации |
|------|-----------|--------|-----------------|
| 1. Inference/Backend | Ollama 0.20.2 + systemd | **Active** | 1–7B, 10C, 14A |
| 1. Inference/Backend | gateway v0.12.0 (/chat/completions, /models, /health, /embeddings, /metrics, /orchestrate) | **Active** | 1–16 |
| 1. Inference/Backend | gateway /v1/orchestrate (self-call pattern, ADR-016) | **Active** | 16 ✅ |
| 1. Inference/Backend | Модуляризация gateway в Python-пакет (11 модулей) | **Active** | 10A–16 ✅ |
| 1. Inference/Backend | Gemma 4: gemma4:31b (Quality-first Agent/Planner/Reviewer/Best Semantic SQL/**Primary Reasoner**) | **Active** | 10C, F-next, **ADR-019** ✅ |
| 1. Inference/Backend | Gemma 4: gemma4:26b (Fast Semantic Agent/Executor, MoE) | **Active** | 10C ✅ |
| 1. Inference/Backend | Gemma 4: gemma4:e4b (Fast edge chat, evaluation) | **PoC** | 10C |
| 2. IDE Agent Layer | Continue.dev v1.2.22 (Chat, Edit, Agent, Apply, Autocomplete) | **Active** | 7A–7C, 9B |
| 2. IDE Agent Layer | Copilot BYOK (plain chat) | **Active** | 7D |
| 2. IDE Agent Layer | Copilot BYOK (Agent mode с локальными моделями) | **Legacy** | Нестабилен, не развивать |
| 3. MCP Tool Layer | mcp-server-git (MCP — Model Context Protocol, Git-инструменты) | **Active** | 8A |
| 3. MCP Tool Layer | Terminal Policy (rules-based, Continue Agent на Windows) | **Active** | 8B ✅ |
| 3. MCP Tool Layer | Custom RAG MCP (RAG — Retrieval-Augmented Generation, поиск по документам) | **Active** | 11 ✅ |
| 3. MCP Tool Layer | Docker MCP (custom, FastMCP, docker SDK 7.1.0, server-side policy enforcement, ADR-017) | **Active** | 12 ✅ |
| 4. Orchestration | orchestrator.py v1.1.0 (sequential pipeline, 6 pipeline) — CLI path | **Active** | 8C ✅ |
| 4. Orchestration | Headless scripts + git hooks (auto-review, auto-commit-msg, auto-docs, pre-push) | **Active** | 8D ✅ |
| 4. Orchestration | gateway.py /v1/orchestrate (self-call pattern, 6 pipelines) — HTTP path | **Active** | 16 ✅ |
| 5. Knowledge/Context | Rules: 3 уровня (глобальный / проектный / файловый) | **Active** | 7C |
| 5. Knowledge/Context | Context providers: 12 штук (code, codebase (deprecated), repo-map и др.) | **Active** | 7C, 9B |
| 5. Knowledge/Context | @Codebase (provider: codebase) — deprecated upstream, миграция на Agent built-in tools | **Deprecated** | 9B → удаление в 14 |
| 5. Knowledge/Context | Embeddings: transformers.js all-MiniLM-L6-v2 | **Legacy** | 7C → заменён в 9B |
| 5. Knowledge/Context | Embeddings: qwen3-embedding через шлюз | **Active** | 9B ✅ |
| 5. Knowledge/Context | ADR multilayer model (foundational + canonical in RAG primary) | **Active** | 13, R ✅ |
| 5. Knowledge/Context | Onboarding пакет (ONBOARDING.md + setup-check.sh + setup-check.ps1) | **Active** | 13, R ✅ |
| 5. Knowledge/Context | Security rule (03-security.md, alwaysApply) | **Active** | 13 ✅ |
| 6. Security/Governance | Mandatory per-user Bearer auth + audit trail (gateway v0.12.0) | **Active** | 14B ✅ |
| 6. Security/Governance | UFW least-privilege (default deny, 8 rules, dual-zone LAN+WG) | **Active** | 14A ✅ |
| 6. Security/Governance | Nightly health-check cron + benchmark history + Ollama Canary SOP | **Active** | 14A ✅ |
| 6. Security/Governance | Terminal Policy rules (PowerShell behavior, self-contained, no temp files) | **Active** | 8B ✅ |
| 6. Security/Governance | **Model retention governance: role-driven, not label-driven (ADR-019)** | **Active** | **Post-R ✅** |
| 7. Observability | journalctl текстовые логи | **Legacy** | 1 → заменён в 10A |
| 7. Observability | Structured JSON logging | **Active** | 10A ✅ |
| 7. Observability | /metrics endpoint (JSON in-memory counters) | **Active** | 10B ✅ |
| 7. Observability | Benchmark matrix + health-check.sh | **Active** | 15, R ✅ |
| **Track F** | **Text-to-SQL PoC (NL→SQL benchmark, SQLite)** | **Active (PoC завершён)** | **11A ✅** |
| **Track F** | **Semantic Layer для NL-to-SQL (retrieval-assisted SQL, ChromaDB sql_knowledge)** | **Active (PoC завершён)** | **F-next ✅** |

### 1.4. Потоки данных

```
Сценарий: Agent mode с MCP tool (например, git commit)

VS Code (Windows 11)
  └── Continue.dev Agent mode
        │
        ├─1─ Отправляет промпт + tools list → gateway.py :8000
        │     └── gateway.py → Ollama :11434 (gemma4:31b / qwen3-coder:30b)
        │           └── Ollama возвращает tool_call: git_commit
        │
        ├─2─ Continue получает tool_call
        │     └── Вызывает MCP server (git) через STDIO
        │           └── mcp-server-git выполняет `git commit`
        │           └── Возвращает результат в Continue
        │
        ├─3─ Continue отправляет tool_result → gateway.py
        │     └── gateway.py → Ollama (модель формирует ответ)
        │
        └─4─ Ответ пользователю в IDE


Сценарий: Autocomplete (без изменений)

VS Code → Continue → Ollama :11434 напрямую (FIM, /api/generate)
                      qwen2.5-coder:7b (резидентная)


Сценарий: Orchestrator (sequential multi-model pipeline)

Клиент (скрипт / CI / IDE)
  │
  ├─1─ POST /v1/orchestrate → gateway.py :8000
  │     body: { task: "...", pipeline: "plan-execute-review" }
  │
  │     gateway.py внутренне:
  │     ├─2─ Step 1: Planner (gemma4:31b) → декомпозиция задачи
  │     │     холодный старт ~20 сек, генерация ~30-60 сек
  │     ├─3─ Step 2: Executor (gemma4:26b) → код/правки
  │     │     холодный старт ~15 сек, генерация ~30-120 сек
  │     └─4─ Step 3: Reviewer (gemma4:31b) → проверка
  │           (модель уже загружена после Step 1, горячий старт)
  │
  └─5─ Финальный ответ клиенту (результат + review)
       Общее время: 2-8 минут (последовательно, Depth over Speed)


Сценарий: Headless automation (auto code review)

git push hook / CI pipeline
  │
  └─── orchestrator.py --pipeline execute-review --task "Review this diff:\n{diff}"
        │
        └─── POST /v1/chat/completions → gateway.py :8000
              → Sequential: gemma4:26b (execute) → gemma4:31b (review)
              → Ответ: структурированный code review → stdout


Сценарий: Text-to-SQL Semantic Layer (F-next)

Вопрос на естественном языке
  │
  └─── text2sql_semantic.py
        ├── search sql_knowledge (ChromaDB, top-k по similarity)
        ├── group by type (ddl, business_doc, sql_example, anti_pattern)
        ├── assemble dynamic semantic context
        ├── POST /v1/chat/completions → gateway → gemma4:31b
        └── validate + execute SQL (read-only) → результат
```

---

## 2. Архитектурные решения

### 2.1. Слой 1 — Inference / Backend

**Что остаётся без изменений (F — подтверждено тестами):**
- Ollama 0.20.2, systemd, override.conf (7 переменных) — стабильно
- gateway v0.12.0 (11 модулей) — стриминг, reasoning policy, tool_calls, mandatory per-user auth, embeddings, metrics, /v1/orchestrate
- **11 моделей** (после ревизии R: 17→12, затем −1 deepseek-r1:32b по ADR-019)
- OLLAMA_MAX_LOADED_MODELS=2, NUM_PARALLEL=1, Flash Attention, KV (Key-Value) cache q8_0

**Что изменилось в 10C–Post-R:**
- Ollama 0.18.0 → 0.20.2 (Gemma 4, security patches)
- 13 → 16 → 15 → 17 → 12 → **11** моделей (+ Gemma 4, − deprecated, − reserve при ревизии R, **−deepseek-r1:32b по ADR-019**)
- Раскладка ролей: Gemma 4 = Tier 1 (ADR-012). **gemma4:31b = Primary Reasoner (ADR-019)**
- Gateway v0.10.0 → v0.12.0: +auth.py (14B), +orchestrate.py (16)
- Mandatory per-user auth + audit trail (14B, ADR-015)
- /v1/orchestrate self-call pattern (16, ADR-016)
- MAX_NUM_CTX 32768→131072, HTTPX_TIMEOUT 600→3600s (15)
- health-check.sh 11/11 + benchmark.py 7/7 + setup-check.sh 66/0/1 (15, 13, R)

**Известное ограничение (F — upstream bug):**
Gemma 4 (31b, 26b) long-context (num_ctx ≥ 65K) → stall (GPU util=0%, no generation). Root cause: llama.cpp SWA context-shift bug (#21379). Hardware-agnostic (подтверждено на RTX 5090, DGX Spark, M1 Max, ROCm). Стабильная граница: ctx ≤ 32768. Для long-context задач — qwen3-coder:30b (единственная Active non-Gemma модель большого размера). Отслеживать: Ollama 0.20.5+.

**Известное ограничение (Ollama 0.20.3–0.20.4):**
Flash Attention для Gemma 4 включён в Ollama 0.20.4, но вызывает зависание gemma4:31b Dense на промптах > 3–4K токенов. gemma4:26b MoE отдаёт пустые ответы на длинных system prompt. Текущая 0.20.2 стабильна. Upgrade заблокирован до исправления upstream.

**Что дорабатывается:**

Нет запланированных изменений Layer 1. Текущее состояние — целевое для лаборатории.

**Что убирается:** Ничего. Все существующие endpoint'ы сохраняют обратную совместимость.

**Решение по модуляризации gateway (A — принято, реализовано в 10A):**

gateway.py v0.7.0 — 994 строки. Разбит на Python-пакет из 11 модулей при добавлении embeddings (9A) + structured logging (10A) + metrics (10B) + auth (14B) + orchestrate (16):

```
~/llm-gateway/
  ├── gateway/
  │   ├── __init__.py        # Версия, общие константы
  │   ├── app.py             # FastAPI app, mount routes
  │   ├── models.py          # Pydantic models, validation
  │   ├── errors.py          # GatewayError + exception handlers
  │   ├── upstream.py        # httpx client, retry, OOM classification
  │   ├── chat.py            # /v1/chat/completions + helpers
  │   ├── embeddings.py      # /v1/embeddings endpoint
  │   ├── listing.py         # /v1/models, /health
  │   ├── logging_config.py  # Structured JSON logging
  │   ├── metrics.py         # /metrics, in-memory counters
  │   ├── auth.py            # Bearer validation, per-user tokens
  │   └── orchestrate.py     # /v1/orchestrate + /v1/orchestrate/pipelines
  ├── pipelines.yaml         # Orchestrator pipeline definitions
  └── run.py                 # uvicorn entrypoint
```

**Решение по маршрутизации моделей (ADR-012, обновлено после ADR-019):**

**Tier 1 — Primary workhorses:**

| Роль | Модель | Путь | num_ctx | reasoning_effort | Этап |
|------|--------|------|---------|-----------------|------|
| Quality-first Agent / Planner / Reviewer / **Best Semantic SQL** / **Primary Reasoner** | **gemma4:31b** | шлюз | 8192 (до 256K) | none / high | 10C, F-next, **ADR-019** |
| Fast Semantic Agent / Fast Executor | **gemma4:26b** (MoE, 3.8B active) | шлюз | 8192 (до 256K) | none | 10C |
| Stable Generic Executor / Backup Agent / **Best Plain SQL Executor** / **Long-context fallback** | qwen3-coder:30b | шлюз | 8192 | none | 7A, 11A |
| Autocomplete (FIM — Fill-In-the-Middle) | qwen2.5-coder:7b | Ollama напрямую | 2048 | — | 7B |
| Embeddings | qwen3-embedding | шлюз /v1/embeddings | — | — | 9A |

**Tier 2 — Specialized:**

| Роль | Модель | Путь | Примечание |
|------|--------|------|-----------|
| Fast chat + light tools | qwen3.5:9b | шлюз | Tool calling восстановлен в Ollama 0.20.0 |
| Fast edge chat (evaluation) | gemma4:e4b | шлюз | Частично протестирована |

**Tier 3 — Legacy / Reserve / PoC:**

| Модель | Статус | Примечание |
|--------|--------|-----------|
| qwen3.5:35b | Legacy | Tools сломаны. Кандидат на удаление (wave 2). |
| glm-4.7-flash | Reserve | Понижен: gemma4:26b. Кандидат на удаление (wave 2). |
| qwen3-coder-next:q4_K_M | PoC | SA 70% semantic — не лучше qwen3-coder:30b. Кандидат на оценку. |
| gpt-oss:20b | PoC | Обнаружена при ревизии R. Не оценивалась. |
| deepseek-coder-v2:16b | **Удалена** (14A) | Роль покрыта Gemma 4 |
| qwen3:30b | **Удалена** (R) | Reserve, роль Planner отдана gemma4:31b |
| qwen3:14b | **Удалена** (R) | Reserve, нет уникальной роли |
| deepseek-r1:14b | **Удалена** (R) | Reserve, есть deepseek-r1:32b |
| qwen2.5-coder:1.5b | **Удалена** (R) | Reserve, fallback не нужен |
| qwen3-vl:8b | **Удалена** (R) | Reserve, vision покрыт Gemma 4 |
| **deepseek-r1:32b** | **Удалена** (Post-R, ADR-019) | **Reasoning-роль покрыта gemma4:31b. Role-based experiment: 6/10 vs 9/10.** |

**ADR-012: Gemma 4 Model Integration (10C)**

Контекст: Gemma 4 (31B Dense #3 Arena, 26B MoE #6 Arena) доступны в Ollama 0.20.0 с подтверждённым function calling (generic + semantic), multi-step chaining, thinking mode и vision. Решение: интегрировать обе модели в primary tier. Не бинарное деление "Gemma semantic / Qwen generic", а ролевое: Gemma — quality-first agent/planner/reviewer, Qwen — stable generic executor. Ключевой нюанс: gemma4:31b требует thin policy layer для стабильного tool selection; gemma4:26b — лучший zero-shot semantic selector.

**ADR-018: Semantic Layer Architecture (F-next)**

Контекст: Retrieval-assisted SQL pipeline через ChromaDB sql_knowledge (34 карточки) устраняет prompt bleed и масштабируется без регрессии. gemma4:31b SA 90% — лучший executor для semantic layer (инверсия по сравнению с plain text-to-sql, где qwen3-coder:30b лидирует). Reasoning-модели предпочтительнее code generators для retrieval-assisted workflows. Knowledge layer drift — главный операционный риск; требует процесса синхронизации cards ↔ фактическая schema. Enterprise evaluation framework для GenBI-платформ зафиксирован.

**ADR-019: Удаление deepseek-r1:32b (Post-R)**

Контекст: Role-based head-to-head сравнение deepseek-r1:32b vs gemma4:31b на заявленном поле deepseek (specialized reasoning). Три теста: logical deconstruction, skeptical second-opinion, competing hypotheses under ambiguity. Результат: gemma4:31b 9/10 vs deepseek-r1:32b 6/10 по всем критериям. Решение: удалить deepseek-r1:32b. Governance principle: retention = role-driven, not label-driven. Историческая метка не является основанием для сохранения модели без подтверждённой уникальной роли.

### 2.2. Слой 2 — IDE Agent Layer

**Что остаётся (F):**
- Continue.dev v1.2.22 — основной agent runtime
- config.yaml: **9 моделей** (1 embed + 1 FIM + 7 chat-capable), 12 context providers, 6 prompts
- Copilot BYOK — дополнительный plain chat
- 3 MCP servers (mcp-server-git STDIO + Lab RAG streamable-http + Docker MCP streamable-http local-only)

**Решение по Agent runtime (F):** Continue.dev — единственный основной agent runtime. Причины: подтверждён для Chat, Edit, Agent, Apply, Context, Rules, Prompts; полностью локальный; поддерживает MCP; Copilot Agent mode с локальными моделями нестабилен и неисправим на стороне шлюза.

**Стратегическое наблюдение (R):** Continue.dev переориентируется на CI/CD checks и CLI-агенты. VS Code extension поддерживается, но стратегический фокус сместился. Одновременно VS Code получил нативную интеграцию с Ollama через Copilot. Мониторинг ситуации — при следующей стратегической ревизии.

### 2.3. Слой 3 — MCP Tool Layer

**Архитектурное решение по транспорту (ADR-014):** STDIO для клиентских MCP-серверов (Windows). Streamable-http — для серверных MCP-серверов (Ubuntu). SSE deprecated в MCP spec.

**Целевой набор MCP-серверов:**

| # | MCP Server | Транспорт | Среда выполнения | Статус | Этап |
|---|-----------|-----------|-----------------|--------|------|
| 1 | **mcp-server-git** (Anthropic, Python) | STDIO | Windows (uvx) | **Active** | 8A ✅ |
| 2 | **Terminal Policy** (rules-based, 01-general.md) | — (нативный VS Code terminal) | Windows (VS Code) | **Active** | 8B ✅ |
| 3 | **Lab RAG Server** (custom, FastMCP, ChromaDB 1.5.5) | streamable-http (:8100) | Сервер (Ubuntu) | **Active** | 11 ✅ |
| 4 | **Docker MCP Server** (custom, FastMCP, docker SDK 7.1.0, policy enforcement) | streamable-http (:8200, **127.0.0.1 only + SSH tunnel**) | Сервер (Ubuntu) | **Active** | 12 ✅ |

**Решение по policy (F — подтверждено на практике, ADR-017):**

| Категория инструмента | Политика | Примеры |
|-----------------------|----------|---------|
| Read-only | Автоматическое выполнение | git status, git log, docker ps, docker inspect |
| Write (файлы/код) | Выполнение с показом diff | git commit, git push, file write |
| Destructive | Подтверждение пользователя | git reset --hard, docker rm, branch delete |
| Network/External | Allowlist | push to remote, docker pull |
| Sensitive paths | Denylist | .env, secrets/, private keys |
| **Exec (Docker)** | **Server-side allowlist/denylist** | **hostname (allowed), rm -rf (denied by policy)** |

> Docker MCP доказал server-side policy enforcement: docker-policy.yaml проверяет каждую операцию до вызова Docker API. Defense in Depth: 3 слоя (Continue Agent approval → server policy → security rule).

### 2.4. Слой 5 — Knowledge / Context Layer

**Что реализовано (F — Этапы 13 + R завершены):**
- Rules: 3 глобальных (01-general, 02-coding, **03-security**) + проектные (01-project)
- 03-security.md: alwaysApply, denylist путей (.env, .ssh), запрет вывода токенов, git safety
- Context providers: 12 штук, включая @Code, @Repository Map
- Embeddings: qwen3-embedding через шлюз (4096d)
- Prompts: 6 slash-команд
- ADR multilayer model: foundational (5) + canonical (**9**, включая ADR-017 и ADR-018) в RAG primary index (**14 files / 18 chunks**, обновлено при R)
- ADR шаблон в workspace: `<workspace>\.continue\docs\adr\000-template.md`
- Onboarding: ONBOARDING.md + setup-check.sh (**66 проверок**, обновлено при R) + setup-check.ps1 (16 проверок)
- `provider: codebase` удалён (deprecated upstream, Этап 14)

> **Примечание v1.15:** ADR-019 создан, но ещё не добавлен в RAG corpus (lab_docs). При следующем reindex — включить как canonical.

**ADR Corpus Policy (принята в Этапе 13):**

> ADR knowledge layer не должен быть плоским. Primary architectural truth для RAG образуют только foundational и canonical ADR. Subsidiary и operational решения являются поддерживающим контуром и не должны конкурировать с canonical ADR в primary retrieval.

**Multilayer ADR структура:**

| Слой | Описание | Кол-во | RAG-статус |
|------|----------|--------|-----------|
| L0 — Foundational | Базовые принципы (Depth over Speed, Continue-first, STDIO, ChromaDB, Terminal Policy) | 5 | Primary index |
| L1 — Canonical | Official architecture decisions (ADR-008…**019**) | **10** | Primary index |
| L2 — Subsidiary | Уточняющие решения (embeddings, planner, allowlist) | 11 | Backup (вне index) |
| L3 — Operational | Execution rules (commit-msg, MAX_LINES, venv) | 5 | Backup (вне index) |
| L9 — Closed | Закрытые/поглощённые | 1 | Backup (вне index) |

**Knowledge drift control (выявлено в F-next + R):**

Semantic Layer knowledge cards чувствительны к drift между cards и фактической schema БД. При ревизии R обнаружен системный drift (DDL, business rules, SQL examples, anti-patterns — все секции). Исправлено полной заменой sql_knowledge_cards.py и переиндексацией. Для production — автоматизация DDL extraction → card generation. setup-check.sh теперь включает проверку sql_knowledge collection.

### 2.5. Слой 6 — Security / Governance

**Что реализовано (F — Этап 14 завершён):**
- Mandatory per-user Bearer auth (gateway v0.12.0, 3 users: vladimir, roadwarrior, orchestrator)
- user_id audit trail в каждом structured log event
- UFW least-privilege: default deny, 8 правил, dual-zone LAN+WG
- Ollama firewall: 11434 только для whitelist клиентов (192.168.0.164, 10.10.10.2)
- Nightly health-check cron + benchmark history (immutable snapshots)
- Ollama Canary SOP (6-step upgrade procedure)
- Terminal Policy через global rule 01-general.md (PowerShell-native, UTF-8)
- Security rule 03-security.md: denylist путей, запрет токенов в terminal/git
- Continue.dev полностью локален — данные не покидают сеть
- .env token storage (chmod 600, shared EnvironmentFile для gateway + rag-mcp)
- Docker MCP: local-only bind (127.0.0.1:8200) + SSH tunnel. ADR-017.
- **Model retention governance: role-driven, not label-driven (ADR-019, Грабли #70)**

**Что может дорабатываться в будущем:**

| Компонент | Что | Когда |
|-----------|-----|-------|
| RBAC | Ролевая модель доступа (вместо плоского per-user) | При 5+ пользователях |
| Dedicated RAG service token | Отдельный token для server-to-server (ADR-015 interim) | При enterprise-переносе |
| Prompt injection guardrails | Валидация RAG-retrieved content | При production RAG |

### 2.6. Слой 4 — Orchestration / Automation

NUM_PARALLEL=1 ограничивает **параллельное** выполнение, но не **последовательную** оркестрацию. Паттерн «Planner → Executor → Reviewer» работает на одном GPU в логике Depth over Speed.

**Dual Orchestration Path (transitional architecture, подтверждено при ревизии R):**

Лаборатория имеет два параллельных orchestration path: HTTP API (`/v1/orchestrate` в gateway) и CLI (`orchestrator.py`). CLI path используется headless scripts (auto-review.sh, auto-commit-msg.sh, auto-docs.sh) — подтверждено как активная зависимость при R. HTTP path — для программного вызова из IDE/MCP. Консолидация в единый path — будущее стратегическое решение.

**Компоненты:**

| Компонент | Что | Реализация | Статус |
|-----------|-----|------------|--------|
| **Sequential Orchestrator (CLI)** | Multi-model pipeline | orchestrator.py v1.1.0 | **Active** ✅ 8C |
| **Sequential Orchestrator (HTTP)** | Multi-model pipeline через gateway | gateway/orchestrate.py, self-call (ADR-016) | **Active** ✅ 16 |
| **Headless Scripts** | Автоматические задачи без IDE | Bash скрипты через orchestrator.py CLI | **Active** ✅ 8D |
| **CI/CD Hooks** | git hooks | git pre-push → auto-review | **Active** ✅ 8D |

**Типовые pipeline (фактическое состояние pipelines.yaml):**

| Pipeline | Шаги | Модели | Типичное время (RTX 3090) | Use case |
|----------|-------|--------|---------------------------|----------|
| `plan-execute-review` | 3 | **gemma4:31b → gemma4:26b → gemma4:31b** | 3–8 мин | Сложные задачи |
| `execute-review` | 2 | **gemma4:26b → gemma4:31b** | 2–5 мин | Стандартные задачи |
| `review-only` | 1 | **gemma4:31b** | 1–3 мин | Code review (headless, CI/CD) |
| `docs-generate` | 1 | **gemma4:26b** | 1–2 мин | Генерация документации |
| `commit-msg` | 1 | qwen3.5:9b | 5–15 сек | Conventional commit message |
| `text-to-sql` | 1 | qwen3-coder:30b | 0.4–2 сек | NL→SQL execution |

**Перенос на Enterprise:**

| Аспект | Лаборатория (1× RTX 3090) | Enterprise (2–4× GPU) |
|--------|---------------------------|----------------------|
| Pipeline | Последовательный | Параллельный |
| Время | 3–8 мин | 1–3 мин |
| NUM_PARALLEL | 1 | 4+ |
| Архитектура | **Идентичная** | **Идентичная** |

### 2.7. Слой 7 — Observability / Operations

**Реализовано:**
- Structured JSON logging (10A): каждый запрос → JSON event
- /metrics endpoint (10B): JSON in-memory counters
- health-check.sh (15, обновлён R): 11 проверок
- setup-check.sh (13, обновлён R): 66 проверок
- benchmark.py (15): 7 сценариев
- benchmark-with-history.sh (14A): immutable snapshots + history.jsonl
- Nightly health cron (14A)

---

## 3. Пошаговый план реализации

### Навигация по этапам

| Этап | Название | Зависимости | Статус |
|------|----------|-------------|--------|
| 8A | MCP: Git Server | — | ✅ Завершён |
| 8B | MCP: Terminal + Policy | 8A | ✅ Завершён |
| 8C | Orchestrator PoC | — | ✅ Завершён |
| 8D | Headless Automation PoC | 8C | ✅ Завершён |
| 9A | gateway /v1/embeddings | — | ✅ Завершён |
| 9B | Embeddings миграция | 9A | ✅ Завершён |
| 10A | Structured Logging + модуляризация | — | ✅ Завершён |
| 10B | Metrics Endpoint | 10A | ✅ Завершён |
| 10C | Ollama Upgrade + Gemma 4 | — | ✅ Завершён |
| 10D | Continue.dev Gemma 4 | 10C | ✅ Завершён |
| 11A | Text-to-SQL PoC | 9B | ✅ Завершён |
| 11 | MCP: RAG / Docs Search | 9B | ✅ Завершён |
| 15 | Benchmark Matrix + Health | 10B | ✅ Завершён |
| 14 | Security Hardening | 10A, 11 | ✅ Завершён |
| 16 | gateway /v1/orchestrate | 8C, 10A | ✅ Завершён |
| 13 | Knowledge Layer | 8A | ✅ Завершён |
| 12 | MCP: Docker | 14 | ✅ Завершён |
| F-next | Semantic Layer | 11A, 11 | ✅ Завершён |
| R | Ревизия / Tech Debt Sweep | Все | ✅ Завершён |
| **Post-R** | **deepseek-r1:32b removal (ADR-019)** | **R** | **✅ Завершён** |

```
Параллельные треки (обновлено v1.15):

Трек A (MCP Tools):          8A✅→ 8B✅ → 11✅ ──────→ 12✅
Трек B (Backend):            9A✅→ 9B✅   10A✅→ 10B✅  10C✅→ 10D✅
Трек C (Knowledge):          ──────────────────────────→ 13✅
Трек D (Ops/Security):       ───── 15✅ → 14✅
Трек E (Orchestration):      8C✅→ 8D✅ ────────→ 16✅
Трек F (AI-as-Interface):    11A✅ → 11✅ → F-next✅

ВСЕ ТРЕКИ ЗАВЕРШЕНЫ. Ревизия R✅ выполнена. Post-R✅ (ADR-019).
Roadmap из v1.0 полностью реализован.
```

---

### Завершённые этапы — краткие итоги

**8A — MCP: Git Server ✅** (2026-03-21): mcp-server-git, STDIO, uvx, 12 tools.

**8B — Terminal Policy ✅** (2026-03-27): rules-based terminal policy через 01-general.md.

**8C — Orchestrator PoC ✅** (2026-03-27): orchestrator.py + pipelines.yaml, 5 pipeline.

**8D — Headless Automation ✅** (2026-03-27): orchestrator.py v1.1.0 (+--stdout), scripts + git hooks.

**9A — gateway /v1/embeddings ✅** (2026-03-28): gateway v0.8.0, POST /v1/embeddings.

**9B — Embeddings миграция ✅** (2026-03-29): transformers.js → qwen3-embedding через gateway.

**10A — Structured Logging ✅** (2026-03-31): gateway v0.9.0, пакет gateway/ (8 модулей), JSON logging.

**10B — /metrics ✅** (2026-04-03): gateway v0.10.0, MetricsCollector.

**10C — Gemma 4 ✅** (2026-04-03): Ollama 0.20.0, +3 Gemma 4, ADR-012.

**10D — Config Sync ✅** (2026-04-04): Continue 10 моделей, pipelines на Gemma 4.

**11A — Text-to-SQL PoC ✅** (2026-04-04): NL→SQL, SA 75–90%, 3 модели. ADR-013.

**11 — MCP RAG ✅** (2026-04-04): RAG MCP, ChromaDB 1.5.5, 5 tools. ADR-014.

**15 — Benchmark Matrix ✅** (2026-04-05): health-check.sh 11/11, benchmark.py 7/7.

**14 — Security Hardening ✅** (2026-04-07): UFW, mandatory auth, audit trail. ADR-015.

**16 — gateway /v1/orchestrate ✅** (2026-04-07): gateway v0.12.0, self-call, ADR-016.

**13 — Knowledge Layer ✅** (2026-04-08): 03-security.md, ADR multilayer, setup-check.sh/ps1. Грабли #52–58.

**12 — MCP Docker ✅** (2026-04-09): Docker MCP, 10 tools, policy enforcement, ADR-017. Грабли #59–64.

**F-next — Semantic Layer ✅** (2026-04-10): Retrieval-assisted SQL, ChromaDB sql_knowledge (34 cards), gemma4:31b SA 90% / EA 100%. ADR-018. Грабли #65–69.

**R — Ревизия ✅** (2026-04-10): Tech debt sweep. 17→12 моделей. health-check.sh и setup-check.sh обновлены. sql_knowledge_cards.py синхронизирован. ADR corpus расширен (14 files / 18 chunks). orchestrator.py подтверждён Active. datetime.utcnow() подтверждён исправленным.

**Post-R — deepseek-r1:32b removal ✅** (2026-04-14): Role-based experiment. gemma4:31b 9/10 vs deepseek-r1:32b 6/10. ADR-019. 12→11 моделей. Governance principle: retention = role-driven. Грабли #70.

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

### 4.2. Как измерять

**Ежедневно (автоматически):** health-check.sh по cron (11/11). journalctl → jq аномалии.

**Еженедельно (15 минут):** benchmark.py baseline. Review tool_call success rate.

**При обновлении:** Full benchmark ПЕРЕД и ПОСЛЕ. Деградация > 20% → rollback.

### 4.3. Как реагировать на деградацию

| Симптом | Вероятная причина | Действие |
|---------|-------------------|----------|
| TTFT вырос в 3+ раза | Модель выгружена (cold start) | Проверить OLLAMA_MAX_LOADED_MODELS |
| OOM 503 | Не помещается в VRAM+RAM | Уменьшить num_ctx |
| Tool calls не работают | Модель путается с tools | Уменьшить количество MCP tools |
| Autocomplete тормозит | Конкуренция за Ollama | Подождать (NUM_PARALLEL=1) |
| Embeddings медленные | qwen3-embedding грузится/выгружается | Рассмотреть возврат на transformers.js |

---

## 5. Матрица зрелости

| Аспект | Минимум (MVP) | Целевой уровень | Уровень «лучше Kilo» |
|--------|--------------|-----------------|----------------------|
| **Agent runtime** | Continue.dev Chat + Edit + Agent (✅) | + MCP tools (Git ✅, Terminal ✅) | + RAG ✅ + **Docker ✅** + Custom tools |
| **MCP tools** | 1 (Git ✅) | 3 (Git ✅ + Terminal ✅ + RAG ✅) | **4 (+ Docker ✅ 12)** |
| **Model routing** | Ручной выбор в UI (✅) | Формализованные profiles (✅ ADR-012, Tier 1/2/3) | Автоматический routing по задаче |
| **Model governance** | Ручной cleanup | **Role-driven retention (✅ ADR-019)** | Automated evaluation pipeline |
| **Orchestration** | Нет | Sequential pipeline PoC (✅ orchestrator.py) | **`/v1/orchestrate` в gateway (✅ 16)** |
| **Headless / CLI** | gateway API для curl (✅) | Готовые скрипты + git hooks (✅ 8D) | CI/CD интеграция + scheduled batch |
| **Knowledge layer** | Rules 3 уровня (✅) | + RAG по docs (✅ 11) + **ADR multilayer (✅ 13)** | + **onboarding (✅ 13)** + **knowledge drift control (✅ R)** |
| **Embeddings** | qwen3-embedding через шлюз (✅ 9B) | + RAG pipeline с vector store (✅ 11, ChromaDB) | **+ Text-to-SQL semantic layer (✅ F-next)** |
| **NL-to-SQL** | Text-to-SQL PoC: SA 75–90% (✅ 11A) | **+ Semantic layer (retrieval-assisted, ✅ F-next) SA 90%** | + Production pipeline + multi-DB + guardrails |
| **Observability** | Structured JSON logs + /metrics (✅ 10A+10B) | + Benchmark matrix + health-check (✅ 15) | + Persistent history + alerting (✅ 14) |
| **Security** | Bearer + UFW (✅) | **Per-user auth + audit trail (✅ 14)** | + RBAC |
| **Onboarding** | Паспорт (✅ v29) | **ONBOARDING.md + setup-check 66 проверок (✅ 13+R)** | Полный onboarding < 30 мин |
| **Automation** | Health check (✅ 15) | **+ Nightly cron + canary upgrade (✅ 14)** | Benchmark CI + auto-rollback |
| **Локальность** | 100% локальный (✅) | + RAG по собственным docs (✅ 11) | + воспроизводимый airgapped deploy |
| **Enterprise-переносимость** | Документация (✅) | Все паттерны на 1 GPU (✅ baseline 15) | **Все паттерны документированы + API (✅ 16)** |

---

## 6. Открытые вопросы и гипотезы

| # | Вопрос | Статус | Влияние | Когда закрыть |
|---|--------|--------|---------|---------------|
| 1 | MCP STDIO на Windows с Python-серверами | [F] Закрыт в 8A | — | ✅ 8A |
| 2 | Количество MCP tools, при котором qwen3-coder путается | [F] 26+ tools стабильно | — | ✅ 8A |
| 3 | qwen3-embedding vs all-MiniLM-L6-v2 для code search | [A] RAG MCP работает удовлетворительно | Низкое | Отложен |
| 4 | GPU-конкуренция при embedding + chat + autocomplete | [F] Закрыт в 9B | — | ✅ 9B |
| 5 | Качество передачи контекста между pipeline шагами | [F] Закрыт в 8C | — | ✅ 8C |
| 6 | qwen3.5:35b как Planner | [F] Нестабилен, заменён | — | ✅ 8C |
| 7 | Оптимальный размер diff для auto-review | [F] MAX_LINES=400 | — | ✅ 8D |
| 8 | Continue CLI для headless | [U] | Низкое | Мониторинг |
| 9 | Ollama NUM_PARALLEL > 1 на одном GPU | [U] | Высокое | Мониторинг |
| 10 | Момент модуляризации gateway | [F] Закрыт в 10A | — | ✅ 10A |
| 11 | ChromaDB vs Qdrant | [F] ChromaDB для PoC, Qdrant при >100K docs | — | ✅ 11 |
| 12 | GPU scheduler для multi-user | [U] | Высокое при 5+ users | Будущее |
| 13 | Text-to-SQL на кириллических схемах | [F] Закрыт в 11A | — | ✅ 11A |
| 14 | Chunking для русской технической документации | [A] ~500 токенов работает | Среднее | При масштабировании |
| 15 | Prompt injection в RAG | [F] 03-security.md как первая линия | — | ✅ 13 |
| 16 | Vanna vs dbt для корпоративных схем | [U] | Высокое | Enterprise pilot |
| 17 | gemma4:31b tool selection при 10+ tools | [A] С thin policy стабилен | Среднее | End-to-end тест |
| 18 | gemma4:26b MoE + GGML_CUDA_NO_GRAPHS performance | [A] Стабильно | Низкое | Отложен |
| 19 | tok/s formal benchmark: gemma4 vs qwen3-coder | [A] Baseline в 15 | Среднее | При оптимизации |
| 20 | gemma4:31b как unified Planner+Reviewer+**Reasoner** | **[F] Подтверждено ADR-019** | — | **✅ Post-R** |
| 21 | deepseek-coder-v2 → удаление | [F] Удалена в 14A | — | ✅ 14A |
| 22 | Semantic layer для >90% SA | [F] Закрыт в F-next — SA 90% (gemma4:31b) | — | ✅ F-next |
| 23 | Prompt bleed: retrieval vs monolithic | [F] Закрыт в F-next — retrieval устраняет | — | ✅ F-next |
| 24 | Evaluator policy как отдельный компонент | [A] Подтверждено в 11A | Среднее | Будущие PoC |
| 25 | Gemma 4 long-context (65K+) stall | [F] Blocked/External. llama.cpp #21379 | Высокое | Ollama 0.20.5+ |
| 26 | Ollama canary upgrade SOP | [F] Закрыт в 14A | — | ✅ 14A |
| 27 | Persistent benchmark history | [F] Закрыт в 14A | — | ✅ 14A |
| 28 | Knowledge cards ↔ DB schema sync: автоматизация DDL extraction → card generation | [U] | Высокое — блокирует масштабирование | Enterprise pilot |
| 29 | Consolidation двух venv (llm-gateway + rag-mcp-server) в единый runtime | [U] | Среднее — tech debt | При рефакторинге |
| 30 | gemma4:31b как primary model для semantic SQL (инверсия ADR-012 для Track F) | [A] Подтверждено в F-next | Среднее | При обновлении ADR-012 |
| 31 | Dual orchestration path: CLI orchestrator.py vs HTTP /v1/orchestrate — консолидация | [A] Оба Active, headless scripts зависят от CLI | Низкое сейчас | Стратегическое решение |
| 32 | Ollama 0.20.4 FA bug: gemma4:31b hang на >3–4K tokens, gemma4:26b empty responses | [F] Blocked/External. Upgrade заблокирован. | Высокое | Ollama 0.20.5+ |
| 33 | Continue.dev pivot на CI/CD checks + CLI. VS Code extension maintenance mode? | [Weak Signal] | Высокое — стратегический risk | Мониторинг |
| 34 | VS Code Copilot native Ollama integration — альтернатива Copilot BYOK? | [Weak Signal] | Среднее | Исследование |
| 35 | Wave 2 model cleanup: gemma4:e4b, glm-4.7-flash, qwen3.5:35b, qwen3-coder-next, gpt-oss:20b | [U] | Низкое (диск) | Стратегическое решение |
| **36** | **deepseek-r1:32b reasoning differentiation** | **[F] Закрыт — не доказана. Модель удалена (ADR-019).** | **—** | **✅ Post-R** |

---

## 7. Governance и актуальность

### 7.1. Роль и границы документа

Данная целевая архитектура определяет **требования и ограничения** для всех реализаций платформы. Она не описывает конкретный инвентарь (версии, IP-адреса, пути к файлам) — это задача паспортов стендов.

### 7.2. Политика актуальности

**Цикл пересмотра:** раз в **6 месяцев** (плановая) и внепланово при: завершении мажорного этапа, принципиальном изменении стека, обнаружении расхождения.

**Версионирование:**
- Мажорная версия (1.x → 2.x): смена стратегии, замена ключевых слоёв.
- Минорная версия (1.2 → 1.3): добавление компонентов, уточнение решений.

**Каскад на паспорта стендов:** изменение архитектуры → новая версия паспорта ≤ 2 недель.

### 7.3. Управление расхождениями

1. **Устранение через изменение стенда** — для техдолга.
2. **Оформление как архитектурное исключение** — для обоснованных отклонений с ADR.

### 7.4. Политика по новым схемам квантизации и компрессии KV-кэша

Лаборатория применяет **только официально поддержанные** схемы квантизации (Ollama/llama.cpp). Переход на новую схему: (1) официальная поддержка, (2) A/B-сравнение, (3) ADR.

### 7.5. ADR Corpus Policy (Этап 13)

Primary architectural truth для RAG = foundational + canonical ADR. При добавлении нового ADR: (1) определить слой, (2) разместить файл, (3) если canonical/foundational — reindex RAG.

### 7.6. Model Retention Governance (ADR-019)

**Retention = role-driven, not label-driven.** Каждая модель со статусом Active должна иметь подтверждённую уникальную роль, верифицированную экспериментом или benchmark. Историческая метка (например, «Deep reasoner») не является основанием для сохранения модели без валидированной дифференциации. При wave cleanup — эксперимент предшествует решению.

---

## 8. Журнал ревью

| Дата | Источник | Что изменилось |
|------|----------|----------------|
| 2026-03-20 | Perplexity AI (внешнее ревью) | Добавлены: модуляризация gateway, ChromaDB, orchestrator preload |
| 2026-03-27 | Ревизия по запросу владельца | v1.3: роль документа, статусы, Governance, квантизация KV |
| 2026-03-27 | Perplexity AI + синхронизация | v1.4: 8B Terminal Policy Active |
| 2026-03-28 | Синхронизация по 9A | v1.5: gateway /v1/embeddings Active |
| 2026-03-29 | Синхронизация по 9B + Playbook | v1.6: 8C–9B завершены. Continue 1.2.22. Embeddings миграция. Трек F добавлен. |
| 2026-04-03 | Этапы 10A–10C | v1.7: Ollama 0.20.0. Gateway v0.10.0. Gemma 4. ADR-012. |
| 2026-04-04 | Этап 11A | v1.8: Text-to-SQL PoC. ADR-013. |
| 2026-04-06 | Этапы 11, 15 + roadmap reprioritization | v1.9: RAG MCP, Benchmark Matrix, Gemma 4 long-context blocked. |
| 2026-04-06 | Hotfix v1.9 | Pipeline table fix, RAG reindex, exact-read tools, micro-cleanup. |
| 2026-04-07 | Этап 14 (A+B) | v1.10: Security Hardening. UFW, mandatory auth, ADR-015. |
| 2026-04-07 | Этап 16 | v1.11: gateway /v1/orchestrate. Self-call. ADR-016. |
| 2026-04-08 | Этап 13 | v1.12: Knowledge Layer. 03-security.md. ADR multilayer. setup-check. |
| 2026-04-09 | Этап 12 | v1.13: MCP Docker. ADR-017. Трек A завершён. |
| 2026-04-10 | Этап F-next + Ревизия R | v1.14: Semantic Layer (SA 90%, ADR-018). Все треки A–F завершены. Tech debt sweep: 17→12 моделей. Roadmap из v1.0 полностью реализован. |
| **2026-04-14** | **Эксперимент deepseek-r1 vs gemma4** | **v1.15: deepseek-r1:32b удалена (ADR-019). 12→11 моделей. gemma4:31b = Primary Reasoner. Вопрос #20 закрыт, #36 добавлен и закрыт. Model Retention Governance policy (§7.6). Tier 2 обновлён. Матрица зрелости +Model governance. Canonical ADR: 9→10 (ADR-019). Грабли #70.** |

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
| SSE | Server-Sent Events — однонаправленный серверный стриминг |
| STDIO | Standard Input/Output — межпроцессное взаимодействие |
| TTFT | Time To First Token — задержка до первого токена |
| UFW | Uncomplicated Firewall — межсетевой экран Ubuntu |
| Vanna AI | Python-библиотека для RAG-улучшенной генерации SQL |
| VRAM thrashing | Частая выгрузка/загрузка моделей в видеопамять |
| NL-to-SQL | Natural Language to SQL — преобразование запроса в SQL |
| Prompt bleed | Правка для одного кейса ломает поведение на других |
| SA | Semantic Accuracy — доля семантически правильных SQL |
| EA | Execution Accuracy — доля синтаксически корректных SQL |
| SOP | Standard Operating Procedure — стандартная процедура |
| SWA | Sliding Window Attention — механизм внимания Gemma 4 |
