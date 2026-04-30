# Enterprise Transfer Brief: Lab RTX3090 → ONDO Production

**Версия:** 1.0  
**Дата:** 2026-04-30  
**Контекст:** ONDO Ukraine (энергетика, производство, отели и рестораны)  
**Источник:** AI-as-Interface Lab Playbook v1.1 + результаты всех этапов

---

## 1. Что переносится: 7 паттернов

Каждый компонент лаборатории проектировался как прототип enterprise-решения. Ниже — конкретная карта переноса.

### 1.1. Inference Gateway

| Аспект | Лаборатория | Enterprise |
|---|---|---|
| Стек | Ollama + custom FastAPI gateway | vLLM / TGI + тот же gateway паттерн |
| GPU | 1× RTX 3090 (24GB) | Multi-GPU / cloud endpoint |
| Модели | Open-weight (Qwen, Gemma) | Open-weight или API (Azure OpenAI, Anthropic) |
| Auth | Per-user Bearer tokens | RBAC + OIDC integration |
| **Инвариант** | **OpenAI-compatible API contract, structured logging, per-request audit** | **Тот же** |

### 1.2. MCP Tool Layer

| Аспект | Лаборатория | Enterprise |
|---|---|---|
| Git | STDIO на Windows клиенте | SSE/streamable-http на сервере |
| RAG | ChromaDB embedded | Qdrant / Weaviate cluster |
| Docker | Local-only + SSH tunnel | Kubernetes API + RBAC |
| **Инвариант** | **MCP protocol, tool categories (read/lifecycle/exec), policy engine** | **Тот же (ADR-017)** |

### 1.3. Orchestration

| Аспект | Лаборатория | Enterprise |
|---|---|---|
| CLI | orchestrator.py (sequential) | LangGraph / Temporal workflow |
| HTTP API | /v1/orchestrate (self-call) | Dedicated orchestration service |
| Pipelines | 6 named pipelines in YAML | Dynamic pipeline registry |
| **Инвариант** | **Planner→Executor→Reviewer паттерн, self-call architecture (ADR-016)** | **Тот же** |

### 1.4. Text-to-SQL (Semantic Layer)

| Аспект | Лаборатория | Enterprise |
|---|---|---|
| DB | SQLite (ondo_demo.db) | PostgreSQL / MSSQL production |
| Knowledge | 34 карточки в ChromaDB | DDL extraction + CI validation |
| Accuracy | SA 90% (gemma4:31b) | Target SA 95%+ с fine-tune |
| **Инвариант** | **Retrieval-assisted pipeline, knowledge cards architecture (ADR-018)** | **Тот же** |

### 1.5. Security Governance

| Аспект | Лаборатория | Enterprise |
|---|---|---|
| Network | UFW least-privilege | Enterprise firewall + WAF |
| Auth | Bearer tokens (.env) | OAuth2 / SAML / OIDC |
| Audit | Structured JSON logs (journalctl) | SIEM integration |
| **Инвариант** | **Defense in depth (ADR-017), mandatory auth, per-user audit trail** | **Тот же** |

### 1.6. Model Governance

| Аспект | Лаборатория | Enterprise |
|---|---|---|
| Intake | ADR-022 + IDE validation gate | Automated model evaluation pipeline |
| Routing | Manual tier selection | Policy-based routing (model registry) |
| **Инвариант** | **9 governance principles, instruction-following as routing dimension (ADR-026)** | **Тот же** |

### 1.7. Observability

| Аспект | Лаборатория | Enterprise |
|---|---|---|
| Logging | Structured JSON → journalctl | ELK / Grafana Loki |
| Metrics | In-memory counters (/metrics) | Prometheus + Grafana |
| Health | health-check.sh (cron) | Kubernetes liveness/readiness probes |
| **Инвариант** | **Per-request structured events, model-level metrics** | **Тот же** |

---

## 2. Девять governance principles (enterprise-ready)

Выработаны эмпирически через 33 версии паспорта. Все переносимы as-is.

