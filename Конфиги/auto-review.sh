#!/usr/bin/env bash
# =============================================================================
# auto-review.sh — Headless LLM code review via orchestrator.py
# =============================================================================
# Этап 8D: Headless Automation PoC
#
# Использование:
#   ./scripts/auto-review.sh [MODE]
#
#   Режимы (MODE):
#     --staged        git diff --cached (по умолчанию)
#     --last-commit   git diff HEAD~1 HEAD
#     --branch <name> git diff <name>...HEAD
#
# Переменные окружения:
#   STRICT_REVIEW=1  — exit 1 при пустом diff (блокировка в CI)
#   MAX_LINES        — максимум строк diff (default: 400)
#
# Выход:
#   exit 0  — всегда (нестрогий режим), если не STRICT_REVIEW=1 при пустом diff
#   exit 1  — только при ошибке вызова orchestrator или STRICT_REVIEW=1 + пустой diff
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ORCH_PY="$ROOT_DIR/venv/bin/python"
ORCH_SCRIPT="$ROOT_DIR/orchestrator.py"
MAX_LINES="${MAX_LINES:-400}"
STRICT="${STRICT_REVIEW:-0}"

# ---------------------------------------------------------------------------
# Проверка зависимостей
# ---------------------------------------------------------------------------
if [[ ! -f "$ORCH_PY" ]]; then
    echo "ERROR: Python venv not found at $ORCH_PY" >&2
    echo "       Run: cd ~/llm-gateway && python3 -m venv venv && ./venv/bin/pip install openai pyyaml" >&2
    exit 1
fi

if [[ ! -f "$ORCH_SCRIPT" ]]; then
    echo "ERROR: orchestrator.py not found at $ORCH_SCRIPT" >&2
    exit 1
fi

if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "ERROR: Not inside a git repository." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Разбор аргументов
# ---------------------------------------------------------------------------
MODE="staged"
BRANCH=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --staged)
            MODE="staged"
            shift
            ;;
        --last-commit)
            MODE="last-commit"
            shift
            ;;
        --branch)
            MODE="branch"
            if [[ -z "${2:-}" ]]; then
                echo "ERROR: --branch requires a branch name argument." >&2
                exit 1
            fi
            BRANCH="$2"
            shift 2
            ;;
        -h|--help)
            sed -n '2,30p' "$0" | grep '^#' | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "ERROR: Unknown argument: $1" >&2
            echo "Usage: $0 [--staged | --last-commit | --branch <name>]" >&2
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Получение diff
# ---------------------------------------------------------------------------
get_diff() {
    case "$MODE" in
        staged)
            git diff --cached
            ;;
        last-commit)
            git diff HEAD~1 HEAD 2>/dev/null || true
            ;;
        branch)
            git diff "${BRANCH}...HEAD" 2>/dev/null || true
            ;;
    esac
}

echo "=== auto-review.sh: mode=$MODE ===" >&2

DIFF_RAW="$(get_diff || true)"

if [[ -z "$DIFF_RAW" ]]; then
    echo "No changes to review (diff is empty)." >&2
    if [[ "$STRICT" == "1" ]]; then
        echo "STRICT_REVIEW=1: treating empty diff as error." >&2
        exit 1
    fi
    exit 0
fi

# ---------------------------------------------------------------------------
# Ограничение размера diff
# ---------------------------------------------------------------------------
DIFF_LINES=$(echo "$DIFF_RAW" | wc -l)

if [[ "$DIFF_LINES" -gt "$MAX_LINES" ]]; then
    echo "WARNING: diff is $DIFF_LINES lines, truncating to $MAX_LINES (set MAX_LINES to override)." >&2
    DIFF_TRUNCATED=$(echo "$DIFF_RAW" | head -n "$MAX_LINES")
    DIFF_TRUNCATED="${DIFF_TRUNCATED}"$'\n'"... [TRUNCATED: $((DIFF_LINES - MAX_LINES)) lines omitted]"
else
    DIFF_TRUNCATED="$DIFF_RAW"
fi

# ---------------------------------------------------------------------------
# Формирование задачи и вызов orchestrator
# ---------------------------------------------------------------------------
TASK=$'Perform code review for the following git diff.\n'
TASK+=$'Identify bugs, security issues, code quality problems, missing error handling, and style violations.\n'
TASK+=$'Provide actionable recommendations for each issue found.\n'
TASK+=$'Format: use headings, severity labels (CRITICAL/HIGH/MEDIUM/LOW), and concrete fix suggestions.\n\n'
TASK+="$DIFF_TRUNCATED"

echo "Running code review pipeline (execute-review)..." >&2
echo "Diff size: ${DIFF_LINES} lines" >&2
echo "" >&2

"$ORCH_PY" "$ORCH_SCRIPT" \
    --pipeline execute-review \
    --task "$TASK" \
    --stdout

exit 0
