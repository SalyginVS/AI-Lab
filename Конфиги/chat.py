"""
/v1/chat/completions — OpenAI-compatible chat endpoint.

Включает: reasoning policy, message conversion, payload builder,
tool_calls Ollama→OpenAI, SSE stream generator, response builder.

Structured logging (10A-2):
  Каждый запрос логирует event="llm_completion" с полным набором полей:
  request_id, model, tokens, latency_ms, ttft_ms, tool_calls_count и т.д.
"""

import json
import time
import uuid
from typing import Optional

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from . import OLLAMA_CHAT_URL, DEFAULT_NUM_CTX, MAX_NUM_CTX
from .errors import GatewayError
from .logging_config import logger
from .models import ChatMessage, ChatCompletionRequest
from .upstream import (
    ollama_post_with_retry,
    ollama_stream_with_retry,
    classify_ollama_error,
)

router = APIRouter()


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
                    logger.warning(
                        "REQ tool_call arguments are not valid JSON; "
                        "using empty object for Ollama")
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
                           request_id: str, model: str,
                           start_time: float, client_ip: str):
    """
    Генератор SSE-чанков из Ollama streaming response.

    Этап 7: поддержка tool_calls в stream-чанках.
    Этап 10A-2: structured logging (llm_completion event в конце стрима).

    Ollama отдаёт tool_calls целиком в одном чанке (не потоково).
    Конвертируем в формат OpenAI и пробрасываем через delta.
    finish_reason: "tool_calls" если были tool_calls, иначе "stop".
    """
    yield format_sse_chunk(request_id, model, delta={"role": "assistant"})

    total_thinking_len = 0
    total_content_len = 0
    has_tool_calls = False
    tool_calls_count = 0
    first_token_time: Optional[float] = None

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

            # --- Structured log: llm_completion (stream) ---
            latency_ms = int((time.monotonic() - start_time) * 1000)
            ttft_ms = (int((first_token_time - start_time) * 1000)
                       if first_token_time else None)
            logger.info(
                "REQ %s completed (stream)", request_id,
                extra={
                    "event": "llm_completion",
                    "request_id": request_id,
                    "endpoint": "/v1/chat/completions",
                    "model": model,
                    "stream": True,
                    "reasoning_effort": effort,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": answer_tokens,
                    "total_tokens": prompt_tokens + answer_tokens,
                    "tool_calls_count": tool_calls_count,
                    "finish_reason": finish_reason,
                    "latency_ms": latency_ms,
                    "ttft_ms": ttft_ms,
                    "status_code": 200,
                    "client_ip": client_ip,
                    "error": None,
                },
            )
            break

        msg = chunk.get("message", {})

        # Этап 7: обработка tool_calls в stream-чанках
        ollama_tool_calls = msg.get("tool_calls")
        if ollama_tool_calls:
            has_tool_calls = True
            openai_tool_calls = convert_ollama_tool_calls_to_openai(
                ollama_tool_calls)
            tool_calls_count += len(openai_tool_calls)
            if first_token_time is None:
                first_token_time = time.monotonic()
            yield format_sse_chunk(
                request_id, model,
                delta={"tool_calls": openai_tool_calls})
            logger.debug("REQ %s tool_calls detected: %d call(s)",
                         request_id, len(openai_tool_calls))
            continue

        thinking_piece = msg.get("thinking", "") or ""
        content_piece = msg.get("content", "") or ""

        total_thinking_len += len(thinking_piece)
        total_content_len += len(content_piece)

        if thinking_piece and not content_piece:
            if first_token_time is None:
                first_token_time = time.monotonic()
            if effort in ("medium", "high"):
                yield format_sse_chunk(
                    request_id, model,
                    delta={"reasoning_content": thinking_piece})
            continue

        if content_piece:
            if first_token_time is None:
                first_token_time = time.monotonic()
            yield format_sse_chunk(
                request_id, model, delta={"content": content_piece})


# ---------------------------------------------------------------------------
# Маршрут
# ---------------------------------------------------------------------------


