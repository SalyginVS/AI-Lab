# Continue / VS Code Integration Result — Qwen3.6 27B MTP

Дата: 2026-05-08
Клиент: Ubuntu laptop `vladimir-Precision-5560`
Сервер: `192.168.0.128` / host `llm`
Профиль Continue: `qwen36-27b-mtp-bounded`
Model id: `qwen3.6-27b-lorbus-mtp-triton-ctx4k`

---

## 1. Executive Summary

Интеграция `qwen3.6-27b-lorbus-mtp-triton-ctx4k` в VS Code / Continue через существующий OpenAI-compatible gateway выполнена.

Итоговый статус:

```text
STATUS=PASS_WITH_MINOR_CONTRACT_DEVIATION
```

Рабочая цепочка подтверждена:

```text
Continue / VS Code
  -> http://192.168.0.128:8000/v1
  -> llm-gateway
  -> vLLM MTP on 127.0.0.1:8027
  -> qwen3.6-27b-lorbus-mtp-triton-ctx4k
```

---

## 2. Verified Facts

### 2.1 Backend / Runtime

- vLLM MTP service отвечает на `/v1/models`.
- Gateway `0.12.0` healthy.
- Gateway non-stream completion через MTP lane возвращал корректный ответ.
- Gateway streaming completion через MTP lane после patch возвращал SSE stream и `data: [DONE]`.
- Continue UI после fixes успешно получил ответ через MTP lane.
- Gateway logs подтвердили:
  - `provider=vllm-mtp`
  - `stream=True`
  - `status_code=200`
  - `error=null`

### 2.2 Continue / VS Code

- VS Code CLI найден: `/snap/bin/code`.
- Continue extension найден: `continue.continue`.
- Активный config: `/home/vladimir/.continue/config.yaml`.
- Локальный tunnel `127.0.0.1:8000` на ноуте отсутствует.
- Прямой LAN-доступ к gateway работает: `http://192.168.0.128:8000/v1`.

### 2.3 Added Continue Profile

Добавлен отдельный bounded profile:

```yaml
- name: qwen36-27b-mtp-bounded
  provider: openai
  model: qwen3.6-27b-lorbus-mtp-triton-ctx4k
  apiBase: http://192.168.0.128:8000/v1
  apiKey: ***REDACTED***
  roles:
    - chat
    - edit
    - apply
  defaultCompletionOptions:
    temperature: 0.1
    maxTokens: 512
  requestOptions:
    timeout: 600000
    extraBodyProperties:
      num_ctx: 4096
      max_tokens: 512
      reasoning_effort: "none"
```

---

## 3. Issues Found and Fixed

### 3.1 Gateway streaming error masking

Initial Continue UI error:

```text
500 Internal gateway error:
ResponseNotRead: Attempted to access streaming response content, without having called read().
```

Root cause:

```text
gateway/chat.py -> raise_for_vllm_status()
```

The function tried to read `resp.json()` / `resp.text` from an httpx streaming response without `await resp.aread()`.

Fix applied:

- Added explicit `await resp.aread()` before reading error body.
- Added fallback error handling.
- Added `finally: await resp.aclose()`.
- Restarted `llm-gateway`.
- Regression passed.

### 3.2 Continue requested 4096 output tokens

After gateway patch, real upstream vLLM error became visible:

```text
400 vLLM rejected request:
This model's maximum context length is 4096 tokens.
However, you requested 4096 output tokens...
```

Fix applied in Continue profile:

```yaml
defaultCompletionOptions:
  maxTokens: 512

requestOptions:
  extraBodyProperties:
    max_tokens: 512
```

Rationale:

- vLLM MTP lane has `max_model_len=4096`.
- Continue was otherwise requesting the full 4096 tokens as output.
- This left zero effective room for input prompt/context.
- `512` is a conservative bounded-output setting for smoke/coding tasks.

---

## 4. Controlled Continue Coding Task

Scratch workspace:

```text
/home/vladimir/tmp/continue_mtp_smoke_20260508_102352
```

Target file:

```text
score_utils.py
```

Task:

```text
Fix only normalize_scores().
Add validation:
- raise ValueError if any score is negative
- raise ValueError if scale <= 0
```

Baseline test result:

```text
BASELINE_TEST_EXIT_CODE=1
```

Final verification:

```text
ALL_TESTS_PASSED
```

Final function:

```python
from typing import Iterable


def normalize_scores(scores: Iterable[int], scale: int = 100) -> list[int]:
    if scale <= 0:
        raise ValueError("scale must be greater than 0")

    cleaned = []
    for value in scores:
        if value is None:
            continue
        val = int(value)
        if val < 0:
            raise ValueError("scores must not contain negative values")
        cleaned.append(val)

    if not cleaned:
        return []

    max_score = max(cleaned)

    if max_score == 0:
        return [0 for _ in cleaned]

    return [round((item / max_score) * scale) for item in cleaned]
```

---

## 5. Output Contract Validation

| Contract item | Result | Notes |
|---|---:|---|
| Bounded function output | PASS | Model returned full replacement function only |
| No secrets access | PASS | No secret/path access requested or printed |
| No raw unified diff as executable artifact | PASS | Model did not output raw diff |
| Approval before apply | PASS | Change was manually applied by deterministic script, not auto-applied |
| Verification command discipline | MINOR DEVIATION | Model proposed its own `python3 -c` verification instead of required `python3 test_score_utils.py` |

Conclusion:

```text
qwen36-27b-mtp-bounded is usable as a controlled bounded executor candidate in Continue,
under external guardrails and deterministic apply/test workflow.
```

---

## 6. Allowed Usage

Allowed:

- bounded coding tasks;
- single-function replacement;
- complete-file output when explicitly requested;
- human-reviewed apply;
- deterministic tool-generated diff;
- syntax/test verification before commit.

Not allowed:

- autonomous multi-file agent;
- raw model-generated unified diff as primary patch artifact;
- secrets/config access;
- destructive shell commands;
- production config, systemd, gateway, Docker, CI/CD changes without explicit approval.

---

## 7. Operational Notes

### 7.1 Continue profile

Use:

```text
qwen36-27b-mtp-bounded
```

Do not use it as an autonomous Agent profile yet.

### 7.2 Gateway patch

Gateway source touched:

```text
/home/vladimir/llm-gateway/gateway/chat.py
```

Backup created:

```text
/home/vladimir/llm-gateway/backups/chat.py.before-vllm-status-read-20260508_070424.bak
```

### 7.3 Known repo hygiene issue

The server repo remains dirty/untracked from earlier work. Do not clean/reset/push as part of this integration unless separately requested.

Known observed state included:

```text
M __pycache__/gateway.cpython-312.pyc
D gateway.py
M orchestrator.py
M pipelines.yaml
?? gateway/
?? backups/
?? .gitignore
?? .githooks/
```

---

## 8. Definition of Done Check

| DoD item | Status |
|---|---:|
| Continue config path and format identified | DONE |
| MTP model added as distinct Continue lane/profile | DONE |
| Continue can call model through gateway | DONE |
| One controlled VS Code/Continue task executed | DONE |
| Output contract validated | DONE_WITH_MINOR_DEVIATION |
| Result documented in export layer | DONE |

---

## 9. Final Status

```text
FINAL_STATUS=CONTINUE_MTP_INTEGRATION_DONE
ROLE=controlled bounded executor candidate
PRODUCTION_AUTONOMOUS_AGENT_READY=no
NEXT_RECOMMENDED_ACTION=commit/document gateway patch after repo hygiene review
```
