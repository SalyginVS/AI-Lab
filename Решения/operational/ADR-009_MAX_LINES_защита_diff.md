---
tags: [решение, adr, shell, llm, контекст, diff]
дата: 2026-03-27
этап: "8D"
компонент: auto-review.sh, auto-commit-msg.sh
статус: принято
---

# ADR-xxx — MAX_LINES=400 как защита от переполнения num_ctx

## Контекст

`auto-review.sh` и `auto-commit-msg.sh` передают `git diff` как часть задачи в orchestrator. Большие коммиты (рефакторинг, merge, bulk-changes) могут генерировать сотни и тысячи строк diff. Pipelines `execute-review` и `commit-msg` настроены на `num_ctx: 4096–8192`. Превышение контекста: модель молча усекает входной текст, качество ответа деградирует непредсказуемо.

## Варианты

**A. Не ограничивать, позволить модели усекать**  
Минус: пользователь не знает, что diff обрезан; quality degradation без предупреждения.

**B. Жёсткий лимит строк с предупреждением (выбрано)**  
Плюс: предсказуемое поведение, явное сообщение пользователю. Порог настраиваем через `MAX_LINES`.

**C. Разбить diff на чанки и вызывать orchestrator несколько раз**  
Плюс: полный охват. Минус: сложно, не нужно для PoC, умножает время выполнения.

## Решение

Вариант **B**. Мягкий truncate с предупреждением:

```bash
MAX_LINES="${MAX_LINES:-400}"

if [[ "$DIFF_LINES" -gt "$MAX_LINES" ]]; then
    echo "WARNING: diff is $DIFF_LINES lines, truncating to $MAX_LINES." >&2
    DIFF_TRUNCATED=$(echo "$DIFF_RAW" | head -n "$MAX_LINES")
    DIFF_TRUNCATED+=$'\n... [TRUNCATED: N lines omitted]'
fi
```

Порог 400 строк: при среднем diff ~5 символов/строка = ~2000 символов + task prompt ~500 символов = ~2500 символов ≈ ~800 токенов. Хорошо вписывается в 4096–8192 num_ctx.

`MAX_LINES` переопределяется через env для конкретных нужд:
```bash
MAX_LINES=800 ./scripts/auto-review.sh --last-commit
```

## Последствия

- Большие рефакторинги: только первые 400 строк diff попадут в review. Для полного охвата — запускать с `MAX_LINES=1000` и pipeline с `num_ctx: 32768`.
- Commit-message: 400 строк достаточно для определения типа и scope изменений в большинстве случаев.

## Связано

[[Этап008D]] · [[auto-review.sh]] · [[auto-commit-msg.sh]] · [[pipelines.yaml]]
