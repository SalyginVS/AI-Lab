---
tags: [компонент, mcp]
---

# mcp-server-git

Официальный Git MCP-сервер от Anthropic. Python-пакет на PyPI. Первый MCP-сервер в нашей платформе (Этап 8A).

## Текущее состояние

| Параметр | Значение |
|----------|----------|
| Версия | **2026.1.14** (Jan 14, 2026) |
| Автор | Anthropic, PBC |
| Python | >= 3.10 |
| Запуск | `uvx mcp-server-git` |
| Репозиторий | github.com/modelcontextprotocol/servers/tree/main/src/git |

## Tools (~12 штук)

| Tool | Тип | Описание |
|------|-----|----------|
| `git_status` | Read | Статус рабочей директории |
| `git_diff_unstaged` | Read | Diff незакоммиченных изменений |
| `git_diff_staged` | Read | Diff staged изменений |
| `git_diff` | Read | Diff между ветками/коммитами |
| `git_log` | Read | История коммитов (фильтры: дата, автор) |
| `git_show` | Read | Содержимое коммита |
| `git_blame` | Read | Авторство строк |
| `git_add` | Write | Stage файлы |
| `git_reset` | Write | Сбросить staging |
| `git_commit` | Write | Создать коммит |
| `git_create_branch` | Write | Создать ветку |
| `git_checkout` | Write | Переключить ветку |

**Удалён:** `git_init` (безопасность). **Отсутствуют:** `git_push`, `git_pull`.

## Безопасность

Три CVE раскрыты в январе 2026, исправлены в 2025.12.18. Подробнее: [[15 mcp-server-git CVE безопасность]]

## Конфигурация
[[git.yaml (MCP)]]

