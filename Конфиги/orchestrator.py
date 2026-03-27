"""
LLM Orchestrator — Sequential multi-model pipeline runner.

Версия: 1.1.0
Дата: 2026-03-27
Сервер: 192.168.0.128, RTX 3090 24 ГБ VRAM, 62 ГБ RAM.

Этап 8D: + флаг --stdout для headless shell-интеграции.
           Исправлен load_pipelines() под схему pipelines.yaml (ключ "pipelines").

Этап 8C: реализация sequential multi-model pipeline.
  Паттерн: Planner → Executor → Reviewer.
  CLI: --list, --pipeline, --task.
  Сохранение результатов: ~/llm-gateway/results/YYYYMMDD_HHMMSS.json.

Зависимости:
  pip install openai pyyaml
  Запуск: ~/llm-gateway/venv/bin/python orchestrator.py ...

Окружение:
  LLM_GATEWAY_API_KEY — Bearer token шлюза (по умолчанию "dev-token").
  Gateway: http://127.0.0.1:8000/v1 (OpenAI-совместимый API).
"""

import argparse
import json
import os
import re
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import yaml
from openai import OpenAI

# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------

GATEWAY_BASE_URL = "http://127.0.0.1:8000/v1"
GATEWAY_API_KEY = os.environ.get("LLM_GATEWAY_API_KEY", "dev-token")

ROOT_DIR = Path(__file__).resolve().parent
PIPELINES_PATH = ROOT_DIR / "pipelines.yaml"
RESULTS_DIR = ROOT_DIR / "results"

# ---------------------------------------------------------------------------
# Клиент
# ---------------------------------------------------------------------------

client = OpenAI(base_url=GATEWAY_BASE_URL, api_key=GATEWAY_API_KEY)


# ---------------------------------------------------------------------------
# Загрузка pipeline-конфигурации
# ---------------------------------------------------------------------------

