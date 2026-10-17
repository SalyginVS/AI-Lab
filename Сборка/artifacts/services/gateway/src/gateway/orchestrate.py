"""
Gateway orchestrate module — POST /v1/orchestrate, GET /v1/orchestrate/pipelines.

Версия: 0.12.0 (Этап 16)

Sequential multi-model pipeline execution через gateway API.
Enterprise-transferable: единый API-контракт для pipeline execution.

Архитектурный паттерн — self-call:
  Каждый шаг pipeline выполняется через POST /v1/chat/completions
  на localhost:8000 с service token (LLM_ORCHESTRATOR_TOKEN).
  Это обеспечивает прохождение каждого шага через auth, structured
  logging и metrics автоматически — без дублирования кода.

  OpenAI SDK sync вызов обёрнут в asyncio.to_thread() чтобы
  не блокировать uvicorn event loop.

Зависимости в gateway venv:
  pip install pyyaml openai
"""

import asyncio
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Request
from openai import OpenAI

from .errors import GatewayError
from .metrics import collector
from .logging_config import logger

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PIPELINES_PATH = Path(__file__).resolve().parent.parent / "pipelines.yaml"
ORCHESTRATOR_TOKEN = os.environ.get("LLM_ORCHESTRATOR_TOKEN", "")
GATEWAY_SELF_URL = "http://127.0.0.1:8000/v1"

# ---------------------------------------------------------------------------
# Pipeline loading (at module import — once per gateway start)
# ---------------------------------------------------------------------------

_pipelines: dict[str, Any] = {}


def load_pipelines() -> dict[str, Any]:
    """Загружает pipelines.yaml. Поддерживает оба формата: с ключом 'pipelines' и без."""
    if not PIPELINES_PATH.exists():
        logger.warning(
            json.dumps({
                "event": "orchestrate_init",
                "status": "warning",
                "message": f"pipelines.yaml not found at {PIPELINES_PATH}",
            })
        )
        return {}

    with PIPELINES_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if "pipelines" in data and isinstance(data["pipelines"], dict):
        raw = data["pipelines"]
    else:
        raw = data

    logger.info(
        json.dumps({
            "event": "orchestrate_init",
            "status": "ok",
            "pipelines_loaded": len(raw),
            "pipeline_names": list(raw.keys()),
        })
    )
    return raw


def get_pipelines() -> dict[str, Any]:
    """Возвращает загруженные pipeline-конфигурации."""
    return _pipelines


def get_pipelines_count() -> int:
    """Количество загруженных pipelines (для /health)."""
    return len(_pipelines)


# ---------------------------------------------------------------------------
# OpenAI client for self-calls
# ---------------------------------------------------------------------------

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    """Ленивая инициализация OpenAI SDK клиента для self-call."""
    global _client
    if _client is None:
        if not ORCHESTRATOR_TOKEN:
            raise GatewayError(
                500,
                "LLM_ORCHESTRATOR_TOKEN not configured. "
                "Set env var with a valid gateway token for orchestrator self-calls.",
            )
        _client = OpenAI(base_url=GATEWAY_SELF_URL, api_key=ORCHESTRATOR_TOKEN)
    return _client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def strip_think_blocks(text: str) -> str:
    """Удаляет <think>...</think> блоки из текста (Qwen3 reasoning traces).

    Planner-модели (deepseek-r1, qwen3) генерируют reasoning traces
    внутри <think> тегов. Executor не должен видеть этот внутренний
    процесс — ему нужен только чистый план.
    """
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


# ---------------------------------------------------------------------------
# Step execution
# ---------------------------------------------------------------------------

def _run_step_sync(
    step_cfg: dict,
    task: str,
    prev_output: str | None,
) -> tuple[str, float]:
    """Выполняет один шаг pipeline через self-call на gateway.

    Синхронный вызов — запускается в asyncio.to_thread() из async handler.
    Self-call на localhost:8000/v1/chat/completions проходит через auth,
    structured logging и metrics gateway автоматически.

    Args:
        step_cfg: конфигурация шага из pipelines.yaml
        task: исходная задача пользователя (для первого шага / planner)
        prev_output: вывод предыдущего шага (None для первого шага)

    Returns:
        (output_text, duration_seconds)
    """
    client = _get_client()

    model = step_cfg["model"]
    system_prompt = step_cfg.get("system_prompt") or step_cfg.get("system", "")
    num_ctx = step_cfg.get("num_ctx")
    temperature = step_cfg.get("temperature", 0.2)
    max_tokens = step_cfg.get("max_tokens", 4096)

    # Первый шаг или planner → исходный task; остальные → prev_output
    user_content = prev_output if prev_output is not None else task

    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_content})

    start = time.monotonic()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        extra_body={} if num_ctx is None else {"num_ctx": num_ctx},
    )
    duration = time.monotonic() - start

    output = response.choices[0].message.content or ""
    return output.strip(), round(duration, 2)


async def _run_step_async(
    step_cfg: dict,
    task: str,
    prev_output: str | None,
) -> tuple[str, float]:
    """Async обёртка: запуск sync OpenAI SDK вызова в thread pool."""
    return await asyncio.to_thread(_run_step_sync, step_cfg, task, prev_output)


# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------

