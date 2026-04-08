---
tags: [грабли, testing, jq, bash]
дата: 2026-04-07
этап: 16
компонент: testing
---

# 51 jq multiline tail

## Симптом

Тесты 10/11 в `test_stage16.sh` падали: `jq: parse error: Unmatched '}'`.

## Причина

`jq -R 'fromjson? | select(...)' | tail -1` выдаёт pretty-printed multiline JSON. `tail -1` берёт только закрывающую `}` — невалидный JSON.

## Решение

Использовать `jq -cR` (compact single-line output). `tail -1` корректно берёт последний полный JSON object.

## Урок

Любые jq → tail/head пайплайны должны использовать `-c` (compact) для гарантии однострочного вывода.

## Связано

- [[Этап016]]
