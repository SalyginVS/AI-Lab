---
tags: [решение, adr, orchestrator, stdout, shell]
дата: 2026-03-27
этап: "8D"
компонент: orchestrator
статус: принято
---

# ADR-xxx — --stdout как bridge между оркестратором и shell

## Контекст

`orchestrator.py` сохраняет результаты pipeline в `results/TIMESTAMP.json`. Shell-скриптам нужен текстовый результат последнего шага без парсинга JSON.

## Варианты

**A. Парсить JSON через `jq` в скриптах**  
Минус: внешняя зависимость от `jq` (не всегда установлен), усложняет скрипты, хрупко при изменении схемы JSON.

**B. Выводить только текст в stdout при флаге --stdout (выбрано)**  
Плюс: стандартный UNIX-паттерн (stdout = данные, stderr = логи), нет внешних зависимостей. JSON в results/ сохраняется параллельно — никаких потерь.

**C. Отдельный скрипт-обёртка parse_result.py**  
Минус: лишний файл, усложняет инфраструктуру без выгоды.

## Решение

Вариант **B**. В orchestrator.py:

```python
parser.add_argument("--stdout", action="store_true",
    help="Print last step output to stdout (for headless scripts)")

# После save_results():
if args.stdout:
    text = get_last_step_text(results)
    if text:
        sys.stdout.write(text.rstrip() + "\n")
```

Весь прогресс (step timing, total duration, path to results file) идёт в `sys.stderr` — не мешает захвату stdout в shell.

## Последствия

- Shell-скрипты: `RESULT=$("$ORCH_PY" orchestrator.py --pipeline X --task "..." --stdout)`
- Логи прогресса видны в терминале (stderr), данные захватываются (stdout).
- При отсутствии `--stdout` поведение не меняется — обратная совместимость сохранена.

## Связано

[[Этап008D]] · [[orchestrator.py]]
