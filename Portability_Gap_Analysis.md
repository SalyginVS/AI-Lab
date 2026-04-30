# Gap Analysis: Данные из этапов, не вошедшие в Паспорт v33 и Архитектуру v1.19

**Дата:** 2026-04-30  
**Цель:** Зафиксировать знания, необходимые для переноса проекта, которые отсутствуют в финальных документах (Паспорт v33, Целевая архитектура v1.19), но содержатся в результатах этапов 1–16, F-next, R.

**Принцип отбора:** включена только информация, критичная для воспроизведения стека с нуля или восстановления после сбоя. Исторические заметки (что было и было заменено) опущены, если не влияют на текущее состояние.

---

## 1. Gateway: внутренняя реализация (Этапы 2–6, 9A, 9B)

Паспорт и архитектура фиксируют **что** делает gateway, но не **как**. При переносе или рефакторинге это критично.

### 1.1. Проброс параметров генерации (Этап 3)

Gateway маппит полный набор OpenAI-совместимых параметров на Ollama `options`:

| OpenAI параметр | Ollama options | Pydantic диапазон |
|---|---|---|
| temperature | temperature | 0.0–2.0 |
| top_p | top_p | 0.0–1.0 |
| max_tokens | num_predict | ≥ 1 |
| frequency_penalty | frequency_penalty | −2.0…2.0 |
| presence_penalty | presence_penalty | −2.0…2.0 |
| seed | seed | ≥ 0 |
| stop (str→[str]) | stop | — |
| num_ctx | num_ctx | 1–131072 (MAX_NUM_CTX) |
| num_gpu | num_gpu | ≥ 0 |
| num_batch | num_batch | ≥ 1 |
| repeat_penalty | repeat_penalty | 0.0–2.0 |
| repeat_last_n | repeat_last_n | ≥ −1 |

**Важно:** Ollama нативно поддерживает `frequency_penalty` и `presence_penalty` через `options` — это прямой маппинг 1:1, не аппроксимация через `repeat_penalty` (исправлено в Этапе 3; ранее было ошибочно задокументировано как «Ollama не поддерживает»).

**Warning при двойном штрафе:** если клиент передаёт `repeat_penalty` одновременно с `frequency_penalty` / `presence_penalty`, gateway логирует WARNING.

### 1.2. OOM-детекция (Этап 4)

Функция `classify_ollama_error()` распознаёт 8 паттернов OOM: `"out of memory"`, `"cuda out of memory"`, `"failed to allocate"` и др. (case-insensitive). При OOM → HTTP 503 + `Retry-After: 30`.

### 1.3. Настоящий стриминг (Этап 6)

Паттерн из документации httpx — «ручной streaming mode»:

```python
req = client.build_request("POST", url, json=payload)
resp = await client.send(req, stream=True)
# HTTP != 200 → aread() + aclose() + classify error
# HTTP 200 → return open response
# StreamingResponse(..., background=BackgroundTask(resp.aclose))
```

`BackgroundTask(resp.aclose)` гарантирует закрытие httpx response после завершения генератора (и при нормальном выходе, и при обрыве клиента). Retry возможен только до начала стриминга.

### 1.4. Tool_calls конвертация (Этап 7A)

Функция `convert_ollama_tool_calls_to_openai()`:
- `arguments`: dict → JSON string
- `index`: из function на верхний уровень
- `type: "function"` добавляется
- `finish_reason`: "tool_calls" вместо "stop" при наличии tool_calls
- Ollama отдаёт tool_calls **одним чанком** целиком (не потоково)

### 1.5. Multimodal messages (Этап 5)

`convert_message_for_ollama()` конвертирует OpenAI-формат в Ollama:
- Извлекает base64 из `data:image/...;base64,...` URI в `images[]`
- HTTP URL пробрасывает как есть
- `tool_calls` / `tool_call_id` передаёт для function calling

`ConfigDict(extra="ignore")` на обеих Pydantic-моделях — неизвестные параметры от клиента (`logprobs`, `logit_bias`, `n`, `user`, `response_format`, `service_tier`) молча игнорируются.

### 1.6. Embeddings hotfix (Этап 9B)

`encoding_format` — silent coerce to float вместо reject (400). Continue.dev отправляет `encoding_format: "float"` обязательно, но другие клиенты могут отправлять другие значения. Gateway всегда возвращает float.

### 1.7. Reasoning policy — решение по ownership (Этап 7B)

