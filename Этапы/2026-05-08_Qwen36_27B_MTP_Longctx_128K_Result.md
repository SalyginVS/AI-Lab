---
tags: [этап, результат, qwen, mtp, vllm, continue, gateway]
дата: 2026-05-08
статус: done
---

# 2026-05-08 — Qwen3.6 27B MTP Longctx 128K Result

## Итог

PASS.

Qwen3.6 27B Lorbus AutoRound MTP model успешно переведена из исторического 4K bounded vLLM lane в working 128K long-context MTP lane.

## Проверенные уровни

- vLLM direct smoke: PASS
- gateway smoke: PASS
- Continue smoke: PASS
- default Ollama lane restored after test: PASS

## Рабочий vLLM backend

Service:

```text
vllm-qwen36-mtp.service
```

Port:

```text
127.0.0.1:8027
```

Model path:

```text
/home/vladimir/models/qwen36-27b-lorbus-autoround
```

Aliases:

```text
qwen3.6-27b-lorbus-mtp-triton-ctx4k
qwen3.6-27b-mtp
qwen3.6-27b-lorbus-mtp-longctx-128k
```

All aliases expose:

```text
max_model_len = 131072
```

## Рабочий launch profile

```text
--language-model-only
--max-model-len 131072
--gpu-memory-utilization 0.97
--cpu-offload-gb 12
--max-num-seqs 1
--generation-config vllm
--enforce-eager
--attention-backend TRITON_ATTN
--speculative-config {"method":"mtp","num_speculative_tokens":1}
```

## Проверенный memory gate

Observed:

```text
Available KV cache memory: 17.25 GiB
GPU KV cache size: 255,975 tokens
Maximum concurrency for 131,072 tokens per request: 1.95x
Application startup complete
```

## Gateway route

Current gateway route uses historical model id:

```text
qwen3.6-27b-lorbus-mtp-triton-ctx4k
```

This historical name now maps to vLLM backend with 128K context.

Do not use these names through gateway until gateway routing is explicitly updated:

```text
qwen3.6-27b-mtp
qwen3.6-27b-lorbus-mtp-longctx-128k
```

They exist as vLLM aliases, but gateway may route them incorrectly.

## Continue profile

Required:

```yaml
name: qwen36-27b-mtp-longctx-128k
provider: openai
model: qwen3.6-27b-lorbus-mtp-triton-ctx4k
apiBase: http://192.168.0.128:8000/v1
roles: [chat, edit, apply]
temperature: 0.1
maxTokens: 1024
num_ctx: 131072
max_tokens: 1024
reasoning_effort: none
chat_template_kwargs.enable_thinking: false
```

## Critical lessons

1. Original 4K limit was launch-level, not model-level.
2. `--max-model-len auto` exposed model-level 262K capability but runtime KV capacity without offload was only about 11.2K.
3. `--cpu-offload-gb 12` made 128K feasible.
4. FP8 KV cache flags are not usable in current runtime path.
5. `chat_template_kwargs.enable_thinking=false` is required to avoid visible thinking-style output.
6. Ollama dense models are faster in practical visual comparison and remain default.
7. vLLM MTP 128K is special long-context heavy lane, not default fast executor.
8. vLLM MTP 128K conflicts with Ollama heavy model loading on the same RTX 3090.

## Final operational decision

Default:

```text
Ollama dense models for normal Continue Chat/Edit/Apply/Agent work.
```

Special:

```text
vLLM Qwen3.6 27B MTP 128K only for long-context tasks where context capacity matters more than latency.
```

## Follow-up documentation

Required follow-up updates:

- Паспорт лаборатории v35
- Целевая архитектура v1.21
- Roadmap
- Continue config reference
- possible gateway route cleanup ADR/MOC later