| # | Принцип | ADR | Enterprise применение |
|---|---|---|---|
| 1 | Retention = role-driven, not label-driven | ADR-019 | Model registry: модели без подтверждённой роли не входят в production roster |
| 2 | Defaults must match platform capability | ADR-020 | CI check: default config values vs actual capability ceiling |
| 3 | No reserve lane for failed models | v31 | Registry cleanup: failed models → cold storage, not shadow inventory |
| 4 | Benchmark contract = deployment contract | ADR-022 | Staging = production topology для model evaluation |
| 5 | Architecture class as risk predictor | ADR-023 | Risk matrix: architecture-based probability weighting |
| 6 | Role persistence across carrier changes | ADR-025 | Role catalog: roles independent of model versions |
| 7 | Freshness-aware intake | Грабли #76 | Knowledge cutoff gate в model intake pipeline |
| 8 | Instruction-following ≠ coding capability | ADR-026 | Separate probe: compliance test independent of task benchmarks |
| 9 | Vendor product architecture as behavioral signal | Грабли #77 | Due diligence: vendor product scan в procurement |

---

## 3. Пять CIO экспериментов для ONDO

### Эксперимент 1: Text-to-SQL на реальных схемах ONDO

**Статус:** ✅ Методология отработана (SA 90% на demo schema)

**Следующий шаг для ONDO:**
1. Взять реальную схему одной системы (ERP billing, hotel PMS, energy SCADA historian)
2. 20–30 вопросов с ground truth ответами
3. Прогнать через pipeline: qwen3-coder:30b (fast) + gemma4:31b (quality)
4. Замерить SA на реальных данных

**Критерий:** SA ≥ 85% = жизнеспособно для pilot. SA < 70% = нужен semantic layer + domain fine-tune.

**Особый вопрос:** кириллические имена таблиц и колонок — **не тестировалось** в лаборатории. Критично для ONDO.

### Эксперимент 2: RAG галлюцинации на внутренних документах

**Статус:** ⚠️ Инфраструктура готова, формальный тест не проведён

**Следующий шаг:**
1. Загрузить 200–500 документов ONDO (регламенты, SOP, техдокументация)
2. 30–50 вопросов с known answers
3. Классификация: correct / partial / hallucination / "don't know"
4. Target: < 5% галлюцинаций

### Эксперимент 3: Дашборд vs. нарративный отчёт

**Статус:** ❌ Не выполнен

**Pipeline (уже готов в лаборатории):**
```
Вопрос → Text-to-SQL → данные → нарративный отчёт (orchestrator pipeline)
```

**Тест:** 5–10 существующих отчётов ONDO → AI-нарратив → бизнес-пользователи сравнивают. Если предпочитают нарратив → пересмотр BI strategy.

### Эксперимент 4: Границы автономии агента

**Статус:** ⚠️ Частично выполнен (MCP Git, Docker Active)

**Матрица автономии для ONDO (заполнить по результатам):**

| Действие | Авто | С подтверждением | Запрещено |
|---|---|---|---|
| git status, git log | ✅ | | |
| git add, git commit | ✅ | | |
| git push | | ✅ | |
| Создание файла | ✅ | | |
| Изменение .env / config | | | ✅ |
| SELECT в production DB | | ✅ | |
| UPDATE/DELETE в production DB | | | ✅ |
| Отправка email | | ✅ | |
| Docker restart (non-prod) | | ✅ | |
| Docker rm/prune | | | ✅ |

