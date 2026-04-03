"""
/v1/embeddings — OpenAI-compatible embeddings endpoint (Этап 9A).

Проксирует запросы к Ollama /api/embed для моделей из ALLOWLIST.
Поддерживает input как строку и batch-массив строк.

Structured logging (10A-2):
  Каждый запрос логирует event="llm_embedding" с полями:
  request_id, model, input_count, embedding_dim, latency_ms и т.д.
"""

import time
import uuid
from typing import Any

from fastapi import APIRouter, Request

from . import OLLAMA_EMBED_URL, EMBEDDING_MODEL_ALLOWLIST
from .errors import GatewayError
from .logging_config import logger
from .models import (
    EmbeddingsRequest,
    EmbeddingsResponse,
    EmbeddingItem,
    EmbeddingsUsage,
    NormalizedEmbeddingsInput,
    OllamaEmbedRequest,
    ValidatedOllamaEmbedResult,
)
from .upstream import ollama_post_with_retry, classify_ollama_error

import httpx

router = APIRouter()


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------


def validate_embeddings_request_semantics(req: EmbeddingsRequest) -> None:
    if req.model not in EMBEDDING_MODEL_ALLOWLIST:
        allowed = ", ".join(sorted(EMBEDDING_MODEL_ALLOWLIST))
        raise GatewayError(
            400,
            f"Model '{req.model}' is not allowed for embeddings. Allowed: {allowed}",
            "invalid_request_error",
            "unsupported_embedding_model",
        )

    if req.encoding_format is not None and req.encoding_format != "float":
        raise GatewayError(
            400,
            "Only encoding_format='float' is supported",
            "invalid_request_error",
            "unsupported_encoding_format",
        )

    if isinstance(req.input, str):
        if not req.input.strip():
            raise GatewayError(
                400,
                "Input must not be empty",
                "invalid_request_error",
                "empty_input",
            )
        return

    if not req.input:
        raise GatewayError(
            400,
            "Input list must not be empty",
            "invalid_request_error",
            "empty_input",
        )

    for idx, item in enumerate(req.input):
        if not item.strip():
            raise GatewayError(
                400,
                f"Input item at index {idx} must not be empty",
                "invalid_request_error",
                "empty_input",
            )


def normalize_embeddings_input(req: EmbeddingsRequest) -> NormalizedEmbeddingsInput:
    normalized_inputs = [req.input] if isinstance(req.input, str) else list(req.input)
    return NormalizedEmbeddingsInput(
        model=req.model,
        inputs=normalized_inputs,
        dimensions=req.dimensions,
        user=req.user,
    )


def build_ollama_embed_request(
    normalized: NormalizedEmbeddingsInput,
) -> OllamaEmbedRequest:
    return OllamaEmbedRequest(
        model=normalized.model,
        input=normalized.inputs,
        dimensions=normalized.dimensions,
    )


async def call_ollama_embed(
    payload: OllamaEmbedRequest,
    request_id: str,
) -> dict:
    body: dict[str, Any] = {
        "model": payload.model,
        "input": payload.input,
    }
    if payload.dimensions is not None:
        body["dimensions"] = payload.dimensions

    try:
        resp = await ollama_post_with_retry(OLLAMA_EMBED_URL, body, request_id)
    except httpx.HTTPStatusError as e:
        error_body = {}
        try:
            error_body = e.response.json() if e.response else {}
        except Exception:
            error_body = {"error": str(e)}
        status_code = e.response.status_code if e.response else 502
        raise classify_ollama_error(status_code, error_body, request_id)

    try:
        return resp.json()
    except ValueError:
        logger.error("REQ %s Ollama /api/embed returned invalid JSON", request_id)
        raise GatewayError(
            502,
            "Ollama returned invalid JSON for /api/embed",
            "server_error",
            "invalid_upstream_json",
        )


