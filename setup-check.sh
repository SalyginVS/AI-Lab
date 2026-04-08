#!/usr/bin/env bash
# setup-check.sh — Полная верификация стека Lab RTX3090
# Паспорт лаборатории v25, Этап 13
# Отличие от health-check.sh: проверяет ВСЁ (версии, файлы, конфиги), не только liveness.
# Использование: bash ~/llm-gateway/scripts/setup-check.sh

set -euo pipefail

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

pass() {
    echo "[PASS] $1"
    PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
    echo "[FAIL] $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

warn() {
    echo "[WARN] $1"
    WARN_COUNT=$((WARN_COUNT + 1))
}

echo "=========================================="
echo "  Lab RTX3090 — Setup Check"
echo "  $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "=========================================="
echo ""

# --- Секция 1: Версии ключевых компонентов ---
echo "--- Версии ---"

# 1. Ubuntu
if grep -q "22.04" /etc/os-release 2>/dev/null; then
    pass "Ubuntu 22.04"
else
    fail "Ubuntu: ожидалось 22.04, факт: $(grep VERSION_ID /etc/os-release 2>/dev/null || echo 'unknown')"
fi

# 2. NVIDIA driver
NVIDIA_VER=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null || echo "not found")
if [[ "$NVIDIA_VER" != "not found" ]]; then
    pass "NVIDIA driver: $NVIDIA_VER"
else
    fail "NVIDIA driver: not found (nvidia-smi not available)"
fi

# 3. CUDA
CUDA_VER=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null || echo "not found")
if [[ "$CUDA_VER" != "not found" ]]; then
    pass "CUDA compute capability: $CUDA_VER"
else
    fail "CUDA: not found"
fi

