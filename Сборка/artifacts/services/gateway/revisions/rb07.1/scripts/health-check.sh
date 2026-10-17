#!/usr/bin/env bash
# Revision RB-07.1, 2026-10-17; owner decision H-6 (2026-10-16).
set -uo pipefail

ROOT="${HOME}/llm-gateway"
OLLAMA_URL="http://127.0.0.1:11434"
GATEWAY_URL="http://127.0.0.1:8000"



REQUIRED_LLM_MODELS=(
  "qwen3.8-flash-next:125b-a6b-q6_K-ab-262k"
)

EMBEDDING_OLLAMA_MODEL="qwen3-embedding:latest"
EMBEDDING_API_MODEL="qwen3-embedding"

PASS_COUNT=0
FAIL_COUNT=0
TOTAL_COUNT=0

ok() {
  printf '[OK]   %s\n' "$1"
  PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
  printf '[FAIL] %s\n' "$1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

check() {
  local description="$1"
  shift

  TOTAL_COUNT=$((TOTAL_COUNT + 1))

  if "$@"; then
    ok "$description"
  else
    fail "$description"
  fi
}


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------

get_gateway_token() {
  python3 -I - "$ROOT/.env" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])

if not path.is_file():
    raise SystemExit(1)

env = {}

for line in path.read_text().splitlines():
    line = line.strip()

    if not line or line.startswith("#") or "=" not in line:
        continue

    key, value = line.split("=", 1)
    env[key] = value.strip().strip("'").strip('"')

try:
    tokens = json.loads(env["LLM_GATEWAY_TOKENS"])
except (KeyError, json.JSONDecodeError):
    raise SystemExit(1)

matches = [
    token
    for token, user in tokens.items()
    if user == "vladimir"
]

if len(matches) != 1:
    raise SystemExit(1)

print(matches[0])
PY
}


# ---------------------------------------------------------------------------
# Host / GPU
# ---------------------------------------------------------------------------

check_gpu_available() {
  command -v nvidia-smi >/dev/null 2>&1 || return 1
  nvidia-smi -L 2>/dev/null | grep -q 'GPU 0:'
}


check_disk_space() {
  local usage

  usage="$(
    df -P / |
      awk 'NR == 2 {gsub(/%/, "", $5); print $5}'
  )"

  [[ "$usage" =~ ^[0-9]+$ ]] || return 1
  [[ "$usage" -lt 90 ]]
}


# ---------------------------------------------------------------------------
# systemd
# ---------------------------------------------------------------------------

check_service_active_enabled() {
  local service="$1"

  systemctl is-active --quiet "$service" &&
    systemctl is-enabled --quiet "$service"
}


# ---------------------------------------------------------------------------
# Ollama
# ---------------------------------------------------------------------------

check_ollama_alive() {
  curl \
    --connect-timeout 5 \
    --max-time 30 \
    -fsS \
    "$OLLAMA_URL/api/tags" \
    >/dev/null
}


check_required_ollama_models() {
  local payload

  payload="$(
    curl \
      --connect-timeout 5 \
      --max-time 30 \
      -fsS \
      "$OLLAMA_URL/api/tags"
  )" || return 1

  python3 -I - "$payload" "${REQUIRED_LLM_MODELS[@]}" "$EMBEDDING_OLLAMA_MODEL" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
required = set(sys.argv[2:])

available = {
    item.get("name")
    for item in payload.get("models", [])
    if item.get("name")
}

missing = sorted(required - available)

if missing:
    print(
        "missing Ollama models: " + ", ".join(missing),
        file=sys.stderr,
    )
    raise SystemExit(1)
PY
}


check_ollama_global_context() {
  local environment

  environment="$(
    systemctl show ollama.service \
      --property=Environment \
      --value
  )" || return 1

  grep -Eq \
    '(^|[[:space:]])OLLAMA_CONTEXT_LENGTH=262144([[:space:]]|$)' \
    <<<"$environment"
}


check_required_model_num_ctx() {
  local model
  local modelfile

  for model in "${REQUIRED_LLM_MODELS[@]}"; do
    modelfile="$(ollama show --modelfile "$model")" || return 1

    grep -Eq \
      '^PARAMETER[[:space:]]+num_ctx[[:space:]]+262144[[:space:]]*$' \
      <<<"$modelfile" \
      || {
        echo \
          "unexpected num_ctx for $model" \
          >&2
        return 1
      }
  done
}


# ---------------------------------------------------------------------------
# Gateway configuration
# ---------------------------------------------------------------------------

