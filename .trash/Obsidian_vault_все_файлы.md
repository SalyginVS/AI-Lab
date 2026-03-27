# Obsidian Vault: Все файлы для нарезки
# Каждый файл отделён строкой: ═══ ФАЙЛ: путь/имя.md ═══
# Разрезать по этим строкам и разложить в папки vault

═══ ФАЙЛ: Грабли/01 Фейковый стриминг httpx.md ═══
---
tags: [грабли, gateway, ollama]
дата: 2026-03-15
этап: "[[Этап01 — Диагностика шлюза]]"
компонент: "[[gateway.py]]"
---

# Фейковый стриминг httpx

## Симптом
TTFT равен полному времени генерации. Клиент ждёт 30-120 секунд до первого символа.

## Причина
`httpx.AsyncClient.post()` буферизует весь ответ в память. `resp.aiter_lines()` итерирует по уже загруженному буферу.

## Решение
Ручной streaming mode:
```python
req = client.build_request("POST", url, json=payload)
resp = await client.send(req, stream=True)
# BackgroundTask(resp.aclose) для закрытия
```

## Результат
TTFT: ~full time → **0.12 сек**. Решено в gateway.py v0.6.0 (Этап 6).


═══ ФАЙЛ: Грабли/02 qwen3.5 tool calling сломан.md ═══
---
tags: [грабли, ollama, модели]
дата: 2026-03-16
этап: "[[Этап07A — Continue Agent]]"
компонент: "[[qwen3.5 35b]]"
---

# qwen3.5:35b — tool calling сломан в Ollama

## Симптом
Agent mode: мусорный текст на китайском вместо tool_calls. Unclosed `<think>` tags. Hang на втором запросе на RTX 3090.

## Причина
1. qwen3.5:35b — thinking-модель, не соблюдает протокол function calling
2. До Ollama 0.17.6 — неправильный parser pipeline (Hermes JSON вместо Qwen-Coder XML)
3. После 0.18.0 — по-прежнему ненадёжен

## Решение
**Никогда не использовать для Agent mode / tool calling.** Только:
- **qwen3-coder:30b** — надёжный function calling
- **glm-4.7-flash** — tools работают

qwen3.5:35b допустим только для текстовых задач без tools.


═══ ФАЙЛ: Грабли/03 Continue timeout миллисекунды.md ═══
---
tags: [грабли, continue]
дата: 2026-03-16
этап: "[[Этап07A — Continue Agent]]"
компонент: "[[Continue.dev]]"
---

# Continue.dev timeout — миллисекунды, не секунды

## Симптом
Agent mode: каскад запросов, ни один не завершается. "Connection error".

## Причина
OpenAI Node.js SDK принимает `timeout` в **миллисекундах**. `timeout: 600` = 0.6 сек.

## Решение
```yaml
requestOptions:
  timeout: 600000   # 10 минут
```
Autocomplete: `timeout: 30000` (30 сек).


═══ ФАЙЛ: Грабли/04 extraBodyProperties внутри requestOptions.md ═══
---
tags: [грабли, continue]
дата: 2026-03-17
этап: "[[Этап07B — Autocomplete и Ollama 0.18]]"
компонент: "[[Continue.dev]]"
---

# extraBodyProperties — внутри requestOptions

## Симптом
HTTP 400 от Ollama. Параметры `num_ctx`, `reasoning_effort` не передаются.

## Причина
`extraBodyProperties` вложено внутри `requestOptions`, не peer-level.

## Решение
```yaml
# ✅ Правильно:
requestOptions:
  timeout: 600000
  extraBodyProperties:
    num_ctx: 8192
    reasoning_effort: "none"
```


═══ ФАЙЛ: Грабли/05 context секция сбрасывает дефолты.md ═══
---
tags: [грабли, continue]
дата: 2026-03-19
этап: "[[Этап07C — Context Rules Prompts]]"
компонент: "[[Continue.dev]]"
---

# Секция context: сбрасывает дефолтные провайдеры

