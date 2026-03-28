# Целевая архитектура: Локальная AI Coding Platform

**Версия:** 1.5  
**Дата:** 2026-03-28  
**Базовый стек:** Ubuntu 22.04 / RTX 3090 / Ollama 0.18.0 / gateway.py v0.8.0 / Continue.dev v1.2.17  
**Стратегия:** Continue-first platform, Depth over Speed, локальность как принцип  
**Назначение:** Лаборатория для наработки решений → перенос на Enterprise

> **Роль документа.** Данный файл является **source of truth** (единым источником правды) для целевой архитектуры AI Coding Platform. Он задаёт принципы, политики и ожидаемое состояние для всех реализаций платформы, включая конкретные лабораторные стенды. Документ `Паспорт_лаборатории_vX` фиксирует фактическое состояние конкретного стенда и должен согласовываться с данной целевой архитектурой. Любое расхождение между паспортом и целевой архитектурой классифицируется как технический долг и оформляется явно.

---

## 1. Целевая архитектура

### 1.1. Обзор

Платформа трансформирует текущую лабораторию (набор работающих компонентов) в управляемую инженерную систему с семью слоями. Каждый слой имеет чёткую ответственность, определённые интерфейсы и может развиваться независимо.

Ключевой принцип: **не заменять, а достраивать**. Всё, что подтверждено тестами в этапах 1–8A, остаётся. Новые компоненты добавляются поверх существующего фундамента.

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
│     Git, Terminal, Docker, RAG/Docs — STDIO transport               │
├─────────────────────────────────────────────────────────────────────┤
│  2. IDE AGENT LAYER                                                 │
│     Continue.dev (primary) — Chat, Edit, Agent, Apply, Autocomplete │
│     Copilot BYOK (secondary) — plain chat only                      │
├─────────────────────────────────────────────────────────────────────┤
│  1. INFERENCE / BACKEND                                             │
│     Ollama 0.18.0 → gateway.py → /v1/chat/completions              │
│     + /v1/embeddings + /v1/orchestrate + /v1/metrics (новые)        │
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
| 1. Inference/Backend | Ollama 0.18.0 + systemd | **Active** | 1–7B |
| 1. Inference/Backend | gateway.py v0.7.0 (/chat/completions, /models, /health) | **Active** | 1–7A |
| 1. Inference/Backend | gateway.py v0.8.0 /v1/embeddings (qwen3-embedding, batch, allowlist) | **Active** | 9A ✅ |
| 1. Inference/Backend | gateway.py /v1/metrics | **Planned** | 10B |
| 1. Inference/Backend | gateway.py /v1/orchestrate | **Planned** | 16 |
| 1. Inference/Backend | Модуляризация gateway.py в Python-пакет | **Planned** | 10A |
| 2. IDE Agent Layer | Continue.dev v1.2.17 (Chat, Edit, Agent, Apply, Autocomplete) | **Active** | 7A–7C |
| 2. IDE Agent Layer | Copilot BYOK (plain chat) | **Active** | 7D |
| 2. IDE Agent Layer | Copilot BYOK (Agent mode с локальными моделями) | **Legacy** | Нестабилен, не развивать |
| 3. MCP Tool Layer | mcp-server-git (MCP — Model Context Protocol, Git-инструменты) | **Active** | 8A |
| 3. MCP Tool Layer | Terminal Policy (rules-based, Continue Agent на Windows) | **Active** | 8B ✅ |
| 3. MCP Tool Layer | Custom RAG MCP (RAG — Retrieval-Augmented Generation, поиск по документам) | **Planned** | 11 |
| 3. MCP Tool Layer | Docker MCP | **Planned** | 12 |
| 4. Orchestration | orchestrator.py PoC (sequential pipeline) | **Planned** | 8C |
| 4. Orchestration | Headless scripts + git hooks | **Planned** | 8D |
| 4. Orchestration | gateway.py /v1/orchestrate (формализация) | **Planned** | 16 |
| 5. Knowledge/Context | Rules: 3 уровня (глобальный / проектный / файловый) | **Active** | 7C |
| 5. Knowledge/Context | Context providers: 11 штук (code, repo-map и др.) | **Active** | 7C |
| 5. Knowledge/Context | Embeddings: transformers.js all-MiniLM-L6-v2 | **Active** | 7C |
| 5. Knowledge/Context | Embeddings: qwen3-embedding через шлюз | **Planned** | 9B |
| 5. Knowledge/Context | ADR (Architecture Decision Records — документы архитектурных решений) | **Planned** | 13 |
| 5. Knowledge/Context | Onboarding пакет + setup-check скрипт | **Planned** | 13 |
| 6. Security/Governance | Bearer token auth (опциональный) | **Active** | 5 |
| 6. Security/Governance | Обязательный Bearer + UFW (Uncomplicated Firewall — межсетевой экран Ubuntu) | **Planned** | 14 |
| 6. Security/Governance | Per-user auth + audit trail | **Planned** | 14 |
| 6. Security/Governance | Terminal Policy rules (PowerShell behavior, self-contained, no temp files) | **Active** | 8B ✅ |
| 7. Observability | journalctl текстовые логи | **Active** | 1 |
| 7. Observability | Structured JSON logging | **Planned** | 10A |
| 7. Observability | /metrics endpoint (Prometheus-совместимый или JSON) | **Planned** | 10B |
| 7. Observability | Benchmark matrix + health-check.sh | **Planned** | 15 |

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
  │     ├─2─ Step 1: Planner (qwen3.5:35b) → декомпозиция задачи
  │     │     холодный старт ~20 сек, генерация ~30-60 сек
  │     ├─3─ Step 2: Executor (qwen3-coder:30b) → код/правки
  │     │     холодный старт ~15 сек, генерация ~30-120 сек
  │     └─4─ Step 3: Reviewer (deepseek-r1:32b) → проверка
  │           холодный старт ~20 сек, генерация ~30-60 сек
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
- Ollama 0.18.0, systemd, override.conf — всё работает стабильно
- gateway.py v0.7.0 — стриминг, reasoning policy, tool_calls проброс, auth
- 13 моделей, раскладка по ролям
- OLLAMA_MAX_LOADED_MODELS=2, NUM_PARALLEL=1, Flash Attention, KV (Key-Value) cache q8_0

