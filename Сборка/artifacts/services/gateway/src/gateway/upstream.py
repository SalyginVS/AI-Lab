"""
Ollama HTTP-клиент LLM Gateway.

Singleton httpx.AsyncClient, retry-обёртки для stream и non-stream,
классификация ошибок Ollama (OOM, 404, 400, 5xx), health check.
"""

import asyncio
from typing import Optional

import httpx

from . import (
    HTTPX_TIMEOUT, OLLAMA_TAGS_URL,
    RETRY_MAX_ATTEMPTS, RETRY_BACKOFF_BASE,
    OOM_PATTERNS,
)
from .errors import GatewayError
from .logging_config import logger


# ---------------------------------------------------------------------------
# HTTP-клиент (singleton)
# ---------------------------------------------------------------------------

client = httpx.AsyncClient(timeout=HTTPX_TIMEOUT)


# ---------------------------------------------------------------------------
# Классификация ошибок (Этап 4)
# ---------------------------------------------------------------------------


def is_oom_error(error_text: str) -> bool:
    lower = error_text.lower()
    return any(p in lower for p in OOM_PATTERNS)


def classify_ollama_error(status_code: int, error_body: dict,
                          request_id: str) -> GatewayError:
    error_msg = error_body.get("error", "")

    if is_oom_error(error_msg):
        logger.error("REQ %s OOM detected: HTTP %d, error=%s",
                     request_id, status_code, error_msg)
        return GatewayError(
            503, f"GPU/RAM out of memory. Try a smaller model or reduce "
                 f"num_ctx. Ollama: {error_msg}",
            "server_error", "oom")

    if status_code == 404:
        logger.warning("REQ %s model not found: %s", request_id, error_msg)
        return GatewayError(
            404, error_msg or "Model not found in Ollama",
            "not_found_error", "model_not_found")

    if status_code == 400:
        logger.warning("REQ %s Ollama bad request: %s",
                       request_id, error_msg)
        return GatewayError(
            400, f"Ollama rejected request: {error_msg}",
            "invalid_request_error", "bad_request")

    if status_code >= 500:
        logger.error("REQ %s Ollama internal error: HTTP %d, error=%s",
                     request_id, status_code, error_msg)
        return GatewayError(
            502, f"Ollama internal error (HTTP {status_code}): {error_msg}",
            "server_error", "ollama_error")

    logger.warning("REQ %s Ollama HTTP %d: %s",
                   request_id, status_code, error_msg)
    return GatewayError(
        status_code, error_msg or f"Ollama returned HTTP {status_code}",
        "api_error", str(status_code))


async def check_ollama_alive() -> bool:
    try:
        resp = await client.get(OLLAMA_TAGS_URL,
                                timeout=httpx.Timeout(timeout=5.0))
        return resp.status_code == 200
    except Exception:
        return False


def build_connection_error(request_id: str, last_error: Exception,
                           ollama_alive: bool) -> GatewayError:
    error_name = type(last_error).__name__
    error_detail = str(last_error) or "(no details)"

    if ollama_alive:
        logger.warning(
            "REQ %s cold start suspected: Ollama alive but chat failed "
            "after %d attempts: %s: %s",
            request_id, RETRY_MAX_ATTEMPTS, error_name, error_detail)
        return GatewayError(
            503, "Model is loading into GPU memory (cold start). "
                 "Please retry shortly.",
            "server_error", "model_loading")
    else:
        logger.error(
            "REQ %s Ollama unreachable after %d attempts: %s: %s",
            request_id, RETRY_MAX_ATTEMPTS, error_name, error_detail)
        return GatewayError(
            502, f"Cannot connect to Ollama after {RETRY_MAX_ATTEMPTS} "
                 f"attempts. Last error: {error_name}: {error_detail}",
            "server_error", "ollama_unavailable")


# ---------------------------------------------------------------------------
# Retry-обёртка для non-stream (Этап 4)
# ---------------------------------------------------------------------------


async def ollama_post_with_retry(url: str, payload: dict,
                                 request_id: str) -> httpx.Response:
    """
    Буферизованный POST для non-stream запросов.
    Читает весь ответ в память — для non-stream это нормально.
    """
    last_error: Optional[Exception] = None
    for attempt in range(RETRY_MAX_ATTEMPTS):
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError:
            raise
        except httpx.RequestError as e:
            last_error = e
            remaining = RETRY_MAX_ATTEMPTS - attempt - 1
            if remaining > 0:
                wait = RETRY_BACKOFF_BASE * (2 ** attempt)
                logger.warning(
                    "REQ %s attempt %d/%d failed: %s: %s — retrying in %.0fs",
                    request_id, attempt + 1, RETRY_MAX_ATTEMPTS,
                    type(e).__name__, str(e) or "(empty)", wait)
                await asyncio.sleep(wait)
            else:
                logger.error(
                    "REQ %s attempt %d/%d failed: %s: %s — no retries left",
                    request_id, attempt + 1, RETRY_MAX_ATTEMPTS,
                    type(e).__name__, str(e) or "(empty)")

    ollama_alive = await check_ollama_alive()
    raise build_connection_error(request_id, last_error, ollama_alive)


# ---------------------------------------------------------------------------
# Retry-обёртка для stream (Этап 6)
# ---------------------------------------------------------------------------


async def ollama_stream_with_retry(url: str, payload: dict,
                                   request_id: str) -> httpx.Response:
    """
    Streaming POST для stream-запросов.

    Использует client.send(req, stream=True) — httpx возвращает response
    сразу после получения HTTP headers, не читая body. Это даёт настоящий
    стриминг: body читается по мере поступления через aiter_lines().

    Retry — только на фазе установления соединения (RequestError).
    При HTTP-ошибке (status != 200): читаем error body, закрываем response,
    классифицируем ошибку через classify_ollama_error().
    При HTTP 200: возвращаем открытый response. Caller ОБЯЗАН закрыть его
    через resp.aclose() (используется BackgroundTask в chat route).
    """
    last_error: Optional[Exception] = None
    for attempt in range(RETRY_MAX_ATTEMPTS):
        try:
            req = client.build_request("POST", url, json=payload)
            resp = await client.send(req, stream=True)

            if resp.status_code != 200:
                # Читаем тело ошибки — response ещё открыт, body не прочитан
                await resp.aread()
                await resp.aclose()
                error_body = {}
                try:
                    error_body = resp.json()
                except Exception:
                    error_body = {"error": resp.text or str(resp.status_code)}
                raise classify_ollama_error(
                    resp.status_code, error_body, request_id)

            # HTTP 200 — возвращаем открытый streaming response
            return resp

        except GatewayError:
            raise
        except httpx.RequestError as e:
            last_error = e
            remaining = RETRY_MAX_ATTEMPTS - attempt - 1
            if remaining > 0:
                wait = RETRY_BACKOFF_BASE * (2 ** attempt)
                logger.warning(
                    "REQ %s stream attempt %d/%d failed: %s: %s "
                    "— retrying in %.0fs",
                    request_id, attempt + 1, RETRY_MAX_ATTEMPTS,
                    type(e).__name__, str(e) or "(empty)", wait)
                await asyncio.sleep(wait)
            else:
                logger.error(
                    "REQ %s stream attempt %d/%d failed: %s: %s "
                    "— no retries left",
                    request_id, attempt + 1, RETRY_MAX_ATTEMPTS,
                    type(e).__name__, str(e) or "(empty)")

    ollama_alive = await check_ollama_alive()
    raise build_connection_error(request_id, last_error, ollama_alive)
