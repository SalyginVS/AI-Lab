---
tags: [компонент, инфра]
---
# uv и uvx

Сверхбыстрый менеджер пакетов Python (Astral, написан на Rust). Заменяет pip, pipx, pyenv, virtualenv. `uvx` — команда для запуска Python-инструментов в изолированных окружениях.

## Текущее состояние

| Параметр | Значение |
|----------|----------|
| Версия | 0.10.11 (Mar 16, 2026) |
| Где | Windows 11 (клиент) |
| Роль | Запуск MCP-серверов через STDIO |

## Зачем нужен

`uvx mcp-server-git` — скачивает пакет и Python (если нет), создаёт изолированное окружение, запускает, после завершения удаляет. Идеально для MCP STDIO: Continue запускает процесс, общается через stdin/stdout, при завершении — чисто.

## Установка на Windows

```powershell
# Любой из вариантов:
winget install astral-sh.uv
choco install uv
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Полезные команды

```powershell
uvx --version              # проверка
uvx mcp-server-git --help  # тест MCP-сервера
uv python install 3.12     # установить Python
uv tool install ruff        # установить инструмент постоянно
```

## Нюанс с PATH
После установки может потребоваться перезапуск VS Code / терминала. uvx обычно в `%USERPROFILE%\.local\bin`.

