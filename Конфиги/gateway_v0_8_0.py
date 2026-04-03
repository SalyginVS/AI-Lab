"""
LLM Gateway — OpenAI-compatible HTTP proxy for Ollama.

Версия: 0.8.0
Дата: 2026-03-28
Сервер: 192.168.0.128, RTX 3090 24 ГБ VRAM, 62 ГБ RAM.

Этап 9A: Поддержка /v1/embeddings.

  Добавлен OpenAI-compatible endpoint POST /v1/embeddings.
  Проксирует запросы к Ollama /api/embed для qwen3-embedding.
  Поддерживает input как строку и batch-массив строк.
  Ответ нормализуется в формат OpenAI Embeddings API.
  Добавлены semantic validation, upstream payload validation
  и защита от mismatch числа векторов.

Этап 7: Поддержка tool_calls (function calling).

  Проблема: Ollama возвращает tool_calls в message.tool_calls,
  но stream_generator() и build_openai_response() обрабатывали
  только content и thinking. Tool_calls терялись — Continue.dev
  Agent mode получал пустой ответ.

  Решение: convert_ollama_tool_calls_to_openai() конвертирует
  формат Ollama (arguments: dict, index внутри function) в формат
  OpenAI (arguments: JSON string, index на верхнем уровне).
  Проброс в stream (delta.tool_calls) и non-stream (message.tool_calls).
  finish_reason: "tool_calls" вместо "stop" при наличии tool_calls.

Этап 6: Настоящий стриминг (без изменений).
Этап 5: API-контракт и совместимость (без изменений).
Этап 4: Обработка ошибок (без изменений).
Этап 3: Валидация, penalties, seed, логирование (без изменений).
Этап 2: Reasoning policy, Depth-over-Speed, stream fixes (без изменений).

Требования к серверу Ollama (systemd env):
  OLLAMA_FLASH_ATTENTION=1
  OLLAMA_KV_CACHE_TYPE=q8_0
  OLLAMA_MAX_LOADED_MODELS=1
  GGML_CUDA_NO_GRAPHS=1

Запуск:
  cd ~/llm-gateway && source venv/bin/activate
  uvicorn gateway:app --host 0.0.0.0 --port 8000

Аутентификация (опционально):
  export LLM_GATEWAY_API_KEY="my-secret-key"
"""

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Literal, Union, Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, ConfigDict
from starlette.background import BackgroundTask

# ---------------------------------------------------------------------------
# Логирование
# ---------------------------------------------------------------------------

logger = logging.getLogger("uvicorn.error")

# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_CHAT_URL = f"{OLLAMA_BASE_URL}/api/chat"
OLLAMA_EMBED_URL = f"{OLLAMA_BASE_URL}/api/embed"
OLLAMA_TAGS_URL = f"{OLLAMA_BASE_URL}/api/tags"

HTTPX_TIMEOUT = httpx.Timeout(timeout=600.0)
DEFAULT_NUM_CTX = 8192
MAX_NUM_CTX = 32768
MAX_TEMPERATURE = 2.0
MAX_PENALTY = 2.0
MIN_PENALTY = -2.0
MAX_REPEAT_PENALTY = 2.0

# Обработка ошибок (Этап 4)
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

# Аутентификация (P7). Пустая строка = без проверки.
GATEWAY_API_KEY = os.environ.get("LLM_GATEWAY_API_KEY", "")

# ---------------------------------------------------------------------------
# HTTP-клиент (singleton)
# ---------------------------------------------------------------------------

client = httpx.AsyncClient(timeout=HTTPX_TIMEOUT)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="LLM Gateway",
    description="OpenAI-compatible proxy → Ollama (RTX 3090 Lab)",
    version="0.8.0",
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
# OpenAI-совместимый формат ошибок (Этап 4)
# ---------------------------------------------------------------------------


class GatewayError(HTTPException):
    def __init__(self, status_code: int, message: str,
                 error_type: str = "api_error",
                 error_code: Optional[str] = None):
        super().__init__(status_code=status_code, detail=message)
        self.message = message
        self.error_type = error_type
        self.error_code = error_code or str(status_code)


@app.exception_handler(GatewayError)
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


@app.exception_handler(HTTPException)
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


@app.exception_handler(RequestValidationError)
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


# ---------------------------------------------------------------------------
# Pydantic-модели запроса (P2, P3)
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    """
    Сообщение чата. extra="ignore" — неизвестные поля молча отбрасываются.
    content: str | list (multimodal vision) | None (tool_calls msg).
    """
    model_config = ConfigDict(extra="ignore")

    role: str
    content: Union[str, list, None] = None
    name: Optional[str] = None
    tool_calls: Optional[list] = None
    tool_call_id: Optional[str] = None


