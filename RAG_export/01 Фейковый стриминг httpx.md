---
tags: [грабли, gateway, ollama]
дата: 2026-03-15
этап: "[[Этап01 — Диагностика шлюза]]"
компонент: "[[gateway.py]]"
---

# Фейковый стриминг httpx

## Симптом
TTFT равен полному времени генерации. Клиент ждёт 30-120 секунд до первого символа.

## Причина
`httpx.AsyncClient.post()` буферизует весь ответ в память. `resp.aiter_lines()` итерирует по уже загруженному буферу.

## Решение
Ручной streaming mode:
```python
req = client.build_request("POST", url, json=payload)
resp = await client.send(req, stream=True)
# BackgroundTask(resp.aclose) для закрытия
```

## Результат
TTFT: ~full time → **0.12 сек**. Решено в gateway.py v0.6.0 (Этап 6).

