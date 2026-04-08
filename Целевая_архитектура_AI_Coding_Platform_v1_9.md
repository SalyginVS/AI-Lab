# Целевая архитектура: Локальная AI Coding Platform

**Версия:** 1.9  
**Дата:** 2026-04-06  
**Базовый стек:** Ubuntu 22.04 / RTX 3090 / Ollama 0.20.0 / gateway v0.10.0 / Continue.dev v1.2.22  
**Стратегия:** Continue-first platform, Depth over Speed, локальность как принцип  
**Назначение:** Лаборатория для наработки решений → перенос на Enterprise  
**Паспорт стенда:** v23.0 (2026-04-05)

> **Роль документа.** Данный файл является **source of truth** (единым источником правды) для целевой архитектуры AI Coding Platform. Он задаёт принципы, политики и ожидаемое состояние для всех реализаций платформы, включая конкретные лабораторные стенды. Документ `Паспорт_лаборатории_vX` фиксирует фактическое состояние конкретного стенда и должен согласовываться с данной целевой архитектурой. Любое расхождение между паспортом и целевой архитектурой классифицируется как технический долг и оформляется явно.

---

## 1. Целевая архитектура

### 1.1. Обзор

Платформа трансформирует текущую лабораторию (набор работающих компонентов) в управляемую инженерную систему с семью слоями. Каждый слой имеет чёткую ответственность, определённые интерфейсы и может развиваться независимо.

Ключевой принцип: **не заменять, а достраивать**. Всё, что подтверждено тестами в этапах 1–11, 15, остаётся. Новые компоненты добавляются поверх существующего фундамента.

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
│     Git (STDIO), Terminal, RAG/Docs (streamable-http), Docker (plan) │
├─────────────────────────────────────────────────────────────────────┤
│  2. IDE AGENT LAYER                                                 │
│     Continue.dev (primary) — Chat, Edit, Agent, Apply, Autocomplete │
│     Copilot BYOK (secondary) — plain chat only                      │
├─────────────────────────────────────────────────────────────────────┤
│  1. INFERENCE / BACKEND                                             │
│     Ollama 0.20.0 → gateway.py → /v1/chat/completions              │
│     + /v1/embeddings + /v1/metrics + /v1/orchestrate (planned)     │
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
| 1. Inference/Backend | Ollama 0.20.0 + systemd | **Active** | 1–7B, 10C |
| 1. Inference/Backend | gateway v0.10.0 (/chat/completions, /models, /health, /embeddings, /metrics) | **Active** | 1–10B |
| 1. Inference/Backend | gateway /v1/orchestrate | **Planned** | 16 |
| 1. Inference/Backend | Модуляризация gateway в Python-пакет (9 модулей) | **Active** | 10A ✅ |
| 1. Inference/Backend | Gemma 4: gemma4:31b (Quality-first Agent/Planner/Reviewer) | **Active** | 10C ✅ |
| 1. Inference/Backend | Gemma 4: gemma4:26b (Fast Semantic Agent/Executor, MoE) | **Active** | 10C ✅ |
| 1. Inference/Backend | Gemma 4: gemma4:e4b (Fast edge chat, evaluation) | **PoC** | 10C |
| 2. IDE Agent Layer | Continue.dev v1.2.22 (Chat, Edit, Agent, Apply, Autocomplete) | **Active** | 7A–7C, 9B |
| 2. IDE Agent Layer | Copilot BYOK (plain chat) | **Active** | 7D |
| 2. IDE Agent Layer | Copilot BYOK (Agent mode с локальными моделями) | **Legacy** | Нестабилен, не развивать |
| 3. MCP Tool Layer | mcp-server-git (MCP — Model Context Protocol, Git-инструменты) | **Active** | 8A |
| 3. MCP Tool Layer | Terminal Policy (rules-based, Continue Agent на Windows) | **Active** | 8B ✅ |
| 3. MCP Tool Layer | Custom RAG MCP (RAG — Retrieval-Augmented Generation, поиск по документам) | **Active** | 11 ✅ |
| 3. MCP Tool Layer | Docker MCP | **Planned** | 12 |
| 4. Orchestration | orchestrator.py v1.1.0 (sequential pipeline, 6 pipeline) | **Active** | 8C ✅ |
| 4. Orchestration | Headless scripts + git hooks (auto-review, auto-commit-msg, auto-docs, pre-push) | **Active** | 8D ✅ |
| 4. Orchestration | gateway.py /v1/orchestrate (формализация) | **Planned** | 16 |
| 5. Knowledge/Context | Rules: 3 уровня (глобальный / проектный / файловый) | **Active** | 7C |
| 5. Knowledge/Context | Context providers: 12 штук (code, codebase (deprecated), repo-map и др.) | **Active** | 7C, 9B |
| 5. Knowledge/Context | @Codebase (provider: codebase) — deprecated upstream, миграция на Agent built-in tools | **Deprecated** | 9B → удаление в 14 |
| 5. Knowledge/Context | Embeddings: transformers.js all-MiniLM-L6-v2 | **Legacy** | 7C → заменён в 9B |
| 5. Knowledge/Context | Embeddings: qwen3-embedding через шлюз | **Active** | 9B ✅ |
| 5. Knowledge/Context | ADR (Architecture Decision Records — документы архитектурных решений) | **Planned** | 13 |
| 5. Knowledge/Context | Onboarding пакет + setup-check скрипт | **Planned** | 13 |
| 6. Security/Governance | Bearer token auth (опциональный) | **Active** | 5 |
| 6. Security/Governance | Обязательный Bearer + UFW (Uncomplicated Firewall — межсетевой экран Ubuntu) | **Planned** | 14 |
| 6. Security/Governance | Per-user auth + audit trail | **Planned** | 14 |
| 6. Security/Governance | Terminal Policy rules (PowerShell behavior, self-contained, no temp files) | **Active** | 8B ✅ |
| 7. Observability | journalctl текстовые логи | **Legacy** | 1 → заменён в 10A |
| 7. Observability | Structured JSON logging | **Active** | 10A ✅ |
| 7. Observability | /metrics endpoint (JSON in-memory counters) | **Active** | 10B ✅ |
| 7. Observability | Benchmark matrix + health-check.sh | **Active** | 15 ✅ |
| **Track F** | **Text-to-SQL PoC (NL→SQL benchmark, SQLite)** | **Active (PoC завершён)** | **11A ✅** |
| **Track F** | **Semantic Layer для NL-to-SQL (schema grounding, retrieval-assisted SQL)** | **Planned** | **TBD** |

### 1.4. Потоки данных

```
Сценарий: Agent mode с MCP tool (например, git commit)

VS Code (Windows 11)
  └── Continue.dev Agent mode
        │
        ├─1─ Отправляет промпт + tools list → gateway.py :8000
        │     └── gateway.py → Ollama :11434 (qwen3-coder:30b)
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
  └─── curl POST /v1/chat/completions → gateway.py :8000
        model: deepseek-r1:32b
        messages: [{ role: user, content: "Review this diff:\n{diff}" }]
        │
        └─── Ответ: структурированный code review
             → записывается в PR comment / файл / stdout
```

---

## 2. Архитектурные решения

### 2.1. Слой 1 — Inference / Backend

**Что остаётся без изменений (F — подтверждено тестами):**
- Ollama 0.20.0, systemd, override.conf — стабильно (обновлён с 0.18.0 в 10C)
- gateway v0.10.0 — стриминг, reasoning policy, tool_calls проброс, auth, embeddings, metrics
- OLLAMA_MAX_LOADED_MODELS=2, NUM_PARALLEL=1, Flash Attention, KV (Key-Value) cache q8_0

**Что изменилось в 10C–15:**
- Ollama 0.18.0 → 0.20.0 (поддержка Gemma 4, fix qwen3.5 tool calling)
- 13 моделей → 16 моделей (+ gemma4:31b, gemma4:26b, gemma4:e4b)
- Раскладка ролей радикально обновлена: Gemma 4 занимает Tier 1
- Gateway: MAX_NUM_CTX 32768→131072, HTTPX_TIMEOUT 600s→3600s (этап 15)
- health-check.sh (11/11 проверок) + benchmark.py (7/7 сценариев) + baseline snapshot (этап 15)

