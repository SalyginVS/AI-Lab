---
tags: [грабли, git, bash, auto-review]
дата: 2026-03-27
этап: "8D"
компонент: auto-review.sh
статус: решено
---

# Грабли — git diff HEAD~1 HEAD на одном коммите

## Симптом

```bash
./scripts/auto-review.sh --last-commit
# fatal: ambiguous argument 'HEAD~1': unknown revision
# DIFF is empty → "No changes to review"
```

В репозитории с единственным коммитом `HEAD~1` не существует.

## Причина

`git diff HEAD~1 HEAD` требует минимум двух коммитов. На свежем репозитории или ветке с первым коммитом `HEAD~1` — несуществующая ревизия.

## Решение

В `auto-review.sh` используется конструкция с `|| true`:

```bash
last-commit)
    git diff HEAD~1 HEAD 2>/dev/null || true
    ;;
```

При ошибке git команда возвращает пустую строку. Далее:

```bash
if [[ -z "$DIFF_RAW" ]]; then
    echo "No changes to review (diff is empty)." >&2
    exit 0
fi
```

Корректная обработка: предупреждение в stderr, exit 0 — хук не блокирует.

## Правило

При работе с `git diff` через относительные ревизии (`HEAD~1`, `HEAD~2`) всегда обрабатывать пустой вывод и ошибки git как мягкий сбой. Для первого коммита ветки альтернатива — `git diff --root HEAD` (показывает всё дерево) или явная проверка числа коммитов: `git rev-list HEAD --count`.

## Связано

[[Этап008D]] · [[auto-review.sh]]
