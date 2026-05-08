---
tags: [adr, решение, mtp, vllm, qwen, continue, longctx]
дата: 2026-05-08
статус: accepted
supersedes: ADR-027 partially
---

# ADR-028 — Qwen3.6 27B MTP 128K как special long-context heavy lane

## Контекст

Ранее Qwen3.6 27B Lorbus AutoRound MTP lane был принят как bounded 4K executor lane через vLLM и gateway provider `vllm-mtp`.

В ходе проверки 2026-05-08 установлено:

- 4K был не ограничением модели, а launch-параметром vLLM: `--max-model-len 4096`;
- модель распознаётся vLLM как MTP-capable;
- `--max-model-len auto` показал model-level capability до 262K, но без offload фактический KV-cache capacity был около 11.2K tokens;
- 128K стал рабочим после включения CPU offload;
- FP8 KV cache path в текущем runtime несовместим;
- direct vLLM smoke, gateway smoke и Continue smoke прошли.

## Решение

Принять Qwen3.6 27B Lorbus AutoRound MTP lane не как default fast executor, а как:

**special long-context heavy lane**

Назначение:

- большие контекстные задачи;
- редкие Continue Chat/Edit/Apply сценарии, где 128K context важнее latency;
- не default Agent lane;
- не замена Ollama dense models.

## Рабочий vLLM service

Unit:

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

Effective aliases:

```text
qwen3.6-27b-lorbus-mtp-triton-ctx4k
qwen3.6-27b-mtp
qwen3.6-27b-lorbus-mtp-longctx-128k
```

Все aliases exposed through vLLM with:

```text
max_model_len = 131072
```

## Effective launch profile

```text
--served-model-name qwen3.6-27b-lorbus-mtp-triton-ctx4k qwen3.6-27b-mtp qwen3.6-27b-lorbus-mtp-longctx-128k
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

## Gateway routing

Gateway currently routes the historical name:

```text
qwen3.6-27b-lorbus-mtp-triton-ctx4k
```

to provider:

```text
vllm-mtp
```

Therefore Continue must keep using the historical routed model id until gateway routing is explicitly refactored.

## Continue profile contract

Continue model id:

```text
qwen3.6-27b-lorbus-mtp-triton-ctx4k
```

Operational name may be:

```text
qwen36-27b-mtp-longctx-128k
```

Required request properties:

```text
num_ctx: 131072
max_tokens: 1024
reasoning_effort: "none"
chat_template_kwargs.enable_thinking: false
```

Do not start with `max_tokens=4096`. Increase to `2048` only after explicit latency/quality need.

## Memory result

Observed working memory gate:

```text
Available KV cache memory: 17.25 GiB
GPU KV cache size: 255,975 tokens
Maximum concurrency for 131,072 tokens per request: 1.95x
Application startup complete
```

## Compatibility findings

Do not use in current runtime path:

```text
--kv-cache-dtype fp8
--kv-cache-dtype fp8_e5m2
```

Observed result:

- `fp8` selected an unsupported FP8 architecture path;
- `fp8_e5m2` passed CLI but failed in attention path assertion;
- default KV dtype with CPU offload is the accepted working path.

## Routing decision

Default speed-sensitive Continue work remains on Ollama dense models.

Qwen3.6 27B MTP 128K is enabled only when large context matters more than latency.

## Consequences

- vLLM MTP 128K and Ollama heavy models must not be assumed to coexist on one RTX 3090.
- A lane switch procedure is required.
- ADR-027 remains historical for the original bounded 4K integration, but is superseded for current operating mode.
- Future architecture/passport versions must reflect this lane as special long-context heavy lane, not default fast executor.
