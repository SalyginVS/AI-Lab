---
tags: [грабли, continue, vllm, mtp]
дата: 2026-05-08
этап: "[[Этап — Qwen3.6 27B MTP / Continue bounded lane]]"
компонент: "[[Continue.dev]]"
---

# Continue запросил output tokens равные всему context window

## Симптом

vLLM MTP lane отвергал запрос: Continue фактически запрашивал `4096` output tokens при `max_model_len=4096`.

## Причина

Для MTP lane context window малый: `4096`. Если output cap равен всему окну контекста, то на input prompt не остаётся допустимого бюджета.

## Решение

Для Continue profile установить явный bounded output cap:

```yaml
defaultCompletionOptions:
  maxTokens: 512
requestOptions:
  extraBodyProperties:
    num_ctx: 4096
    max_tokens: 512
    reasoning_effort: "none"
```

Operational rule: для каждого backend lane фиксировать отдельно:

- context window;
- output token cap;
- Continue `maxTokens`;
- backend-specific `max_tokens`;
- failure mode при превышении бюджета.
