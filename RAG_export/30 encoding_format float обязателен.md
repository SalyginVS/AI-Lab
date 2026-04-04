---
tags:
  - грабли
  - continue
  - embeddings
  - gateway
дата: 2026-03-29
этап: 9B
компонент: Continue.dev, gateway.py
---

# 26 encoding_format float обязателен

## Симптом

После переключения Continue embeddings на `provider: openai` через gateway — массовые 400 Bad Request на все embedding-запросы. Индексация не происходит.

Точная ошибка:
```
Embedding: Failed to generate embeddings for 358 chunks with provider:
OpenAI2::qwen3-embedding::512: Error: 400 Only encoding_format='float' is supported
```

## Причина

Continue.dev с `provider: openai` использует OpenAI SDK, который по дефолту отправляет `encoding_format` со значением, отличным от `"float"` (предположительно `"base64"` — дефолт в OpenAI SDK v1.x). Gateway [[gateway.py]] v0.8.0 отвергал всё кроме `float`.

## Решение

Двухуровневый fix (defense in depth):

**Клиент** — добавить в `config.yaml`:
```yaml
requestOptions:
  extraBodyProperties:
    encoding_format: float
```

**Сервер** — hotfix в gateway.py: silent coerce вместо reject:
```python
if req.encoding_format is not None and req.encoding_format != "float":
    req.encoding_format = "float"
```

## Проверка

```bash
curl -s http://192.168.0.128:8000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3-embedding","input":"test","encoding_format":"base64"}' \
  | jq '.object'
# Ожидание: "list" (200 OK, coerced to float)
```

## Связи

- [[Этап010]] (9B)
- [[gateway.py]]
