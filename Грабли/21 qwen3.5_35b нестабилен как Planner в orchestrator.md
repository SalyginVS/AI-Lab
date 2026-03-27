---
tags: [грабли, ollama, модели, orchestrator]
дата: 2026-03-27
этап: "8C"
компонент: ollama
статус: активная
---

# qwen3.5:35b нестабилен как Planner в orchestrator

## Симптом

При запуске `plan-execute-review` pipeline с `qwen3.5:35b` в роли Planner:
- gateway.py возвращает **500 / 502**
- Логи Ollama: `model failed to load` / `llama runner terminated`
- Pipeline падает на первом шаге

## Условия воспроизведения

- Ollama 0.18.0, RTX 3090 24 ГБ
- `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`
- Модель `qwen3.5:35b` (23 ГБ) загружается в контексте orchestrator

## Причина (гипотеза)

Нестабильность llama-runner при загрузке модели в конкретной конфигурации Ollama 0.18.0 + RTX 3090. Модель нормально работает в интерактивном chat-режиме (Continue.dev), но при вызове через orchestrator.py даёт сбой. Точная причина не установлена.

## Решение

Planner переключён на [[qwen3:30b]] (18 ГБ). Модель:
- Стабильна при загрузке
- Вписывается в VRAM при текущей квантизации
- Демонстрирует качественное планирование

**ADR:** [[ADR-001 Planner qwen3:30b вместо qwen3.5:35b]]

## Статус qwen3.5:35b

Остаётся **Active** для экспериментального chat (Continue.dev). В orchestrator **не использовать** до:
1. Отдельного PoC с диагностикой загрузки
2. Возможного обновления Ollama
3. Явного обновления паспорта лаборатории

## Связанные грабли

- [[Грабли/qwen3.5 tool calling сломан в Ollama]] — отдельная проблема (function calling), не связана напрямую