Gateway оставляет собственную логику `resolve_effort()` → `think: true/false`. Параметр `reasoning_effort` **НЕ** передаётся в payload Ollama (хотя Ollama с 0.17.7 его понимает). Причина: gateway фильтрует thinking из content, разделяет usage на `completion_tokens` и `reasoning_tokens`, управляет `reasoning_content`. Пересмотр — когда Ollama добавит гранулярные уровни thinking.

### 1.8. Логгер (Этап 3)

`logging.getLogger("uvicorn.error")` — единственный рабочий вариант для systemd journal output. `logging.getLogger("llm-gateway")` не работает — у него нет handler.

---

## 2. Copilot BYOK: конфигурация (Этап 7D)

Паспорт упоминает Copilot BYOK как «plain chat only», но не содержит конфигурацию.

### 2.1. VS Code settings.json

```json
{
  "github.copilot.chat.byok.ollamaEndpoint": "http://192.168.0.128:11434",
  "oaicopilot.baseUrl": "http://192.168.0.128:8000/v1",
  "oaicopilot.models": [
    {"id": "qwen3-coder:30b", "owned_by": "ollama", "context_length": 8192, "temperature": 0.3},
    {"id": "qwen3.5:9b", "owned_by": "ollama", "context_length": 8192, "temperature": 0.7},
    {"id": "glm-4.7-flash", "owned_by": "ollama", "context_length": 8192, "temperature": 0.7}
  ]
}
```

### 2.2. Расширение VS Code

OAI Compatible Provider for Copilot: `johnny-zhao.oai-compatible-copilot` — обязательно для Пути C (через шлюз).

### 2.3. Ограничения BYOK

- Доступен только для Free / Pro / Pro+ планов Copilot. **НЕ** доступен для Business / Enterprise.
- Путь B (`github.copilot.chat.customOAIModels`) **никогда не проверялся** — потенциально самый «чистый» вариант без стороннего расширения.
- Agent mode с локальными моделями нестабилен — модели не дообучены под формат инструментов Copilot (зацикливание, текст вместо tool_call JSON).

---

## 3. AI-as-Interface Lab Playbook v1.1 (отдельный документ)

**Полностью отсутствует** в паспорте и архитектуре. Содержит:

### 3.1. Пять экспериментов CIO

| # | Эксперимент | Что проверяет | Статус |
|---|---|---|---|
| 1 | Аудит точности Text-to-SQL | Жизнеспособность NL→SQL для реальных схем ONDO | ✅ Выполнен (11A, F-next) |
| 2 | Измерение галлюцинаций RAG | Можно ли доверять RAG по внутренним документам | Частично (RAG Active, формальный тест не выполнен) |
| 3 | Дашборд vs. нарративный отчёт | «Смерть дашбордов» применимость | Не выполнен |
| 4 | Границы автономии агента | Где read / write / destructive | Частично (MCP Git, Docker Active) |
| 5 | Red Team: Prompt Injection | Уязвимость AI-интерфейсов | Не выполнен |

### 3.2. Матрица enterprise-переносимости

| Паттерн | Лаборатория | Enterprise | Инвариант |
|---|---|---|---|
| MCP-коннекторы | STDIO на Windows | SSE/streamable-http на сервере | Архитектура MCP, протокол |
| LLM-оркестратор | Sequential, 53–88 сек/pipeline | Parallel, NUM_PARALLEL>1 | gateway.py + orchestrator.py |
| Hybrid RAG | ChromaDB embedded, один узел | Qdrant cluster, реплики | Паттерн retrieval |
| Text-to-SQL | qwen3-coder:30b | Крупная модель или fine-tune | Pipeline, semantic layer |
| Детерм. оркестрация | orchestrator.py | LangGraph / Temporal | HITL-политики |

### 3.3. Вендорский benchmark-фреймворк

Принцип: «вендор должен пройти ваш тест на ваших данных. Демо на чужих данных — не доказательство.» Пять контрольных вопросов с метриками из лабораторных экспериментов.

---

## 4. Операционные команды и процедуры

### 4.1. Активация git hooks

```bash
cd ~/llm-gateway
git config core.hooksPath .githooks
chmod +x .githooks/pre-push
chmod +x scripts/auto-review.sh scripts/auto-commit-msg.sh scripts/auto-docs.sh
```

### 4.2. Вызов orchestrator через venv

```bash
~/llm-gateway/venv/bin/python ~/llm-gateway/orchestrator.py --pipeline <name> --task "..." --stdout
```

