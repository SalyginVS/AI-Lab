"""
/v1/models и /health — информационные endpoints LLM Gateway.

/v1/models — OpenAI-compatible список моделей из Ollama.
/health    — статус gateway + Ollama (без аутентификации).

Этап 14B: /health показывает auth_enabled=true (mandatory) и user_count.
"""

import time
from datetime import datetime

import httpx
from fastapi import APIRouter

from . import VERSION, OLLAMA_TAGS_URL, VLLM_MTP_MODELS_URL, VLLM_MTP_MODEL_ID
from .auth import USER_COUNT
from .errors import GatewayError
from .upstream import client
from .orchestrate import get_pipelines_count

router = APIRouter()


async def maybe_get_vllm_mtp_model() -> dict | None:
    """
    Return the validated vLLM MTP model only when the local vLLM endpoint is up.
    This avoids advertising a model that the gateway cannot currently reach.
    """
    try:
        resp = await client.get(
            VLLM_MTP_MODELS_URL,
            timeout=httpx.Timeout(timeout=2.0),
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        for model in data.get("data", []):
            if model.get("id") == VLLM_MTP_MODEL_ID:
                return {
                    "id": VLLM_MTP_MODEL_ID,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "vllm",
                    "permission": [],
                    "root": model.get("root", VLLM_MTP_MODEL_ID),
                    "parent": None,
                }
    except Exception:
        return None
    return None



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

    vllm_model = await maybe_get_vllm_mtp_model()
    if vllm_model is not None:
        openai_models.append(vllm_model)

    return {"object": "list", "data": openai_models}


@router.get("/health")
async def health():
    result = {
        "gateway": "ok",
        "version": VERSION,
        "ollama": "unknown",
        "models_count": 0,
        "pipelines_count": get_pipelines_count(),
        "auth_enabled": True,
        "user_count": USER_COUNT,
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
