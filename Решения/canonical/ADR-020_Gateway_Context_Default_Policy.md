# ADR-020: Gateway Context Default Policy — снятие 8K потолка

**Дата:** 2026-04-15  
**Статус:** Accepted  
**Слой:** L1 — Canonical  
**Компоненты:** Inference/Backend (Layer 1), gateway v0.12.0  
**Связанные ADR:** ADR-012 (Gemma 4 Model Integration), ADR-018 (Semantic Layer)

---

## Контекст

Gateway имел `DEFAULT_NUM_CTX = 8192` в `__init__.py` и hardcoded `8192` в `orchestrate.py`. При этом `MAX_NUM_CTX` был уже поднят до `131072` (Этап 15). В результате все запросы без явного `num_ctx` получали 8K контекст, несмотря на то что модели (gemma4:31b, qwen3-coder:30b) поддерживают до 256K.

Это создавало невидимый потолок: модели были способны на больший контекст, но gateway не давал им его использовать. Симптом был ранее ошибочно атрибутирован upstream багам (llama.cpp SWA, Ollama FA), хотя root cause находился в integration layer.

## Решение

**Поднять DEFAULT_NUM_CTX до 131072 в обеих точках:**

1. `gateway/__init__.py`: `DEFAULT_NUM_CTX = 131072`
2. `gateway/orchestrate.py`: `num_ctx = step_cfg.get("num_ctx", 131072)`

## Валидация

После патча и рестарта gateway:
- `POST /v1/chat/completions` с gemma4:31b
- `prompt_tokens = 131072`, `completion_tokens = 1232`, `total_tokens = 132304`
- Запрос завершён успешно (~10 минут end-to-end)

## Последствия

### Подтверждено
- Gateway больше не ограничивает effective prompt context на 8K
- gemma4:31b через gateway обрабатывает 131K prompt tokens
- Root cause 8K ceiling = gateway defaults, не Ollama, не Gemma 4

### Не подтверждено (требует отдельной валидации)
- Повторяемая стабильность long-context workloads (GPU util не измерен)
- Рутинная стабильность 4–8K промптов на Ollama 0.20.7
- Влияние на RAM/VRAM pressure при регулярном использовании 131K

### Открытые вопросы (#25, #32) — переоценка
- Вопрос #25 (SWA stall 65K+): один успешный run на 131K — позитивный сигнал, но GPU util не измерен, повторяемость не подтверждена. Статус: [A] Partially addressed.
- Вопрос #32 (FA bug 0.20.4): Ollama 0.20.7 установлена, 131K прошёл, но рутинная стабильность не валидирована. Статус: [A] Partially addressed.

### Tech debt
- `131072` в `orchestrate.py` — hardcoded дубликат вместо `from gateway import DEFAULT_NUM_CTX`. Тактический fix, рефакторинг при следующем релизе gateway.

## Архитектурный принцип (новый)

**Integration layer defaults must match platform capability.** Дефолтные значения в gateway должны отражать реальные возможности inference layer, а не исторические ограничения. Расхождение между capability и default создаёт invisible bottleneck, который маскируется под upstream проблему (Грабли #71).

## Альтернативы (отложены)

- **Model-specific context policy** (gemma4:31b → 131072, qwen3.5:9b → 32768): корректнее, но требует routing-aware defaults. Отложено до следующей ревизии gateway.
- **Client-specified num_ctx only** (убрать default): опасно — клиенты без явного num_ctx получат модельный default, который может быть слишком мал или слишком велик.
