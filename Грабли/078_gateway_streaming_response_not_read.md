---
tags: [грабли, gateway, vllm, streaming]
дата: 2026-05-08
этап: "[[Этап — Qwen3.6 27B MTP / Continue bounded lane]]"
компонент: "[[gateway]]"
---

# Gateway streaming response body был прочитан некорректно

## Симптом

Continue / gateway integration с vLLM MTP lane давала ошибку уровня 500 / `ResponseNotRead` при streaming path, хотя upstream vLLM backend был доступен.

## Причина

Gateway пытался обработать streaming response как обычный response body. Для streaming response нужно явно прочитать/закрыть body корректным способом, иначе error masking скрывает реальную upstream-причину.

## Решение

В gateway patch добавить корректный read/close handling для vLLM response перед формированием ошибки/ответа.

Operational rule: при интеграции нового OpenAI-compatible backend проверять отдельно:

- non-stream completion;
- streaming completion;
- upstream error propagation;
- gateway log fields: provider, stream, status_code, error.
