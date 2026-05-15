---
tags: [конфиг, opencode, terminal-agent, wrappers, permissions]
дата: 2026-05-15
статус: active
---

# OpenCode AI-Lab wrappers

## Назначение

Два user-local wrapper-скрипта задают безопасные OpenCode profiles для AI Lab RTX 3090:

```text
~/.local/bin/oc-ailab-readonly
~/.local/bin/oc-ailab-edit
```

Оба wrappers:

- используют OpenCode binary: `~/.opencode/bin/opencode`;
- используют provider `ailab`;
- используют gateway endpoint: `http://192.168.0.128:8000/v1`;
- используют model id: `qwen3.6:27b`;
- берут gateway token из `AILAB_GATEWAY_TOKEN`;
- если token не задан — запрашивают его скрытым вводом;
- не сохраняют token на диск;
- запускают OpenCode через `opencode run`;
- требуют явный working directory;
- используют `--pure`.

## Usage

### Read-only

```bash
oc-ailab-readonly <dir> "<prompt>"
```

Пример:

```bash
oc-ailab-readonly "$HOME/llm/AI-Lab" \
  "Read README.md and summarize the source-of-truth rules. Do not edit files."
```

### Bounded edit

```bash
oc-ailab-edit <dir> "<prompt>"
```

Пример:

```bash
oc-ailab-edit "$HOME/tmp/sandbox" \
  "Modify only file.md. Replace the first line with exactly: test. Do not use bash. Do not use subagents. Do not access the web."
```

## Wrapper: `oc-ailab-readonly`

```bash
#!/usr/bin/env bash
set -euo pipefail

OPENCODE="${OPENCODE:-$HOME/.opencode/bin/opencode}"

if [ $# -lt 2 ]; then
  echo "Usage: oc-ailab-readonly <dir> <prompt...>" >&2
  exit 2
fi

WORKDIR="$1"
shift
PROMPT="$*"

if [ ! -d "$WORKDIR" ]; then
  echo "ERROR: directory does not exist: $WORKDIR" >&2
  exit 2
fi

if [ -z "${AILAB_GATEWAY_TOKEN:-}" ]; then
  read -rsp "Paste AILAB gateway token here, hidden input: " AILAB_GATEWAY_TOKEN
  printf '\n' >&2
  export AILAB_GATEWAY_TOKEN
fi

OPENCODE_CONFIG_CONTENT='{
  "$schema": "https://opencode.ai/config.json",
  "model": "ailab/qwen3.6:27b",
  "small_model": "ailab/qwen3.6:27b",
  "provider": {
    "ailab": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "AI Lab llm-gateway",
      "options": {
        "baseURL": "http://192.168.0.128:8000/v1",
        "apiKey": "{env:AILAB_GATEWAY_TOKEN}"
      },
      "models": {
        "qwen3.6:27b": {
          "name": "Qwen3.6 27B via llm-gateway",
          "limit": {
            "context": 8192,
            "output": 512
          }
        }
      }
    }
  },
  "permission": {
    "read": "allow",
    "glob": "allow",
    "grep": "allow",
    "list": "allow",
    "edit": "deny",
    "bash": "deny",
    "task": "deny",
    "webfetch": "deny",
    "websearch": "deny",
    "external_directory": "deny",
    "todowrite": "allow",
    "skill": "deny"
  }
}' "$OPENCODE" run \
  --model ailab/qwen3.6:27b \
  --dir "$WORKDIR" \
  --pure \
  "$PROMPT"
```

## Wrapper: `oc-ailab-edit`

```bash
#!/usr/bin/env bash
set -euo pipefail

OPENCODE="${OPENCODE:-$HOME/.opencode/bin/opencode}"

if [ $# -lt 2 ]; then
  echo "Usage: oc-ailab-edit <dir> <prompt...>" >&2
  exit 2
fi

WORKDIR="$1"
shift
PROMPT="$*"

if [ ! -d "$WORKDIR" ]; then
  echo "ERROR: directory does not exist: $WORKDIR" >&2
  exit 2
fi

if [ -z "${AILAB_GATEWAY_TOKEN:-}" ]; then
  read -rsp "Paste AILAB gateway token here, hidden input: " AILAB_GATEWAY_TOKEN
  printf '\n' >&2
  export AILAB_GATEWAY_TOKEN
fi

OPENCODE_CONFIG_CONTENT='{
  "$schema": "https://opencode.ai/config.json",
  "model": "ailab/qwen3.6:27b",
  "small_model": "ailab/qwen3.6:27b",
  "provider": {
    "ailab": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "AI Lab llm-gateway",
      "options": {
        "baseURL": "http://192.168.0.128:8000/v1",
        "apiKey": "{env:AILAB_GATEWAY_TOKEN}"
      },
      "models": {
        "qwen3.6:27b": {
          "name": "Qwen3.6 27B via llm-gateway",
          "limit": {
            "context": 8192,
            "output": 512
          }
        }
      }
    }
  },
  "permission": {
    "read": "allow",
    "glob": "allow",
    "grep": "allow",
    "list": "allow",
    "edit": "allow",
    "bash": "deny",
    "task": "deny",
    "webfetch": "deny",
    "websearch": "deny",
    "external_directory": "deny",
    "todowrite": "allow",
    "skill": "deny"
  }
}' "$OPENCODE" run \
  --model ailab/qwen3.6:27b \
  --dir "$WORKDIR" \
  --pure \
  "$PROMPT"
```

