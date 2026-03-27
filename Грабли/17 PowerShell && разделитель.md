---
tags: [грабли, mcp, инфра]
дата: 2026-03-21
этап: "[[Этап08A — MCP Git Server]]"
компонент: "[[mcp-server-git]]"
---

# PowerShell: && не работает как разделитель команд

## Симптом
В первом tool call `git_status` внутренний шаг `pwd && git status` дал ошибку парсинга.

## Причина
`&&` — bash/cmd-синтаксис. В PowerShell — не валидный разделитель команд (до PS 7.0). Continue Agent / mcp-server-git может генерировать bash-синтаксис.

## Решение
Не блокер — Continue корректно продолжает с чистой командой. Но стоит учитывать при диагностике tool call errors на Windows.