check_gateway_alive() {
  curl \
    --connect-timeout 5 \
    --max-time 30 \
    -fsS \
    "$GATEWAY_URL/health" \
    >/dev/null
}


check_gateway_health_contract() {
  local payload

  payload="$(
    curl \
      --connect-timeout 5 \
      --max-time 30 \
      -fsS \
      "$GATEWAY_URL/health"
  )" || return 1

  python3 -I - "$payload" "$((${#REQUIRED_LLM_MODELS[@]} + 1))" <<'PY'
import json
import sys

data = json.loads(sys.argv[1])

ok = (
    data.get("gateway") == "ok"
    and data.get("ollama") == "ok"
    and data.get("auth_enabled") is True
    and isinstance(data.get("models_count"), int)
    and data["models_count"] >= int(sys.argv[2])
    and isinstance(data.get("pipelines_count"), int)
    and data["pipelines_count"] >= 1
)

raise SystemExit(0 if ok else 1)
PY
}


check_gateway_version_matches_source() {
  local payload
  local api_version

  payload="$(
    curl \
      --connect-timeout 5 \
      --max-time 30 \
      -fsS \
      "$GATEWAY_URL/health"
  )" || return 1

  api_version="$(
    python3 -I - "$payload" <<'PY'
import json
import sys

print(json.loads(sys.argv[1]).get("version", ""))
PY
  )"

  python3 -I - "$ROOT/gateway/__init__.py" "$api_version" <<'PY'
import ast
import sys
from pathlib import Path

path = Path(sys.argv[1])
api_version = sys.argv[2]

tree = ast.parse(path.read_text())

source_version = None

for node in tree.body:
    if not isinstance(node, ast.Assign):
        continue

    for target in node.targets:
        if (
            isinstance(target, ast.Name)
            and target.id == "VERSION"
            and isinstance(node.value, ast.Constant)
        ):
            source_version = node.value.value

if not source_version:
    raise SystemExit(1)

raise SystemExit(
    0 if str(source_version) == api_version else 1
)
PY
}


check_gateway_context_policy() {
  python3 -I - "$ROOT/gateway/__init__.py" <<'PY'
import ast
import sys
from pathlib import Path

tree = ast.parse(Path(sys.argv[1]).read_text())

wanted = {
    "DEFAULT_NUM_CTX": 262144,
    "MAX_NUM_CTX": 262144,
}

found = {}

for node in tree.body:
    if not isinstance(node, ast.Assign):
        continue

    if not isinstance(node.value, ast.Constant):
        continue

    for target in node.targets:
        if (
            isinstance(target, ast.Name)
            and target.id in wanted
        ):
            found[target.id] = node.value.value

raise SystemExit(
    0 if found == wanted else 1
)
PY
}


check_gateway_auth_config() {
  python3 -I - "$ROOT/.env" <<'PY'
import json
import stat
import sys
from pathlib import Path

path = Path(sys.argv[1])

if not path.is_file():
    raise SystemExit(1)

if stat.S_IMODE(path.stat().st_mode) != 0o600:
    raise SystemExit(1)

env = {}

for line in path.read_text().splitlines():
    line = line.strip()

    if not line or line.startswith("#") or "=" not in line:
        continue

    key, value = line.split("=", 1)
    env[key] = value.strip().strip("'").strip('"')

try:
    tokens = json.loads(env["LLM_GATEWAY_TOKENS"])
    orchestrator = env["LLM_ORCHESTRATOR_TOKEN"]
except (KeyError, json.JSONDecodeError):
    raise SystemExit(1)

required_users = {
    "vladimir",
    "roadwarrior",
    "orchestrator",
}

if len(tokens) != 3:
    raise SystemExit(1)

if set(tokens.values()) != required_users:
    raise SystemExit(1)

if tokens.get(orchestrator) != "orchestrator":
    raise SystemExit(1)
PY
}


check_gateway_catalog() {
  local token
  local payload

  token="$(get_gateway_token)" || return 1
  [[ -n "$token" ]] || return 1

  payload="$(
    curl \
      --connect-timeout 5 \
      --max-time 30 \
      -fsS \
      -H "Authorization: Bearer $token" \
      "$GATEWAY_URL/v1/models"
  )" || return 1

  python3 -I - "$payload" "${REQUIRED_LLM_MODELS[@]}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
required = set(sys.argv[2:])

available = {
    item.get("id")
    for item in payload.get("data", [])
    if item.get("id")
}

missing = sorted(required - available)

if missing:
    print(
        "missing Gateway models: " + ", ".join(missing),
        file=sys.stderr,
    )
    raise SystemExit(1)
