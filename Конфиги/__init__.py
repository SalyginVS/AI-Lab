"""
LLM Gateway — OpenAI-compatible HTTP proxy for Ollama.

Версия: 0.9.0
Пакет: gateway/
Сервер: 192.168.0.128, RTX 3090 24 ГБ VRAM, 62 ГБ RAM.

Этап 10A: Модуляризация gateway.py в Python-пакет.

  Монолит gateway.py (1305 строк) разбит на 8 модулей:
    __init__.py      — версия, константы конфигурации
    logging_config.py — настройка логирования (JSON structured — 10A-2)
    models.py        — Pydantic-модели запросов/ответов
    errors.py        — GatewayError, обработчики исключений
    upstream.py      — httpx-клиент, retry, health check, классификация ошибок
    chat.py          — /v1/chat/completions + helpers (reasoning, tool_calls, SSE)
    embeddings.py    — /v1/embeddings + helpers (validate, normalize, build)
    listing.py       — /v1/models, /health, parse_ollama_timestamp
    app.py           — FastAPI app, middleware, mount routers

  Принцип: gateway остаётся ОДНИМ процессом (один systemd unit, один порт).
  Модуляризация — логическая, не на уровне сервисов.

История (сохранена для контекста):
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

Аутентификация (опционально):
  export LLM_GATEWAY_API_KEY="my-secret-key"
"""

import os

import httpx

# ---------------------------------------------------------------------------
# Версия
# ---------------------------------------------------------------------------

VERSION = "0.9.0"

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

HTTPX_TIMEOUT = httpx.Timeout(timeout=600.0)

# ---------------------------------------------------------------------------
# Лимиты валидации
# ---------------------------------------------------------------------------

DEFAULT_NUM_CTX = 8192
MAX_NUM_CTX = 32768
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
# Аутентификация (P7). Пустая строка = без проверки.
# ---------------------------------------------------------------------------

GATEWAY_API_KEY = os.environ.get("LLM_GATEWAY_API_KEY", "")

# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

EMBEDDING_MODEL_ALLOWLIST = {"qwen3-embedding"}
