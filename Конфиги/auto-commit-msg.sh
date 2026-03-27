#!/usr/bin/env bash
# =============================================================================
# auto-commit-msg.sh — Headless conventional commit message generation
# =============================================================================
# Этап 8D: Headless Automation PoC
#
# Использование:
#   ./scripts/auto-commit-msg.sh
#
#   Генерирует conventional commit message для staged изменений.
#   Вывод: одна строка в stdout.
#   Подходит для: ручного вызова, prepare-commit-msg hook.
#
# Переменные окружения:
#   MAX_LINES  — максимум строк diff (default: 400)
#
# Выход:
#   exit 0  — commit message выведен в stdout
#   exit 1  — нет staged изменений или ошибка orchestrator
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ORCH_PY="$ROOT_DIR/venv/bin/python"
ORCH_SCRIPT="$ROOT_DIR/orchestrator.py"
MAX_LINES="${MAX_LINES:-400}"

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

if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "ERROR: Not inside a git repository." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Проверка staged изменений
# ---------------------------------------------------------------------------
if git diff --cached --quiet --exit-code; then
    echo "ERROR: No staged changes found. Stage files with 'git add' first." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Получение diff
# ---------------------------------------------------------------------------
DIFF_RAW="$(git diff --cached)"
DIFF_LINES=$(echo "$DIFF_RAW" | wc -l)

echo "=== auto-commit-msg.sh ===" >&2
echo "Staged diff: ${DIFF_LINES} lines" >&2

# ---------------------------------------------------------------------------
# Ограничение размера diff
# ---------------------------------------------------------------------------
if [[ "$DIFF_LINES" -gt "$MAX_LINES" ]]; then
    echo "WARNING: diff is $DIFF_LINES lines, truncating to $MAX_LINES." >&2
    DIFF_TRUNCATED=$(echo "$DIFF_RAW" | head -n "$MAX_LINES")
    DIFF_TRUNCATED="${DIFF_TRUNCATED}"$'\n'"... [TRUNCATED: $((DIFF_LINES - MAX_LINES)) lines omitted]"
else
    DIFF_TRUNCATED="$DIFF_RAW"
fi

# ---------------------------------------------------------------------------
# Формирование задачи и вызов orchestrator
# ---------------------------------------------------------------------------
TASK=$'Generate a conventional git commit message for the following staged git diff.\n'
TASK+=$'Output ONLY the commit message — one line, max 72 characters, no markdown, no explanation.\n\n'
TASK+="$DIFF_TRUNCATED"

echo "Generating commit message (commit-msg pipeline)..." >&2
echo "" >&2

"$ORCH_PY" "$ORCH_SCRIPT" \
    --pipeline commit-msg \
    --task "$TASK" \
    --stdout

exit 0
