---
tags: [грабли, benchmark, ops]
дата: 2026-04-06
этап: 14A
компонент: benchmark.py
статус: решено
---

# 46 Benchmark baseline перезаписывается при повторном запуске

## Симптом

`benchmark.py --output benchmarks/` создаёт файл `baseline_YYYY-MM-DD.json`. Два запуска в один день перезаписывают один и тот же файл.

## Влияние

Canary upgrade SOP (pre-upgrade → post-upgrade) в рамках одного дня теряет pre-upgrade данные. Невозможно сравнить before/after.

## Причина

`benchmark.py` именует output только по дате: `baseline_{date_tag}.json`. Нет timestamp или label в имени файла.

## Решение

`benchmark-with-history.sh` создаёт immutable snapshot-копии с label и ISO timestamp:
- `benchmark_<label>_<timestamp>.json`
- `benchmark_<label>_<timestamp>.md`

Baseline-файлы по-прежнему создаются (backward compatibility), но snapshot — primary artifact.

## Связано

- [[Этап14A]] — обнаружено при создании benchmark history wrapper
- [[SOP Ollama Upgrade]] — SOP ссылается на snapshot-артефакты
