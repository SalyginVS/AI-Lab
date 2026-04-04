---
tags: [грабли, gateway, python]
дата: 2026-03-15
этап: "[[Этап03 — Параметры генерации]]"
компонент: "[[gateway.py]]"
---

# logging: использовать uvicorn.error, не custom name

## Симптом
Логи не появляются в `journalctl -u llm-gateway`.

## Причина
`logging.getLogger("my-name")` без handler'а → нет вывода. uvicorn уже настроил handler для `"uvicorn.error"`.

## Решение
```python
logger = logging.getLogger("uvicorn.error")
```
