# Новые файлы для Obsidian vault из Этапа 8A
# Нарезать по ═══ ФАЙЛ: ═══


═══ ФАЙЛ: Грабли/16 uvx PATH-эффект Windows.md ═══
---
tags: [грабли, инфра, mcp]
дата: 2026-03-21
этап: "[[Этап08A — MCP Git Server]]"
компонент: "[[uv и uvx]]"
---

# uvx: PATH-эффект после установки на Windows

## Симптом
`uvx --version` → "не найдена команда" сразу после `winget install astral-sh.uv`.

## Причина
Windows не обновляет PATH в уже запущенных сеансах терминала и VS Code.

## Решение
Перезапустить VS Code и/или PowerShell. Новый сеанс подхватит обновлённый PATH.


═══ ФАЙЛ: Грабли/17 PowerShell && разделитель.md ═══
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


═══ ФАЙЛ: Грабли/18 git add . по умолчанию в Agent.md ═══
---
tags: [грабли, mcp, безопасность]
дата: 2026-03-21
этап: "[[Этап08A — MCP Git Server]]"
компонент: "[[mcp-server-git]]"
---

# Agent по умолчанию делает git add . — добавляет ВСЁ

## Симптом
При запросе "stage all changes" агент выполняет `git add .` без уточнения списка файлов.

## Причина
Модель интерпретирует "all" буквально. MCP-сервер не имеет ограничений на scope.

## Митигация
Для критичных репозиториев — добавить правило в rules:
```
При git add всегда сначала показывай список файлов и запрашивай подтверждение.
Никогда не делай git add . — только именованные файлы.
```

Системная защита (per-tool policy) — пока не реализована в Continue. Планируется в будущих этапах.


═══ ФАЙЛ: Этапы/Этап08A — MCP Git Server.md ═══
---
tags: [этап, lab, mcp]
дата: 2026-03-21
статус: завершён
зависимости: []
---

# Этап 8A — MCP: Git Server

## Задача
Подключить первый MCP-сервер (Git) к Continue.dev Agent mode. Proof-of-concept MCP-интеграции.

## Результат
Agent mode выполняет git status, log, diff, add, commit, branch через tool calls к MCP-серверу. 12 tools видны и работают. Модель обрабатывает 26+ tools без деградации.

## Что сделано
- Установлен [[uv и uvx]] на Windows (0.10.12)
- Создан конфиг [[git.yaml (MCP)]] в `.continue/mcpServers/`
- [[mcp-server-git]] подключён через STDIO
- Протокол из 7 git-операций (5 основных + 2 cleanup) — все пройдены

## Грабли
- [[16 uvx PATH-эффект Windows]]
- [[17 PowerShell && разделитель]]
- [[18 git add . по умолчанию в Agent]]

## Закрытые вопросы архитектуры
| Вопрос | Был | Стал |
|--------|-----|------|
| MCP STDIO на Windows | [U] | [F] Работает |
| Количество tools для 30B | [U] | [F] 26+ без деградации |
| Формат mcpServers Continue | [U] | [F] YAML, schema v1 |

## Решения (ADR)
- [[ADR-003 STDIO транспорт для MCP]] — подтверждён

## Критерии завершения
- [x] uvx установлен, работает
- [x] mcp-server-git запускается
- [x] git.yaml создан
- [x] 12 MCP tools видны в Agent mode
- [x] 5 тестов пройдены (status, log, diff, add+commit, branch+checkout)
- [x] 2 cleanup-теста пройдены (checkout main, delete branch)
