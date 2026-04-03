"""
/v1/models и /health — информационные endpoints LLM Gateway.

/v1/models — OpenAI-compatible список моделей из Ollama.
/health    — статус gateway + Ollama (без аутентификации).
"""

import time
from datetime import datetime

import httpx
from fastapi import APIRouter

from . import VERSION, OLLAMA_TAGS_URL, GATEWAY_API_KEY
from .errors import GatewayError
from .upstream import client

router = APIRouter()


# ---------------------------------------------------------------------------
# Утилита: парсинг Ollama timestamp (P6)
# ---------------------------------------------------------------------------


def parse_ollama_timestamp(modified_at: str) -> int:
    """
    ISO datetime из Ollama → Unix timestamp.
    Ollama: "2026-03-15T10:30:00.123456789+03:00" (наносекунды).
    Python datetime max 6 знаков дробной части → обрезаем.
    """
    if not modified_at:
        return int(time.time())
    try:
        s = modified_at
        # Обрезаем дробную часть секунд до 6 знаков
        dot_pos = s.find(".")
        if dot_pos != -1:
            # Найти конец дробной части (до + или - или Z)
            end = dot_pos + 1
            while end < len(s) and s[end].isdigit():
                end += 1
            frac = s[dot_pos + 1:end]
            frac = frac[:6].ljust(6, "0")
            s = s[:dot_pos + 1] + frac + s[end:]
        dt = datetime.fromisoformat(s)
        return int(dt.timestamp())
    except (ValueError, TypeError, OverflowError):
        return int(time.time())


# ---------------------------------------------------------------------------
# Маршруты
# ---------------------------------------------------------------------------


@router.get("/v1/models")
async def list_models():
    """P6: парсинг modified_at вместо time.time()."""
    try:
        resp = await client.get(OLLAMA_TAGS_URL)
        resp.raise_for_status()
        data = resp.json()
    except httpx.RequestError as e:
        raise GatewayError(
            502, f"Cannot connect to Ollama: {type(e).__name__}: {e}",
            "server_error", "ollama_unavailable")
    except httpx.HTTPStatusError as e:
        raise GatewayError(
            502, f"Ollama error fetching models: {e}",
            "server_error", "ollama_error")

    openai_models = []
    for m in data.get("models", []):
        name = m.get("name", "")
        created = parse_ollama_timestamp(m.get("modified_at", ""))
        openai_models.append({
            "id": name,
            "object": "model",
            "created": created,
            "owned_by": "ollama",
            "permission": [],
            "root": name,
            "parent": None,
        })

    return {"object": "list", "data": openai_models}


@router.get("/health")
async def health():
    result = {
        "gateway": "ok",
        "version": VERSION,
        "ollama": "unknown",
        "models_count": 0,
        "auth_enabled": bool(GATEWAY_API_KEY),
        "timestamp": int(time.time()),
    }
    try:
        resp = await client.get(OLLAMA_TAGS_URL)
        resp.raise_for_status()
        data = resp.json()
        result["ollama"] = "ok"
        result["models_count"] = len(data.get("models", []))
    except Exception as e:
        result["ollama"] = f"error: {type(e).__name__}: {e}"
    return result