Без venv → `ModuleNotFoundError: openai`. Все shell-скрипты жёстко ссылаются на `$ROOT_DIR/venv/bin/python`.

### 4.3. Runtime bridge для text2sql_semantic.py

```bash
cd ~/llm-gateway/scripts && \
RAG_SITE=$(~/rag-mcp-server/.venv/bin/python -c "import site; paths=[p for p in site.getsitepackages() if 'site-packages' in p]; print(paths[0] if paths else '')") && \
PYTHONPATH="$RAG_SITE:$PYTHONPATH" llmrun ~/llm-gateway/venv/bin/python text2sql_semantic.py
```

`llmrun` — утилита для загрузки `.env` с токенами. Два venv: `~/llm-gateway/venv` (openai SDK) и `~/rag-mcp-server/.venv` (chromadb + gateway_embeddings). Это tech debt.

### 4.4. Парсинг structured logs

```bash
# Все events
journalctl -u llm-gateway -o cat | jq -R 'fromjson? | select(.)'

# По пользователю
journalctl -u llm-gateway -o cat | jq -R 'fromjson? | select(.user_id == "roadwarrior")'

# Orchestrate events
journalctl -u llm-gateway -o cat | jq -R 'fromjson? | select(.event == "llm_orchestrate")'
```

### 4.5. SSH-tunnel для Docker MCP

```bash
ssh -L 8200:127.0.0.1:8200 user@192.168.0.128
```

