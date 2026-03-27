---
tags: [грабли, gateway, ollama]
дата: 2026-03-16
этап: "[[Этап07A — Continue Agent]]"
компонент: "[[gateway.py]]"
---

# Ollama tool_calls формат отличается от OpenAI

## Симптом
Agent получает пустой ответ через шлюз.

## Причина
Ollama: arguments=dict, index внутри function, нет type.
OpenAI: arguments=JSON string, index top-level, type="function".

## Решение
Конвертер `convert_ollama_tool_calls_to_openai()` в gateway.py v0.7.0.
`finish_reason: "tool_calls"` вместо `"stop"`.

