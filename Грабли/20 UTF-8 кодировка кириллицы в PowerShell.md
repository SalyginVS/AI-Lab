---
tags: [грабли, Continue.dev]
дата: 2026-03-27
этап: "[[Этап08B]]"
компонент: "[[Continue.dev]]"
---

# 20 UTF-8 кодировка кириллицы в PowerShell

## Симптом
При выводе файлов с кириллическими именами через `Get-ChildItem` в PowerShell-сессии Continue Agent имена отображаются кракозябрами. Проблема воспроизводится и при прямом запуске PowerShell без дополнительных настроек.

## Причина
Runtime-кодировка PowerShell по умолчанию ≠ UTF-8. `$OutputEncoding`, `[Console]::InputEncoding`, `[Console]::OutputEncoding` установлены в системную кодировку (cp1251 или latin-1 в зависимости от Windows-локали).

Это не проблема rules или модели — проблема PowerShell-сессии.

## Решение
Выставить UTF-8 перед командой вывода. Рабочая команда:

```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new(); [Console]::InputEncoding = [System.Text.UTF8Encoding]::new(); [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); Get-ChildItem -Name
```

Добавить в `01-general.md` правило для Agent:

```markdown
Для файлов с кириллицей и другими non-ASCII именами перед directory listing / file read
выставляй UTF-8:
$OutputEncoding = [System.Text.UTF8Encoding]::new();
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new();
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new();
```
