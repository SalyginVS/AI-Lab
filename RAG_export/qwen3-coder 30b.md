---
tags: [модель, qwen]
---

# qwen3-coder:30b

**Основная модель Agent + Code + Edit.** Единственная 30B-модель с надёжным function calling в Ollama.

| Параметр | Значение |
|----------|----------|
| Размер | 18 ГБ (Q4_K_M) |
| Параметры | 30B |
| Контекст | 8192 (наш дефолт) |
| Capabilities | completion, tools |
| Провайдер | openai (через шлюз) |

## Роли в платформе
- **Agent mode** — основная (tool calling подтверждён)
- **Edit / Refactor** — основная
- **Apply** — подтверждён
- **Chat** — доступен

## Настройки
- temperature: 0.3 (кодирование)
- reasoning_effort: none (instruct-модель, не thinking)
- timeout: 600000

## Связано с
- [[glm-4.7-flash]] — альтернатива для Agent mode
- [[02 qwen3.5 tool calling сломан]] — почему НЕ qwen3.5 для Agent