async def run_pipeline(
    pipeline_name: str,
    pipeline_cfg: dict,
    task: str,
    user_id: str,
) -> dict[str, Any]:
    """Выполняет multi-step pipeline последовательно.

    Каждый шаг pipeline — self-call на gateway /v1/chat/completions.
    Planner output очищается от <think> блоков перед передачей executor.
    Результат каждого шага сохраняет полный output (с <think> если есть).

    Args:
        pipeline_name: имя pipeline из pipelines.yaml
        pipeline_cfg: конфигурация pipeline
        task: исходная задача пользователя
        user_id: кто инициировал pipeline (из auth middleware)

    Returns:
        dict с результатами всех шагов pipeline
    """
    steps_cfg = pipeline_cfg.get("steps", [])
    steps_results: list[dict[str, Any]] = []
    prev_output: str | None = None
    total_start = time.monotonic()

    logger.info(
        json.dumps({
            "event": "llm_orchestrate_start",
            "pipeline": pipeline_name,
            "steps_count": len(steps_cfg),
            "task_length": len(task),
            "user_id": user_id,
        })
    )

    for i, step in enumerate(steps_cfg, start=1):
        step_name = step.get("name", f"step_{i}")
        model = step["model"]

        # Planner всегда получает task; остальные — prev_output
        if prev_output is None or step_name == "planner":
            step_prev = None
        else:
            step_prev = prev_output

        try:
            output, duration = await _run_step_async(step, task, step_prev)
        except GatewayError:
            # GatewayError (например, 500 — no token) пробрасываем as-is
            raise
        except Exception as exc:
            error_msg = (
                f"Pipeline '{pipeline_name}' failed at step {i}/{len(steps_cfg)} "
                f"'{step_name}' ({model}): {exc}"
            )
            logger.error(
                json.dumps({
                    "event": "llm_orchestrate_step_error",
                    "pipeline": pipeline_name,
                    "step": step_name,
                    "step_number": i,
                    "model": model,
                    "error": str(exc),
                    "user_id": user_id,
                })
            )
            # Записываем метрику ошибки
            collector.record({
                "endpoint": "/v1/orchestrate",
                "model": f"pipeline:{pipeline_name}",
                "status_code": 502,
                "latency_ms": int((time.monotonic() - total_start) * 1000),
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "error": True,
            })
            raise GatewayError(502, error_msg)

        # Planner output: strip <think> перед передачей executor
        clean_output = strip_think_blocks(output) if step_name == "planner" else output

        steps_results.append({
            "name": step_name,
            "model": model,
            "duration_sec": duration,
            "output": output,  # полный output (с <think> если есть)
        })

        prev_output = clean_output

    total_duration = round(time.monotonic() - total_start, 2)

    # --- Structured log: pipeline completed ---
    log_data = {
        "event": "llm_orchestrate",
        "pipeline": pipeline_name,
        "steps_count": len(steps_results),
        "total_duration_sec": total_duration,
        "task_length": len(task),
        "user_id": user_id,
        "status_code": 200,
    }
    logger.info(f"PIPELINE {pipeline_name} completed", extra=log_data)

    # --- Metrics ---
    collector.record({
        "endpoint": "/v1/orchestrate",
        "model": f"pipeline:{pipeline_name}",
        "status_code": 200,
        "latency_ms": int(total_duration * 1000),
        "prompt_tokens": 0,  # tokens counted per-step in chat.py self-calls
        "completion_tokens": 0,
        "error": False,
    })

    return {
        "pipeline": pipeline_name,
        "task": task,
        "steps": steps_results,
        "total_duration_sec": total_duration,
        "user_id": user_id,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/v1/orchestrate/pipelines")
async def list_pipelines():
    """Список доступных pipeline-конфигураций.

    Возвращает имя, описание, количество шагов и имена шагов
    для каждого pipeline из pipelines.yaml.
    """
    result = {}
    for name, cfg in _pipelines.items():
        steps = cfg.get("steps", [])
        result[name] = {
            "description": cfg.get("description", ""),
            "steps_count": len(steps),
            "steps": [s.get("name", f"step_{i+1}") for i, s in enumerate(steps)],
        }
    return {"pipelines": result}


@router.post("/v1/orchestrate")
async def orchestrate(body: dict, request: Request):
    """Запуск named pipeline с указанной задачей.

    Body:
        {"pipeline": "plan-execute-review", "task": "Implement a CSV parser..."}

    Returns:
        Structured result с output каждого шага, timing и user_id.

    Errors:
        400 — pipeline не найден или task пуст
        401 — нет/невалидный Bearer token (auth middleware)
        502 — ошибка Ollama на каком-то шаге (с указанием failed step)
    """
    # --- Валидация ---
    pipeline_name = body.get("pipeline", "").strip()
    task = body.get("task", "").strip()
    user_id = getattr(request.state, "user_id", "unknown")

    if not pipeline_name:
        raise GatewayError(400, "Field 'pipeline' is required and must be non-empty.")

    if not task:
        raise GatewayError(400, "Field 'task' is required and must be non-empty.")

    if pipeline_name not in _pipelines:
        available = list(_pipelines.keys())
        raise GatewayError(
            400,
            f"Pipeline '{pipeline_name}' not found. Available: {available}",
        )

    # --- Выполнение ---
    pipeline_cfg = _pipelines[pipeline_name]
    result = await run_pipeline(pipeline_name, pipeline_cfg, task, user_id)
    return result


# ---------------------------------------------------------------------------
# Module init
# ---------------------------------------------------------------------------

_pipelines = load_pipelines()