**Enterprise-вывод:** этот порог — input для проектирования approval gates (Open question #46).

### Эксперимент 5: Red Team (Prompt Injection)

**Статус:** ❌ Не выполнен

**Три сценария:**
- A: Скрытая инструкция в RAG-документе → проверить извлечение как команды
- B: SQL-инъекция через Text-to-SQL → проверить DML/DDL блокировку
- C: Утечка системного промпта через Agent mode

**Обязателен до enterprise pilot.**

---

## 4. Открытый вопрос #46: Server-side approval gate

[Weak Signal] Для enterprise транспозиции нужен infrastructure-level approval gate (Слой 3 MCP Tool Layer) по аналогии с ADR-017 Docker policy. Не блокирующий для лаборатории — routing через disciplined модели (ADR-026) решает operational risk. 

**Trigger для проектирования:** начало enterprise pilot либо появление требования audit trail compliance.

**Концепция:** gateway middleware, который перехватывает tool_calls и проверяет по policy matrix перед исполнением. Архитектурно аналогичен Docker policy engine, но уровнем выше (между LLM response и tool execution).

---

## 5. Документы проекта: полный реестр

### Серверная сторона

| Компонент | Расположение |
|---|---|
| Gateway package | `~/llm-gateway/gateway/` (11 модулей) |
| Gateway entry | `~/llm-gateway/run.py` |
| Tokens | `~/llm-gateway/.env` (chmod 600) |
| Orchestrator CLI | `~/llm-gateway/orchestrator.py` v1.1.0 |
| Pipeline registry | `~/llm-gateway/pipelines.yaml` (6 pipelines) |
| Headless scripts | `~/llm-gateway/scripts/auto-*.sh` |
| Git hooks | `~/llm-gateway/.githooks/pre-push` |
| Text-to-SQL | `~/llm-gateway/scripts/text2sql_*.py` |
| SQL knowledge | `~/llm-gateway/scripts/sql_knowledge_cards.py` (34 cards) |
| SQL indexer | `~/llm-gateway/scripts/sql_indexer.py` |
| Benchmark | `~/llm-gateway/scripts/benchmark.py` (7 scenarios) |
| Health check | `~/llm-gateway/scripts/health-check.sh` (11 checks) |
| Setup check | `~/llm-gateway/scripts/setup-check.sh` (66 checks) |
| Ollama SOP | `~/llm-gateway/docs/SOP_Ollama_Upgrade.md` |
| Onboarding | `~/llm-gateway/docs/ONBOARDING.md` |
| Demo DB | `~/llm-gateway/ondo_demo.db` (SQLite) |
| RAG MCP | `~/rag-mcp-server/` |
| ADR corpus | `~/rag-mcp-server/docs/` (14 файлов; pending +6 = 20) |
| ChromaDB data | `~/rag-data/chroma/` |
| Docker MCP | `~/docker-mcp-server/` |
| Docker policy | `~/docker-mcp-server/docker-policy.yaml` |

### Клиентская сторона (Windows)

| Компонент | Расположение |
|---|---|
| Continue config | `%USERPROFILE%\.continue\config.yaml` |
| Global rules | `%USERPROFILE%\.continue\rules\01-general.md` |
| Coding rules | `%USERPROFILE%\.continue\rules\02-coding.md` |
| Security rules | `%USERPROFILE%\.continue\rules\03-security.md` |
| Project rules | `<workspace>\.continue\rules\01-project.md` |
| MCP Git | `%USERPROFILE%\.continue\mcpServers\git.yaml` |
| MCP RAG | `%USERPROFILE%\.continue\mcpServers\rag.yaml` |
| MCP Docker | `%USERPROFILE%\.continue\mcpServers\docker.yaml` |
| Client check | `%USERPROFILE%\.continue\scripts\setup-check.ps1` |
| VS Code settings | `%APPDATA%\Code\User\settings.json` |
| Config backups | `config.yaml.before_v32_*.bak`, `config.yaml.before_v33_*.bak` |

### Документация проекта (Obsidian vault convention)

| Папка | Содержимое |
|---|---|
| `Грабли/` | #01–#77 — numbered pitfalls |
| `Компоненты/` | Component descriptions |
| `Конфиги/` | Configuration snapshots |
| `Модели/` | Model evaluation records |
| `Решения/` | ADR-001–ADR-026 |
| `Этапы/` | Stage results (1–16, F-next, R) |
| `Briefings/` | Pre-stage research briefings |
| `Meta/` | Process meta-documentation |

---

## 6. Вендорский benchmark-фреймворк

При оценке любого AI-вендора для ONDO — использовать лабораторные результаты как baseline.

| Вендор заявляет | Лабораторный тест | Метрика |
|---|---|---|
| «ИИ заменит BI-аналитика» | Text-to-SQL (11A, F-next) | SA на реальных схемах ONDO |
| «RAG даёт точные ответы» | RAG hallucination test | % галлюцинаций на документах ONDO |
| «Агент автономно работает» | Agent autonomy test | Частота ошибок при снижении контроля |
| «Наш продукт безопасен» | Red Team test | Результаты prompt injection |
| «ROI за N месяцев» | Все эксперименты | Baseline время задачи без/с ИИ |

**Принцип:** вендор проходит ваш тест на ваших данных. Демо на чужих данных — не доказательство.
