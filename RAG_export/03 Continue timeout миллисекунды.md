---
tags: [грабли, continue]
дата: 2026-03-16
этап: "[[Этап07A — Continue Agent]]"
компонент: "[[Continue.dev]]"
---

# Continue.dev timeout — миллисекунды, не секунды

## Симптом
Agent mode: каскад запросов, ни один не завершается. "Connection error".

## Причина
OpenAI Node.js SDK принимает `timeout` в **миллисекундах**. `timeout: 600` = 0.6 сек.

## Решение
```yaml
requestOptions:
  timeout: 600000   # 10 минут
```
Autocomplete: `timeout: 30000` (30 сек).