def validate_ollama_embed_response(
    raw: dict,
    expected_count: int,
) -> ValidatedOllamaEmbedResult:
    embeddings = raw.get("embeddings")
    if not isinstance(embeddings, list):
        raise GatewayError(
            502,
            "Ollama response missing 'embeddings'",
            "server_error",
            "invalid_upstream_payload",
        )

    if len(embeddings) != expected_count:
        raise GatewayError(
            502,
            "Ollama response embedding count does not match input count",
            "server_error",
            "embedding_count_mismatch",
        )

    validated_vectors: list[list[float]] = []
    for vector in embeddings:
        if not isinstance(vector, list):
            raise GatewayError(
                502,
                "Invalid embedding vector shape from Ollama",
                "server_error",
                "invalid_embedding_shape",
            )
        normalized_vector: list[float] = []
        for value in vector:
            if not isinstance(value, (int, float)):
                raise GatewayError(
                    502,
                    "Invalid embedding vector value from Ollama",
                    "server_error",
                    "invalid_embedding_value",
                )
            normalized_vector.append(float(value))
        validated_vectors.append(normalized_vector)

    model = raw.get("model")
    if not isinstance(model, str) or not model.strip():
        model = ""

    prompt_eval_count = raw.get("prompt_eval_count", 0)
    if not isinstance(prompt_eval_count, int) or prompt_eval_count < 0:
        prompt_eval_count = 0

    return ValidatedOllamaEmbedResult(
        model=model,
        embeddings=validated_vectors,
        prompt_eval_count=prompt_eval_count,
    )


def build_openai_embeddings_response(
    result: ValidatedOllamaEmbedResult,
    fallback_model: str,
) -> EmbeddingsResponse:
    data = [
        EmbeddingItem(
            embedding=vector,
            index=idx,
        )
        for idx, vector in enumerate(result.embeddings)
    ]
    model_name = result.model or fallback_model
    usage = EmbeddingsUsage(
        prompt_tokens=result.prompt_eval_count,
        total_tokens=result.prompt_eval_count,
    )
    return EmbeddingsResponse(
        data=data,
        model=model_name,
        usage=usage,
    )


# ---------------------------------------------------------------------------
# Маршрут
# ---------------------------------------------------------------------------


@router.post("/v1/embeddings", response_model=EmbeddingsResponse)
async def create_embeddings(body: EmbeddingsRequest, request: Request):
    start_time = time.monotonic()
    client_ip = request.client.host if request.client else "unknown"
    request_id = f"ollama-embed-{uuid.uuid4().hex}"

    logger.info("REQ %s model=%s embeddings", request_id, body.model)

    try:
        validate_embeddings_request_semantics(body)
        normalized = normalize_embeddings_input(body)
        ollama_payload = build_ollama_embed_request(normalized)
        raw_ollama_response = await call_ollama_embed(ollama_payload, request_id)
        validated_result = validate_ollama_embed_response(
            raw_ollama_response,
            expected_count=len(normalized.inputs),
        )
        response = build_openai_embeddings_response(
            validated_result,
            fallback_model=normalized.model,
        )

        # --- Structured log: llm_embedding ---
        embedding_dim = (len(validated_result.embeddings[0])
                         if validated_result.embeddings else 0)
        latency_ms = int((time.monotonic() - start_time) * 1000)
        logger.info(
            "REQ %s completed", request_id,
            extra={
                "event": "llm_embedding",
                "request_id": request_id,
                "endpoint": "/v1/embeddings",
                "model": body.model,
                "input_count": len(normalized.inputs),
                "embedding_dim": embedding_dim,
                "prompt_tokens": validated_result.prompt_eval_count,
                "latency_ms": latency_ms,
                "status_code": 200,
                "client_ip": client_ip,
                "error": None,
            },
        )
        return response

    except GatewayError as e:
        latency_ms = int((time.monotonic() - start_time) * 1000)
        logger.info(
            "REQ %s error", request_id,
            extra={
                "event": "llm_embedding",
                "request_id": request_id,
                "endpoint": "/v1/embeddings",
                "model": body.model,
                "input_count": 0,
                "embedding_dim": 0,
                "prompt_tokens": 0,
                "latency_ms": latency_ms,
                "status_code": e.status_code,
                "client_ip": client_ip,
                "error": e.message,
            },
        )
        raise

    except Exception as e:
        latency_ms = int((time.monotonic() - start_time) * 1000)
        logger.exception(
            "REQ %s unexpected embeddings error: %s", request_id, e,
            extra={
                "event": "llm_embedding",
                "request_id": request_id,
                "endpoint": "/v1/embeddings",
                "model": body.model,
                "input_count": 0,
                "embedding_dim": 0,
                "prompt_tokens": 0,
                "latency_ms": latency_ms,
                "status_code": 500,
                "client_ip": client_ip,
                "error": f"{type(e).__name__}: {e}",
            },
        )
        raise GatewayError(
            500, f"Internal gateway error: {type(e).__name__}: {e}",
            "server_error", "internal_error")