## Симптом
После добавления `context:` пропадают @File, @Code, @Diff и др.

## Причина
Continue 1.2.17 заменяет дефолты на то, что указано в конфиге.

## Решение
Перечислить ВСЕ 11 провайдеров явно: code, repo-map, file, currentFile, open, diff, terminal, tree, problems, clipboard, os.


═══ ФАЙЛ: Грабли/06 logging uvicorn.error.md ═══
---
tags: [грабли, gateway, python]
дата: 2026-03-15
этап: "[[Этап03 — Параметры генерации]]"
компонент: "[[gateway.py]]"
---

# logging: использовать uvicorn.error, не custom name

## Симптом
Логи не появляются в `journalctl -u llm-gateway`.

## Причина
`logging.getLogger("my-name")` без handler'а → нет вывода. uvicorn уже настроил handler для `"uvicorn.error"`.

## Решение
```python
logger = logging.getLogger("uvicorn.error")
```


═══ ФАЙЛ: Грабли/07 Ollama tool_calls формат.md ═══
---
tags: [грабли, gateway, ollama]
дата: 2026-03-16
этап: "[[Этап07A — Continue Agent]]"
компонент: "[[gateway.py]]"
---

# Ollama tool_calls формат отличается от OpenAI

## Симптом
Agent получает пустой ответ через шлюз.

## Причина
Ollama: arguments=dict, index внутри function, нет type.
OpenAI: arguments=JSON string, index top-level, type="function".

## Решение
Конвертер `convert_ollama_tool_calls_to_openai()` в gateway.py v0.7.0.
`finish_reason: "tool_calls"` вместо `"stop"`.


═══ ФАЙЛ: Грабли/08 OLLAMA_HOST формат с портом.md ═══
---
tags: [грабли, ollama]
дата: 2026-03-15
компонент: "[[Ollama]]"
---

# OLLAMA_HOST — обязательно с портом

## Решение
```ini
Environment="OLLAMA_HOST=0.0.0.0:11434"
```
Без порта — непредсказуемое поведение.


═══ ФАЙЛ: Грабли/09 CUDA graph crash.md ═══
---
tags: [грабли, ollama, gpu]
дата: 2026-03-16
этап: "[[Этап07A — Continue Agent]]"
компонент: "[[Ollama]]"
---

# CUDA graph capture crash → GGML_CUDA_NO_GRAPHS=1

## Симптом
Ollama SIGABRT при быстрой последовательности запросов (Agent mode).

## Решение
```ini
Environment="GGML_CUDA_NO_GRAPHS=1"
```


═══ ФАЙЛ: Грабли/10 YAML quirks Continue 1.2.17.md ═══
---
tags: [грабли, continue]
дата: 2026-03-16
этап: "[[Этап07A — Continue Agent]]"
компонент: "[[Continue.dev]]"
---

# YAML quirks Continue 1.2.17 — сборник

- **YAML anchors** (`<<: *defaults`) — не поддерживаются
- **Имена с скобками** — `"model (reasoning)"` → `Invalid input`. Простые имена только
- **roles: [agent]** — невалидная роль. Валидные: chat, edit, apply, autocomplete
- **debounce** → правильно `debounceDelay`
- **Prompts** — через `prompts:` в config.yaml, НЕ через `rules/`
- **capabilities: [tool_use]** — НЕ требуется, Continue автодетектит
- **Проектные rules** — требуют `Developer: Reload Window` при первом создании
- **YAML comments с двоеточиями** — вызывают parse errors


═══ ФАЙЛ: Грабли/11 nano sed ненадёжен для Python.md ═══
---
tags: [грабли, инфра]
дата: 2026-03-15
компонент: "[[gateway.py]]"
---

# nano/sed ненадёжен для Python файлов

## Решение
Полная замена через `scp`:
```powershell
scp gateway.py user@192.168.0.128:~/llm-gateway/gateway.py
```


═══ ФАЙЛ: Грабли/12 bash set-e VAR++.md ═══
---
tags: [грабли, инфра, bash]
дата: 2026-03-15
---