**Что дорабатывается:**

| Компонент | Изменение | Обоснование |
|-----------|-----------|-------------|
| gateway.py → v0.8.0 | Добавить `/v1/embeddings` endpoint | Проброс embedding-запросов для будущего RAG и перехода с transformers.js на qwen3-embedding |
| gateway.py → v0.9.0 | Structured JSON logging | Машиночитаемые логи для observability: timestamp, model, tokens, latency, tool_calls count |
| gateway.py → v0.10.0 | `/metrics` endpoint | Prometheus-совместимые метрики или JSON-счётчики для мониторинга |
| gateway.py → v0.11.0 | `/v1/orchestrate` endpoint | Sequential multi-model pipeline (Planner→Executor→Reviewer). Формализация паттерна после PoC на скрипте |

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

**Решение по маршрутизации моделей (F — уже реализовано, формализуется):**

| Роль | Модель | Путь | num_ctx | reasoning_effort |
|------|--------|------|---------|-----------------|
| Chat (повседневный) | qwen3.5:9b | шлюз | 8192 | none |
| Chat (reasoning) | deepseek-r1:32b | шлюз | 8192 | medium |
| Edit / Refactor | qwen3-coder:30b | шлюз | 8192 | none |
| Agent (tools) — основная | qwen3-coder:30b | шлюз | 8192 | none |
| Agent (tools) — альтернативная | glm-4.7-flash | шлюз | 8192 | none |
| Vision | qwen3-vl:8b | шлюз | 8192 | none |
| Experimental reasoning | qwen3.5:35b | шлюз | 8192 | none |
| Autocomplete (FIM — Fill-In-the-Middle) | qwen2.5-coder:7b | Ollama напрямую | 2048 | — |
| Embeddings (текущие) | all-MiniLM-L6-v2 | transformers.js в VS Code | — | — |
| Embeddings (целевые) | qwen3-embedding | шлюз /v1/embeddings | — | — |

### 2.2. Слой 2 — IDE Agent Layer

**Что остаётся (F):**
- Continue.dev v1.2.17 — основной agent runtime
- config.yaml: 8 моделей, 11 context providers, 6 prompts
- Copilot BYOK — дополнительный plain chat

**Что дорабатывается:**

| Компонент | Изменение | Обоснование |
|-----------|-----------|-------------|
| config.yaml | Добавить секцию `mcpServers:` | Подключение MCP tools для Agent mode |
| config.yaml | Формализовать model profiles в комментариях | Документирование ролей для onboarding |
| Copilot BYOK | Зафиксировать как «compatibility check only» | Agent mode нестабилен — не тратить усилия |

**Что убирается:** Ничего. Copilot BYOK остаётся, но с пониженным статусом.

**Решение по Agent runtime (F):** Continue.dev — единственный основной agent runtime. Причины: подтверждён для Chat, Edit, Agent, Apply, Context, Rules, Prompts; полностью локальный; поддерживает MCP; Copilot Agent mode с локальными моделями нестабилен и неисправим на стороне шлюза.

