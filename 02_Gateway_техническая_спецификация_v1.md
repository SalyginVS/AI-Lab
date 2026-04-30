# Gateway v0.12.0: Техническая спецификация

**Версия:** 1.0  
**Дата:** 2026-04-30  
**Назначение:** Внутренняя реализация gateway для воспроизведения, рефакторинга или переноса на другой стек.

---

## 1. Архитектура модулей

Расположение: `~/llm-gateway/gateway/` (Python-пакет, 11 модулей).

```
gateway/
├── __init__.py         # VERSION="0.12.0", DEFAULT_NUM_CTX=131072, MAX_NUM_CTX=131072, константы
├── app.py              # FastAPI assembly: middleware, handlers, routers, startup
├── auth.py             # Per-user Bearer token validation (mandatory)
├── models.py           # Pydantic/dataclass модели запросов/ответов
├── errors.py           # GatewayError + 3 exception handlers (HTTPException, RequestValidationError, generic)
├── upstream.py         # httpx AsyncClient singleton, retry, OOM classification
├── chat.py             # POST /v1/chat/completions + tool_calls conversion + reasoning policy
├── embeddings.py       # POST /v1/embeddings + batch + allowlist
├── listing.py          # GET /v1/models, GET /health
├── logging_config.py   # JSONFormatter, structured logging (stdlib, 0 dependencies)
├── metrics.py          # MetricsCollector (threading.Lock), GET /metrics
└── orchestrate.py      # POST /v1/orchestrate + GET /v1/orchestrate/pipelines (self-call pattern)
```

Entrypoint: `~/llm-gateway/run.py` → `uvicorn gateway.app:app`.

---

## 2. Ключевые реализационные паттерны

### 2.1. Стриминг (httpx ручной mode)

```python
# Функция: ollama_stream_with_retry()
req = client.build_request("POST", url, json=payload)
resp = await client.send(req, stream=True)
# HTTP != 200 → await resp.aread() + await resp.aclose() + classify_ollama_error()
# HTTP 200 → return resp (open, body не прочитан)
# Вызывающий код:
StreamingResponse(stream_generator(resp), ..., background=BackgroundTask(resp.aclose))
```

BackgroundTask гарантирует закрытие response даже при обрыве клиента. Retry только до начала стриминга (connection phase).

### 2.2. Tool_calls конвертация Ollama → OpenAI

```python
# Функция: convert_ollama_tool_calls_to_openai(tool_calls_list)
# Ollama формат: {"function": {"index": 0, "name": "...", "arguments": {...}}}
# OpenAI формат: {"index": 0, "id": "call_...", "type": "function", "function": {"name": "...", "arguments": "{...}"}}

# Ключевые преобразования:
# 1. arguments: dict → JSON string
# 2. index: из function на верхний уровень
# 3. type: "function" добавляется
# 4. finish_reason: "tool_calls" вместо "stop"
```

Ollama отдаёт tool_calls одним чанком целиком (не потоково).

### 2.3. Multimodal messages

```python
# Функция: convert_message_for_ollama(messages)
# Обработка content: Union[str, list, None]
# - text blocks → content string
# - image_url blocks:
#   - data:image/...;base64,... → извлечение base64 в images[]
#   - http(s):// URL → проброс как есть
# - tool_calls / tool_call_id → проброс
```

### 2.4. Reasoning policy

```python
# Функция: resolve_effort(request) → bool (think: true/false)
# Приоритет: request.reasoning.effort > request.reasoning_effort > "none"
# Маппинг:
#   "none" / "low" → think: false
#   "medium" / "high" → think: true

# reasoning_effort НЕ передаётся в Ollama payload (хотя Ollama 0.17.7+ понимает)
# Gateway владеет: фильтрация thinking из content, разделение usage, reasoning_content
```

### 2.5. OOM classification

```python
# Функция: classify_ollama_error(status_code, body_text)
# 8 паттернов OOM (case-insensitive):
OOM_PATTERNS = [
    "out of memory", "cuda out of memory", "failed to allocate",
    "insufficient memory", "memory allocation failed", "oom",
    "not enough memory", "cuda error"
]
# OOM → HTTP 503 + Retry-After: 30
# 404 → 404 (model not found)
# 400 → 400 (invalid request)
# 5xx → 502 (upstream error)
```

### 2.6. Auth middleware

```python
# Модуль: auth.py
# LLM_GATEWAY_TOKENS env → JSON dict {token: user_id}
# Отсутствие env → sys.exit(1) (mandatory)
# AUTH_EXEMPT_PATHS = {"/health", "/metrics"}
# Middleware: token lookup → request.state.user_id
# 401 → OpenAI-совместимый формат {"error": {"message": ..., "type": "authentication_error"}}
```

### 2.7. Self-call orchestration (ADR-016)

