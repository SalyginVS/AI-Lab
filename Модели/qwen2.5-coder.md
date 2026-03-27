---
tags: [модель, qwen]
---

# qwen2.5-coder (7b и 1.5b)

Семейство FIM (Fill-In-the-Middle) моделей для tab-autocomplete. Обучены специальным токенам `<|fim_prefix|>`, `<|fim_suffix|>`, `<|fim_middle|>`.

## qwen2.5-coder:7b — основная

| Параметр | Значение |
|----------|----------|
| Размер | 4.7 ГБ |
| Роль | **Autocomplete FIM** (резидентная) |
| Провайдер | ollama (напрямую, минуя шлюз) |
| Эндпоинт | /api/generate (не /v1/chat/completions) |

Настройки в Continue:
- `roles: [autocomplete]`
- `debounceDelay: 500`
- `maxPromptTokens: 2048`
- `timeout: 30000` (холодный старт)

## qwen2.5-coder:1.5b — fallback

| Параметр | Значение |
|----------|----------|
| Размер | 986 МБ |
| Роль | Autocomplete FIM fallback |

Если 7b мешает по памяти — переключиться на 1.5b.

## Почему FIM, а не chat
Chat-модели не обучены формату fill-in-the-middle. Они не понимают «вот код до курсора, вот код после, допиши середину». Для autocomplete нужны специально обученные FIM-модели.