### 2.3. Слой 3 — MCP Tool Layer

**Архитектурное решение по транспорту:** STDIO (Standard Input/Output — межпроцессное взаимодействие) по умолчанию для всех локальных инструментов. SSE (Server-Sent Events — однонаправленный серверный стриминг) / streamable-http — только если инструмент работает на удалённом хосте.

**Критическая архитектурная заметка:** Continue.dev запущен на Windows-клиенте. MCP-серверы, запущенные через STDIO, будут выполняться тоже на Windows. Git MCP работает с локальными репозиториями на Windows. Terminal MCP выполняет команды на Windows. Docker MCP и RAG MCP требуют либо DOCKER_HOST/SSH-туннеля, либо SSE-сервера на Ubuntu.

**Целевой набор MCP-серверов:**

| # | MCP Server | Транспорт | Среда выполнения | Статус | Приоритет |
|---|-----------|-----------|-----------------|--------|-----------|
| 1 | **mcp-server-git** (Anthropic, Python) | STDIO | Windows (uvx) | **Active** | Этап 8A ✅ |
| 2 | **Terminal Policy** (rules-based, 01-general.md) | — (нативный VS Code terminal) | Windows (VS Code) | **Active** | Этап 8B ✅ |
| 3 | **Custom RAG MCP** (Python, FastMCP) | STDIO или SSE | Сервер (Ubuntu) | **Planned** | Этап 11 |
| 4 | **Docker MCP** (custom или docker/hub-mcp) | SSE (streamable-http) | Сервер (Ubuntu) | **Planned** | Этап 12 |

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
- Context providers: 11 штук, включая @Code и @Repository Map
- Embeddings: transformers.js (all-MiniLM-L6-v2)
- Prompts: 6 slash-команд

**Что дорабатывается:**

| Компонент | Изменение | Обоснование |
|-----------|-----------|-------------|
| Глобальные rules | Добавить `03-security.md` | Правила по обращению с секретами, .env, credentials |
| Проектные rules | Шаблон `01-project.md` с обязательными секциями | Стандартизация для onboarding |
| docs: в config.yaml | Добавить корпоративные docs для @Docs context | Индексация внутренней документации |
| ADR | Шаблон `.continue/docs/adr/` в workspace | Фиксация архитектурных решений для AI-контекста |
| Embeddings | Миграция transformers.js → qwen3-embedding через шлюз | Более качественные embeddings, поддержка русского языка |

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
| **Sequential Orchestrator** | Multi-model pipeline: Planner → Executor → Reviewer | Сначала Python-скрипт (PoC), затем `/v1/orchestrate` в gateway.py | **Planned** |
| **Headless Scripts** | Автоматические задачи без IDE: code review, doc generation, commit messages | Bash/Python скрипты через curl/OpenAI SDK | **Planned** |
| **CI/CD Hooks** | Интеграция с git hooks и CI pipeline | git pre-push → auto-review, post-merge → auto-docs | **Planned** |

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

**Типовые pipeline (целевые):**

| Pipeline | Шаги | Модели | Типичное время (RTX 3090) | Use case |
|----------|-------|--------|---------------------------|----------|
| `plan-execute-review` | 3 | qwen3.5:35b → qwen3-coder:30b → deepseek-r1:32b | 3–8 мин | Сложные задачи: новая фича, рефакторинг модуля |
| `execute-review` | 2 | qwen3-coder:30b → deepseek-r1:32b | 2–5 мин | Стандартные задачи: реализация по спецификации |
| `review-only` | 1 | deepseek-r1:32b | 1–3 мин | Code review (headless, CI/CD) |
| `docs-generate` | 1 | qwen3-coder:30b | 1–2 мин | Генерация документации (headless) |

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
| **8C** | **Orchestrator PoC (sequential multi-model pipeline)** | **—** | **⬜ Planned** | **1–2 спринта** |
| **8D** | **Headless Automation PoC (скрипты + git hooks)** | **8C** | **⬜ Planned** | **1 спринт** |
| 9A | gateway.py v0.8.0: /v1/embeddings | — | ⬜ Planned | 1 спринт |
| 9B | Embeddings миграция: transformers.js → qwen3-embedding | 9A | ⬜ Planned | 1 спринт |
| 10A | gateway.py v0.9.0: Structured Logging | — | ⬜ Planned | 1 спринт |
| 10B | gateway.py v0.10.0: Metrics Endpoint | 10A | ⬜ Planned | 1 спринт |
| 11 | MCP: RAG / Docs Search | 9B | ⬜ Planned | 2 спринта |
| 12 | MCP: Docker | — | ⬜ Planned | 1 спринт |
| 13 | Knowledge Layer: Rules + ADR + Onboarding | 8A | ⬜ Planned | 1–2 спринта |
| 14 | Security Hardening + Multi-user Auth | 10A | ⬜ Planned | 1 спринт |
| 15 | Benchmark Matrix + Health Automation | 10B | ⬜ Planned | 1 спринт |
| **16** | **gateway.py v0.11.0: /v1/orchestrate (формализация)** | **8C, 10A** | **⬜ Planned** | **2 спринта** |