```python
# Модуль: orchestrate.py
# Каждый pipeline step → POST /v1/chat/completions на localhost:8000
# Token: LLM_ORCHESTRATOR_TOKEN (user_id "orchestrator")
# Sync OpenAI SDK → asyncio.to_thread() (не блокирует uvicorn event loop)
# strip_think_blocks() — удаление <think>...</think> из planner output перед передачей executor
# Tech debt: num_ctx hardcoded 131072 (не импортирует DEFAULT_NUM_CTX)
```

---

## 3. Pydantic модели и валидация

### 3.1. ChatCompletionRequest

```python
class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    seed: Optional[int] = Field(default=None, ge=0)
    stop: Optional[Union[str, list]] = None
    tools: Optional[list] = None
    tool_choice: Optional[Any] = None
    # Ollama-specific:
    num_ctx: int = Field(default=DEFAULT_NUM_CTX, ge=1, le=MAX_NUM_CTX)  # 131072
    num_gpu: Optional[int] = Field(default=None, ge=0)
    num_batch: Optional[int] = Field(default=None, ge=1)
    repeat_penalty: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    repeat_last_n: Optional[int] = Field(default=None, ge=-1)
    # Reasoning:
    reasoning: Optional[ReasoningConfig] = None
    reasoning_effort: Optional[str] = None

    class Config:
        extra = "ignore"  # SDK compatibility — неизвестные поля молча игнорируются
```

### 3.2. ChatMessage

```python
class ChatMessage(BaseModel):
    role: str
    content: Optional[Union[str, list]] = None  # str | image blocks | None
    name: Optional[str] = None
    tool_calls: Optional[list] = None
    tool_call_id: Optional[str] = None

    class Config:
        extra = "ignore"
```

---

## 4. Structured logging

### 4.1. Формат

JSONFormatter (stdlib logging, 0 dependencies). Каждый event → одна JSON-строка в systemd journal.

### 4.2. Event types

| Event | Поля |
|---|---|
| `llm_completion` | model, tokens (prompt/completion/reasoning), latency_ms, ttft_ms, tool_calls_count, reasoning_effort, user_id, status_code |
| `llm_embedding` | model, input_count, dim, latency_ms, user_id |
| `llm_orchestrate` | pipeline, steps_count, total_duration, user_id |

### 4.3. Logger

```python
logger = logging.getLogger("uvicorn.error")
# НЕ logging.getLogger("llm-gateway") — у него нет handler
```

---

## 5. Embeddings endpoint

### 5.1. Staged pipeline

1. Parse request (Pydantic)
2. Semantic validation (пустой input, allowlist, dimensions)
3. Normalize (str → list[str])
4. Build upstream payload (Ollama /api/embed)
5. Call Ollama
6. Validate response (embeddings, types, cardinality)
7. Build OpenAI response

### 5.2. Hotfix

`encoding_format` — silent coerce to float вместо reject (400). Gateway всегда возвращает float embeddings. Continue.dev отправляет `encoding_format: "float"` обязательно.

### 5.3. Allowlist

Только модели с capability "embedding" допускаются в /v1/embeddings.

---

## 6. Metrics

### 6.1. Структура

```json
{
  "totals": {"requests": N, "errors": N, "uptime_seconds": N},
  "endpoints": {
    "/v1/chat/completions": {"requests": N, "tokens_total": N, "latency_ms_sum": N, "latency_ms_count": N}
  },
  "models": {
    "gemma4:31b": {"requests": N, "tokens_total": N, "errors": N}
  }
}
```

### 6.2. Характеристики

- Счётчики монотонные, сбрасываются при рестарте
- Thread-safe (threading.Lock)
- Без auth (как /health)

---

## 7. Pipelines (pipelines.yaml)

### 7.1. Текущие 6 pipeline (v33)

| Pipeline | Шаги | Executor model |
|---|---|---|
| plan-execute-review | planner → executor → reviewer | gemma4:31b → qwen3.6 → gemma4:31b |
| execute-review | executor → reviewer | qwen3.6 → gemma4:31b |
| review-only | reviewer | gemma4:31b |
| docs-generate | executor | qwen3-coder:30b (narrow, single-shot) |
| commit-msg | executor | qwen3.5:9b |
| bounded-fix | executor | qwen3.6 |

### 7.2. Формат pipeline step

```yaml
pipelines:
  plan-execute-review:
    steps:
      - name: planner
        model: gemma4:31b
        system_prompt: "You are a software architect..."
        options:
          temperature: 0.4
          num_ctx: 8192
      - name: executor
        model: qwen3.6:35b-a3b-q4_K_M
        system_prompt: "You are a senior developer..."
        options:
          temperature: 0.2
          num_ctx: 8192
```

---

## 8. Зависимости и версии

### 8.1. Python пакеты (gateway venv)

```
fastapi
uvicorn[standard]
httpx
pydantic
openai  # для orchestrator.py
```

### 8.2. Python пакеты (RAG MCP venv)

```
mcp>=1.27.0
chromadb>=1.5.5
# gateway_embeddings wrapper
```

### 8.3. Python пакеты (Docker MCP venv)

```
mcp>=1.27.0
docker>=7.1.0
pyyaml
```
