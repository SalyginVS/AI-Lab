---
tags: [грабли, инструменты, отладка]
дата: 2026-03-28
этап: "9A"
компонент: gateway.py
статус: зафиксировано
---

# 23 curl без jq для embeddings нечитаем

## Проблема

`curl` на `/v1/embeddings` без пайпа в `jq` возвращает сплошной поток чисел — вектор из сотен float-значений. Проверить форму ответа (наличие полей `object`, `data`, `usage`, `index`) практически невозможно.

## Решение

**Всегда** пайпить в `jq` с проекцией только нужных полей:

```bash
# Проверка формы без вектора
curl -s http://localhost:8000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3-embedding","input":["alpha","beta"]}' \
  | jq '{object, model, usage, data_count: (.data | length), indexes: [.data[].index]}'

# HTTP-код отдельно
curl -s -o /dev/null -w "%{http_code}\n" \
  http://localhost:8000/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3-embedding","input":"test"}'
```

## Правило

Для embedding-эндпоинтов: проверять **форму ответа** (структуру), а не содержимое вектора. HTTP-код и тело JSON — всегда две отдельные команды.

## Связь

[[Этапы/Этап009|Этап 9A]], [[Грабли/25 HTTP-код и тело JSON — отдельные проверки|25]]