## Permission profiles

### Read-only profile

| Permission | Value | Purpose |
|---|---|---|
| `read` | `allow` | read files inside `--dir` |
| `glob` | `allow` | find files |
| `grep` | `allow` | search text |
| `list` | `allow` | directory listing if supported |
| `edit` | `deny` | no file modifications |
| `bash` | `deny` | no shell execution |
| `task` | `deny` | no subagents |
| `webfetch` | `deny` | no URL fetch |
| `websearch` | `deny` | no web search |
| `external_directory` | `deny` | no access outside `--dir` |
| `todowrite` | `allow` | internal todo list only |
| `skill` | `deny` | no skill loading |

### Bounded-edit profile

| Permission | Value | Purpose |
|---|---|---|
| `read` | `allow` | read files inside `--dir` |
| `glob` | `allow` | find files |
| `grep` | `allow` | search text |
| `list` | `allow` | directory listing if supported |
| `edit` | `allow` | allow file write/edit/apply_patch inside boundary |
| `bash` | `deny` | no shell execution |
| `task` | `deny` | no subagents |
| `webfetch` | `deny` | no URL fetch |
| `websearch` | `deny` | no web search |
| `external_directory` | `deny` | no access outside `--dir` |
| `todowrite` | `allow` | internal todo list only |
| `skill` | `deny` | no skill loading |

## Validation summary

| Test | Result |
|---|---:|
| Read-only edit denial | PASS |
| Read-only bash denial | PASS |
| Bounded-edit write inside sandbox | PASS |
| Bounded-edit bash denial | PASS |
| Bounded-edit task/subagent denial | PASS |
| Bounded-edit webfetch denial | PASS by result |
| Bounded-edit websearch denial | PASS by result |
| Bounded-edit external directory denial | PASS |
| Token literal leak in scripts | PASS |
| No lingering `opencode` process | PASS |

## Operational rules

1. Do not store gateway token inside wrapper scripts.
2. Do not use `edit=ask` for scripted `opencode run` until separately validated.
3. For scripted bounded edit, use `edit=allow` with `bash/task/web/external_directory=deny`.
4. Always verify actual file/diff after run.
5. Do not trust model self-report about available tools.
6. Treat `Invalid Tool`, filesystem state, git diff and gateway logs as evidence.
7. Before changing profile or scenario, stop current run and check for lingering `opencode` processes.

## Current status

```text
READONLY_WRAPPER_STATUS=validated
BOUNDED_EDIT_WRAPPER_STATUS=validated_in_sandbox
REPO_WRITE_STATUS=not_yet_validated
```

---

## Approved repo-write mode

`oc-ailab-edit` прошёл controlled repo-write smoke против AI-Lab documentation repo.

Evidence:

```text
adee92f test: validate OpenCode bounded repo write
```

Разрешённый режим:

```text
OPEN_CODE_REPO_WRITE_MODE=allowed_only_for_small_scoped_docs_edits_with_manual_review
AUTONOMOUS_AGENT_READY=no
```

### Usage constraints

Разрешено:

- small scoped documentation edits;
- explicit directory boundary via wrapper argument;
- one small change set per run;
- manual review before commit;
- deterministic post-checks.

Обязательно после каждого write-run:

```bash
pgrep -af 'opencode' || echo "NO_OPENCODE_PROCESS_FOUND"
git status --short --branch
git diff
grep -RInE 'sk-lab-|AILAB_GATEWAY_TOKEN|Bearer ' <changed-path> || true
```

Запрещено:

- using OpenCode as autonomous repo agent;
- enabling `bash`;
- enabling `task` / subagent;
- enabling `webfetch` / `websearch`;
- enabling `external_directory`;
- using `edit=ask` in scripted `opencode run`;
- using `--dangerously-skip-permissions`.

### Tool boundary wording

Use this evidence wording:

```text
No successful use of bash/task/web/external_directory was observed.
These tools are denied by wrapper policy.
The visible OpenCode trace showed only read/edit operations inside the scoped directory.
Post-state checks showed no boundary breach.
```

Do not overstate this as full internal telemetry proof.

### PATH note

If shell returns:

```text
oc-ailab-edit: No such file or directory
```

use the absolute wrapper path:

```bash
/home/vladimir/.local/bin/oc-ailab-edit <dir> "<prompt>"
```

or ensure `~/.local/bin` is present in `PATH`.
