---
tags: [adr, решение, mtp, continue, gateway, qwen]
дата: 2026-05-08
статус: accepted
---

# ADR-027 — Qwen3.6 27B MTP как bounded executor lane, не Agent

## Контекст

В лаборатории появился дополнительный inference backend lane: `vLLM MTP` для модели `qwen3.6-27b-lorbus-mtp-triton-ctx4k`. Lane подключён к существующему OpenAI-compatible gateway и доступен в Continue / VS Code как profile `qwen36-27b-mtp-bounded`.

MTP (Multi-Token Prediction — предсказание нескольких токенов за шаг) потенциально улучшает latency/throughput profile, но не является доказательством безопасного autonomous agent behavior.

## Решение

Принять `qwen3.6-27b-lorbus-mtp-triton-ctx4k` как **controlled bounded executor candidate**.

Разрешённый профиль:

```text
Continue / VS Code
  -> gateway /v1
  -> provider=vllm-mtp
  -> vLLM MTP 127.0.0.1:8027
  -> qwen3.6-27b-lorbus-mtp-triton-ctx4k
```

Обязательные параметры:

```yaml
num_ctx: 4096
max_tokens: 512
reasoning_effort: "none"
temperature: 0.1
roles: [chat, edit, apply]
```

## Разрешено

- bounded coding tasks;
- small scoped edits;
- human-reviewed apply;
- deterministic tool-generated diff после review;
- syntax/test verification до commit.

## Запрещено

- autonomous multi-file agent;
- secrets/config access;
- destructive shell commands;
- production config, systemd, gateway, Docker, CI/CD changes без отдельного approval gate;
- использование raw model-generated patch как единственного источника изменения.

## Последствия

- MTP lane добавляется в архитектуру как отдельный backend lane, а не как замена Ollama.
- Promotion path в Agent возможен только после отдельного validation gate.
- Performance optimization не отменяет instruction-following validation, safety boundary и source-of-truth discipline.

## Связанные документы

- [[Целевая_архитектура_AI_Coding_Platform_v1_20]]
- [[Паспорт_лаборатории_v34]]
- [[078_gateway_streaming_response_not_read]]
- [[079_continue_max_tokens_equals_context_window]]
- [[080_runtime_repo_not_source_of_truth]]
