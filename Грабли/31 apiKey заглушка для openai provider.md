---
tags:
  - грабли
  - continue
  - embeddings
дата: 2026-03-29
этап: 9B
компонент: Continue.dev
---

# 27 apiKey заглушка для openai provider

## Симптом

При настройке embedding-модели с `provider: openai` и отсутствующим полем `apiKey` — Continue не отправляет запросы к gateway. Ошибок в UI нет, но индексация молча не происходит.

## Причина

Continue.dev с `provider: openai` проверяет наличие `apiKey` до отправки запросов. При отсутствии — запросы не формируются. Gateway auth при этом опциональна и не требует реального ключа.

## Решение

Добавить любую непустую строку в поле `apiKey`:
```yaml
- name: qwen3-embedding
  provider: openai
  apiKey: ollama    # заглушка — gateway auth опциональна
  ...
```

## Урок

При использовании `provider: openai` для подключения к non-OpenAI endpoint — всегда указывать `apiKey` даже если сервер не проверяет auth. Это ограничение клиентской библиотеки, не серверной.

## Связи

- [[Этап010]] (9B)
- [[26 encoding_format float обязателен]]
