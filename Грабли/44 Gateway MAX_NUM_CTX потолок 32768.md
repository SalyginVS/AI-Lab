---
tags:
  - грабли
  - gateway
дата: 2026-04-05
этап: "015"
компонент: gateway
---

# 44 Gateway MAX_NUM_CTX потолок 32768

## Симптом

Gateway отклоняет запросы с num_ctx > 32768 (Pydantic validation error).

## Причина

Жёстко заданный потолок `MAX_NUM_CTX = 32768` в `gateway/models.py`. Установлен при начальной разработке gateway, не пересматривался после появления моделей с ctx 128K+.

## Решение

`MAX_NUM_CTX = 131072` в `gateway/models.py`. Применено в этапе 15.

## Связи

- [[Этап 015]]
- [[43 Gemma 4 long-context stall в Ollama 0.20.0]]
