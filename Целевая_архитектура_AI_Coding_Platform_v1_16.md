# Целевая архитектура: Локальная AI Coding Platform

**Версия:** 1.16  
**Дата:** 2026-04-15  
**Базовый стек:** Ubuntu 24.04 / RTX 3090 / Ollama 0.20.7 / gateway v0.12.0+patch / Continue.dev v1.2.22  
**Стратегия:** Continue-first platform, Depth over Speed, локальность как принцип  
**Назначение:** Лаборатория для наработки решений → перенос на Enterprise  
**Паспорт стенда:** v30.0 (2026-04-15)

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
| 1. Inference/Backend | Gemma 4: gemma4:26b (Fast Semantic Agent/Tool Selector) | **Active** | 10C ✅ |
| 1. Inference/Backend | Gemma 4: gemma4:e4b (Fast edge chat, evaluation) | **PoC** | 10C |
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
| 7. Observability | Structured JSON logging | **Active** | 10A ✅ |
| 7. Observability | /metrics endpoint | **Active** | 10B ✅ |
| 7. Observability | Benchmark matrix + health-check.sh | **Active** | 15, R ✅ |
| Track F | Text-to-SQL PoC + Semantic Layer | **Active (PoC завершён)** | 11A, F-next ✅ |

---

## 2. Архитектурные решения

### 2.1. Слой 1 — Inference / Backend

**Текущее состояние (Post-R):**
- **Ollama 0.20.7**, systemd, override.conf (7 переменных)
- gateway v0.12.0+patch (11 модулей), **DEFAULT_NUM_CTX=131072** (ADR-020)
- **11 моделей** (R: 17→12; Post-R: −1 deepseek-r1:32b)
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

**Решение по маршрутизации моделей (ADR-012, обновлено Post-R с routing refinement):**

**Tier 1 — Primary workhorses:**

| Роль | Модель | Путь | Routing policy | Этап |
|------|--------|------|----------------|------|
| Quality-first Agent / Planner / Reviewer / Best Semantic SQL / Primary Reasoner | **gemma4:31b** | шлюз | Planning, review, reasoning, semantic arbitration, long-context | 10C, F-next, ADR-019 |
| Fast Semantic Agent / Tool Selector | **gemma4:26b** (MoE) | шлюз | **Semantic executor, agent/tool scenarios, fast semantic assistance.** НЕ strict code patcher, НЕ default SQL executor. | 10C, **Post-R** |
| **Best Strict Executor** (code + SQL) / Backup Agent | qwen3-coder:30b | шлюз | **Bounded coding: refactor, bug-fix, SQL repair, strict-format output, INSUFFICIENT_SCHEMA discipline.** | 7A, 11A, **Post-R** |
| Autocomplete (FIM) | qwen2.5-coder:7b | Ollama напрямую | FIM autocomplete | 7B |
| Embeddings | qwen3-embedding | шлюз /v1/embeddings | Embedding queries | 9A |

**Tier 2 — Specialized:**

| Роль | Модель | Примечание |
|------|--------|-----------|
| Fast chat + light tools | qwen3.5:9b | Tool calling восстановлен в Ollama 0.20.0 |
| Fast edge chat (evaluation) | gemma4:e4b | PoC, частично протестирована |

**Tier 3 — Legacy / Reserve / PoC:**

