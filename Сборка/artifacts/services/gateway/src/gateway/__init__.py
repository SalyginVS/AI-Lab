"""
LLM Gateway — OpenAI-compatible HTTP proxy for Ollama.

Версия: 0.11.0
Пакет: gateway/
Сервер: 192.168.0.128, RTX 3090 24 ГБ VRAM, 62 ГБ RAM.

Этап 14B: Per-user auth (mandatory) + user_id в structured logs (audit trail).
Этап 10B: /metrics endpoint — in-memory счётчики для мониторинга.
Этап 10A: Модуляризация gateway.py в Python-пакет.

  Модули пакета:
    __init__.py      — версия, константы конфигурации
    auth.py          — per-user Bearer token auth (14B)
    logging_config.py — настройка логирования (JSON structured — 10A-2)
    models.py        — Pydantic-модели запросов/ответов
    errors.py        — GatewayError, обработчики исключений
    upstream.py      — httpx-клиент, retry, health check, классификация ошибок
    chat.py          — /v1/chat/completions + helpers (reasoning, tool_calls, SSE)
    embeddings.py    — /v1/embeddings + helpers (validate, normalize, build)
    listing.py       — /v1/models, /health, parse_ollama_timestamp
    metrics.py       — /metrics, in-memory counters (10B)
    app.py           — FastAPI app, middleware, mount routers

  Принцип: gateway остаётся ОДНИМ процессом (один systemd unit, один порт).
  Модуляризация — логическая, не на уровне сервисов.

История (сохранена для контекста):
  Этап 14B: Per-user mandatory auth, user_id audit trail.
  Этап 10B: /metrics endpoint — JSON-счётчики для мониторинга.
  Этап 10A: Structured JSON logging + модуляризация в пакет.
  Этап 9A/9B: /v1/embeddings endpoint, qwen3-embedding.
  Этап 7: tool_calls (function calling) проброс Ollama → OpenAI формат.
  Этап 6: Настоящий стриминг SSE.
  Этап 5: API-контракт и OpenAI SDK совместимость.
  Этап 4: Обработка ошибок, OOM-детекция, retry.
  Этап 3: Валидация, penalties, seed.
  Этап 2: Reasoning policy, Depth-over-Speed.

Требования к серверу Ollama (systemd env):
  OLLAMA_FLASH_ATTENTION=1
  OLLAMA_KV_CACHE_TYPE=q8_0
  OLLAMA_MAX_LOADED_MODELS=2
  GGML_CUDA_NO_GRAPHS=1

Запуск:
  cd ~/llm-gateway && source venv/bin/activate
  python run.py
  # или: uvicorn gateway.app:app --host 0.0.0.0 --port 8000

Аутентификация (mandatory, Этап 14B):
  export LLM_GATEWAY_TOKENS='{"sk-lab-xxx": "vladimir", "sk-lab-yyy": "roadwarrior"}'
"""

import httpx

# ---------------------------------------------------------------------------
# Версия
# ---------------------------------------------------------------------------

VERSION = "0.12.0"

# ---------------------------------------------------------------------------
# Ollama URLs
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_CHAT_URL = f"{OLLAMA_BASE_URL}/api/chat"
OLLAMA_EMBED_URL = f"{OLLAMA_BASE_URL}/api/embed"
OLLAMA_TAGS_URL = f"{OLLAMA_BASE_URL}/api/tags"

# ---------------------------------------------------------------------------
# HTTP-клиент
# ---------------------------------------------------------------------------

HTTPX_TIMEOUT = httpx.Timeout(timeout=3600.0)

# ---------------------------------------------------------------------------
# Лимиты валидации
# ---------------------------------------------------------------------------

DEFAULT_NUM_CTX = 262144
MAX_NUM_CTX = 262144
MAX_TEMPERATURE = 2.0
MAX_PENALTY = 2.0
MIN_PENALTY = -2.0
MAX_REPEAT_PENALTY = 2.0

# ---------------------------------------------------------------------------
# Retry / обработка ошибок (Этап 4)
# ---------------------------------------------------------------------------

RETRY_MAX_ATTEMPTS = 3
RETRY_BACKOFF_BASE = 2.0
RETRY_AFTER_SECONDS = 30

OOM_PATTERNS = (
    "out of memory",
    "oom",
    "cuda out of memory",
    "not enough memory",
    "failed to allocate",
    "memory allocation failed",
    "ggml_cuda_op_mul_mat_cublas",
    "insufficient memory",
)

# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

EMBEDDING_MODEL_ALLOWLIST = {"qwen3-embedding"}

# ---------------------------------------------------------------------------
# vLLM MTP lane: Lorbus/Qwen3.6-27B-int4-AutoRound
# ---------------------------------------------------------------------------

VLLM_MTP_BASE_URL = "http://127.0.0.1:8027"
VLLM_MTP_CHAT_URL = f"{VLLM_MTP_BASE_URL}/v1/chat/completions"
VLLM_MTP_MODELS_URL = f"{VLLM_MTP_BASE_URL}/v1/models"
VLLM_MTP_MODEL_ID = "qwen3.6-27b-lorbus-mtp-triton-ctx4k"
