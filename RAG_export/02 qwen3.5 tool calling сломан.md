---
tags: [грабли, ollama, модели]
дата: 2026-03-16
этап: "[[Этап07A — Continue Agent]]"
компонент: "[[qwen3.5 35b]]"
---

# qwen3.5:35b — tool calling сломан в Ollama

## Симптом
Agent mode: мусорный текст на китайском вместо tool_calls. Unclosed `<think>` tags. Hang на втором запросе на RTX 3090.

## Причина
1. qwen3.5:35b — thinking-модель, не соблюдает протокол function calling
2. До Ollama 0.17.6 — неправильный parser pipeline (Hermes JSON вместо Qwen-Coder XML)
3. После 0.18.0 — по-прежнему ненадёжен

## Решение
**Никогда не использовать для Agent mode / tool calling.** Только:
- **qwen3-coder:30b** — надёжный function calling
- **glm-4.7-flash** — tools работают

qwen3.5:35b допустим только для текстовых задач без tools.