PY
}


check_smoke_pipeline_policy() {
  "$ROOT/venv/bin/python" -I - "$ROOT/pipelines.yaml" <<'PY'
import sys
from pathlib import Path

import yaml

path = Path(sys.argv[1])
data = yaml.safe_load(path.read_text())

try:
    steps = data["pipelines"]["smoke"]["steps"]
except (KeyError, TypeError):
    raise SystemExit(1)

if not isinstance(steps, list) or len(steps) != 1:
    raise SystemExit(1)

step = steps[0]

ok = (
    isinstance(step, dict)
    and step.get("model") == "qwen3.8-flash-next:125b-a6b-q6_K-ab-262k"
    and "num_ctx" not in step
)

raise SystemExit(0 if ok else 1)
PY
}


check_gateway_metrics() {
  local payload

  payload="$(
    curl \
      --connect-timeout 5 \
      --max-time 30 \
      -fsS \
      "$GATEWAY_URL/metrics"
  )" || return 1

  python3 -I - "$payload" <<'PY'
import json
import sys

data = json.loads(sys.argv[1])

ok = all(
    key in data
    for key in ("totals", "endpoints", "models")
)

raise SystemExit(0 if ok else 1)
PY
}


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

check_embedding_contract() {
  local token
  local payload

  token="$(get_gateway_token)" || return 1
  [[ -n "$token" ]] || return 1

  payload="$(
    curl \
      --connect-timeout 5 \
      --max-time 180 \
      -fsS \
      -H "Authorization: Bearer $token" \
      -H "Content-Type: application/json" \
      -d \
      "{\"model\":\"${EMBEDDING_API_MODEL}\",\"input\":\"health check\"}" \
      "$GATEWAY_URL/v1/embeddings"
  )" || return 1

  python3 -I - "$payload" <<'PY'
import json
import sys

data = json.loads(sys.argv[1])

try:
    vector = data["data"][0]["embedding"]
except (KeyError, IndexError, TypeError):
    raise SystemExit(1)

ok = (
    data.get("object") == "list"
    and isinstance(vector, list)
    and len(vector) == 4096
)

raise SystemExit(0 if ok else 1)
PY
}


# ---------------------------------------------------------------------------
# UFW
# ---------------------------------------------------------------------------

get_ufw_status() {
  sudo -n ufw status 2>/dev/null
}


check_ufw_active() {
  get_ufw_status |
    grep -q '^Status: active'
}


check_ufw_allow_rules() {
  local count

  count="$(
    get_ufw_status |
      grep -c 'ALLOW'
  )" || true

  [[ "$count" =~ ^[0-9]+$ ]] || return 1
  [[ "$count" -ge 3 ]]
}


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

check "NVIDIA GPU available" \
  check_gpu_available

check "Ollama service active + enabled" \
  check_service_active_enabled ollama.service

check "Ollama API alive" \
  check_ollama_alive

check "Required Ollama models present" \
  check_required_ollama_models

check "Ollama global context = 262144" \
  check_ollama_global_context

check "Required LLMs have num_ctx = 262144" \
  check_required_model_num_ctx

check "Gateway service active + enabled" \
  check_service_active_enabled llm-gateway.service

check "Gateway health contract" \
  check_gateway_health_contract

check "Gateway API version matches source" \
  check_gateway_version_matches_source

check "Gateway default/max context = 262144" \
  check_gateway_context_policy

check "Gateway auth configuration + permissions" \
  check_gateway_auth_config

check "Required models published by Gateway" \
  check_gateway_catalog

check "Smoke pipeline inherits 256k Gateway context" \
  check_smoke_pipeline_policy

check "Gateway metrics contract" \
  check_gateway_metrics

check "Embedding endpoint + 4096 dimension" \
  check_embedding_contract

check "RAG MCP service active + enabled" \
  check_service_active_enabled rag-mcp.service

check "Docker MCP service active + enabled" \
  check_service_active_enabled docker-mcp.service

check "UFW active (non-interactive sudo)" \
  check_ufw_active

check "UFW has >=3 ALLOW rules" \
  check_ufw_allow_rules

check "Root disk usage < 90%" \
  check_disk_space


echo "---"

if [[ "$FAIL_COUNT" -eq 0 ]]; then
  echo "Health check: ${PASS_COUNT}/${TOTAL_COUNT} passed"
  exit 0
else
  echo \
    "Health check: ${PASS_COUNT}/${TOTAL_COUNT} passed " \
    "(${FAIL_COUNT} FAILED)"
  exit 1
fi
