---
tags: [грабли, env, bash, security]
дата: 2026-04-07
этап: 16
компонент: deployment
---

# 49 Shell .env JSON quoting

## Симптом

`source ~/llm-gateway/.env` → `json.decoder.JSONDecodeError` при валидации `LLM_GATEWAY_TOKENS`.

## Причина

`LLM_GATEWAY_TOKENS={"sk-lab-xxx":"vladimir",...}` без внешних кавычек. Bash интерпретирует фигурные скобки и внутренние двойные кавычки при `source`, ломая JSON-структуру.

## Решение

Обернуть JSON в single quotes: `LLM_GATEWAY_TOKENS='{"sk-lab-xxx":"vladimir",...}'`.

Systemd `EnvironmentFile` парсит оба формата корректно — single quotes не ломают systemd.

## Урок

Любые JSON-значения в `.env` файлах, которые используются через bash `source`, должны быть обёрнуты в одинарные кавычки.

## Связано

- [[Этап016]]
- [[Этап014B]] (создание .env)
