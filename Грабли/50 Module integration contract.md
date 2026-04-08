---
tags: [грабли, gateway, integration, python]
дата: 2026-04-07
этап: 16
компонент: gateway
---

# 50 Module integration contract mismatch

## Симптом

Три ошибки при интеграции нового модуля `orchestrate.py`:

1. `ImportError: cannot import name 'logger' from 'gateway.errors'`
2. /metrics endpoint bucket = `"unknown"` вместо `/v1/orchestrate`
3. Structured log event: JSON строка внутри `message` вместо structured fields

## Причина

`orchestrate.py` написан Claude на основе документации, а не по live коду. Три несовпадения с реальным internal API пакета:

1. `logger` живёт в `logging_config.py`, не экспортируется из `errors.py`
2. `MetricsCollector.record()` ожидает ключ `endpoint`, orchestrate.py передавал `path`
3. Gateway `JSONFormatter` собирает structured fields из `extra={}`, а не из `json.dumps()` в message

## Решение

Три точечные правки в orchestrate.py при деплое: исправить import, field name, logging pattern.

## Урок

При написании нового модуля для существующего пакета — всегда проверять imports и internal contracts по live коду (`scp` с сервера), не по документации и не по памяти. Усиление [[32 Deployment file mismatch]]: mismatch может быть не только в файлах, но и в API-контрактах между модулями.

## Связано

- [[Этап016]]
- [[32 Deployment file mismatch]]
