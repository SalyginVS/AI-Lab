---
tags: [грабли, тестирование, контракт]
дата: 2026-03-28
этап: "9A"
компонент: gateway.py
статус: зафиксировано
---

# 22 Один happy path не подтверждает контракт

## Проблема

После реализации `POST /v1/embeddings` первый же happy path (single input, HTTP 200) выдавал корректный ответ. Соблазн — считать endpoint подтверждённым и двигаться дальше.

## Что оказалось

Negative tests вскрыли, что semantic validation и schema validation работают **независимо** и каждая требует отдельной проверки:

- `input=""` → должно быть 400 (semantic), а не 422 (schema) и не 200
- `input=[1,2]` → 422 (schema), а не 400 или 200
- `model=qwen3:30b` → 400 (allowlist policy), а не прокинуть в Ollama

Без negative tests эти три класса ошибок могли бы незаметно работать неправильно.

## Правило

**Endpoint считается подтверждённым только после полного набора: happy path + все классы негативных сценариев.**

Минимальный набор для любого нового endpoint в gateway.py:
1. Happy path (один или несколько)
2. Semantic validation (бизнес-правила)
3. Schema validation (Pydantic)
4. Policy-layer (allowlist/denylist, если есть)
5. Upstream error (Ollama недоступен / модель не загружена)

## Связь

[[Этапы/Этап009|Этап 9A]]
