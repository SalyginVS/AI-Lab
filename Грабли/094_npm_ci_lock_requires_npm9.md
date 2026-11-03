---
tags: [грабли, pi, npm, lockfile, lenovo]
дата: 2026-11-03
этап: LAPTOP-02
компонент: Pi client / npm
---

# 094 - npm ci по принятому lock требует npm 9.2.0

## Симптом

На Lenovo npm 12.2.1 отклонил `npm ci` с ошибкой `EUSAGE` и сообщением `Missing: @esbuild/*@0.28.2` о платформенных пакетах (LAPTOP-02:A3, первая попытка).

## Причина

В принятом `package-lock.json` из платформенных пакетов esbuild перечислен только `@esbuild/linux-x64`. npm 12.2.1 считает этот lock недостаточным. Приёмщик отдельно воспроизвёл отказ npm 12.2.1 и установку npm 9.2.0 с совпадающим SHA256 cli.js (LAPTOP-02:A3 и воспроизведение приёмщика). Несовместимость не является основанием переписывать lock.

## Решение

Использовать npm 9.2.0 для принятого lock, оставляя `package-lock.json` неизменным. При другом системном npm в каталоге prefix и с теми же временными HOME и npm-кэшем выполнить `npx -y npm@9.2.0 ci --no-audit --no-fund`. До запуска проверить `npm view npm@9.2.0 dist.integrity` и совпадение со значением `sha512-oypVdaWGHDuV79RXLvp+B9gh6gDyAmoHKrQ0/JBYTWWx5D8/+AAxFdZC84fSIiyDdyW4qfrSyYGKhekxDOaMXQ==`. См. раздел 4 [runbook 60](../Сборка/60_Клиент_Dell.md) (LAPTOP-02:A3.1-A3.2).

## Проверка

На Lenovo npm 9.2.0 установил 121 пакет, Pi 1.0.3, `LOCK_MATCH=121/121`, `npm ls` завершился с кодом 0. SHA256 `dist/bundle/cli.js` совпал с эталоном `e79626f2dd6f94aa45d30f3fa63cd84319a6eefcd150b353cfaf274366926774` (LAPTOP-02:A3.1-A3.4). npm 9.2.0 получен из npm registry через `npx`, не через Ubuntu APT, это отдельное ограничение приёмки.