```
Параллельные треки:

Трек A (MCP Tools):          8A✅→ 8B✅ ─────────────────────→ 11 → 12
Трек B (Backend):            9A → 9B    10A → 10B
Трек C (Knowledge):          ──────────────────→ 13
Трек D (Ops/Security):       ────────────────────────→ 14 → 15
Трек E (Orchestration):      8C → 8D ────────────────────────────→ 16
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

### Этап 9A — gateway.py v0.8.0: /v1/embeddings

**Задача:** Добавить endpoint `/v1/embeddings` в шлюз для проксирования embedding-запросов к Ollama (qwen3-embedding).

**Критерий завершения:**
- [ ] `curl -X POST :8000/v1/embeddings -d '{"model":"qwen3-embedding","input":"test"}'` возвращает корректный response
- [ ] Response совместим с OpenAI embedding format
- [ ] Логи шлюза записывают embedding-запросы

---

### Этап 9B — Embeddings миграция: transformers.js → qwen3-embedding

**Задача:** Переключить Continue.dev с transformers.js на qwen3-embedding через шлюз.

**Решение (A):** Попробовать qwen3-embedding. Если GPU-конкуренция критична (выталкивает FIM-модель), откатиться на transformers.js и пометить как «отложено до NUM_PARALLEL > 1 или второй GPU».

**Критерий завершения:**
- [ ] Continue.dev config переключен на qwen3-embedding
- [ ] @Code поиск работает корректно
- [ ] A/B тест задокументирован

---

### Этап 10A — gateway.py v0.9.0: Structured Logging

**Задача:** Перевести логирование gateway.py с текстового формата на структурированный JSON.

**Результат:** Каждый запрос логируется как JSON-объект с полями: timestamp, request_id, model, tokens, latency_ms (TTFT/total), status_code, tool_calls_count, reasoning_effort, client_ip.

---

### Этап 10B — gateway.py v0.10.0: Metrics Endpoint

**Задача:** Добавить `/metrics` endpoint для внешнего мониторинга.

**Критерий завершения:**
- [ ] `curl :8000/metrics` возвращает JSON с актуальными счётчиками
- [ ] Счётчики инкрементируются при каждом запросе

---

### Этап 11 — MCP: RAG / Docs Search

**Задача:** Создать MCP-сервер для поиска по документации с использованием embeddings.

**Решение по vector DB (A — принято по результатам ревью):**

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

**Вариант реализации:** Custom MCP server на сервере (Python, FastMCP, streamable-http) → SSE из Continue. Предпочтительнее STDIO: не требует Docker CLI на Windows, безопаснее.

---

### Этап 13 — Knowledge Layer: Rules + ADR + Onboarding

**Задача:** Формализовать knowledge layer. Воспроизводимый онбординг за 30 минут.

**Артефакты:**
1. `03-security.md` — глобальный rule
2. ADR шаблон + первые 3 ADR
3. Onboarding README
4. `setup-check.sh` + `setup-check.ps1`

---

### Этап 14 — Security Hardening + Multi-user Auth

**Задача:** Per-user tokens, UFW, audit log.

**Критерий завершения:**
- [ ] Два разных токена → два разных user_id в логах
- [ ] Запрос без токена → 401
- [ ] `ufw status` показывает правила для LLM-портов

---

### Этап 15 — Benchmark Matrix + Health Automation

**Задача:** Регрессионное тестирование и автоматический health check за 5 минут.

**Критерий завершения:**
- [ ] `./health-check.sh` проверяет все компоненты и выдаёт pass/fail
- [ ] Benchmark matrix покрывает: chat, reasoning, agent+tool, autocomplete, embeddings, orchestrator pipeline
- [ ] Baseline зафиксирован для текущей конфигурации

---

### Этап 16 — gateway.py v0.11.0: /v1/orchestrate (Формализация)

**Задача:** Перенести отлаженный orchestrator паттерн из скрипта (этап 8C) в gateway.py как формальный endpoint.

**Зависимости:** Этап 8C (PoC валидирует паттерн), Этап 10A (structured logging для трейсинга шагов).

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
| **Agent runtime** | Continue.dev Chat + Edit + Agent (✅ уже) | + MCP tools (Git, Terminal) | + RAG + Docker + Custom tools |
| **MCP tools** | 1 (Git ✅ текущее) | 2 (Git + Terminal) | 4+ (Git, Terminal, RAG, Docker) |
| **Model routing** | Ручной выбор в UI (✅ уже) | Формализованные profiles в docs | Автоматический routing по задаче (gateway-level) |
| **Orchestration** | Нет (✅ текущее) | Sequential pipeline PoC (orchestrator.py) | `/v1/orchestrate` в gateway.py + configurable pipelines |
| **Headless / CLI** | gateway.py API доступен для curl (✅ уже) | Готовые скрипты + git hooks | CI/CD интеграция + scheduled batch jobs |
| **Knowledge layer** | Rules 3 уровня (✅ уже) | + ADR + docs + security rules | + RAG по корпоративным docs + auto-context |
| **Embeddings** | transformers.js (✅ уже) | qwen3-embedding через шлюз | + RAG pipeline с vector store |
| **Observability** | journalctl текстовые логи (✅ уже) | Structured JSON logs + /metrics | + Dashboard + alerting + benchmark CI |
| **Security** | Опциональный Bearer (✅ уже) | Обязательный Bearer + UFW + denylist | Per-user auth + audit trail + RBAC |
| **Onboarding** | Паспорт лаборатории (✅ уже) | README + setup-check скрипт | Полный onboarding пакет < 30 мин |
| **Automation** | Ручное управление (✅ уже) | Health check скрипт | Benchmark CI + auto-rollback |
| **Локальность** | 100% локальный inference (✅ уже) | 100% локальный inference + tools | 100% + воспроизводимый airgapped deploy |
| **Enterprise-переносимость** | Документация (✅ паспорт) | Все паттерны работают на 1 GPU | Все паттерны документированы для multi-GPU масштабирования |

---

## 6. Открытые вопросы и гипотезы

| # | Вопрос | Статус | Влияние | Когда закрыть |
|---|--------|--------|---------|---------------|
| 1 | Совместимость MCP STDIO на Windows с Python-серверами | [F] Закрыт в 8A — uvx работает | — | ✅ 8A |
| 2 | Количество MCP tools, при котором qwen3-coder:30b начинает путаться | [F] 26+ tools работают стабильно (12 MCP + 14 built-in) | Высокое | ✅ 8A |
| 3 | Качество qwen3-embedding vs all-MiniLM-L6-v2 для code search | [U] | Среднее — определяет embeddings стратегию | Этап 9B |
| 4 | GPU-конкуренция при embedding + chat + autocomplete (3 модели) | [A] | Высокое — при MAX_LOADED_MODELS=2 одна модель выгружается | Этап 9B |
| 5 | Качество передачи контекста между шагами orchestrator pipeline | [U] | Высокое — определяет полезность multi-model оркестрации | Этап 8C |
| 6 | qwen3.5:35b как Planner (без tools, только текстовый output) | [A] | Среднее — если не справляется, заменить на qwen3-coder:30b | Этап 8C |
| 7 | Оптимальный размер diff для headless auto-review | [U] | Среднее — слишком большой diff = потеря качества | Этап 8D |
| 8 | Continue CLI — состояние и пригодность для headless automation | [U] | Низкое сейчас (есть curl/SDK path), высокое для будущего | Мониторинг |
| 9 | Ollama roadmap: NUM_PARALLEL > 1 на одном GPU | [U] | Высокое для multi-user и параллельного orchestrator | Мониторинг |
| 10 | Момент перехода gateway.py из монолита в пакет модулей | [A] | Среднее — при >1500 строк становится неуправляемым | Этап 9A (первое расширение) |
| 11 | ChromaDB embedded vs Qdrant для RAG | [A] | Низкое сейчас — ChromaDB для PoC, Qdrant при масштабировании | Этап 11 |
| 12 | GPU scheduler / очередь задач для multi-user | [U] | Высокое при 5+ пользователях — OOM и деградация | Этап 14 |

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

---

## 9. Глоссарий

| Термин | Расшифровка |
|--------|-------------|
| ADR | Architecture Decision Record — документ, фиксирующий архитектурное решение с контекстом и обоснованием |
| ChromaDB | Встраиваемая (embedded) векторная база данных на Python, использует SQLite для хранения |
| FIM | Fill-In-the-Middle — формат промпта для autocomplete: prefix + suffix → middle |
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
| VRAM thrashing | Частая выгрузка/загрузка моделей в видеопамять (Video RAM), вызывающая деградацию производительности |
