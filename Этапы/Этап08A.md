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
