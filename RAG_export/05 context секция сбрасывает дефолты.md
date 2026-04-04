---
tags: [грабли, continue]
дата: 2026-03-19
этап: "[[Этап07C — Context Rules Prompts]]"
компонент: "[[Continue.dev]]"
---

# Секция context: сбрасывает дефолтные провайдеры

## Симптом
После добавления `context:` пропадают @File, @Code, @Diff и др.

## Причина
Continue 1.2.17 заменяет дефолты на то, что указано в конфиге.

## Решение
Перечислить ВСЕ 11 провайдеров явно: code, repo-map, file, currentFile, open, diff, terminal, tree, problems, clipboard, os.

