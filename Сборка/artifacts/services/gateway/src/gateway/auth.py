"""
Per-user Bearer token authentication — LLM Gateway (Этап 14B).

Токены загружаются из env LLM_GATEWAY_TOKENS (JSON: {token: user_id}).
Если env не задана или невалидна — gateway отказывается стартовать.

Формат env:
  LLM_GATEWAY_TOKENS='{"sk-lab-abc123": "vladimir", "sk-lab-def456": "roadwarrior"}'

AUTH_EXEMPT_PATHS — пути, доступные без аутентификации:
  /health  — мониторинг (Этап 5)
  /metrics — observability (Этап 10B)
"""

import json
import logging
import os
import sys

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("uvicorn.error")

# ---------------------------------------------------------------------------
# Пути, освобождённые от проверки Bearer token.
# ---------------------------------------------------------------------------

AUTH_EXEMPT_PATHS = {"/health", "/metrics"}

# ---------------------------------------------------------------------------
# Загрузка токенов при старте (module-level).
# Если env не задана → gateway не стартует (mandatory auth).
# ---------------------------------------------------------------------------

_raw_tokens = os.environ.get("LLM_GATEWAY_TOKENS", "").strip()

if not _raw_tokens:
    print(
        "FATAL: LLM_GATEWAY_TOKENS env var is not set.\n"
        "Gateway requires per-user tokens. Format:\n"
        '  LLM_GATEWAY_TOKENS=\'{"token1": "user1", "token2": "user2"}\'',
        file=sys.stderr,
    )
    sys.exit(1)

try:
    _parsed: dict = json.loads(_raw_tokens)
    if not isinstance(_parsed, dict) or not _parsed:
        raise ValueError("Must be a non-empty JSON object {token: user_id}")
    for k, v in _parsed.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise ValueError(
                f"Both token and user_id must be strings, got: "
                f"{type(k).__name__}, {type(v).__name__}"
            )
        if not k.strip() or not v.strip():
            raise ValueError("Token and user_id must not be empty strings")
except (json.JSONDecodeError, ValueError) as exc:
    print(
        f"FATAL: LLM_GATEWAY_TOKENS is invalid: {exc}\n"
        "Expected JSON: {\"token1\": \"user1\", \"token2\": \"user2\"}",
        file=sys.stderr,
    )
    sys.exit(1)

# Immutable mapping: token → user_id
TOKENS: dict[str, str] = dict(_parsed)
USER_COUNT: int = len(TOKENS)


def _user_ids() -> list[str]:
    """Список зарегистрированных user_id (для /health, логов)."""
    return sorted(set(TOKENS.values()))


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


async def auth_middleware(request: Request, call_next):
    """
    Per-user Bearer token проверка (Этап 14B).

    Логика:
      1. Путь в AUTH_EXEMPT_PATHS → пропускаем без проверки.
      2. Нет Authorization header → 401.
      3. Токен не найден в TOKENS → 401.
      4. Токен валиден → request.state.user_id = user_id, пропускаем.
    """
    if request.url.path in AUTH_EXEMPT_PATHS:
        return await call_next(request)

    auth_header = request.headers.get("authorization", "")

    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "message": "Missing Authorization header. "
                    "Expected: Bearer <api_key>",
                    "type": "authentication_error",
                    "code": "missing_api_key",
                }
            },
        )

    token = auth_header[7:]
    user_id = TOKENS.get(token)

    if user_id is None:
        return JSONResponse(
            status_code=401,
            content={
                "error": {
                    "message": "Invalid API key",
                    "type": "authentication_error",
                    "code": "invalid_api_key",
                }
            },
        )

    # Прикрепляем user_id к request для structured logging
    request.state.user_id = user_id
    return await call_next(request)
