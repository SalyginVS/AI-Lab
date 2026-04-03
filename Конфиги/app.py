"""
FastAPI application assembly — LLM Gateway.

Создаёт app, регистрирует middleware и exception handlers,
подключает роутеры из chat, embeddings, listing.

Логирование: JSON конфигурация применяется uvicorn при старте
через LOGGING_CONFIG из run.py. Здесь не вызываем setup_logging().
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import VERSION, GATEWAY_API_KEY
from .errors import (
    GatewayError,
    gateway_error_handler,
    http_exception_handler,
    validation_error_handler,
)
from .chat import router as chat_router
from .embeddings import router as embeddings_router
from .listing import router as listing_router


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="LLM Gateway",
    description="OpenAI-compatible proxy → Ollama (RTX 3090 Lab)",
    version=VERSION,
)

# ---------------------------------------------------------------------------
# Аутентификация middleware (P7)
# ---------------------------------------------------------------------------


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """
    Bearer token проверка, если LLM_GATEWAY_API_KEY задана.
    /health освобождён — для мониторинга без ключа.
    """
    if GATEWAY_API_KEY and request.url.path != "/health":
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"error": {
                    "message": "Missing Authorization header. "
                               "Expected: Bearer <api_key>",
                    "type": "authentication_error",
                    "code": "missing_api_key",
                }},
            )
        token = auth_header[7:]
        if token != GATEWAY_API_KEY:
            return JSONResponse(
                status_code=401,
                content={"error": {
                    "message": "Invalid API key",
                    "type": "authentication_error",
                    "code": "invalid_api_key",
                }},
            )
    return await call_next(request)


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