@router.post("/v1/chat/completions")
async def chat_completions(body: ChatCompletionRequest, request: Request):
    start_time = time.monotonic()
    client_ip = request.client.host if request.client else "unknown"

    effort = resolve_effort(body)
    think_enabled = effort != "none"
    request_id = f"ollama-chat-{uuid.uuid4().hex}"
    ollama_payload = build_ollama_payload(body, think_enabled)

    logger.info("REQ %s model=%s stream=%s effort=%s",
                request_id, body.model, body.stream, effort)
    logger.debug("REQ %s options=%s",
                 request_id, ollama_payload.get("options", {}))

    has_openai_penalties = (body.frequency_penalty is not None
                           or body.presence_penalty is not None)
    if body.repeat_penalty is not None and has_openai_penalties:
        logger.warning(
            "REQ %s both repeat_penalty and frequency/presence_penalty set",
            request_id)

    try:
        if body.stream:
            # ------ Этап 6: настоящий стриминг ------
            resp = await ollama_stream_with_retry(
                OLLAMA_CHAT_URL, ollama_payload, request_id)
            return StreamingResponse(
                stream_generator(resp, effort, request_id, body.model,
                                 start_time, client_ip),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache",
                         "X-Accel-Buffering": "no"},
                background=BackgroundTask(resp.aclose))
        else:
            # ------ Non-stream ------
            resp = await ollama_post_with_retry(
                OLLAMA_CHAT_URL, ollama_payload, request_id)
            ollama_data = resp.json()
            result = build_openai_response(ollama_data, effort, request_id)

            # --- Structured log: llm_completion (non-stream) ---
            latency_ms = int((time.monotonic() - start_time) * 1000)
            usage = result.get("usage", {})
            choice = result.get("choices", [{}])[0]
            tc_list = choice.get("message", {}).get("tool_calls")
            logger.info(
                "REQ %s completed", request_id,
                extra={
                    "event": "llm_completion",
                    "request_id": request_id,
                    "endpoint": "/v1/chat/completions",
                    "model": body.model,
                    "stream": False,
                    "reasoning_effort": effort,
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                    "tool_calls_count": len(tc_list) if tc_list else 0,
                    "finish_reason": choice.get("finish_reason", "stop"),
                    "latency_ms": latency_ms,
                    "ttft_ms": None,
                    "status_code": 200,
                    "client_ip": client_ip,
                    "error": None,
                },
            )
            return result

    except httpx.HTTPStatusError as e:
        error_body = {}
        try:
            error_body = e.response.json() if e.response else {}
        except Exception:
            error_body = {"error": str(e)}
        status_code = e.response.status_code if e.response else 502
        latency_ms = int((time.monotonic() - start_time) * 1000)
        logger.info(
            "REQ %s error", request_id,
            extra={
                "event": "llm_completion",
                "request_id": request_id,
                "endpoint": "/v1/chat/completions",
                "model": body.model,
                "stream": body.stream,
                "reasoning_effort": effort,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "tool_calls_count": 0,
                "finish_reason": None,
                "latency_ms": latency_ms,
                "ttft_ms": None,
                "status_code": status_code,
                "client_ip": client_ip,
                "error": error_body.get("error", str(e)),
            },
        )
        raise classify_ollama_error(status_code, error_body, request_id)

    except GatewayError as e:
        latency_ms = int((time.monotonic() - start_time) * 1000)
        logger.info(
            "REQ %s gateway error", request_id,
            extra={
                "event": "llm_completion",
                "request_id": request_id,
                "endpoint": "/v1/chat/completions",
                "model": body.model,
                "stream": body.stream,
                "reasoning_effort": effort,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "tool_calls_count": 0,
                "finish_reason": None,
                "latency_ms": latency_ms,
                "ttft_ms": None,
                "status_code": e.status_code,
                "client_ip": client_ip,
                "error": e.message,
            },
        )
        raise

    except Exception as e:
        latency_ms = int((time.monotonic() - start_time) * 1000)
        logger.exception(
            "REQ %s unexpected error: %s", request_id, e,
            extra={
                "event": "llm_completion",
                "request_id": request_id,
                "endpoint": "/v1/chat/completions",
                "model": body.model,
                "stream": body.stream,
                "reasoning_effort": effort,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "tool_calls_count": 0,
                "finish_reason": None,
                "latency_ms": latency_ms,
                "ttft_ms": None,
                "status_code": 500,
                "client_ip": client_ip,
                "error": f"{type(e).__name__}: {e}",
            },
        )
        raise GatewayError(
            500, f"Internal gateway error: {type(e).__name__}: {e}",
            "server_error", "internal_error")