class ReasoningConfig(BaseModel):
    effort: Literal["none", "low", "medium", "high"] = "none"


class ChatCompletionRequest(BaseModel):
    """extra="ignore" — неизвестные параметры от клиента молча игнорируются."""
    model_config = ConfigDict(extra="ignore")

    model: str
    messages: list[ChatMessage]
    stream: bool = False

    temperature: Optional[float] = Field(
        default=None, ge=0.0, le=MAX_TEMPERATURE)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    frequency_penalty: Optional[float] = Field(
        default=None, ge=MIN_PENALTY, le=MAX_PENALTY)
    presence_penalty: Optional[float] = Field(
        default=None, ge=MIN_PENALTY, le=MAX_PENALTY)
    seed: Optional[int] = Field(default=None, ge=0)

    # P3: stop, tools, tool_choice
    stop: Union[str, list, None] = Field(default=None)
    tools: Optional[list] = Field(default=None)
    tool_choice: Union[str, dict, None] = Field(default=None)

    # Reasoning (Этап 2)
    reasoning: Optional[ReasoningConfig] = None
    reasoning_effort: Optional[str] = None

    # Depth-over-Speed (Этап 2)
    num_ctx: Optional[int] = Field(default=None, ge=1, le=MAX_NUM_CTX)
    num_gpu: Optional[int] = Field(default=None, ge=0)
    num_batch: Optional[int] = Field(default=None, ge=1)

    # Ollama-native (Этап 3)
    repeat_penalty: Optional[float] = Field(
        default=None, ge=0.0, le=MAX_REPEAT_PENALTY)
    repeat_last_n: Optional[int] = Field(default=None, ge=-1)





class EmbeddingsRequest(BaseModel):
    """OpenAI-compatible embeddings request."""
    model_config = ConfigDict(extra="ignore")

    model: str
    input: Union[str, list[str]]
    encoding_format: Optional[str] = None
    dimensions: Optional[int] = Field(default=None, ge=1)
    user: Optional[str] = None


class EmbeddingItem(BaseModel):
    object: str = "embedding"
    embedding: list[float]
    index: int


class EmbeddingsUsage(BaseModel):
    prompt_tokens: int
    total_tokens: int


class EmbeddingsResponse(BaseModel):
    object: str = "list"
    data: list[EmbeddingItem]
    model: str
    usage: EmbeddingsUsage


@dataclass
class NormalizedEmbeddingsInput:
    model: str
    inputs: list[str]
    dimensions: Optional[int]
    user: Optional[str]


@dataclass
class OllamaEmbedRequest:
    model: str
    input: list[str]
    dimensions: Optional[int] = None


@dataclass
class ValidatedOllamaEmbedResult:
    model: str
    embeddings: list[list[float]]
    prompt_eval_count: int


EMBEDDING_MODEL_ALLOWLIST = {"qwen3-embedding"}

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
# Retry-обёртка для non-stream (Этап 4, без изменений)
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
    через resp.aclose() (используется BackgroundTask в chat_completions).
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


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------


def resolve_effort(request: ChatCompletionRequest) -> str:
    if request.reasoning and request.reasoning.effort:
        return request.reasoning.effort
    if request.reasoning_effort:
        raw = request.reasoning_effort.lower().strip()
        if raw in ("none", "low", "medium", "high"):
            return raw
    return "none"


def convert_message_for_ollama(msg: ChatMessage) -> dict:
    """
    Конвертер OpenAI message → Ollama /api/chat message.

    content str → as-is.
    content None → "" (Ollama не принимает null).
    content list → multimodal: text → content, image_url → images[].
    """
    ollama_msg: dict = {"role": msg.role}
    images: list[str] = []

    if msg.content is None:
        ollama_msg["content"] = ""
    elif isinstance(msg.content, str):
        ollama_msg["content"] = msg.content
    elif isinstance(msg.content, list):
        text_parts: list[str] = []
        for block in msg.content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            if btype == "text":
                text_parts.append(block.get("text", ""))
            elif btype == "image_url":
                url_obj = block.get("image_url", {})
                url = (url_obj.get("url", "")
                       if isinstance(url_obj, dict) else "")
                if url.startswith("data:"):
                    comma = url.find(",")
                    if comma != -1:
                        images.append(url[comma + 1:])
                elif url:
                    images.append(url)
        ollama_msg["content"] = "\n".join(text_parts)
    else:
        ollama_msg["content"] = str(msg.content)

    if images:
        ollama_msg["images"] = images
    if msg.name is not None:
        ollama_msg["name"] = msg.name
    if msg.tool_calls is not None:
        normalized_tool_calls: list[dict] = []
        for tc in msg.tool_calls:
            if not isinstance(tc, dict):
                continue

            func = tc.get("function")
            if not isinstance(func, dict):
                continue

            func_out = dict(func)

            if "index" in tc and "index" not in func_out:
                func_out["index"] = tc["index"]

            args = func_out.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    logger.warning("REQ tool_call arguments are not valid JSON; using empty object for Ollama")
                    args = {}
            elif args is None:
                args = {}
            elif not isinstance(args, dict):
                try:
                    args = dict(args)
                except Exception:
                    args = {}

            func_out["arguments"] = args
            normalized_tool_calls.append({
                "type": tc.get("type", "function"),
                "function": func_out,
            })

        ollama_msg["tool_calls"] = normalized_tool_calls
    if msg.tool_call_id is not None:
        ollama_msg["tool_call_id"] = msg.tool_call_id

    return ollama_msg