| Модель | Статус | Примечание |
|--------|--------|-----------|
| qwen3.5:35b | Legacy | Tools сломаны. Кандидат на удаление (wave 2). |
| glm-4.7-flash | Reserve | **Semantic overreach на SQL** — додумывает бизнес-семантику вместо INSUFFICIENT_SCHEMA (Post-R). Кандидат на удаление (wave 2). |
| qwen3-coder-next:q4_K_M | PoC | **Не вытеснил qwen3-coder:30b** из роли stable executor (Post-R). Интересный профиль, но не baseline replacement. |
| gpt-oss:20b | PoC | Не оценивалась. |
| deepseek-r1:32b | **Удалена** (Post-R, ADR-019) | Reasoning покрыта gemma4:31b |
| qwen3-next:80b-a3b-thinking | **Удалена** (Post-R) | Тяжёлые MoE >50B нет ROI на single RTX 3090 (Грабли #72) |

**ADR-012: Gemma 4 Model Integration (10C, updated Post-R)**

Ролевое разделение: Gemma — quality-first agent/planner/reviewer + semantic executor; Qwen — stable strict executor. **Уточнение Post-R:** gemma4:26b сильнее как semantic/agent executor, но уступает qwen3-coder:30b на strict-format задачах (code patching, SQL repair, bounded output). Routing policy должна направлять strict executor задачи на qwen3-coder:30b, а semantic/tool/agent задачи — на gemma4:26b.

**ADR-018: Semantic Layer Architecture (F-next)** — без изменений.

**ADR-019: Удаление deepseek-r1:32b (Post-R)** — без изменений.

**ADR-020: Gateway Context Default Policy (Post-R)**

Root cause: DEFAULT_NUM_CTX=8192 создавал invisible bottleneck, маскировавшийся под upstream bug. Патч: 131072 в обеих точках. Валидация: 131K tokens. Принцип: defaults must match capability. Tech debt: orchestrate.py hardcoded.

### 2.2–2.7 — Слои 2–7

Без структурных изменений относительно v1.15. Ключевые обновления:
- **Слой 2:** gemma4:26b НЕ default code patcher (routing refinement)
- **Слой 4:** orchestrate.py tech debt (hardcoded 131072)
- **Слой 5:** ADR-019, ADR-020 pending RAG reindex (canonical ADR: 9→11)
- **Слой 6:** Два governance principles: retention = role-driven (ADR-019) + defaults = capability-matched (ADR-020)
- **Слой 7:** health-check.sh/setup-check.sh: pending update для Ollama 0.20.7 и models=11

---

## 3. Пошаговый план реализации

Все этапы Roadmap v1.0 завершены. Без новых запланированных этапов.

```
ВСЕ ТРЕКИ ЗАВЕРШЕНЫ. Ревизия R✅. Post-R✅ (ADR-019, ADR-020, routing refinement).
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
| **Model routing** | Ручной выбор (✅) | Формализованные profiles (✅ ADR-012) | **Role-validated routing (✅ Post-R)** |
| **Model governance** | Ручной cleanup | Role-driven retention (✅ ADR-019) | **+ Defaults governance (✅ ADR-020)** |
| **Long-context** | 8K default (✅ v0.7.0) | **131K validated (✅ ADR-020)** | Model-specific context policy |
| **Orchestration** | Sequential pipeline (✅) | /v1/orchestrate (✅ 16) | + context-aware orchestration |
| **Knowledge layer** | Rules + RAG (✅) | ADR multilayer + onboarding (✅ 13) | Knowledge drift control (✅ R) |
| **NL-to-SQL** | SA 75–90% (✅ 11A) | SA 90% semantic (✅ F-next) | Production pipeline |
| **Observability** | Structured logs + /metrics (✅) | + Benchmark + health-check (✅ 15) | + alerting (✅ 14) |
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
| 35 | Wave 2 model cleanup: gemma4:e4b, glm-4.7-flash, qwen3.5:35b, qwen3-coder-next, gpt-oss:20b | [U] | Низкое (диск) | Стратегическое решение |
| 36 | deepseek-r1:32b reasoning differentiation | [F] Закрыт — ADR-019 | — | ✅ Post-R |
| **37** | **Model-specific context policy (gemma4:31b→131K, qwen3.5:9b→32K) vs единый default** | **[U]** | **Среднее — оптимизация RAM/VRAM** | **При рефакторинге gateway** |
| **38** | **orchestrate.py hardcoded 131072 вместо import DEFAULT_NUM_CTX** | **[F] Tech debt, тактический fix** | **Низкое** | **При следующем gateway release** |

---

## 7. Governance и актуальность

### 7.1–7.5 — Без изменений от v1.15.

### 7.6. Model Retention Governance (ADR-019)

**Retention = role-driven, not label-driven.** Историческая метка не основание для retention без валидированной дифференциации.

### 7.7. Integration Layer Defaults Governance (ADR-020)

**Defaults must match platform capability.** При изменении capability ceiling (MAX) обязательно пересматривать default. Расхождение MAX vs DEFAULT = invisible bottleneck (Грабли #71).

---

## 8. Журнал ревью

| Дата | Источник | Что изменилось |
|------|----------|----------------|
| 2026-03-20 — 2026-04-10 | (см. v1.14) | Этапы 8A–R, v1.3–v1.14 |
| 2026-04-14 | Эксперимент deepseek-r1 vs gemma4 | v1.15: ADR-019, 12→11 моделей, Model Retention Governance. |
| **2026-04-15** | **Модельная валидация + gateway context fix** | **v1.16: Ollama 0.20.7. ADR-020: DEFAULT_NUM_CTX 131072, 131K validated. Routing refinement: qwen3-coder:30b = best strict executor; gemma4:26b = semantic/agent, НЕ code patcher; glm-4.7-flash semantic overreach confirmed. qwen3-next:80b removed (Грабли #72). Вопросы #25, #32 partially addressed. #37, #38 добавлены. Canonical ADR: 10→11. Governance: §7.7 Defaults governance. Грабли #71–72.** |

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
