---
tags: [грабли, continue]
дата: 2026-03-17
этап: "[[Этап07B — Autocomplete и Ollama 0.18]]"
компонент: "[[Continue.dev]]"
---

# extraBodyProperties — внутри requestOptions

## Симптом
HTTP 400 от Ollama. Параметры `num_ctx`, `reasoning_effort` не передаются.

## Причина
`extraBodyProperties` вложено внутри `requestOptions`, не peer-level.

## Решение
```yaml
# ✅ Правильно:
requestOptions:
  timeout: 600000
  extraBodyProperties:
    num_ctx: 8192
    reasoning_effort: "none"
```
