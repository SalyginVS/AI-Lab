---
tags: [модель, deepseek]
---

# deepseek-r1 (32b и 14b)

Семейство reasoning-моделей для глубокого математического и логического анализа.

## deepseek-r1:32b

| Параметр | Значение |
|----------|----------|
| Размер | 19 ГБ |
| Роль | Deep math/reasoning, code review |

- **Reviewer** в orchestrator pipeline (Этап 8C)
- **Headless auto-review** (Этап 8D)
- Chat (reasoning) в Continue

Настройки: temperature 0.6, reasoning_effort: medium.

## deepseek-r1:14b

| Параметр | Значение |
|----------|----------|
| Размер | 9.0 ГБ |
| Роль | Компактная math/reasoning |

Резервная модель для случаев когда 32b слишком тяжела (например, параллельно с другой 30B моделью в памяти).

