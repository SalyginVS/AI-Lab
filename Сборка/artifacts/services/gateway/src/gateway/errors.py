"""
OpenAI-совместимый формат ошибок LLM Gateway (Этап 4).

GatewayError — HTTP-исключение с полями message, error_type, error_code.
Три обработчика: GatewayError, HTTPException, RequestValidationError.
Обработчики регистрируются в app.py через app.add_exception_handler().
"""

from typing import Optional

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import RETRY_AFTER_SECONDS


class GatewayError(HTTPException):
    def __init__(self, status_code: int, message: str,
                 error_type: str = "api_error",
                 error_code: Optional[str] = None):
        super().__init__(status_code=status_code, detail=message)
        self.message = message
        self.error_type = error_type
        self.error_code = error_code or str(status_code)


async def gateway_error_handler(request: Request, exc: GatewayError):
    headers = {}
    if exc.status_code == 503:
        headers["Retry-After"] = str(RETRY_AFTER_SECONDS)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {
            "message": exc.message,
            "type": exc.error_type,
            "code": exc.error_code,
        }},
        headers=headers,
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {
            "message": (exc.detail if isinstance(exc.detail, str)
                        else str(exc.detail)),
            "type": ("invalid_request_error" if exc.status_code == 422
                     else "api_error"),
            "code": str(exc.status_code),
        }},
    )


async def validation_error_handler(request: Request,
                                   exc: RequestValidationError):
    messages = []
    for err in exc.errors():
        loc = " → ".join(str(x) for x in err.get("loc", []))
        messages.append(f"{loc}: {err.get('msg', 'invalid')}")
    return JSONResponse(
        status_code=422,
        content={"error": {
            "message": "; ".join(messages),
            "type": "invalid_request_error",
            "code": "validation_error",
        }},
    )
