---
tags:
  - грабли
  - gateway
  - timeout
дата: 2026-04-05
этап: "015"
компонент: gateway
---

# 45 Gateway HTTPX_TIMEOUT 600s недостаточен

## Симптом

Gateway прерывает long-context запрос по timeout до завершения prompt processing.

## Причина

`HTTPX_TIMEOUT = 600.0` (10 мин) в `gateway/__init__.py`. Достаточно для стандартных ctx (8K–32K), но недостаточно для cold-start + long prompt eval при ctx 65K+.

## Решение

`HTTPX_TIMEOUT = 3600.0` (1 час) в `gateway/__init__.py`. Применено в этапе 15.

## Связи

- [[Этап 015]]
- [[43 Gemma 4 long-context stall в Ollama 0.20.0]]