# 4. Docker
DOCKER_VER=$(docker --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' || echo "not found")
if [[ "$DOCKER_VER" != "not found" ]]; then
    pass "Docker: $DOCKER_VER"
else
    warn "Docker: not found (не блокирует, нужен для этапа 12)"
fi

# 5. Ollama
OLLAMA_VER=$(ollama --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' || echo "not found")
if [[ "$OLLAMA_VER" == "0.20.2" ]]; then
    pass "Ollama: $OLLAMA_VER"
elif [[ "$OLLAMA_VER" != "not found" ]]; then
    warn "Ollama: $OLLAMA_VER (паспорт: 0.20.2)"
else
    fail "Ollama: not found"
fi

# 6. Gateway version
GW_VER=$(grep -oP "VERSION\s*=\s*\"([^\"]+)\"" ~/llm-gateway/gateway/__init__.py 2>/dev/null | grep -oP '"[^"]+"' | tr -d '"' || echo "not found")
if [[ "$GW_VER" == "0.12.0" ]]; then
    pass "Gateway version: $GW_VER"
elif [[ "$GW_VER" != "not found" ]]; then
    warn "Gateway version: $GW_VER (паспорт: 0.12.0)"
else
    fail "Gateway: __init__.py not found"
fi

# 7. uv
UV_VER=$(uv --version 2>/dev/null | grep -oP '\d+\.\d+' || echo "not found")
if [[ "$UV_VER" != "not found" ]]; then
    pass "uv: $UV_VER"
else
    warn "uv: not found (нужен на клиенте для mcp-server-git)"
fi

echo ""

# --- Секция 2: Ollama конфигурация ---
echo "--- Ollama конфигурация ---"

OVERRIDE="/etc/systemd/system/ollama.service.d/override.conf"
if [[ -f "$OVERRIDE" ]]; then
    pass "override.conf exists"

    grep -q "OLLAMA_KV_CACHE_TYPE.*q8_0" "$OVERRIDE" 2>/dev/null && pass "KV_CACHE_TYPE=q8_0" || fail "KV_CACHE_TYPE != q8_0"
    grep -q "OLLAMA_MAX_LOADED_MODELS.*2" "$OVERRIDE" 2>/dev/null && pass "MAX_LOADED_MODELS=2" || fail "MAX_LOADED_MODELS != 2"
    grep -q "OLLAMA_NUM_PARALLEL.*1" "$OVERRIDE" 2>/dev/null && pass "NUM_PARALLEL=1" || fail "NUM_PARALLEL != 1"
    grep -q "OLLAMA_FLASH_ATTENTION.*1" "$OVERRIDE" 2>/dev/null && pass "FLASH_ATTENTION=1" || fail "FLASH_ATTENTION != 1"
else
    fail "override.conf not found at $OVERRIDE"
fi

# Модели
MODEL_COUNT=$(curl -sf http://localhost:11434/api/tags 2>/dev/null | jq '.models | length' 2>/dev/null || echo "0")
if [[ "$MODEL_COUNT" -eq 15 ]]; then
    pass "Ollama models: $MODEL_COUNT"
elif [[ "$MODEL_COUNT" -gt 0 ]]; then
    warn "Ollama models: $MODEL_COUNT (паспорт: 15)"
else
    fail "Ollama: не удалось получить список моделей"
fi

echo ""

# --- Секция 3: Gateway ---
echo "--- Gateway ---"

# Gateway alive
GW_HEALTH=$(curl -sf http://localhost:8000/health 2>/dev/null)
if [[ -n "$GW_HEALTH" ]]; then
    pass "Gateway /health alive"

    GW_H_VER=$(echo "$GW_HEALTH" | jq -r '.version' 2>/dev/null || echo "unknown")
    [[ "$GW_H_VER" == "0.12.0" ]] && pass "Gateway health version: $GW_H_VER" || warn "Gateway health version: $GW_H_VER (паспорт: 0.12.0)"

    GW_AUTH=$(echo "$GW_HEALTH" | jq -r '.auth_enabled' 2>/dev/null || echo "unknown")
    [[ "$GW_AUTH" == "true" ]] && pass "Gateway auth: mandatory" || fail "Gateway auth: not enabled"

    GW_USERS=$(echo "$GW_HEALTH" | jq -r '.user_count' 2>/dev/null || echo "0")
    [[ "$GW_USERS" -ge 3 ]] && pass "Gateway users: $GW_USERS" || fail "Gateway users: $GW_USERS (ожидалось ≥3)"

    GW_PIPE=$(echo "$GW_HEALTH" | jq -r '.pipelines_count' 2>/dev/null || echo "0")
    [[ "$GW_PIPE" -eq 6 ]] && pass "Gateway pipelines: $GW_PIPE" || warn "Gateway pipelines: $GW_PIPE (паспорт: 6)"
else
    fail "Gateway /health: не отвечает"
fi

# /metrics
METRICS=$(curl -sf http://localhost:8000/metrics 2>/dev/null)
if [[ -n "$METRICS" ]] && echo "$METRICS" | jq '.totals' >/dev/null 2>&1; then
    pass "Gateway /metrics alive"
else
    fail "Gateway /metrics: не отвечает или не JSON"
fi

# Gateway модули
GW_MODULE_COUNT=$(ls ~/llm-gateway/gateway/*.py 2>/dev/null | grep -cv __pycache__ || echo "0")
if [[ "$GW_MODULE_COUNT" -ge 11 ]]; then
    pass "Gateway modules: $GW_MODULE_COUNT"
else
    fail "Gateway modules: $GW_MODULE_COUNT (ожидалось ≥11)"
fi

# run.py
[[ -f ~/llm-gateway/run.py ]] && pass "run.py exists" || fail "run.py not found"

echo ""

# --- Секция 4: Embeddings ---
echo "--- Embeddings ---"

# Нужен токен для проверки
if [[ -f ~/llm-gateway/.env ]]; then
    pass ".env exists"

    ENV_PERMS=$(stat -c "%a" ~/llm-gateway/.env 2>/dev/null || echo "unknown")
    [[ "$ENV_PERMS" == "600" ]] && pass ".env permissions: 600" || warn ".env permissions: $ENV_PERMS (ожидалось 600)"

    # Загружаем токен для дальнейших проверок
    set -a
    source ~/llm-gateway/.env 2>/dev/null || true
    set +a
    TOKEN=$(python3 -c "import json,os; d=json.loads(os.environ.get('LLM_GATEWAY_TOKENS','{}')); print(list(d.keys())[0] if d else '')" 2>/dev/null || echo "")

    if [[ -n "$TOKEN" ]]; then
        EMB_RESP=$(curl -sf -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
            -d '{"model":"qwen3-embedding","input":"setup check test"}' \
            http://localhost:8000/v1/embeddings 2>/dev/null || echo "")

        if [[ -n "$EMB_RESP" ]]; then
            EMB_OBJ=$(echo "$EMB_RESP" | jq -r '.object' 2>/dev/null || echo "")
            [[ "$EMB_OBJ" == "list" ]] && pass "Embeddings: OK" || fail "Embeddings: unexpected response"

            EMB_DIM=$(echo "$EMB_RESP" | jq '.data[0].embedding | length' 2>/dev/null || echo "0")
            [[ "$EMB_DIM" -eq 4096 ]] && pass "Embedding dim: $EMB_DIM" || fail "Embedding dim: $EMB_DIM (ожидалось 4096)"
        else
            fail "Embeddings endpoint: не отвечает"
        fi
    else
        fail "Не удалось извлечь токен из .env"
    fi
else
    fail ".env not found"
fi

echo ""

# --- Секция 5: RAG MCP ---
echo "--- RAG MCP ---"

RAG_STATUS=$(systemctl is-active rag-mcp 2>/dev/null || echo "inactive")
[[ "$RAG_STATUS" == "active" ]] && pass "rag-mcp.service: active" || fail "rag-mcp.service: $RAG_STATUS"

if [[ -f ~/rag-mcp-server/index_status.json ]]; then
    CHUNKS=$(cat ~/rag-mcp-server/index_status.json | jq '.chunks_indexed' 2>/dev/null || echo "0")
    [[ "$CHUNKS" -gt 0 ]] && pass "RAG chunks indexed: $CHUNKS" || fail "RAG chunks: 0"
else
    fail "RAG index_status.json not found"
fi

echo ""

# --- Секция 6: UFW ---
echo "--- UFW ---"

UFW_STATUS=$(sudo ufw status 2>/dev/null | head -1 || echo "unknown")
if echo "$UFW_STATUS" | grep -qi "active"; then
    pass "UFW: active"
    UFW_RULES=$(sudo ufw status numbered 2>/dev/null | grep -c "^\[" || echo "0")
    [[ "$UFW_RULES" -ge 8 ]] && pass "UFW rules: $UFW_RULES" || warn "UFW rules: $UFW_RULES (паспорт: 8)"
else
    fail "UFW: inactive"
fi

echo ""

# --- Секция 7: Файлы и структура ---
echo "--- Файлы ---"

[[ -f ~/llm-gateway/orchestrator.py ]] && pass "orchestrator.py" || fail "orchestrator.py not found"
[[ -f ~/llm-gateway/pipelines.yaml ]] && pass "pipelines.yaml" || fail "pipelines.yaml not found"

# Gemma 4 в pipelines
GEMMA_IN_PIPE=$(grep -c "gemma4" ~/llm-gateway/pipelines.yaml 2>/dev/null || echo "0")
[[ "$GEMMA_IN_PIPE" -gt 0 ]] && pass "Gemma 4 in pipelines: $GEMMA_IN_PIPE refs" || warn "Gemma 4 not found in pipelines.yaml"

# Scripts
for SCRIPT in auto-review.sh auto-commit-msg.sh auto-docs.sh health-check.sh benchmark.py; do
    [[ -f ~/llm-gateway/scripts/$SCRIPT ]] && pass "scripts/$SCRIPT" || fail "scripts/$SCRIPT not found"
done

# Git hooks
[[ -f ~/llm-gateway/.githooks/pre-push ]] && pass ".githooks/pre-push" || fail ".githooks/pre-push not found"
[[ -x ~/llm-gateway/.githooks/pre-push ]] && pass ".githooks/pre-push +x" || fail ".githooks/pre-push not executable"

GIT_HOOKS_PATH=$(git -C ~/llm-gateway config core.hooksPath 2>/dev/null || echo "not set")
[[ "$GIT_HOOKS_PATH" == ".githooks" ]] && pass "git hooksPath: .githooks" || fail "git hooksPath: $GIT_HOOKS_PATH (ожидалось .githooks)"

# Text-to-SQL
[[ -f ~/llm-gateway/ondo_demo.db ]] && pass "ondo_demo.db" || warn "ondo_demo.db not found (11A)"
if [[ -f ~/llm-gateway/ondo_demo.db ]]; then
    EMP_COUNT=$(sqlite3 ~/llm-gateway/ondo_demo.db "SELECT COUNT(*) FROM employees" 2>/dev/null || echo "0")
    [[ "$EMP_COUNT" -eq 30 ]] && pass "ondo_demo.db employees: $EMP_COUNT" || warn "ondo_demo.db employees: $EMP_COUNT (ожидалось 30)"
fi

# Benchmarks
[[ -d ~/llm-gateway/benchmarks ]] && pass "benchmarks/ dir" || fail "benchmarks/ not found"
BASELINE_COUNT=$(ls ~/llm-gateway/benchmarks/baseline_*.json 2>/dev/null | wc -l || echo "0")
[[ "$BASELINE_COUNT" -gt 0 ]] && pass "Baseline snapshots: $BASELINE_COUNT" || warn "No baseline snapshots found"

# SOP
[[ -f ~/llm-gateway/docs/SOP_Ollama_Upgrade.md ]] && pass "SOP_Ollama_Upgrade.md" || warn "SOP not found"

# ONBOARDING
[[ -f ~/llm-gateway/docs/ONBOARDING.md ]] && pass "ONBOARDING.md" || warn "ONBOARDING.md not found"

echo ""

# --- Секция 8: Systemd ---
echo "--- Systemd ---"

GW_ACTIVE=$(systemctl is-active llm-gateway 2>/dev/null || echo "inactive")
[[ "$GW_ACTIVE" == "active" ]] && pass "llm-gateway.service: active" || fail "llm-gateway.service: $GW_ACTIVE"

GW_ENABLED=$(systemctl is-enabled llm-gateway 2>/dev/null || echo "disabled")
[[ "$GW_ENABLED" == "enabled" ]] && pass "llm-gateway.service: enabled" || warn "llm-gateway.service: not enabled"

RAG_ENABLED=$(systemctl is-enabled rag-mcp 2>/dev/null || echo "disabled")
[[ "$RAG_ENABLED" == "enabled" ]] && pass "rag-mcp.service: enabled" || warn "rag-mcp.service: not enabled"

# Structured logging check
LOG_JSON=$(journalctl -u llm-gateway -n 3 -o cat 2>/dev/null | head -1 | jq '.' 2>/dev/null && echo "ok" || echo "not json")
[[ "$LOG_JSON" == *"ok"* ]] && pass "Structured JSON logging" || warn "Gateway logs may not be JSON"

echo ""

# --- Секция 9: Pipelines ---
echo "--- Pipelines ---"

PIPE_CLI=$(cd ~/llm-gateway && ./venv/bin/python orchestrator.py --list 2>/dev/null | grep -c ":" || echo "0")
[[ "$PIPE_CLI" -ge 6 ]] && pass "Orchestrator CLI pipelines: $PIPE_CLI" || warn "Orchestrator CLI pipelines: $PIPE_CLI (ожидалось 6)"

if [[ -n "$TOKEN" ]]; then
    PIPE_API=$(curl -sf -H "Authorization: Bearer $TOKEN" http://localhost:8000/v1/orchestrate/pipelines 2>/dev/null | jq '.pipelines | keys | length' 2>/dev/null || echo "0")
    [[ "$PIPE_API" -ge 6 ]] && pass "Gateway API pipelines: $PIPE_API" || warn "Gateway API pipelines: $PIPE_API (ожидалось 6)"
fi

echo ""

# --- Секция 10: Disk ---
echo "--- Disk ---"

DISK_PCT=$(df / --output=pcent | tail -1 | tr -d ' %')
[[ "$DISK_PCT" -lt 90 ]] && pass "Disk usage: ${DISK_PCT}%" || fail "Disk usage: ${DISK_PCT}% (≥90%!)"

echo ""

# --- Summary ---
TOTAL=$((PASS_COUNT + FAIL_COUNT + WARN_COUNT))
echo "=========================================="
echo "  PASS: $PASS_COUNT  |  FAIL: $FAIL_COUNT  |  WARN: $WARN_COUNT  |  TOTAL: $TOTAL"
echo "=========================================="

if [[ "$FAIL_COUNT" -gt 0 ]]; then
    echo "  STATUS: FAIL — есть критичные проблемы"
    exit 1
else
    if [[ "$WARN_COUNT" -gt 0 ]]; then
        echo "  STATUS: PASS with warnings"
    else
        echo "  STATUS: ALL PASS"
    fi
    exit 0
fi