**Известное ограничение (F — upstream bug):**
Gemma 4 (31b, 26b) long-context (num_ctx ≥ 65K) → stall (GPU util=0%, no generation). Root cause: llama.cpp SWA context-shift bug (#21379). Hardware-agnostic (подтверждено на RTX 5090, DGX Spark, M1 Max, ROCm). Стабильная граница: ctx ≤ 32768. Для long-context задач — non-Gemma модели (qwen3-coder, deepseek-r1). Отслеживать: Ollama 0.20.1+.

**Что дорабатывается:**

| Компонент | Изменение | Обоснование |
|-----------|-----------|-------------|
| gateway → v0.11.0 | `/v1/orchestrate` endpoint | Sequential multi-model pipeline. Формализация паттерна после PoC на скрипте |

**Что убирается:** Ничего. Все существующие endpoint'ы сохраняют обратную совместимость.

**Решение по модуляризации gateway (A — принято по результатам ревью):**

gateway.py v0.7.0 — 994 строки. При добавлении embeddings, structured logging, metrics, orchestrate вырастет до 2000+. Монолитный файл станет неуправляемым и превратится в single point of failure.

Решение: при первом расширении (этап 9A или 10A) разбить на Python-пакет. Не отдельные сервисы (overkill для лаборатории), а модули в одном процессе:

```
~/llm-gateway/
  ├── gateway/
  │   ├── __init__.py        # Версия, общие константы
  │   ├── app.py             # FastAPI app, mount routes
  │   ├── router.py          # Model routing, reasoning policy, resolve_effort()
  │   ├── streaming.py       # Stream generator, SSE, tool_calls conversion
  │   ├── embeddings.py      # /v1/embeddings endpoint (этап 9A)
  │   ├── orchestrator.py    # /v1/orchestrate endpoint (этап 16)
  │   ├── metrics.py         # /metrics, in-memory counters (этап 10B)
  │   ├── auth.py            # Bearer validation, per-user tokens (этап 14)
  │   ├── logging_config.py  # Structured JSON logging (этап 10A)
  │   └── models.py          # Pydantic models, validation
  ├── pipelines.yaml         # Orchestrator pipeline definitions
  ├── config.yaml            # Gateway configuration (если потребуется)
  └── run.py                 # uvicorn entrypoint
```

Принцип: gateway остаётся **одним процессом** (один systemd unit, один порт), но логически разделён на модули. Это позволяет: обновлять embeddings не трогая streaming; тестировать orchestrator изолированно; при переносе на Enterprise — вынести модули в отдельные сервисы, если нагрузка потребует.

**Решение по маршрутизации моделей (обновлено в 10C — интеграция Gemma 4):**

**Tier 1 — Primary workhorses:**

| Роль | Модель | Путь | num_ctx | reasoning_effort | Этап |
|------|--------|------|---------|-----------------|------|
| Quality-first Agent / Planner / Reviewer | **gemma4:31b** | шлюз | 8192 (до 256K) | none / high | 10C |
| Fast Semantic Agent / Fast Executor | **gemma4:26b** (MoE, 3.8B active) | шлюз | 8192 (до 256K) | none | 10C |
| Stable Generic Executor / Backup Agent / **Best SQL Executor** | qwen3-coder:30b | шлюз | 8192 | none | 7A, **11A** |
| Autocomplete (FIM — Fill-In-the-Middle) | qwen2.5-coder:7b | Ollama напрямую | 2048 | — | 7B |
| Embeddings | qwen3-embedding | шлюз /v1/embeddings | — | — | 9A |

**Tier 2 — Specialized:**

| Роль | Модель | Путь | Примечание |
|------|--------|------|-----------|
| Deep Reasoning | deepseek-r1:32b | шлюз | Специализированный reasoner |
| Fast chat + light tools | qwen3.5:9b | шлюз | Tool calling восстановлен в Ollama 0.20.0 |
| General / Planner reserve | qwen3:30b | шлюз | Понижен: gemma4:31b забрала роль Planner |
| Vision reserve | qwen3-vl:8b | шлюз | Понижен: gemma4:26b/31b имеют vision |
| Fast edge chat (evaluation) | gemma4:e4b | шлюз | Частично протестирована |

**Tier 3 — Legacy / Reserve:**

| Модель | Статус | Примечание |
|--------|--------|-----------|
| qwen3.5:35b | Legacy | Tools сломаны в Ollama. НЕ использовать как Agent/Planner |
| glm-4.7-flash | Reserve | Понижен: gemma4:26b занимает нишу fast agent |
| deepseek-r1:14b | Reserve | Компактный reasoning |
| qwen3:14b | Reserve | Chat reserve |
| qwen2.5-coder:1.5b | Reserve | FIM fallback |
| deepseek-coder-v2:16b | **Deprecated** | Роль полностью покрыта Gemma 4. Рекомендовать удаление |

**ADR-012: Gemma 4 Model Integration (10C)**

Контекст: Gemma 4 (31B Dense #3 Arena, 26B MoE #6 Arena) доступны в Ollama 0.20.0 с подтверждённым function calling (generic + semantic), multi-step chaining, thinking mode и vision. Решение: интегрировать обе модели в primary tier. Не бинарное деление "Gemma semantic / Qwen generic", а ролевое: Gemma — quality-first agent/planner/reviewer, Qwen — stable generic executor. Ключевой нюанс: gemma4:31b требует thin policy layer для стабильного tool selection; gemma4:26b — лучший zero-shot semantic selector.

### 2.2. Слой 2 — IDE Agent Layer

**Что остаётся (F):**
- Continue.dev v1.2.22 — основной agent runtime
- config.yaml: 10 моделей (1 embed + 1 FIM + 8 chat-capable), 12 context providers, 6 prompts
- Copilot BYOK — дополнительный plain chat
- 2 MCP servers (mcp-server-git STDIO + Lab RAG streamable-http)

**Что дорабатывается:**

| Компонент | Изменение | Обоснование |
|-----------|-----------|-------------|
| config.yaml | Добавить секцию `mcpServers:` | Подключение MCP tools для Agent mode |
| config.yaml | Формализовать model profiles в комментариях | Документирование ролей для onboarding |
| Copilot BYOK | Зафиксировать как «compatibility check only» | Agent mode нестабилен — не тратить усилия |

**Что убирается:** Ничего. Copilot BYOK остаётся, но с пониженным статусом.

**Решение по Agent runtime (F):** Continue.dev — единственный основной agent runtime. Причины: подтверждён для Chat, Edit, Agent, Apply, Context, Rules, Prompts; полностью локальный; поддерживает MCP; Copilot Agent mode с локальными моделями нестабилен и неисправим на стороне шлюза.

### 2.3. Слой 3 — MCP Tool Layer

**Архитектурное решение по транспорту (ADR-014):** STDIO (Standard Input/Output — межпроцессное взаимодействие) для клиентских MCP-серверов (работают на Windows). Streamable-http — для серверных MCP-серверов (работают на Ubuntu, нужен доступ к ресурсам сервера). SSE (Server-Sent Events) deprecated в MCP spec — не использовать для новых серверов.

**Критическая архитектурная заметка:** Continue.dev запущен на Windows-клиенте. MCP-серверы, запущенные через STDIO, будут выполняться тоже на Windows. Git MCP работает с локальными репозиториями на Windows. Terminal MCP выполняет команды на Windows. Docker MCP и RAG MCP требуют либо DOCKER_HOST/SSH-туннеля, либо SSE-сервера на Ubuntu.

**Целевой набор MCP-серверов:**

| # | MCP Server | Транспорт | Среда выполнения | Статус | Приоритет |
|---|-----------|-----------|-----------------|--------|-----------|
| 1 | **mcp-server-git** (Anthropic, Python) | STDIO | Windows (uvx) | **Active** | Этап 8A ✅ |
| 2 | **Terminal Policy** (rules-based, 01-general.md) | — (нативный VS Code terminal) | Windows (VS Code) | **Active** | Этап 8B ✅ |
| 3 | **Lab RAG Server** (custom, FastMCP, ChromaDB 1.5.5, 286 chunks) | streamable-http (:8100) | Сервер (Ubuntu) | **Active** | Этап 11 ✅ |
| 4 | **Docker MCP** (custom или docker/hub-mcp) | streamable-http | Сервер (Ubuntu) | **Planned** | Этап 12 |

**Решение по policy (A — гипотеза, требует проверки на практике):**

| Категория инструмента | Политика | Примеры |
|-----------------------|----------|---------|
| Read-only | Автоматическое выполнение | git status, git log, git diff, docker ps, file read |
| Write (файлы/код) | Выполнение с показом diff | git commit, git push, file write |
| Destructive | Подтверждение пользователя | git reset --hard, docker rm, branch delete |
| Network/External | Allowlist | push to remote, docker pull |
| Sensitive paths | Denylist | .env, secrets/, private keys |

> **[A]** Continue.dev v1.2.17 управляет approval на уровне Agent mode. Гранулярная per-tool policy — будущая доработка через Continue API или custom MCP server wrapper.

### 2.4. Слой 5 — Knowledge / Context Layer

**Что остаётся (F):**
- Rules: 3 уровня (встроенный → глобальные → проектные)
- Context providers: 12 штук, включая @Code, @Repository Map, @Codebase (deprecated)
- Embeddings: qwen3-embedding через шлюз (заменил transformers.js в 9B)
- Prompts: 6 slash-команд

**Что требует миграции:**
- `provider: codebase` (deprecated upstream) → удалить из config.yaml, заменить на Agent mode built-in tools + RAG MCP

**Что дорабатывается:**

| Компонент | Изменение | Обоснование |
|-----------|-----------|-------------|
| Глобальные rules | Добавить `03-security.md` | Правила по обращению с секретами, .env, credentials |
| Проектные rules | Шаблон `01-project.md` с обязательными секциями | Стандартизация для onboarding |
| docs: в config.yaml | Добавить корпоративные docs для @Docs context | Индексация внутренней документации |
| ADR | Шаблон `.continue/docs/adr/` в workspace | Фиксация архитектурных решений для AI-контекста |
| provider: codebase | Удалить из config.yaml | Deprecated upstream; Agent built-in tools + RAG MCP покрывают use cases |

**Целевая структура Knowledge:**

```
%USERPROFILE%\.continue\              # Глобальный уровень (организация)
  ├── config.yaml                     # Модели, MCP, context, prompts
  ├── rules\
  │   ├── 01-general.md               # Язык, стиль, окружение
  │   ├── 02-coding.md                # Стандарты кода
  │   └── 03-security.md              # Обращение с секретами (НОВЫЙ)
  └── mcpServers\
      └── git.yaml                    # Глобальный MCP (НОВЫЙ)

<workspace>\.continue\                # Проектный уровень
  ├── rules\
  │   └── 01-project.md               # Стек, структура, naming
  ├── mcpServers\
  │   └── project-tools.yaml          # Проектные MCP (опционально)
  └── docs\
      └── adr\
          └── 001-template.md         # ADR шаблон
```

### 2.5. Слой 6 — Security / Governance

**Что уже есть (F):**
- Bearer auth в gateway.py (опциональная)
- Continue.dev полностью локален — данные не покидают сеть
- Ollama слушает 0.0.0.0 — доступен в LAN

**Что добавляется:**

| Компонент | Что | Обоснование |
|-----------|-----|-------------|
| gateway.py auth | Обязательный Bearer token при multi-user | Защита от несанкционированного использования GPU |
| MCP tool policy | Denylist путей в rules + MCP server config | Защита .env, ключей, приватных данных |
| Ollama firewall | UFW правила: 11434 только из LAN | Ollama не должен быть доступен извне |
| Audit trail | Лог tool_calls с user id, tool name, args, result | Трассируемость действий для governance |
| Onboarding пакет | Единый config + инструкция + проверочный скрипт | Воспроизводимость для новых участников |

**Решение по multi-user auth (A — для будущего 5+ пользователей):**

Текущая модель: один Bearer token на весь шлюз. Целевая модель: per-user tokens в gateway.py с идентификацией в логах. Реализация — когда появится второй пользователь. Не раньше.

### 2.6. Слой 4 — Orchestration / Automation

**Это полностью новый слой.** Текущая лаборатория не имеет ни оркестрации, ни headless-автоматизации.

NUM_PARALLEL=1 ограничивает **параллельное** выполнение нескольких агентов, но не ограничивает **последовательную** оркестрацию. Паттерн «Planner → Executor → Reviewer» работает на одном GPU, просто каждый шаг выполняется по очереди с холодным стартом при смене модели. Это полностью в логике Depth over Speed: тратим время, получаем качество, которое одна модель дать не может.

**Три компонента Orchestration / Automation:**

| Компонент | Что | Реализация | Статус |
|-----------|-----|------------|--------|
| **Sequential Orchestrator** | Multi-model pipeline: Planner → Executor → Reviewer | orchestrator.py v1.1.0 (6 pipelines, Gemma 4 — ADR-012) | **Active** ✅ 8C |
| **Headless Scripts** | Автоматические задачи без IDE: code review, doc generation, commit messages | Bash/Python скрипты через curl/OpenAI SDK | **Active** ✅ 8D |
| **CI/CD Hooks** | Интеграция с git hooks и CI pipeline | git pre-push → auto-review | **Active** ✅ 8D |
| **gateway /v1/orchestrate** | Формализованный API endpoint для pipeline execution | Перенос orchestrator.py в gateway | **Planned** → 16 |

**Архитектура Orchestrator:**

```
orchestrator.py (или gateway.py /v1/orchestrate)
  │
  ├── Pipeline registry (YAML)
  │   ├── plan-execute-review    # Planner (35b) → Executor (30b) → Reviewer (32b)
  │   ├── code-review            # Reviewer only (deepseek-r1:32b)
  │   └── generate-docs          # Executor only (qwen3-coder:30b)
  │
  ├── Step executor
  │   └── Каждый шаг = POST /v1/chat/completions к gateway.py
  │       с указанием модели, промпта, и контекста предыдущего шага
  │
  └── Result aggregator
      └── Собирает результаты всех шагов в финальный ответ
```

**Типовые pipeline (фактическое состояние pipelines.yaml):**

| Pipeline | Шаги | Модели (факт) | Типичное время (RTX 3090) | Use case |
|----------|-------|--------|---------------------------|----------|
| `plan-execute-review` | 3 | qwen3:30b → qwen3-coder:30b → deepseek-r1:32b | 3–8 мин | Сложные задачи: новая фича, рефакторинг модуля |
| `execute-review` | 2 | qwen3-coder:30b → deepseek-r1:32b | 2–5 мин | Стандартные задачи: реализация по спецификации |
| `review-only` | 1 | deepseek-r1:32b | 1–3 мин | Code review (headless, CI/CD) |
| `docs-generate` | 1 | qwen3-coder:30b | 1–2 мин | Генерация документации (headless) |
| `commit-msg` | 1 | qwen3.5:9b | 5–15 сек | Conventional commit message |
| `text-to-sql` | 1 | qwen3-coder:30b | 0.4–2 сек | NL→SQL execution (лучший SQL executor, 11A) |

> **Миграция на Gemma 4 (целевая, ADR-012):** plan-execute-review → gemma4:31b → gemma4:26b → gemma4:31b; execute-review → qwen3-coder:30b → gemma4:31b; review-only → gemma4:31b. Миграция pipelines.yaml запланирована на Этап 16 (/v1/orchestrate) — при формализации pipeline в gateway обновить и модельную раскладку.

**Решение по реализации — двухфазный подход:**

Фаза 1 (этап 8C): **orchestrator.py** — отдельный Python-скрипт. PoC: быстро экспериментировать, искать рабочий паттерн.

Фаза 2 (позже): **gateway.py `/v1/orchestrate`** — формализованный endpoint. Pipeline registry в конфиге шлюза. Стриминг промежуточных результатов. Логирование каждого шага.

**Перенос на Enterprise:**

| Аспект | Лаборатория (1× RTX 3090) | Enterprise (2–4× GPU) |
|--------|---------------------------|----------------------|
| Pipeline | Последовательный (шаги по очереди) | Параллельный (Planner и Reviewer на разных GPU) |
| Время | 3–8 мин на сложный pipeline | 1–3 мин (параллелизм + быстрее GPU) |
| NUM_PARALLEL | 1 | 4+ |
| Архитектура | **Идентичная** — gateway.py + orchestrator.py | **Идентичная** — gateway.py + orchestrator.py |
| Модели | Те же (или крупнее) | Те же (или крупнее, full precision) |

### 2.7. Слой 7 — Observability / Operations

**Что уже есть (F):**
- Логи через `uvicorn.error` → systemd journal
- `/health` endpoint
- `journalctl -u llm-gateway -f` для live мониторинга

**Что добавляется:**

| Компонент | Что | Обоснование |
|-----------|-----|-------------|
| Structured logging | JSON-формат логов в gateway.py | Машиночитаемость, парсинг, агрегация |
| Per-request metrics | model, tokens (prompt/completion), latency (TTFT/total), status | Мониторинг деградации |
| Tool-call tracing | tool name, arguments (sanitized), duration, success/fail | Отладка agent workflows |
| `/metrics` endpoint | JSON или Prometheus text format | Внешний мониторинг, дашборд |
| Benchmark matrix | Набор стандартных промптов с эталонными ответами | Регрессионное тестирование при обновлении моделей |
| Health check скрипт | Bash-скрипт: Ollama alive + gateway alive + модель отвечает | Автоматическая диагностика |

---

## 3. Пошаговый план реализации

### Навигация по этапам

| Этап | Название | Зависимости | Статус | Оценка трудоёмкости |
|------|----------|-------------|--------|---------------------|
| 8A | MCP: Git Server | — | ✅ **Завершён** | — |
| 8B | MCP: Terminal + Policy | 8A | ✅ **Завершён** | — |
| 8C | Orchestrator PoC (sequential multi-model pipeline) | — | ✅ **Завершён** | — |
| 8D | Headless Automation PoC (скрипты + git hooks) | 8C | ✅ **Завершён** | — |
| 9A | gateway.py v0.8.0: /v1/embeddings | — | ✅ **Завершён** | — |
| 9B | Embeddings миграция: transformers.js → qwen3-embedding | 9A | ✅ **Завершён** | — |
| 10A | gateway.py v0.9.0: Structured Logging + модуляризация | — | ✅ **Завершён** | — |
| 10B | gateway.py v0.10.0: Metrics Endpoint | 10A | ✅ **Завершён** | — |
| 10C | Ollama Upgrade + Gemma 4 Integration | — | ✅ **Завершён** | — |
| 10D | Continue.dev Gemma 4 Integration | 10C | ✅ **Завершён** | — |
| **11A** | **Text-to-SQL PoC** | **9B** | **✅ Завершён** | **—** |
| **11** | **MCP: RAG / Docs Search (ChromaDB, FastMCP, streamable-http)** | **9B** | **✅ Завершён** | **—** |
| **15** | **Benchmark Matrix + Health Automation** | **10B** | **✅ Завершён** | **—** |
| **14** | **Security Hardening + Multi-user Auth (расширенный)** | **10A, 11** | ⬜ **Следующий** | **2 спринта** |
| **16** | **gateway.py v0.11.0: /v1/orchestrate (формализация)** | **8C, 10A** | ⬜ Planned | **2 спринта** |
| 13 | Knowledge Layer: Rules + ADR + Onboarding | 8A | ⬜ Planned | 1–2 спринта |
| 12 | MCP: Docker | 14 (security boundary) | ⬜ Planned | 1 спринт |
| F-next | Semantic Layer: retrieval-assisted SQL | 11A, 11 | ⬜ Planned | 2–3 спринта |

```
Параллельные треки (обновлено v1.9):

Трек A (MCP Tools):          8A✅→ 8B✅ → 11✅ ─────────────────────→ 12
Трек B (Backend):            9A✅→ 9B✅   10A✅→ 10B✅  10C✅→ 10D✅
Трек C (Knowledge):          ────────────────────────────────────→ 13
Трек D (Ops/Security):       ──────────────── 15✅ → 14 ◄── СЛЕДУЮЩИЙ
Трек E (Orchestration):      8C✅→ 8D✅ ──────────────────→ 16
Трек F (AI-as-Interface):    9B✅ → [11A Text-to-SQL]✅ → [11 RAG MCP]✅ → [Semantic Layer] → [AI Report]

Приоритетный порядок следующих этапов: 14 → 16 → 13 → 12 → F-next
```

---

### Этап 8A — MCP: Git Server ✅ Завершён

**Задача:** Подключить первый MCP-сервер (Git) к Continue.dev Agent mode. Proof-of-concept MCP-интеграции.

**Результат подтверждён (2026-03-21):** mcp-server-git работает, STDIO транспорт на Windows через uvx, 12 tools доступны в Agent mode. git status, log, diff, add, commit, branch — все подтверждены.

---

### Этап 8B — Terminal Policy Framework ✅ Завершён

**Результат подтверждён (2026-03-27):** Terminal Policy Baseline реализован для Continue Agent на Windows через global rule `01-general.md` (`alwaysApply: true`). Отдельный Terminal MCP server не разворачивался — встроенных возможностей Continue terminal оказалось достаточно для baseline-уровня.

**Реализованные правила (terminal block в `01-general.md`):**
- PowerShell-native команды вместо bash-style (`Get-ChildItem` вместо `ls -la`)
- Self-contained execution — каждая команда не зависит от состояния предыдущей
- Не создавать временные файлы без явного запроса
- Не оборачивать всю команду в строковые кавычки
- UTF-8 preamble для кириллических и других non-ASCII имён файлов:
  `$OutputEncoding = [System.Text.UTF8Encoding]::new(); [Console]::InputEncoding = [System.Text.UTF8Encoding]::new(); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new();`

**Проверено на стенде:**
- Agent перестал генерировать `ls -la`, перешёл на `Get-ChildItem`, `Get-Content`, `Where-Object`
- Кириллические имена файлов читаются корректно после UTF-8 preambule

**Scope:** rules-based terminal policy baseline в Continue/Windows. Это слой 5 (Knowledge/Context) + частично слой 6 (Security/Governance). Бэкенд (Ollama, gateway.py, Ubuntu) не менялся.

**Residual issue:** иногда модель оборачивает команду в строку и печатает вместо выполнения — дефект качества tool-call generation, не блокирующий. Мониторируется.

**Артефакты:**
1. `01-general.md` — обновлён (Windows terminal block)
2. `Этап8B_результаты.md`

---

### Этап 8C — Orchestrator PoC (Sequential Multi-Model Pipeline)

**Задача:** Создать Python-скрипт `orchestrator.py`, реализующий последовательный multi-model pipeline через gateway.py.

**Артефакты:**
1. `orchestrator.py` — скрипт с OpenAI SDK, YAML-конфиг pipeline
2. `pipelines.yaml` — описание pipeline
3. Тестовый протокол: 3 задачи через pipeline с замерами времени
4. Этап8C_результаты.md

**Критерий завершения:**
- [ ] `python orchestrator.py --pipeline plan-execute-review --task "..."` возвращает результат
- [ ] Все три тестовые задачи прошли pipeline с осмысленным результатом
- [ ] Замеры: время каждого шага и общее время pipeline задокументированы
- [ ] Результат Reviewer содержит конкретные замечания

---

### Этап 8D — Headless Automation PoC (Скрипты + Git Hooks)

**Задача:** Создать набор готовых скриптов для автоматизации без IDE: auto code review, auto commit message, auto docs generation.

**Артефакты:**
1. `scripts/auto-review.sh`
2. `scripts/auto-commit-msg.sh`
3. `scripts/auto-docs.sh`
4. `.githooks/pre-push`
5. Этап8D_результаты.md

**Критерий завершения:**
- [ ] `./scripts/auto-review.sh` выдаёт осмысленный review для diff gateway.py
- [ ] `./scripts/auto-commit-msg.sh` генерирует conventional commit message
- [ ] Git pre-push hook работает
- [ ] Документирован выбор: синхронный или асинхронный режим

---

### Этап 9A — gateway.py v0.8.0: /v1/embeddings ✅ Завершён

**Результат подтверждён (2026-03-28):** Endpoint `POST /v1/embeddings` добавлен в gateway.py v0.8.0. OpenAI-compatible формат, batch support, staged pipeline validation, allowlist (qwen3-embedding). Негативные тесты подтверждены: empty_input (400), schema 422, unsupported_model (400). Hotfix (9B): encoding_format silent coerce.

---

### Этап 9B — Embeddings миграция: transformers.js → qwen3-embedding ✅ Завершён

**Результат подтверждён (2026-03-29):** Continue.dev embeddings переключены с transformers.js (all-MiniLM-L6-v2, 384 dim) на qwen3-embedding (8B, 4096 dim) через gateway `/v1/embeddings`. Transport path подтверждён (batched 200 OK, automatic reindex). FIM и chat не деградировали. Грабли: encoding_format float обязателен, apiKey заглушка, Windows EBUSY при rebuild, @Codebase provider deprecated.

---

### Этап 11A — Text-to-SQL PoC ✅ Завершён

**Результат подтверждён (2026-04-04):** NL→SQL PoC доказан на SQLite (6 таблиц, 171 запись, ONDO-тематика: departments, employees, facilities, energy_consumption, hotel_bookings, production_orders). 20 тестовых вопросов (4 уровня сложности) по 3 моделям.

Baseline truth (v2 business-aware evaluator): qwen3-coder:30b EA 100% / SA 75% / 0.4s, gemma4:31b EA 95% / SA 70% / 4.0s, gemma4:26b EA 95% / SA 65% / 1.5s. Prompt addendum (v3): SA 85–90% для всех моделей (+15–20 п.п., model-agnostic эффект). Safety/hallucination: 100% pass (все модели).

qwen3-coder:30b — лучший SQL executor (speed + accuracy). Prompt bleed подтверждён при micro-tuning: точечная правка одного rule вызвала regression на других кейсах (Грабли #36). ADR-013: evaluator separation (strict vs business-aware = 2–3x разница в SA) + prompt freeze после достижения 90% SA. Следующий шаг — semantic layer / retrieval-assisted SQL (Vanna, few-shot retrieval по schema), а не prompt polishing.

**Enterprise-переносимость:** паттерн NL→SQL + semantic layer переносится на любые СУБД и модели. Лабораторный результат = benchmark для оценки вендорских BI-решений с ИИ.

---

### Этап 10A — gateway v0.9.0: Structured Logging + модуляризация ✅ Завершён

**Результат подтверждён (2026-03-31):** Монолит gateway.py (1305 строк) разбит на пакет gateway/ (8 модулей, ADR-008 закрыт). Structured JSON logging: Custom JSONFormatter (stdlib), события llm_completion + llm_embedding. uvicorn.access заменён на свой middleware. run.py entrypoint. systemd ExecStart обновлён.

---

### Этап 10B — gateway v0.10.0: Metrics Endpoint ✅ Завершён

**Результат подтверждён (2026-04-03):** Новый модуль metrics.py (9-й в пакете). GET /metrics: JSON in-memory counters (totals, endpoints, models). MetricsCollector singleton, thread-safe. collector.record() в 8 точках (5 chat + 3 embed). /metrics освобождён от Bearer auth. Observability baseline закрыт: health + structured logs + metrics.

---

### Этап 10C — Ollama Upgrade + Gemma 4 Integration ✅ Завершён

**Результат подтверждён (2026-04-03):** Ollama 0.18.0 → 0.20.0. Три модели Gemma 4 загружены и протестированы (31B Dense, 26B MoE, E4B). Regression стека подтверждён. Tool calling (generic + semantic) подтверждён для gemma4:31b и gemma4:26b. Multi-step semantic chaining подтверждён. Thinking mode подтверждён. Code/review quality: Gemma 4 превосходит qwen3-coder:30b. Ключевой нюанс: gemma4:31b чувствительна к tool selection policy — стабилизируется thin policy prompt. gemma4:26b — лучший zero-shot semantic selector. qwen3.5:9b tool calling восстановлен после Ollama 0.20.0. ADR-012 зафиксирован. 13 → 16 моделей.

---

### Этап 11 — MCP: RAG / Docs Search ✅ Завершён

**Результат подтверждён (2026-04-04):** Lab RAG Server — custom MCP server (Python, FastMCP), streamable-http транспорт на порту 8100 (ADR-014). ChromaDB 1.5.5 (embedded), 133 файлов / 286 chunks проиндексировано. 3 tools: search_docs, list_collections, index_status. systemd rag-mcp.service. UFW 8100/tcp LAN-only. 9/10 тестовых запросов ✅ релевантно, cross-tool (git+RAG) работает, кириллица работает. Грабли #38–42.

**Решение по vector DB (F — подтверждено на практике):**

| Вариант | Плюсы | Минусы | Решение |
|---------|-------|--------|---------|
| **ChromaDB** (embedded) | Встроенный, zero-config, Python-native, SQLite backend | Ограничен масштаб (~100K документов) | **PoC — ChromaDB** |
| Qdrant | Production-grade, быстрый, REST API | Отдельный сервис, больше инфраструктуры | Миграция при > 100K docs или multi-user |

**RAG pipeline:**

```
Индексация (batch, offline):
  Docs (.md, .py, .yaml)
    → Chunking (~500 токенов)
      → qwen3-embedding через gateway /v1/embeddings
        → ChromaDB collection (embedded)

Поиск (online, через MCP tool):
  Agent query
    → MCP server → qwen3-embedding (query → vector)
      → ChromaDB similarity search (top-5)
        → Результаты с source и score → Agent контекст
```

---

### Этап 12 — MCP: Docker

**Задача:** Подключить Docker Engine на сервере как MCP tool.

**Зависимости:** Этап 14 (security boundary — Docker MCP увеличивает blast radius, требует hardened perimeter).

**Вариант реализации:** Custom MCP server на сервере (Python, FastMCP, streamable-http) → из Continue Agent mode. Предпочтительнее STDIO: не требует Docker CLI на Windows, безопаснее. Транспорт: streamable-http (ADR-014).

---

### Этап 13 — Knowledge Layer: Rules + ADR + Onboarding

**Задача:** Формализовать knowledge layer. Воспроизводимый онбординг за 30 минут.

**Артефакты:**
1. `03-security.md` — глобальный rule
2. ADR шаблон + первые 3 ADR
3. Onboarding README
4. `setup-check.sh` + `setup-check.ps1`

---

### Этап 14 — Security Hardening + Multi-user Auth (расширенный)

**Задача:** Единый ingress через gateway, security perimeter, persistent observability.

**Scope расширен** (по результатам архитектурного ревью v1.9): помимо auth и UFW, включает Ollama perimeter hardening, canary upgrade procedure, persistent benchmark history и @Codebase cleanup.

**Компоненты:**

| Блок | Что | Обоснование |
|------|-----|-------------|
| UFW hardening | Ограничить Ollama 11434 → localhost + whitelist Windows-клиента | Единый ingress через gateway. Прямой доступ только для FIM (latency) |
| Gateway auth | Mandatory Bearer (не optional), per-user tokens | Защита от несанкционированного использования GPU |
| Audit log | user_id в structured JSON logs | Трассируемость для governance |
| MCP streamable-http | Origin validation для rag-mcp-server :8100 | Защита MCP endpoints от неавторизованного доступа |
| Ollama canary procedure | benchmark.py before/after при каждом обновлении Ollama | Regression guardrail (Грабли #43 — upstream bugs) |
| Persistent benchmark history | Append-only JSON log + cron для nightly health-check | Trending, деградация заметна раньше |
| @Codebase cleanup | Удалить `provider: codebase` из config.yaml | Deprecated upstream, Agent built-in tools + RAG MCP как замена |
| deepseek-coder-v2:16b | `ollama rm deepseek-coder-v2:16b` | Deprecated, роль покрыта Gemma 4 |
| datetime.utcnow() fix | Заменить на datetime.now(UTC) в orchestrator.py | Python 3.12+ DeprecationWarning (Грабли #34) |

**Критерий завершения:**
- [ ] Два разных токена → два разных user_id в логах
- [ ] Запрос без токена → 401
- [ ] `ufw status` показывает: 11434 только localhost + client IP, 8000 LAN, 8100 LAN
- [ ] Ollama canary upgrade SOP (Standard Operating Procedure) задокументирована
- [ ] `crontab -l` показывает nightly health-check
- [ ] benchmark history: ≥2 записи в append-only log
- [ ] `provider: codebase` отсутствует в config.yaml
- [ ] deepseek-coder-v2:16b отсутствует в `ollama list`
- [ ] orchestrator.py: `datetime.utcnow()` заменён

---

### Этап 15 — Benchmark Matrix + Health Automation ✅ Завершён

**Результат подтверждён (2026-04-05):** health-check.sh (11/11 проверок). benchmark.py (7/7 сценариев: chat quality/fast/executor, reasoning, embeddings, orchestrator smoke, text-to-sql regression). Baseline snapshot: JSON + markdown в ~/llm-gateway/benchmarks/. 128K context window: Blocked/External — upstream bug Ollama 0.20.0 / llama.cpp SWA (Грабли #43). Gateway fixes: MAX_NUM_CTX 32768→131072, HTTPX_TIMEOUT 600s→3600s. Грабли #43–45.

---

### Этап 16 — gateway.py v0.11.0: /v1/orchestrate (Формализация)

**Задача:** Перенести отлаженный orchestrator паттерн из скрипта (этап 8C) в gateway.py как формальный endpoint. Enterprise-transferable: единый API-контракт для pipeline execution переносится в enterprise as-is.

**Зависимости:** Этап 8C ✅ (PoC валидирует паттерн), Этап 10A ✅ (structured logging для трейсинга шагов).

**Критерий завершения:**
- [ ] `curl -X POST :8000/v1/orchestrate -d '{"task":"...","pipeline":"plan-execute-review"}'` работает
- [ ] Stream mode показывает промежуточные результаты
- [ ] Логи содержат трейс каждого шага pipeline
- [ ] Pipeline конфигурируется через YAML без изменения кода

---

## 4. План контроля и эксплуатации

### 4.1. Что измерять

| Метрика | Как | Порог нормы | Порог тревоги |
|---------|-----|-------------|--------------|
| TTFT (Time To First Token — время до первого токена) | Structured log, поле `ttft_ms` | < 5 сек (холодный < 30 сек) | > 10 сек (горячий) |
| Tokens/sec | Structured log, completion_tokens / total_latency | > 5 t/s (30B модели) | < 2 t/s |
| Tool call success rate | Подсчёт finish_reason=tool_calls / total agent requests | > 80% | < 50% |
| Apply success rate | Ручной мониторинг (пока) | > 90% | < 70% |
| OOM (Out of Memory) rate | Подсчёт 503 в логах | < 1/день | > 5/день |
| Gateway uptime | `/health` + systemd | > 99.5% | < 99% |
| Autocomplete latency | Continue devtools / ручной замер | < 2 сек | > 5 сек |
| Embedding query latency | Structured log (этап 9A) | < 1 сек | > 3 сек |
| Model load time (cold start) | Structured log | < 30 сек | > 60 сек |

### 4.2. Как измерять

**Ежедневно (автоматически):**
- `health-check.sh` по cron — проверка live-статуса всех компонентов
- `journalctl -u llm-gateway --since "24 hours ago" | jq` — аномалии за сутки

**Еженедельно (вручную, 15 минут):**
- `benchmark.py` — запуск baseline тестов, сравнение с предыдущей неделей
- Проверка: не деградировали ли модели после Ollama update
- Review tool_call success rate

**При обновлении (модели, Ollama, Continue, gateway):**
- Full benchmark ПЕРЕД обновлением (зафиксировать baseline)
- Full benchmark ПОСЛЕ обновления
- Diff: если деградация > 20% по любой метрике — rollback

### 4.3. Как реагировать на деградацию

| Симптом | Вероятная причина | Действие |
|---------|-------------------|----------|
| TTFT вырос в 3+ раза | Модель выгружена (cold start) | Проверить OLLAMA_MAX_LOADED_MODELS, перезагрузить модель |
| OOM 503 | Модель не помещается в VRAM+RAM | Уменьшить num_ctx или переключить на меньшую модель |
| Tool calls не работают | Модель путается с tools | Уменьшить количество MCP tools в agent session |
| Autocomplete тормозит | Конкуренция с chat-моделью за Ollama | Подождать завершения chat-запроса (NUM_PARALLEL=1) |
| Embeddings медленные | qwen3-embedding грузится/выгружается | Рассмотреть возврат на transformers.js |

---

## 5. Матрица зрелости

| Аспект | Минимум (MVP) | Целевой уровень | Уровень «лучше Kilo» |
|--------|--------------|-----------------|----------------------|
| **Agent runtime** | Continue.dev Chat + Edit + Agent (✅) | + MCP tools (Git ✅, Terminal ✅) | + RAG ✅ + Docker + Custom tools |
| **MCP tools** | 1 (Git ✅) | 3 (Git ✅ + Terminal ✅ + RAG ✅) | 4+ (+ Docker) |
| **Model routing** | Ручной выбор в UI (✅) | Формализованные profiles (✅ ADR-012, Tier 1/2/3) | Автоматический routing по задаче (gateway-level) |
| **Orchestration** | Нет | Sequential pipeline PoC (✅ orchestrator.py v1.1.0, 6 pipelines) | `/v1/orchestrate` в gateway.py (этап 16) |
| **Headless / CLI** | gateway.py API для curl (✅) | Готовые скрипты + git hooks (✅ 8D) | CI/CD интеграция + scheduled batch jobs |
| **Knowledge layer** | Rules 3 уровня (✅) | + RAG по docs (✅ 11) + ADR (13) + security rules (14) | + auto-context + onboarding пакет |
| **Embeddings** | qwen3-embedding через шлюз (✅ 9B) | + RAG pipeline с vector store (✅ 11, ChromaDB) | + Text-to-SQL semantic layer (F-next) |
| **NL-to-SQL** | Text-to-SQL PoC: SA 75–90% (✅ 11A) | + Semantic layer (Vanna / retrieval) + schema grounding | + Production pipeline + multi-DB + guardrails |
| **Observability** | Structured JSON logs + /metrics (✅ 10A+10B) | + Benchmark matrix + health-check (✅ 15) | + Persistent history + alerting + benchmark CI (14) |
| **Security** | Опциональный Bearer + UFW Active (✅) | Обязательный Bearer + UFW hardening + denylist (14) | Per-user auth + audit trail + RBAC |
| **Onboarding** | Паспорт лаборатории (✅ v23) | README + setup-check скрипт (13) | Полный onboarding пакет < 30 мин |
| **Automation** | Health check скрипт (✅ 15) | + Nightly cron + canary upgrade (14) | Benchmark CI + auto-rollback |
| **Локальность** | 100% локальный inference + tools (✅) | 100% + RAG по собственным docs (✅ 11) | + воспроизводимый airgapped deploy |
| **Enterprise-переносимость** | Документация (✅ паспорт + архитектура) | Все паттерны работают на 1 GPU (✅ baseline 15) | Все паттерны документированы + /v1/orchestrate API (16) |

---

## 6. Открытые вопросы и гипотезы

| # | Вопрос | Статус | Влияние | Когда закрыть |
|---|--------|--------|---------|---------------|
| 1 | Совместимость MCP STDIO на Windows с Python-серверами | [F] Закрыт в 8A — uvx работает | — | ✅ 8A |
| 2 | Количество MCP tools, при котором qwen3-coder:30b начинает путаться | [F] 26+ tools работают стабильно (12 MCP + 14 built-in) | — | ✅ 8A |
| 3 | Качество qwen3-embedding vs all-MiniLM-L6-v2 для code search | [A] Transport подтверждён, symbol lookup частичный. @Codebase provider deprecated — не подходит для валидации. RAG MCP (11) работает с qwen3-embedding удовлетворительно. | Низкое | Отложен: изолированный A/B при необходимости |
| 4 | GPU-конкуренция при embedding + chat + autocomplete (3 модели) | [F] Закрыт в 9B — embedding занимает слот 2 только при индексации, FIM (слот 1) не деградирует. Chat требует холодный старт после индексации — приемлемо. | — | ✅ 9B |
| 5 | Качество передачи контекста между шагами orchestrator pipeline | [F] Закрыт в 8C — qwen3:30b→qwen3-coder:30b→deepseek-r1:32b pipeline подтверждён. Время 53–88 сек. | — | ✅ 8C |
| 6 | qwen3.5:35b как Planner (без tools, только текстовый output) | [F] Закрыт в 8C — нестабилен (500, llama runner terminated). Заменён на qwen3:30b. | — | ✅ 8C |
| 7 | Оптимальный размер diff для headless auto-review | [F] Закрыт в 8D — MAX_LINES=400 установлен как защита от превышения num_ctx. | — | ✅ 8D |
| 8 | Continue CLI — состояние и пригодность для headless automation | [U] | Низкое сейчас (есть curl/SDK path), высокое для будущего | Мониторинг |
| 9 | Ollama roadmap: NUM_PARALLEL > 1 на одном GPU | [U] | Высокое для multi-user и параллельного orchestrator | Мониторинг |
| 10 | Момент перехода gateway.py из монолита в пакет модулей | [F] Закрыт в 10A — gateway v0.9.0 модуляризирован в пакет из 9 модулей (ADR-008) | — | ✅ 10A |
| 11 | ChromaDB embedded vs Qdrant для RAG | [F] Закрыт в 11 — ChromaDB 1.5.5 подтверждён для PoC (133 файлов / 286 chunks). Qdrant при масштабировании > 100K docs | — | ✅ 11 |
| 12 | GPU scheduler / очередь задач для multi-user | [U] | Высокое при 5+ пользователях — OOM и деградация | Этап 14 |
| 13 | Точность Text-to-SQL на кириллических схемах (названия полей/таблиц на русском) | [F] Закрыт в 11A — колонки латиница, данные кириллица: работает. SA 65–90% в зависимости от модели и prompt. | — | ✅ 11A |
| 14 | Оптимальная стратегия chunking для технической документации на русском языке | [A] Текущий ~500 токенов работает для 133 файлов. Оптимизация при масштабировании RAG | Среднее — влияет на RAG качество | При масштабировании |
| 15 | Prompt injection: покрывает ли текущий allowlist в gateway.py RAG-сценарии | [U] | Высокое — безопасность | Этап 14 |
| 16 | Семантический слой: достаточен ли Vanna для корпоративных схем ONDO или нужен dbt | [U] | Высокое для enterprise-переносимости | Track F: Semantic Layer |
| 17 | gemma4:31b tool selection stability без policy layer при 10+ tools | [A] При 5 tools стабилен с thin policy. При 10+ unknown. | Среднее — влияет на Continue Agent | End-to-end тест |
| 18 | gemma4:26b MoE + GGML_CUDA_NO_GRAPHS=1 — performance implications | [A] Benchmark 15 показал: gemma4:26b работает стабильно с GGML_CUDA_NO_GRAPHS=1. Формальное сравнение on/off не проведено | Низкое | Отложен |
| 19 | tok/s formal benchmark: gemma4:26b vs gemma4:31b vs qwen3-coder:30b | [A] Baseline snapshot в 15 содержит данные по всем трём моделям. Формальный протокол сравнения не оформлен | Среднее — влияет на pipeline timing | При оптимизации pipeline (16) |
| 20 | gemma4:31b как unified Planner+Reviewer в pipeline (экономия на cold start) | [A] Возможно, но не тестировалось с реальными pipeline | Высокое — может сократить pipeline время вдвое | Этап 16 |
| 21 | deepseek-coder-v2:16b → удаление: все зависимости покрыты Gemma 4? | [F] Подтверждено в 10C. Запланировано к удалению в этапе 14 | — | Этап 14 |
| 22 | Semantic layer (Vanna / few-shot retrieval) для >90% SA в NL-to-SQL | [U] | Высокое — следующий слой после PoC | Track F: Semantic Layer |
| 23 | Prompt bleed mitigation: retrieval-based vs monolithic prompt для NL-to-SQL | [A] Monolithic prompt bleed подтверждён в 11A (Грабли #36) | Среднее | Track F: Semantic Layer |
| 24 | Evaluator policy как отдельный компонент: unit-тестируемый, версионируемый | [A] Подтверждено в 11A: strict vs business-aware evaluator = 2–3x разница в SA (ADR-013) | Среднее | Стандартизация в будущих PoC |
| 25 | Gemma 4 long-context (65K+) stall — upstream bug llama.cpp SWA | [F] Blocked/External. Подтверждено в 15: hardware-agnostic (RTX 5090, DGX Spark, M1 Max, ROCm). llama.cpp #21379, Ollama #15237 | Высокое — блокирует 128K use cases | Мониторинг: Ollama 0.20.1+ |
| 26 | Ollama canary upgrade procedure — формализация smoke suite | [A] benchmark.py 7/7 может служить основой. Нужна SOP: before → upgrade → after → compare → rollback criteria | Среднее — защита от regression | Этап 14 |
| 27 | Persistent metrics / benchmark history trending | [U] /metrics in-memory (сбрасываются при рестарте). Нет исторического trending | Среднее — деградация заметна поздно | Этап 14 |

---

## 7. Governance и актуальность

### 7.1. Роль и границы документа

Данная целевая архитектура определяет **требования и ограничения** для всех реализаций платформы. Она не описывает конкретный инвентарь (версии, IP-адреса, пути к файлам) — это задача паспортов стендов. Целевая архитектура фиксирует принципы, статусы компонентов, политики и roadmap.

### 7.2. Политика актуальности

**Цикл пересмотра:** Целевая архитектура пересматривается раз в **6 месяцев** (плановая ревизия) и внепланово при любом из следующих событий:
- Завершение мажорного этапа (8A, 8C, 9A, 10A, 11, 14, 16 и т.д.);
- Принципиальное изменение стека (смена agent runtime, замена модельной линейки, появление нового GPU);
- Обнаружение расхождения между архитектурным решением и реальным поведением системы.

**Версионирование:**
- Мажорная версия (1.x → 2.x): смена стратегии, замена ключевых слоёв.
- Минорная версия (1.2 → 1.3): добавление компонентов, уточнение решений, закрытие вопросов из секции 6.

**Каскад на паспорта стендов:** Любое изменение целевой архитектуры, влияющее на конкретный стенд, требует выпуска новой версии паспорта не позднее чем через 2 недели после публикации новой версии архитектуры.

### 7.3. Управление расхождениями

Расхождение между фактическим паспортом стенда и данной целевой архитектурой разрешается одним из двух способов:

1. **Устранение через изменение стенда** — для расхождений, которые являются техническим долгом (не реализованы Planned-компоненты, используется Legacy без оснований).
2. **Оформление как архитектурный исключение** — для обоснованных отклонений с явным описанием причины и горизонтом устранения. Оформляется как ADR или явная пометка в паспорте стенда.

### 7.4. Политика по новым схемам квантизации и компрессии KV-кэша

**KV-кэш** (Key-Value cache — кэш пар ключ-значение) — структура данных, в которой хранятся промежуточные вычисления трансформера для ускорения генерации. **Квантизация** — сжатие весов и активаций до меньшей разрядности (например, q8_0, q4_0) для экономии памяти.

Лаборатория применяет **только те схемы квантизации и компрессии KV-кэша**, которые официально поддержаны в используемых движках (Ollama, llama.cpp, vLLM). Исследовательские алгоритмы (например, TurboQuant и аналоги) допускаются исключительно как PoC на отдельном экспериментальном стенде — без влияния на продуктивные сценарии и до официальной поддержки в основных инструментах. Переход на новую схему квантизации в основном контуре требует: (1) наличия официальной поддержки в используемой версии движка, (2) A/B-сравнения по качеству и скорости, (3) записи результата в ADR.

---

## 8. Журнал ревью

| Дата | Источник | Что изменилось |
|------|----------|----------------|
| 2026-03-20 | Perplexity AI (внешнее ревью) | Добавлены: модуляризация gateway (пакет вместо монолита), ChromaDB как vector DB для RAG PoC, orchestrator preload/warmup. Расширены: risk assessment для GPU thrashing, security scope для enterprise |
| 2026-03-27 | Ревизия по запросу владельца | v1.3: добавлены роль документа как source of truth, раздел 1.3 (статусы компонентов), раздел 7 (Governance и актуальность), политика по квантизации KV-кэша; обновлён статус этапа 8A (✅), закрыты вопросы 1–2 в секции 6 |
| 2026-03-27 | Perplexity AI + синхронизация | v1.4: закрыт этап 8B — Terminal Policy Framework Active; статус Terminal MCP обновлён с Planned на Active; Terminal Policy row добавлена в Security/Governance; секция 3 «Этап 8B» переведена из плана в результат; трек A обновлён (8B✅) |
| 2026-03-28 | Синхронизация по 9A | v1.5: gateway.py v0.8.0 /v1/embeddings Active. Этапы 8C, 8D подтверждены в таблице статусов. Orchestration layer обновлён. |
| **2026-03-29** | **Синхронизация по 9B + AI-as-Interface Playbook** | **v1.6: Этапы 8C–9B → ✅ Завершены (все 6). Continue.dev 1.2.17 → 1.2.22. Embeddings: transformers.js → Legacy, qwen3-embedding → Active. Context providers: 11 → 12. Добавлен Этап 11A (Text-to-SQL PoC) и Трек F (AI-as-Interface). Открытые вопросы: 3–7 закрыты, 13–16 добавлены. Матрица зрелости обновлена (Embeddings baseline). 10A расширен: + модуляризация gateway.** |
| **2026-04-03** | **Этапы 10A–10C: Observability + Gemma 4** | **v1.7: Ollama 0.18.0 → 0.20.0. Gateway v0.8.0 → v0.10.0 (structured logging 10A + /metrics 10B). 13 → 16 моделей: + gemma4:31b, gemma4:26b, gemma4:e4b. Раскладка ролей радикально обновлена (ADR-012): Gemma 4 → Tier 1 (Quality-first Agent/Planner/Reviewer + Fast Semantic Agent). qwen3-coder:30b → Stable Generic Executor / Backup Agent. deepseek-coder-v2:16b → Deprecated. qwen3.5:9b tool calling восстановлен. Observability baseline закрыт (health + logs + metrics). Открытые вопросы 17–21 добавлены. Матрица зрелости обновлена.** |
| **2026-04-04** | **Этап 11A: Text-to-SQL PoC (Track F)** | **v1.8: NL→SQL PoC доказан (SA 75–90%, 3 модели, 20 вопросов). qwen3-coder:30b → + Best SQL Executor role (ADR-012 дополнен). ADR-013: evaluator separation + prompt freeze. Открытый вопрос #13 закрыт. Открытые вопросы #22–24 добавлены. Матрица зрелости: + NL-to-SQL row. Этапы 10A, 10B обновлены в навигации (✅). Трек F обновлён (11A✅).** |
| **2026-04-06** | **Этапы 11, 15 + архитектурное ревью + roadmap reprioritization** | **v1.9: Этапы 11 (RAG MCP) и 15 (Benchmark Matrix) → ✅ Завершены. RAG MCP Active (FastMCP, streamable-http:8100, ChromaDB 1.5.5, ADR-014). Benchmark 11/11 health + 7/7 scenarios + baseline snapshot. Gemma 4 long-context (65K+) Blocked/External — upstream llama.cpp SWA bug (#21379). Gateway fixes: MAX_NUM_CTX→131072, HTTPX_TIMEOUT→3600s. @Codebase provider → Deprecated (удаление в 14). deepseek-coder-v2:16b → Deprecated (удаление в 14). Этап 14 расширен: + UFW hardening + canary upgrade + persistent history + @Codebase cleanup + datetime fix. Roadmap reprioritization: 14→16→13→12→F-next (обоснование: security перед blast radius, /v1/orchestrate как enterprise-transferable API). Track F: Semantic Layer формализован. 10C/10D добавлены в навигацию. Открытые вопросы: #10, #11, #21 закрыты; #25–27 добавлены. Матрица зрелости полностью пересмотрена.** |
| **2026-04-06** | **Hotfix v1.9: pipeline table + RAG reindex + exact-read tools** | **Таблица pipeline исправлена: «актуальные» → «фактическое состояние pipelines.yaml» (реальные модели: qwen3:30b, deepseek-r1:32b). Gemma 4 pipeline — целевое, миграция в этапе 16. RAG corpus обновлён (133 файлов / 297 chunks). RAG MCP server: +2 exact-read tools (get_doc_section, grep_doc) → 5 tools total. Micro-cleanup закрыт: provider:codebase удалён, deepseek-coder-v2:16b удалена (15 моделей), utcnow() fix. Известный drift: паспорт v23 header → v1.8 (fix при v24), model count 16 vs фактические 15 (fix при v24).** |

---

## 9. Глоссарий

| Термин | Расшифровка |
|--------|-------------|
| ADR | Architecture Decision Record — документ, фиксирующий архитектурное решение с контекстом и обоснованием |
| ChromaDB | Встраиваемая (embedded) векторная база данных на Python, использует SQLite для хранения |
| FIM | Fill-In-the-Middle — формат промпта для autocomplete: prefix + suffix → middle |
| Gemma 4 | Семейство open-weight моделей Google DeepMind (Apache 2.0), включает E2B, E4B, 26B MoE и 31B Dense варианты |
| MoE | Mixture of Experts — архитектура, где на каждый токен активируется только часть параметров (например, 3.8B из 26B) |
| PLE | Per-Layer Embeddings — техника Gemma 4 E-моделей: дополнительная embedding-таблица подаётся в каждый decoder-слой |
| FastMCP | Python-библиотека для быстрого создания MCP-серверов |
| KV cache | Key-Value cache — кэш ключ-значение; хранит промежуточные вычисления трансформера для ускорения генерации |
| MCP | Model Context Protocol — открытый стандарт Anthropic для подключения AI к внешним инструментам |
| OOM | Out of Memory — ошибка нехватки памяти |
| PoC | Proof of Concept — проверка концепции; прототип для валидации подхода |
| Qdrant | Продуктовая векторная база данных с REST API, для масштабных RAG-сценариев |
| RBAC | Role-Based Access Control — управление доступом на основе ролей |
| RAG | Retrieval-Augmented Generation — генерация с подгрузкой релевантных документов |
| SSE | Server-Sent Events — однонаправленный серверный стриминг через HTTP |
| STDIO | Standard Input/Output — межпроцессное взаимодействие через stdin/stdout |
| TTFT | Time To First Token — задержка до первого токена ответа |
| UFW | Uncomplicated Firewall — межсетевой экран Ubuntu |
| Vanna AI | Python-библиотека для RAG-улучшенной генерации SQL, интегрируется с Ollama |
| VRAM thrashing | Частая выгрузка/загрузка моделей в видеопамять (Video RAM), вызывающая деградацию производительности |
| NL-to-SQL | Natural Language to SQL — паттерн преобразования запроса на естественном языке в SQL-запрос к базе данных |
| Prompt bleed | Побочный эффект при добавлении или изменении правил в system prompt: правка для одного кейса ломает поведение на других кейсах |
| SA | Semantic Accuracy — доля вопросов, на которые модель сгенерировала SQL, возвращающий семантически правильный результат |
| EA | Execution Accuracy — доля вопросов, на которые модель сгенерировала синтаксически корректный (исполняемый) SQL |
| SOP | Standard Operating Procedure — стандартная операционная процедура, формализованный пошаговый регламент |
| SWA | Sliding Window Attention — механизм внимания с скользящим окном, используемый в Gemma 4 для работы с длинными контекстами |
