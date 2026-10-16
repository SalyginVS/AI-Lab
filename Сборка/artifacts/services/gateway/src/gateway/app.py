"""
FastAPI application assembly — LLM Gateway.

Создаёт app, регистрирует middleware и exception handlers,
подключает роутеры из chat, embeddings, listing, metrics.

Этап 14B: auth middleware вынесена в auth.py (per-user tokens).

Логирование: JSON конфигурация применяется uvicorn при старте
через LOGGING_CONFIG из run.py. Здесь не вызываем setup_logging().
"""

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError

from . import VERSION
from .auth import auth_middleware
from .errors import (
    GatewayError,
    gateway_error_handler,
    http_exception_handler,
    validation_error_handler,
)
from .chat import router as chat_router
from .embeddings import router as embeddings_router
from .listing import router as listing_router
from .metrics import router as metrics_router
from .orchestrate import router as orchestrate_router


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="LLM Gateway",
    description="OpenAI-compatible proxy → Ollama (RTX 3090 Lab)",
    version=VERSION,
)

# ---------------------------------------------------------------------------
# Аутентификация middleware (Этап 14B: per-user tokens из auth.py)
# ---------------------------------------------------------------------------

app.middleware("http")(auth_middleware)

# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

app.add_exception_handler(GatewayError, gateway_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)

# ---------------------------------------------------------------------------
# Роутеры
# ---------------------------------------------------------------------------

app.include_router(chat_router)
app.include_router(embeddings_router)
app.include_router(listing_router)
app.include_router(metrics_router)
app.include_router(orchestrate_router)