# bash set -e: ((VAR++)) при VAR=0 = silent exit

## Причина
`((0++))` возвращает exit code 1. С `set -e` — скрипт тихо умирает.

## Решение
```bash
COUNTER=$((COUNTER + 1))   # безопасно
```


═══ ФАЙЛ: Грабли/13 tabAutocompleteModel нет в YAML.md ═══
---
tags: [грабли, continue]
дата: 2026-03-17
этап: "[[Этап07B — Autocomplete и Ollama 0.18]]"
компонент: "[[Continue.dev]]"
---

# tabAutocompleteModel — синтаксис JSON, нет в YAML

## Решение
В YAML: модель с `roles: [autocomplete]` внутри `models`. `autocompleteOptions` на уровне модели.


═══ ФАЙЛ: Грабли/14 Copilot BYOK Agent нестабилен.md ═══
---
tags: [грабли, copilot]
дата: 2026-03-19
этап: "[[Этап07D — Copilot BYOK]]"
компонент: "[[Copilot BYOK]]"
---

# Copilot BYOK Agent mode нестабилен с локальными моделями

## Симптом
«Болтовня» вместо tool_calls. Зацикливание.

## Причина
Copilot Agent uses own tool protocol. 30B models не дисциплинированы для него.

## Решение
Copilot BYOK — только plain chat. Agent mode — только Continue.dev. Неисправим на стороне шлюза.


═══ ФАЙЛ: Грабли/15 mcp-server-git CVE безопасность.md ═══
---
tags: [грабли, mcp, безопасность]
дата: 2026-03-20
этап: "[[Этап08A — MCP Git Server]]"
компонент: "[[mcp-server-git]]"
---

# mcp-server-git: три CVE (январь 2026)

CVE-2025-68143 (git_init), CVE-2025-68144 (arg injection), CVE-2025-68145 (path bypass).
Исправлены в **2025.12.18**. `git_init` удалён. Используй >= 2026.1.14.


═══ ФАЙЛ: Решения/ADR-001 Depth over Speed.md ═══
---
tags: [adr, решение]
дата: 2026-03-15
статус: принято
---

# ADR-001: Depth over Speed

## Контекст
RTX 3090 (24 ГБ VRAM) + 62 ГБ RAM. Одно GPU. Нужно выбрать приоритет: скорость генерации или глубина контекста.

## Решение
Приоритет — **глубина контекста**. RAM используется как расширение VRAM (~86 ГБ суммарный пул). num_ctx по умолчанию 8192, поддержка до 32768. Скорость генерации вторична. Flash Attention + KV cache q8_0 оптимизируют расход памяти.

## Альтернативы
| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| Speed-first (малые модели, малый контекст) | Быстрее | Поверхностные ответы |
| **Depth-first** (большие модели, большой контекст) | Качественные ответы | Медленнее |

## Последствия
- NUM_PARALLEL=1 — один запрос за раз
- Холодный старт 8-30 сек при смене модели — приемлемо
- Orchestrator pipeline 3-8 минут — приемлемо
- При переносе на Enterprise multi-GPU — скорость добавляется без изменения архитектуры


═══ ФАЙЛ: Решения/ADR-002 Continue-first.md ═══
---
tags: [adr, решение]
дата: 2026-03-16
статус: принято
---

# ADR-002: Continue.dev как единственный primary agent runtime

## Контекст
Нужен IDE agent runtime для Chat, Edit, Agent mode с tool calling. Варианты: Continue.dev, Copilot BYOK, Kilo Code.

## Решение
**Continue.dev** — единственный primary runtime. Copilot BYOK — secondary, только plain chat. Причины:
- Подтверждён для Chat, Edit, Agent, Apply, Context, Rules, Prompts
- Полностью локальный, YAML-конфигурируемый
- Поддерживает MCP стандарт
- Copilot Agent mode с локальными моделями **нестабилен** и неисправим на стороне шлюза

