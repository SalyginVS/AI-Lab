#!/usr/bin/env bash
# =============================================================================
# auto-docs.sh — Headless documentation generation via orchestrator.py
# =============================================================================
# Этап 8D: Headless Automation PoC
#
# Использование:
#   ./scripts/auto-docs.sh <file_path> [--format docstring|markdown]
#
#   Форматы:
#     docstring (default) — Python docstrings для функций и классов
#     markdown            — Markdown-документация модуля
#
# Примеры:
#   ./scripts/auto-docs.sh gateway.py
#   ./scripts/auto-docs.sh orchestrator.py --format markdown
#   ./scripts/auto-docs.sh src/module.py --format docstring > src/module_docs.md
#
# Переменные окружения:
#   MAX_CHARS  — максимум символов файла (default: 16000)
#
# Выход:
#   exit 0  — документация выведена в stdout
#   exit 1  — файл не найден или ошибка
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ORCH_PY="$ROOT_DIR/venv/bin/python"
ORCH_SCRIPT="$ROOT_DIR/orchestrator.py"
MAX_CHARS="${MAX_CHARS:-16000}"

# ---------------------------------------------------------------------------
# Проверка зависимостей
# ---------------------------------------------------------------------------
if [[ ! -f "$ORCH_PY" ]]; then
    echo "ERROR: Python venv not found at $ORCH_PY" >&2
    exit 1
fi

if [[ ! -f "$ORCH_SCRIPT" ]]; then
    echo "ERROR: orchestrator.py not found at $ORCH_SCRIPT" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Разбор аргументов
# ---------------------------------------------------------------------------
FILE_PATH=""
FORMAT="docstring"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --format)
            if [[ -z "${2:-}" ]]; then
                echo "ERROR: --format requires a value: docstring or markdown" >&2
                exit 1
            fi
            case "$2" in
                docstring|markdown)
                    FORMAT="$2"
                    ;;
                *)
                    echo "ERROR: Unknown format '$2'. Use: docstring, markdown" >&2
                    exit 1
                    ;;
            esac
            shift 2
            ;;
        -h|--help)
            sed -n '2,30p' "$0" | grep '^#' | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        -*)
            echo "ERROR: Unknown option: $1" >&2
            exit 1
            ;;
        *)
            if [[ -z "$FILE_PATH" ]]; then
                FILE_PATH="$1"
            else
                echo "ERROR: Unexpected argument: $1" >&2
                exit 1
            fi
            shift
            ;;
    esac
done

if [[ -z "$FILE_PATH" ]]; then
    echo "ERROR: File path is required." >&2
    echo "Usage: $0 <file_path> [--format docstring|markdown]" >&2
    exit 1
fi

if [[ ! -f "$FILE_PATH" ]]; then
    echo "ERROR: File not found: $FILE_PATH" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Чтение и ограничение содержимого файла
# ---------------------------------------------------------------------------
CODE_CONTENT="$(cat "$FILE_PATH")"
CODE_CHARS="${#CODE_CONTENT}"
FILENAME="$(basename "$FILE_PATH")"

echo "=== auto-docs.sh: $FILENAME (format=$FORMAT) ===" >&2
echo "File size: ${CODE_CHARS} chars" >&2

if [[ "$CODE_CHARS" -gt "$MAX_CHARS" ]]; then
    echo "WARNING: file is $CODE_CHARS chars, truncating to $MAX_CHARS (set MAX_CHARS to override)." >&2
    CODE_CONTENT="${CODE_CONTENT:0:$MAX_CHARS}"
    CODE_CONTENT+=$'\n... [TRUNCATED]'
fi

# ---------------------------------------------------------------------------
# Формирование задачи по формату
# ---------------------------------------------------------------------------
case "$FORMAT" in
    docstring)
        TASK=$'Generate Python docstrings for all functions and classes in the following code.\n'
        TASK+=$'Return only the updated code with inserted docstrings.\n'
        TASK+=$'Use Google-style docstrings (Args:, Returns:, Raises:).\n'
        TASK+=$'Do not change any logic, only add docstrings where missing.\n\n'
        TASK+="File: ${FILENAME}"$'\n\n'
        TASK+="$CODE_CONTENT"
        ;;
    markdown)
        TASK=$'Generate clear and concise Markdown documentation for the following code file.\n'
        TASK+=$'Include sections: Overview, Key Components (classes/functions with signatures and purpose),\n'
        TASK+=$'Configuration, Usage Examples, Important Notes.\n'
        TASK+=$'Do not wrap the output in a code fence. Return Markdown directly.\n\n'
        TASK+="File: ${FILENAME}"$'\n\n'
        TASK+="$CODE_CONTENT"
        ;;
esac

# ---------------------------------------------------------------------------
# Вызов orchestrator
# ---------------------------------------------------------------------------
echo "Running docs-generate pipeline..." >&2
echo "" >&2

"$ORCH_PY" "$ORCH_SCRIPT" \
    --pipeline docs-generate \
    --task "$TASK" \
    --stdout

exit 0
