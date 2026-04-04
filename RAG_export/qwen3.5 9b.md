---
tags: [модель, qwen]
---

# qwen3.5:9b

Быстрый повседневный чат. Dense-архитектура (не MoE как 35b). Замена тяжёлой qwen3.5:35b для рутинных задач.

| Параметр | Значение |
|----------|----------|
| Размер | 6.6 ГБ |
| Архитектура | qwen35 (dense) |
| Параметры | 9.7B |
| Capabilities | completion, vision, tools, thinking |

## Роли в платформе
- **Повседневный chat** — основная лёгкая модель
- **Vision** — поддерживает image_input
- Chat, Edit, Apply — доступен

## Настройки
- temperature: 0.7
- reasoning_effort: none (дефолт)