## Последствия
- Все MCP-серверы подключаются через Continue
- Copilot BYOK зафиксирован как «compatibility check only»


═══ ФАЙЛ: Решения/ADR-003 STDIO транспорт для MCP.md ═══
---
tags: [adr, решение, mcp]
дата: 2026-03-20
статус: принято
---

# ADR-003: STDIO транспорт по умолчанию для локальных MCP-серверов

## Контекст
MCP поддерживает три транспорта: STDIO, SSE, streamable-http. MCP-серверы запускаются на стороне клиента (Windows), т.к. Continue — VS Code extension.

## Решение
**STDIO по умолчанию** для всех локальных инструментов. SSE/streamable-http — только для серверных (Docker MCP на Ubuntu, RAG с Ollama embeddings).

## Альтернативы
| Транспорт | Плюсы | Минусы |
|-----------|-------|--------|
| **STDIO** | Минимальная задержка, нет портов, лучшая безопасность | Только локально |
| SSE | Удалённые серверы | Открытые порты, HTTP overhead |
| streamable-http | Стандартный HTTP | Больший overhead |

## Последствия
- Git MCP → STDIO на Windows (uvx)
- Terminal MCP → нативный Continue (встроенный)
- Docker MCP → SSE на Ubuntu (DOCKER_HOST=ssh://...)
- RAG MCP → SSE на Ubuntu (Ollama embeddings на GPU)


═══ ФАЙЛ: Решения/ADR-004 transformers.js вместо Ollama embeddings.md ═══
---
tags: [adr, решение]
дата: 2026-03-19
статус: принято
---

# ADR-004: transformers.js для embeddings (вместо Ollama)

## Контекст
Нужны embeddings для индексации кодовой базы (@Code, @Repository Map). OLLAMA_NUM_PARALLEL=1 — один запрос за раз.

## Решение
**transformers.js** (all-MiniLM-L6-v2), встроенный в VS Code extension host. Нулевая нагрузка на Ollama, не блокирует chat/agent/autocomplete.

## Альтернативы
| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| **transformers.js** | Параллельно с Ollama, zero-config | Модель маленькая, нет русского |
| qwen3-embedding через Ollama | Лучше качество, русский | Блокирует GPU при индексации |

## Последствия
- Индексация не мешает работе с моделями
- Качество embeddings базовое (code search — достаточно)
- Миграция на qwen3-embedding запланирована на Этап 9B (через /v1/embeddings)


═══ ФАЙЛ: Решения/ADR-005 ChromaDB для RAG PoC.md ═══
---
tags: [adr, решение]
дата: 2026-03-20
статус: принято
---

# ADR-005: ChromaDB для RAG PoC

## Контекст
Нужна vector DB для RAG-сервера (Этап 11). Варианты: ChromaDB (embedded), Qdrant (server), SQLite+faiss (manual).

## Решение
**ChromaDB в embedded режиме** для PoC. SQLite backend, zero-config, Python API.

## Последствия
- Ограничение ~100K документов — достаточно для лаборатории
- При масштабировании — миграция на Qdrant
- Этап 11


═══ ФАЙЛ: Решения/ADR-006 Модуляризация gateway.md ═══
---
tags: [adr, решение]
дата: 2026-03-20
статус: принято
---

# ADR-006: Модуляризация gateway.py при первом расширении

## Контекст
gateway.py v0.7.0 — 994 строки. При добавлении embeddings, logging, metrics, orchestrate вырастет до 2000+.

## Решение
При первом расширении (Этап 9A/10A) разбить на Python-пакет `~/llm-gateway/gateway/`. Модули в одном процессе (один systemd unit, один порт), логически разделённые: app.py, router.py, streaming.py, embeddings.py, metrics.py, auth.py, logging_config.py, models.py, orchestrator.py.

## Последствия
- Можно обновлять embeddings не трогая streaming
- Тестировать orchestrator изолированно
- При переносе на Enterprise — вынести модули в отдельные сервисы если нужно


═══ ФАЙЛ: Конфиги/Ollama override.conf.md ═══
---
tags: [конфиг, ollama]
дата: 2026-03-17
---

# Ollama systemd override

Файл: `/etc/systemd/system/ollama.service.d/override.conf`

```ini
[Service]
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
Environment="OLLAMA_MAX_LOADED_MODELS=2"
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="CUDA_VISIBLE_DEVICES=0"
Environment="GGML_CUDA_NO_GRAPHS=1"
```

| Параметр | Значение | Зачем |
|----------|----------|-------|
| FLASH_ATTENTION | 1 | Экономия VRAM |
| KV_CACHE_TYPE | q8_0 | KV cache сжимается вдвое |
| MAX_LOADED_MODELS | 2 | FIM + chat/agent одновременно |
| HOST | 0.0.0.0:11434 | Доступ из LAN |
| CUDA_VISIBLE_DEVICES | 0 | Одна GPU |
| GGML_CUDA_NO_GRAPHS | 1 | Защита от crash при Agent mode |

После изменений: `sudo systemctl daemon-reload && sudo systemctl restart ollama`


═══ ФАЙЛ: Конфиги/gateway.py эндпоинты.md ═══
---
tags: [конфиг, gateway]
дата: 2026-03-19
---

# gateway.py v0.7.0 — эндпоинты и параметры

Файл: `~/llm-gateway/gateway.py`
Сервис: `llm-gateway.service`
Порт: 8000

## Эндпоинты

| Метод | Путь | Назначение |
|-------|------|-----------|
| POST | /v1/chat/completions | Основной — проксирует в Ollama |
| GET | /v1/models | Список моделей (OpenAI-формат) |
| GET | /health | Статус шлюза, Ollama, моделей |

## Ключевые параметры

- **reasoning_effort**: none/low/medium/high → think: true/false
- **num_ctx**: 1–32768 (дефолт 8192)
- **tools/tool_choice**: проброс для function calling
- **Auth**: Bearer token через env `LLM_GATEWAY_API_KEY` (опционально)
- **Retry**: 3 попытки при connection errors, exponential backoff
- **OOM**: 8 паттернов, HTTP 503 + Retry-After: 30


═══ ФАЙЛ: Конфиги/systemd llm-gateway.service.md ═══
---
tags: [конфиг, gateway]
дата: 2026-03-15
---

# systemd: llm-gateway.service

Файл: `/etc/systemd/system/llm-gateway.service`

```ini
[Unit]
Description=LLM Gateway
After=ollama.service
Wants=ollama.service

[Service]
Type=simple
User=user
WorkingDirectory=/home/user/llm-gateway
ExecStart=/usr/bin/uvicorn gateway:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Управление:
```bash
sudo systemctl start llm-gateway
sudo systemctl status llm-gateway
sudo journalctl -u llm-gateway -f    # live логи
```


═══ ФАЙЛ: Конфиги/git.yaml (MCP).md ═══
---
tags: [конфиг, mcp]
дата: 2026-03-20
---

# MCP Git Server — конфигурация

Файл: `%USERPROFILE%\.continue\mcpServers\git.yaml`

```yaml
name: Git MCP Server
version: 0.0.1
schema: v1

mcpServers:
  - name: git
    type: stdio
    command: uvx
    args:
      - "mcp-server-git"
```

Без `--repository` — работает с любым репозиторием, путь через `repo_path` в каждом tool call.


═══ ФАЙЛ: Конфиги/Continue config.yaml обзор.md ═══
---
tags: [конфиг, continue]
дата: 2026-03-19
---

# Continue.dev config.yaml — обзор

Файл: `%USERPROFILE%\.continue\config.yaml`

## Структура
- **8 моделей**: 1 embed (transformers.js) + 1 autocomplete (qwen2.5-coder:7b) + 6 chat-capable
- **11 context providers**: code, repo-map, file, currentFile, open, diff, terminal, tree, problems, clipboard, os
- **6 prompts**: review, explain, refactor, docstring, test, security
- **Rules**: 2 глобальных (general, coding) + проектные

## Модели и роли
| Модель | Provider | Роли |
|--------|----------|------|
| qwen2.5-coder:7b | ollama напрямую | autocomplete |
| all-MiniLM-L6-v2 | transformers.js | embeddings |
| qwen3.5:9b | openai (шлюз) | chat, edit, apply |
| qwen3-coder:30b | openai (шлюз) | chat, edit, apply |
| glm-4.7-flash | openai (шлюз) | chat, edit, apply |
| deepseek-r1:32b | openai (шлюз) | chat |
| qwen3.5:35b | openai (шлюз) | chat, edit |
| qwen3-vl:8b | openai (шлюз) | chat (vision) |

## Ключевые грабли
- [[03 Continue timeout миллисекунды]]
- [[04 extraBodyProperties внутри requestOptions]]
- [[05 context секция сбрасывает дефолты]]
- [[10 YAML quirks Continue 1.2.17]]
- [[13 tabAutocompleteModel нет в YAML]]


═══ ФАЙЛ: Meta/Глоссарий.md ═══
---
tags: [meta]
---

# Глоссарий

| Термин | Расшифровка |
|--------|-------------|
| ADR | Architecture Decision Record — документ, фиксирующий решение с контекстом |
| BYOK | Bring Your Own Key — подключение своих моделей к Copilot |
| ChromaDB | Встраиваемая векторная БД на Python (SQLite backend) |
| FIM | Fill-In-the-Middle — формат промпта для autocomplete: prefix + suffix → middle |
| FastMCP | Python-библиотека для быстрого создания MCP-серверов |
| MCP | Model Context Protocol — открытый стандарт Anthropic для подключения AI к инструментам |
| OOM | Out Of Memory — нехватка GPU/RAM памяти |
| RAG | Retrieval-Augmented Generation — генерация с подгрузкой релевантных документов |
| SSE | Server-Sent Events — однонаправленный серверный стриминг через HTTP |
| STDIO | Standard Input/Output — межпроцессное взаимодействие через stdin/stdout |
| TTFT | Time To First Token — задержка до первого токена ответа |
| UFW | Uncomplicated Firewall — межсетевой экран Ubuntu |
| uvx | Команда uv для запуска Python-инструментов в изолированных окружениях |


═══ ФАЙЛ: Meta/Roadmap.md ═══
---
tags: [meta]
---

# Roadmap: 16 этапов, 5 треков

## Статус этапов

| Этап | Название | Статус |
|------|----------|--------|
| 1–6 | Gateway v0.1.0 → v0.7.0 | ✅ Завершены |
| 7A | Continue Agent mode | ✅ Завершён |
| 7B | Autocomplete + Ollama 0.18 | ✅ Завершён |
| 7C | Context + Rules + Prompts | ✅ Завершён |
| 7D | Copilot BYOK | ✅ Завершён |
| **8A** | **MCP: Git Server** | **🔄 В работе** |
| 8B | MCP: Terminal + Policy | ⬜ План |
| 8C | Orchestrator PoC | ⬜ План |
| 8D | Headless Automation | ⬜ План |
| 9A | gateway /v1/embeddings | ⬜ План |
| 9B | Embeddings миграция | ⬜ План |
| 10A | Structured Logging | ⬜ План |
| 10B | Metrics Endpoint | ⬜ План |
| 11 | MCP: RAG/Docs | ⬜ План |
| 12 | MCP: Docker | ⬜ План |
| 13 | Knowledge Layer | ⬜ План |
| 14 | Security Hardening | ⬜ План |
| 15 | Benchmark Matrix | ⬜ План |
| 16 | gateway /v1/orchestrate | ⬜ План |

## Параллельные треки
```
A (MCP Tools):      8A → 8B ────────────────→ 11 → 12
B (Backend):        9A → 9B    10A → 10B
C (Knowledge):      ──────────────→ 13
D (Ops/Security):   ────────────────→ 14 → 15
E (Orchestration):  8C → 8D ──────────────────→ 16
```


═══ ФАЙЛ: Meta/Рабочий процесс.md ═══
---
tags: [meta]
---

# Рабочий процесс

1. **Claude** — глубокий анализ, проверка актуальности, подготовка материалов (план, конфиги, скрипты, тесты)
2. **Perplexity AI** — исследование текущего состояния инструментов. Claude готовит briefing-блоки
3. **Vladimir** — выполнение на сервере/клиенте под управлением Perplexity
4. **Claude** — проверка результатов, финализация, обновление паспорта и документации

## Правила
- Пошагово, один подэтап за раз
- Конфигурации: полные файлы, не фрагменты
- Перед деплоем: аудит на соответствие live-серверу
- Каждый этап: результаты.md + паспорт + стартовый промпт


═══ ФАЙЛ: Шаблоны/_Шаблон этапа.md ═══
---
tags: [шаблон]
---

```
---
tags: [этап, lab]
дата: {{date}}
статус: план/в_работе/завершён
зависимости: []
---

# Этап XX — Название

## Задача
Одно предложение.

## Результат
Что конкретно работает после завершения.

## Что сделано
### Подэтап 1
...

## Грабли
- [[Название грабли]]

## Замеры
| Метрика | До | После |
|---------|-----|-------|

## Артефакты
- Файл 1

## Решения (ADR)
- [[ADR-NNN Название]]

## Критерии завершения
- [x] / [ ] ...
```


═══ ФАЙЛ: Шаблоны/_Шаблон грабли.md ═══
---
tags: [шаблон]
---

```
---
tags: [грабли, компонент]
дата: {{date}}
этап: "[[Этап XX]]"
компонент: "[[Компонент]]"
---

# Название проблемы

## Симптом
Что видно.

## Причина
Почему.

## Решение
Что делать. Код/команда.
```


═══ ФАЙЛ: Шаблоны/_Шаблон ADR.md ═══
---
tags: [шаблон]
---

```
---
tags: [adr, решение]
дата: {{date}}
статус: принято/отклонено/заменено
---

# ADR-NNN: Название

## Контекст
Какой выбор стоял.

## Решение
Что выбрали и почему.

## Альтернативы
| Вариант | Плюсы | Минусы |
|---------|-------|--------|

## Последствия
Что это означает для архитектуры.
```


═══ ФАЙЛ: Шаблоны/_Шаблон briefing.md ═══
---
tags: [шаблон]
---

```
---
tags: [briefing, perplexity]
дата: {{date}}
этап: "[[Этап XX]]"
---

# Briefing: Тема

> Самодостаточный блок для Perplexity AI

## Контекст
...

## Вопросы
1. ...

## Результат исследования
*(заполняется после)*
```


═══ ФАЙЛ: README.md ═══
---
tags: [meta]
---

# AI Lab Knowledge Base

Obsidian vault для домашней ИИ лаборатории → AI Coding Platform.

## Навигация

- **[[Паспорт лаборатории]]** — текущее состояние стека (живой документ)
- **[[Целевая архитектура]]** — 7 слоёв, 16 этапов
- **[[Meta/Roadmap]]** — прогресс по этапам
- **Этапы/** — хронология, один файл на этап
- **Грабли/** — найденные проблемы (симптом → причина → решение)
- **Решения/** — ADR (Architecture Decision Records)
- **Конфиги/** — эталонные конфигурации с комментариями
- **Briefings/** — блоки для Perplexity AI

## Инфраструктура

| Компонент | Где | Версия |
|-----------|-----|--------|
| Сервер | 192.168.0.128 | Ubuntu 22.04, RTX 3090, i9-9900KF |
| Ollama | :11434 | 0.18.0, 13 моделей |
| gateway.py | :8000 | v0.7.0 |
| Continue.dev | VS Code | v1.2.17 |
| Стратегия | — | Depth over Speed |

## Рекомендуемые плагины
Dataview, Templater, Calendar, Graph Analysis