После поднятия tunnel — обязательно `Developer: Reload Window` в VS Code (Continue не reconnects автоматически, Грабли #63).

### 4.6. Ollama Canary SOP

Документ: `~/llm-gateway/docs/SOP_Ollama_Upgrade.md` — процедура безопасного обновления Ollama.

### 4.7. Восстановление стека с нуля

Документ: `~/llm-gateway/docs/ONBOARDING.md` — полная процедура развёртывания стека.

---

## 5. Continue.dev: внутренняя механика (Этапы 7A–7C, 9B)

### 5.1. Диагностика ошибок конфигурации

- Ошибки конфига: правый нижний угол VS Code `⚠ Continue (config error)` + DevTools Console фильтр `continuedev`
- **Network tab DevTools НЕ показывает** запросы Continue — они идут из extension host, не из webview
- Команда «Continue: Open Config File» **не существует** — используйте «Continue: Open Settings»

### 5.2. Prompts — файловая система

Промпты через `.md` файлы работают из `.continue/prompts/`, **НЕ** из `.continue/rules/`. Rules и prompts — разные папки. Надёжнее определять промпты через `prompts:` секцию в config.yaml.

### 5.3. Provider codebase deprecated

`provider: codebase` в секции `context:` помечен как deprecated в документации Continue. Рекомендуемая замена — Agent mode built-in tools. Оставлен для backward compatibility.

### 5.4. transformers.js vs серверный embedding

transformers.js (all-MiniLM-L6-v2, 384d) работает внутри VS Code extension host — нулевая нагрузка на Ollama. При OLLAMA_NUM_PARALLEL=1 серверный embedding блокировал бы chat/agent при индексации. Текущая конфигурация: серверный qwen3-embedding (4096d) через gateway для @Codebase, transformers.js для @Code/@Repository Map индексации.

### 5.5. MCP YAML format (Грабли #60)

```yaml
# Правильно — плоская структура:
- name: git
  type: stdio
  command: uvx
  args: ["mcp-server-git"]

# Неправильно — вложенный transport:
- name: git
  transport:
    type: stdio
    ...
```

---

## 6. Semantic Tool Pack v1 (Этап 10C)

При оценке Gemma 4 был собран минимальный read-only tool pack из 5 инструментов:

| Tool | Назначение |
|---|---|
| list_directory | Листинг директории |
| find_files | Поиск файлов по паттерну |
| read_text_file | Чтение текстового файла |
| get_git_status | Git status |
| get_changed_files | Изменённые файлы |

**Находки:**
- gemma4:31b чувствительна к tool selection — требует thin policy prompt (`"Use the most specific tool available"`) для стабильного 3/3
- gemma4:26b — лучший zero-shot semantic tool selector (3/3 без policy)
- Multi-step semantic chaining работает (найди файл → прочитай) для обеих Gemma 4

---

## 7. Pipeline timing benchmarks (Этап 8C)

Реальные замеры на pipeline `plan-execute-review`:

| Сложность | Planner | Executor | Reviewer | Total |
|---|---|---|---|---|
| Simple (email validate) | 45.25s | ~6s | ~37s | 88.49s |
| Medium (async refactor) | 11.80s | 4.08s | 37.46s | 53.34s |
| Complex (log parse) | 26.63s | 5.01s | 35.02s | 66.66s |

JSON-артефакты сохранены в `~/llm-gateway/results/`.

**Наблюдения:**
- Planner вариативен: cold start + развёрнутый план = 45s; горячий + краткий = 12s
- Executor стабильно быстр: 4–6s
- Reviewer стабильно: 35–37s (reasoning перед ответом)
- Суммарно 53–88s — значительно лучше оценки 3–8 минут

---

## 8. Headless scripts: архитектурные решения (Этап 8D)

### 8.1. --stdout как bridge

Флаг `--stdout` в orchestrator.py: текст последнего шага → `sys.stdout` (без JSON-обёртки). JSON в `results/` при этом продолжает сохраняться.

### 8.2. pre-push STRICT_REVIEW

- `STRICT_REVIEW=0` (default): review выводится, push продолжается
- `STRICT_REVIEW=1` + TTY: интерактивный вопрос y/Y
- `STRICT_REVIEW=1` + non-TTY (CI/CD): `exit 1` — fail-closed

Проверка TTY: `-t 0` (stdin на TTY).

### 8.3. MAX_LINES=400

Защита от превышения `num_ctx` при больших диффах. Жёсткий truncate по числу строк.

### 8.4. commit-msg — одноступенчатый by design

qwen3.5:9b, без Reviewer — скорость важнее глубины проверки для commit message.

---

## 9. Ollama upgrade history: критические фиксы (Этап 7B)

Специфичные фиксы, влиявшие на стек:

| Версия Ollama | Фикс | Влияние |
|---|---|---|
| 0.17.5 | Краш qwen3.5 при GPU+CPU offload | Depth over Speed strategy |
| 0.17.5 | Penalties (repeat/presence/frequency) игнорировались Go runner | Шлюз передавал — Ollama отбрасывала |
| 0.17.5 | qwen3.5 бесконечные повторы (missing presence penalty) | Требовал re-pull модели |
| 0.17.6 | Tool calling qwen3.5 — Hermes JSON вместо Qwen-Coder XML | Объяснение «мусора» в Agent mode |
| 0.17.7 | reasoning_effort в OpenAI-совместимом API | Конфликт с нашим маппингом (решён — оставили свою логику) |
| 0.19+ | qwen3.5:9b tool calling восстановлен | Расширение capabilities |
| 0.20.4 | **Flash Attention bug** | **Была причина блокировки версии** |

**Текущая:** 0.20.7 (stable). GitHub issue references: #14493, #14745 (qwen3.5 tool calling), #14662 (qwen3.5:35b hang), #12387 (qwen3-coder FIM template missing).

---

## 10. Docker MCP: Policy Engine детали (Этап 12)

### 10.1. Категории tools

| Категория | Поведение | Tools |
|---|---|---|
| READ | Всегда разрешены | system_info, list_containers, list_images, container_inspect, container_logs, container_stats |
| LIFECYCLE | Разрешены + audit | start_container, stop_container, restart_container |
| EXEC | Allowlist/denylist + audit | exec_command |

### 10.2. Явно исключённые операции

`docker run`, `build`, `rm`, `rmi`, `pull`, `push`, `volume rm`, `network rm`, `prune` — **не реализованы как tools** (defense by omission).

### 10.3. Тестовый workload

`lab-nginx` (nginx:alpine, порт 8080:80) — используется для тестирования Docker MCP.

### 10.4. sync Docker SDK в async FastMCP

`asyncio.to_thread()` — обязательный паттерн для sync Docker SDK 7.1.0 в async FastMCP handlers.

---

## 11. RAG MCP Server: индексация и retrieval (Этапы 11, F-next)

### 11.1. Embedded dependencies

- FastMCP: `mcp 1.27.0`
- ChromaDB: `1.5.5`, PersistentClient
- Embedding: использует gateway_embeddings (wrapper), **не** прямой API вызов

### 11.2. Retrieval verification protocol

7 тестов retrieval quality в `test_sql_retrieval.py`:
- Каждый тест: вопрос → top-k results → проверка что релевантные карточки в top-3
- Контекстная изоляция: HR вопрос не тянет Hotel карточки

### 11.3. Knowledge drift (Грабли #65)

Schema drift — главный операционный риск semantic layer. Карточки содержали устаревшие имена колонок (`price_per_night` vs `total_uah`, `salary` vs `salary_uah`). В enterprise решается через DDL extraction + CI validation.

---

## 12. VS Code settings: полная конфигурация клиента

Паспорт фиксирует `config.yaml` Continue и `mcpServers/*.yaml`, но **не** VS Code settings.json:

```json
{
  "github.copilot.chat.byok.ollamaEndpoint": "http://192.168.0.128:11434",
  "oaicopilot.baseUrl": "http://192.168.0.128:8000/v1",
  "oaicopilot.models": [...]
}
```

Расширения VS Code установленные для проекта:
- Continue.dev (основное)
- OAI Compatible Provider for Copilot (`johnny-zhao.oai-compatible-copilot`)
- GitHub Copilot (Free plan)

---

## 13. GGML_CUDA_NO_GRAPHS=1 (Этап 7A)

Без этого флага Agent mode вызывал **CUDA graph capture crash (SIGABRT)** при быстрой последовательности запросов. Добавлен в override.conf. В паспорте перечислен как параметр, но **без объяснения причины** — при переносе на другое железо может возникнуть вопрос «нужен ли».

**Ответ:** нужен для стабильности Agent mode (каскад tool-call запросов). Без него — SIGABRT при быстрых последовательных запросах к GPU.

---

## 14. Бэкапы файлов

### 14.1. Gateway.py бэкапы на сервере

| Файл | Содержимое |
|---|---|
| `gateway.py.v060.bak` | v0.6.0 |
| `gateway.py.v050.bak` | v0.5.0 |
| `gateway.py.v040.bak` | v0.4.0 |
| `gateway.py.v030.bak` | v0.3.0 |
| `gateway.py.v020.bak` | v0.2.0 |
| `gateway.py.bak.20260315_182445` | v0.1.0 (оригинал) |
| `gateway.py.save` | Самый первый файл |

### 14.2. Continue config.yaml бэкапы на клиенте

| Файл | Содержимое |
|---|---|
| `config.yaml.before_v32_2026-04-19.bak` | До Qwen3.6 carrier change |
| `config.yaml.before_v33_2026-04-19.bak` | До qwen3-coder demotion |

---

## 15. Открытые вопросы из ранних этапов (не мигрировали в архитектуру)

| Источник | Вопрос | Статус |
|---|---|---|
| Этап 7B | reasoning_effort нативный Ollama vs наш think — мониторинг | Open — не закрыт формально |
| Этап 7D | customOAIModels (Путь B) в стабильном VS Code | Open — не проверен |
| Этап 7D | Thinking/reasoning display в Copilot Chat | Open — не проверен |
| Playbook v1.1 | Точность Text-to-SQL на кириллических схемах | Open — не тестировалось |
| Playbook v1.1 | Оптимальная стратегия chunking для русского языка | Open — не тестировалось |
| Playbook v1.1 | Prompt injection: RAG-сценарии | Open — Red Team не проводился |
| Playbook v1.1 | Vanna vs dbt для корпоративных схем ONDO | Open — не тестировалось |

---

## 16. Рекомендация: что включить в документацию при переносе

### Обязательно (блокирует восстановление):

1. **ONBOARDING.md** (`~/llm-gateway/docs/`) — убедиться что актуален относительно v33 (tech debt)
2. **SOP_Ollama_Upgrade.md** (`~/llm-gateway/docs/`) — критичен для операционной стабильности
3. **Разделы 1, 4, 5, 13** данного документа — gateway internals, команды, Continue mechanics, CUDA_NO_GRAPHS
4. **Раздел 2** — Copilot BYOK конфигурация

### Важно (ускоряет восстановление):

5. **Раздел 3** — AI-as-Interface Playbook (стратегический контекст для ONDO)
6. **Раздел 7** — реальные замеры pipeline timing
7. **Раздел 9** — history Ollama upgrade фиксов (помогает при следующем upgrade)
8. **Раздел 10** — Docker MCP policy details

### Желательно (экономит время):

9. **Раздел 6** — Semantic Tool Pack v1 (тестовый набор tools)
10. **Раздел 14** — расположение бэкапов
11. **Раздел 15** — незакрытые вопросы

---

*Документ создан автоматическим анализом 30+ файлов проекта.*