def build_ollama_payload(request: ChatCompletionRequest,
                         think_enabled: bool) -> dict:
    messages = [convert_message_for_ollama(m) for m in request.messages]
    options: dict = {}

    if request.temperature is not None:
        options["temperature"] = request.temperature
    if request.max_tokens is not None:
        options["num_predict"] = request.max_tokens
    if request.top_p is not None:
        options["top_p"] = request.top_p
    if request.frequency_penalty is not None:
        options["frequency_penalty"] = request.frequency_penalty
    if request.presence_penalty is not None:
        options["presence_penalty"] = request.presence_penalty
    if request.seed is not None:
        options["seed"] = request.seed

    if request.stop is not None:
        if isinstance(request.stop, str):
            options["stop"] = [request.stop]
        elif isinstance(request.stop, list):
            options["stop"] = request.stop

    if request.repeat_penalty is not None:
        options["repeat_penalty"] = request.repeat_penalty
    if request.repeat_last_n is not None:
        options["repeat_last_n"] = request.repeat_last_n

    num_ctx = request.num_ctx if request.num_ctx is not None else DEFAULT_NUM_CTX
    options["num_ctx"] = min(num_ctx, MAX_NUM_CTX)

    if request.num_gpu is not None:
        options["num_gpu"] = request.num_gpu
    if request.num_batch is not None:
        options["num_batch"] = request.num_batch

    payload = {
        "model": request.model,
        "messages": messages,
        "stream": request.stream,
        "think": think_enabled,
        "options": options,
    }

    if request.tools is not None:
        payload["tools"] = request.tools
    if request.tool_choice is not None:
        payload["tool_choice"] = request.tool_choice

    return payload


def extract_content_and_reasoning(ollama_message: dict,
                                  effort: str) -> tuple[str, Optional[str]]:
    content = ollama_message.get("content", "") or ""
    thinking = ollama_message.get("thinking", "") or ""

    if not content.strip() and thinking.strip():
        content = thinking
        thinking = ""

    reasoning_content = None
    if effort in ("medium", "high") and thinking.strip():
        reasoning_content = thinking

    return content, reasoning_content


def estimate_token_split(ollama_resp: dict) -> tuple[int, int, int]:
    """Returns (prompt_tokens, answer_tokens, reasoning_tokens)."""
    prompt_tokens = ollama_resp.get("prompt_eval_count", 0) or 0
    total_eval = ollama_resp.get("eval_count", 0) or 0

    msg = ollama_resp.get("message", {})
    thinking_text = msg.get("thinking", "") or ""
    content_text = msg.get("content", "") or ""
    total_len = len(thinking_text) + len(content_text)

    if total_len > 0 and thinking_text:
        reasoning_tokens = int(total_eval * len(thinking_text) / total_len)
        answer_tokens = total_eval - reasoning_tokens
    else:
        reasoning_tokens = 0
        answer_tokens = total_eval

    return prompt_tokens, answer_tokens, reasoning_tokens


# ---------------------------------------------------------------------------
# Tool calls: Ollama → OpenAI формат (Этап 7)
# ---------------------------------------------------------------------------


