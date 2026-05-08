---
tags: [грабли, git, hooks, process]
дата: 2026-05-08
этап: "[[Этап — Qwen3.6 27B MTP / Continue bounded lane]]"
компонент: "[[Git hooks]]"
---

# Pre-push hook сломал push из-за синтаксической ошибки

## Симптом

`git push origin master` в server runtime repo завершался ошибкой:

```text
.githooks/pre-push: line 42: syntax error near unexpected token `newline'
.githooks/pre-push: line 42: `fi'
```

## Причина

В hook после `case` block стояло `fi`, хотя корректное закрытие `case` — `esac`.

## Решение

Техническое исправление:

```diff
-fi
+esac
```

Стратегический вывод: hook failure был вторичным симптомом. Главная ошибка — попытка использовать server runtime repo как documentation/source-of-truth контур. После de-git сервера этот hook больше не является активной частью лабораторного governance.
