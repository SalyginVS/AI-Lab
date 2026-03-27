---
tags: [грабли, Continue.dev]
дата: 2026-03-27
этап: "[[Этап08B]]"
компонент: "[[Continue.dev]]"
---

# 19 PowerShell bash-style команды от Agent

## Симптом
Continue Agent в Windows генерирует bash-style команды: `ls -la`, `cat file.txt`, `grep pattern file`. PowerShell их не понимает — ошибка выполнения или молчаливый фейл.

## Причина
Модель обучена на Linux-среде. Без явного указания среды выполнения она выбирает bash-синтаксис как дефолт.

## Решение
Добавить в `%USERPROFILE%\.continue\rules\01-general.md` (`alwaysApply: true`) блок:

```markdown
## Terminal (Windows / PowerShell)
- Используй PowerShell-native команды: Get-ChildItem, Get-Content, Where-Object, Select-String
- Не используй bash-style флаги: ls -la, cat, grep недоступны нативно
- Каждая команда self-contained
- Не оборачивай всю команду в строковые кавычки
```

После изменения: `Developer: Reload Window` + новый чат.