def convert_ollama_tool_calls_to_openai(
        ollama_tool_calls: list) -> list[dict]:
    """
    Конвертирует tool_calls из формата Ollama в формат OpenAI.

    Ollama формат:
    {
      "id": "call_abc123",
      "function": {
        "index": 0,
        "name": "run_terminal_command",
        "arguments": {"command": "ls -R"}     ← dict
      }
    }

    OpenAI формат:
    {
      "index": 0,
      "id": "call_abc123",
      "type": "function",
      "function": {
        "name": "run_terminal_command",
        "arguments": "{\"command\": \"ls -R\"}"  ← JSON string
      }
    }

    Различия:
    - index перемещается из function на верхний уровень
    - type: "function" добавляется на верхний уровень
    - arguments конвертируется из dict в JSON string
    - Если id отсутствует — генерируем
    """
    openai_calls = []
    for i, tc in enumerate(ollama_tool_calls):
        if not isinstance(tc, dict):
            continue

        func = tc.get("function", {})
        if not isinstance(func, dict):
            continue

        # arguments: dict → JSON string
        args = func.get("arguments", {})
        if isinstance(args, dict):
            args_str = json.dumps(args, ensure_ascii=False)
        elif isinstance(args, str):
            args_str = args
        else:
            args_str = json.dumps(args, ensure_ascii=False)

        # index: из function или порядковый
        index = func.get("index", i)

        # id: из Ollama или генерируем
        call_id = tc.get("id", f"call_{uuid.uuid4().hex[:8]}")

        openai_calls.append({
            "index": index,
            "id": call_id,
            "type": "function",
            "function": {
                "name": func.get("name", ""),
                "arguments": args_str,
            },
        })

    return openai_calls




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
# Построение OpenAI-ответов
# ---------------------------------------------------------------------------


def build_openai_response(ollama_resp: dict, effort: str,
                          request_id: str) -> dict:
    """
    Non-stream OpenAI response.
    Этап 7: поддержка tool_calls в message и finish_reason.
    """
    msg = ollama_resp.get("message", {})
    content, reasoning_content = extract_content_and_reasoning(msg, effort)
    prompt_tokens, answer_tokens, reasoning_tokens = estimate_token_split(
        ollama_resp)

    # Определяем наличие tool_calls
    ollama_tool_calls = msg.get("tool_calls")
    has_tool_calls = bool(ollama_tool_calls)

    message_payload: dict = {"role": "assistant", "content": content}
    if reasoning_content is not None:
        message_payload["reasoning_content"] = reasoning_content

    # Этап 7: добавляем tool_calls в message
    if has_tool_calls:
        message_payload["tool_calls"] = convert_ollama_tool_calls_to_openai(
            ollama_tool_calls)
        # OpenAI: content может быть null при tool_calls
        if not content.strip():
            message_payload["content"] = None

    finish_reason = "tool_calls" if has_tool_calls else "stop"

    return {
        "id": request_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": ollama_resp.get("model", ""),
        "system_fingerprint": None,
        "service_tier": None,
        "choices": [{
            "index": 0,
            "message": message_payload,
            "finish_reason": finish_reason,
        }],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": answer_tokens,
            "total_tokens": prompt_tokens + answer_tokens,
            "completion_tokens_details": {
                "reasoning_tokens": reasoning_tokens,
            },
        },
    }


def format_sse_chunk(request_id: str, model: str, delta: dict,
                     finish_reason: Optional[str] = None,
                     usage: Optional[dict] = None) -> str:
    """P1/P5: system_fingerprint и service_tier в каждом чанке."""
    chunk: dict = {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "system_fingerprint": None,
        "service_tier": None,
        "choices": [{
            "index": 0,
            "delta": delta,
            "finish_reason": finish_reason,
        }],
    }
    if usage is not None:
        chunk["usage"] = usage
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"