def load_pipelines() -> dict:
    """Загружает pipelines.yaml и возвращает словарь pipeline-конфигураций."""
    if not PIPELINES_PATH.exists():
        raise FileNotFoundError(f"pipelines.yaml not found at {PIPELINES_PATH}")
    with PIPELINES_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    # Поддержка обоих форматов: с ключом "pipelines" и без
    if "pipelines" in data and isinstance(data["pipelines"], dict):
        return data["pipelines"]
    return data


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def strip_think_blocks(text: str) -> str:
    """Удаляет <think>...</think> блоки из текста (Qwen3 reasoning)."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def get_last_step_text(results: dict) -> str:
    """Извлекает текст последнего шага pipeline из results."""
    steps = results.get("steps", [])
    if not steps:
        return ""
    last = steps[-1]
    return last.get("output", "")


def save_results(results: dict) -> Path:
    """Сохраняет результаты pipeline в JSON-файл с timestamp."""
    RESULTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = RESULTS_DIR / f"{ts}.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return out_path


# ---------------------------------------------------------------------------
# Выполнение pipeline
# ---------------------------------------------------------------------------

def run_step(step: dict, task: str, prev_output: str | None = None) -> tuple[str, float]:
    """
    Выполняет один шаг pipeline.

    Args:
        step: конфигурация шага из pipelines.yaml.
        task: исходная задача пользователя.
        prev_output: вывод предыдущего шага (None для первого шага).

    Returns:
        (output_text, duration_seconds)
    """
    model = step["model"]
    system_prompt = step.get("system") or step.get("system_prompt", "")
    num_ctx = step.get("num_ctx", 8192)
    temperature = step.get("temperature", 0.2)
    max_tokens = step.get("max_tokens", 4096)

    # Формируем user-сообщение
    if prev_output is not None:
        user_content = prev_output
    else:
        user_content = task

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_content})

    start = time.monotonic()
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        extra_body={"num_ctx": num_ctx},
    )
    duration = time.monotonic() - start

    output = response.choices[0].message.content or ""
    return output.strip(), round(duration, 2)


def run_pipeline(pipeline_name: str, pipeline_cfg: dict, task: str) -> dict:
    """
    Выполняет multi-step pipeline.

    Args:
        pipeline_name: имя pipeline.
        pipeline_cfg: конфигурация pipeline из pipelines.yaml.
        task: исходная задача.

    Returns:
        dict с полями: task, pipeline, steps, total_duration_sec.
    """
    steps_cfg = pipeline_cfg.get("steps", [])
    steps_results = []
    prev_output: str | None = None
    total_start = time.monotonic()

    print(f"\n=== Pipeline: {pipeline_name} ({len(steps_cfg)} steps) ===", file=sys.stderr)
    print(f"Task: {task[:120]}{'...' if len(task) > 120 else ''}\n", file=sys.stderr)

    for i, step in enumerate(steps_cfg, start=1):
        step_name = step.get("name", f"step_{i}")
        model = step["model"]
        print(f"[{i}/{len(steps_cfg)}] {step_name} ({model})...", file=sys.stderr, end="", flush=True)

        # Первый шаг получает task, последующие — вывод предыдущего
        # Исключение: шаг "planner" — всегда получает task
        if prev_output is None or step_name == "planner":
            step_input = task
        else:
            step_input = prev_output

        output, duration = run_step(step, task, prev_output=None if (prev_output is None or step_name == "planner") else prev_output)

        print(f" {duration}s", file=sys.stderr)

        # Для planner — фильтруем <think> перед передачей Executor
        if step_name == "planner":
            clean_output = strip_think_blocks(output)
        else:
            clean_output = output

        steps_results.append({
            "name": step_name,
            "model": model,
            "duration_sec": duration,
            "output": output,  # сохраняем оригинал с <think> если есть
        })

        prev_output = clean_output

    total_duration = round(time.monotonic() - total_start, 2)
    print(f"\nTotal: {total_duration}s", file=sys.stderr)

    return {
        "task": task,
        "pipeline": pipeline_name,
        "steps": steps_results,
        "total_duration_sec": total_duration,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sequential multi-model orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Список доступных pipeline
  ./venv/bin/python orchestrator.py --list

  # Запуск pipeline, результат в JSON
  ./venv/bin/python orchestrator.py --pipeline execute-review --task "Review this code: ..."

  # Запуск pipeline, вывод последнего шага в stdout (для shell-скриптов)
  ./venv/bin/python orchestrator.py --pipeline commit-msg --task "$(git diff --cached)" --stdout
""",
    )
    parser.add_argument("--list", action="store_true", help="List available pipelines and exit")
    parser.add_argument("--pipeline", type=str, help="Pipeline name to run")
    parser.add_argument("--task", type=str, help="Task text for the selected pipeline")
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print last step output to stdout (for headless scripts). JSON is still saved to results/.",
    )
    args = parser.parse_args()

    # Подавляем DeprecationWarning от datetime.utcnow() в OpenAI SDK
    warnings.filterwarnings("ignore", category=DeprecationWarning)

    try:
        pipelines = load_pipelines()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if args.list:
        print("Available pipelines:")
        for name, cfg in pipelines.items():
            steps = cfg.get("steps", [])
            desc = cfg.get("description", "")
            desc_str = f" — {desc}" if desc else ""
            print(f"  - {name} ({len(steps)} steps){desc_str}")
        sys.exit(0)

    if not args.pipeline:
        parser.error("--pipeline is required (or use --list to see available pipelines)")
    if not args.task:
        parser.error("--task is required")

    if args.pipeline not in pipelines:
        print(f"ERROR: pipeline '{args.pipeline}' not found. Use --list to see available.", file=sys.stderr)
        sys.exit(1)

    pipeline_cfg = pipelines[args.pipeline]
    results = run_pipeline(args.pipeline, pipeline_cfg, args.task)

    out_path = save_results(results)
    print(f"\nResults saved: {out_path}", file=sys.stderr)

    if args.stdout:
        text = get_last_step_text(results)
        if text:
            sys.stdout.write(text.rstrip() + "\n")


if __name__ == "__main__":
    main()