async def stream_generator(resp: httpx.Response, effort: str,
                           request_id: str, model: str):
    """
    Генератор SSE-чанков из Ollama streaming response.
    Этап 7: поддержка tool_calls в stream-чанках.

    Ollama отдаёт tool_calls целиком в одном чанке (не потоково).
    Конвертируем в формат OpenAI и пробрасываем через delta.
    finish_reason: "tool_calls" если были tool_calls, иначе "stop".
    """
    yield format_sse_chunk(request_id, model, delta={"role": "assistant"})

    total_thinking_len = 0
    total_content_len = 0
    has_tool_calls = False

    async for line in resp.aiter_lines():
        line = line.strip()
        if not line:
            continue
        try:
            chunk = json.loads(line)
        except json.JSONDecodeError:
            continue

        if chunk.get("done", False):
            prompt_tokens = chunk.get("prompt_eval_count", 0) or 0
            eval_count = chunk.get("eval_count", 0) or 0

            total_len = total_thinking_len + total_content_len
            if total_len > 0 and total_thinking_len > 0:
                reasoning_tokens = int(
                    eval_count * total_thinking_len / total_len)
                answer_tokens = eval_count - reasoning_tokens
            else:
                reasoning_tokens = 0
                answer_tokens = eval_count

            usage = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": answer_tokens,
                "total_tokens": prompt_tokens + answer_tokens,
                "completion_tokens_details": {
                    "reasoning_tokens": reasoning_tokens,
                },
            }
            finish_reason = "tool_calls" if has_tool_calls else "stop"
            yield format_sse_chunk(request_id, model, delta={},
                                   finish_reason=finish_reason, usage=usage)
            yield "data: [DONE]\n\n"
            break

        msg = chunk.get("message", {})

        # Этап 7: обработка tool_calls в stream-чанках
        ollama_tool_calls = msg.get("tool_calls")
        if ollama_tool_calls:
            has_tool_calls = True
            openai_tool_calls = convert_ollama_tool_calls_to_openai(
                ollama_tool_calls)
            yield format_sse_chunk(
                request_id, model,
                delta={"tool_calls": openai_tool_calls})
            logger.info("REQ %s tool_calls detected: %d call(s)",
                        request_id, len(openai_tool_calls))
            continue

        thinking_piece = msg.get("thinking", "") or ""
        content_piece = msg.get("content", "") or ""

        total_thinking_len += len(thinking_piece)
        total_content_len += len(content_piece)

        if thinking_piece and not content_piece:
            if effort in ("medium", "high"):
                yield format_sse_chunk(
                    request_id, model,
                    delta={"reasoning_content": thinking_piece})
            continue

        if content_piece:
            yield format_sse_chunk(
                request_id, model, delta={"content": content_piece})


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


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    effort = resolve_effort(request)
    think_enabled = effort != "none"
    request_id = f"ollama-chat-{uuid.uuid4().hex}"
    ollama_payload = build_ollama_payload(request, think_enabled)

    logger.info("REQ %s model=%s stream=%s effort=%s",
                request_id, request.model, request.stream, effort)
    logger.debug("REQ %s options=%s",
                 request_id, ollama_payload.get("options", {}))

    has_openai_penalties = (request.frequency_penalty is not None
                           or request.presence_penalty is not None)
    if request.repeat_penalty is not None and has_openai_penalties:
        logger.warning(
            "REQ %s both repeat_penalty and frequency/presence_penalty set",
            request_id)

    try:
        if request.stream:
            # ------ Этап 6: настоящий стриминг ------
            resp = await ollama_stream_with_retry(
                OLLAMA_CHAT_URL, ollama_payload, request_id)
            return StreamingResponse(
                stream_generator(resp, effort, request_id, request.model),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache",
                         "X-Accel-Buffering": "no"},
                background=BackgroundTask(resp.aclose))
        else:
            # ------ Non-stream: без изменений ------
            resp = await ollama_post_with_retry(
                OLLAMA_CHAT_URL, ollama_payload, request_id)
            ollama_data = resp.json()
            return build_openai_response(ollama_data, effort, request_id)

    except httpx.HTTPStatusError as e:
        error_body = {}
        try:
            error_body = e.response.json() if e.response else {}
        except Exception:
            error_body = {"error": str(e)}
        status_code = e.response.status_code if e.response else 502
        raise classify_ollama_error(status_code, error_body, request_id)

    except GatewayError:
        raise

    except Exception as e:
        logger.exception("REQ %s unexpected error: %s", request_id, e)
        raise GatewayError(
            500, f"Internal gateway error: {type(e).__name__}: {e}",
            "server_error", "internal_error")



@app.post("/v1/embeddings", response_model=EmbeddingsResponse)
async def create_embeddings(request: EmbeddingsRequest):
    request_id = f"ollama-embed-{uuid.uuid4().hex}"
    logger.info("REQ %s model=%s embeddings", request_id, request.model)

    try:
        validate_embeddings_request_semantics(request)
        normalized = normalize_embeddings_input(request)
        ollama_payload = build_ollama_embed_request(normalized)
        raw_ollama_response = await call_ollama_embed(ollama_payload, request_id)
        validated_result = validate_ollama_embed_response(
            raw_ollama_response,
            expected_count=len(normalized.inputs),
        )
        return build_openai_embeddings_response(
            validated_result,
            fallback_model=normalized.model,
        )

    except GatewayError:
        raise

    except Exception as e:
        logger.exception("REQ %s unexpected embeddings error: %s", request_id, e)
        raise GatewayError(
            500, f"Internal gateway error: {type(e).__name__}: {e}",
            "server_error", "internal_error")




@app.get("/v1/models")
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


@app.get("/health")
async def health():
    result = {
        "gateway": "ok",
        "version": "0.8.0",
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
