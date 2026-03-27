---
tags: [компонент, mcp]
---

# MCP (Model Context Protocol)

Открытый стандарт Anthropic для подключения AI к внешним инструментам. Унифицирует prompts, context и tool use. В нашей платформе — Слой 3 целевой архитектуры.

## Как работает

```
Пользователь → Continue Agent → gateway.py → Ollama → tool_call
                                                ↓
                Continue Agent → MCP Server (STDIO) → инструмент (git, terminal, ...)
                                                ↓ tool_result
                Continue Agent → gateway.py → Ollama → ответ
```

## Транспорты

| Транспорт | Когда | Пример |
|-----------|-------|--------|
| **STDIO** | Локальные инструменты | Git, Terminal |
| SSE | Удалённые серверы | RAG на Ubuntu |
| streamable-http | Стандартный HTTP | Docker MCP на Ubuntu |

Решение: [[ADR-003 STDIO транспорт для MCP]]

## Конфигурация в Continue

Папка: `.continue/mcpServers/` (глобально или в workspace).
Формат: YAML (name, version, schema: v1, mcpServers array) или JSON.
**Только Agent mode.**

## Целевой набор серверов

| # | Сервер | Транспорт | Этап | Статус |
|---|--------|-----------|------|--------|
| 1 | [[mcp-server-git]] | STDIO | 8A | 🔄 В работе |
| 2 | Terminal (встроенный Continue) | Нативный | 8B | ⬜ План |
| 3 | Custom RAG MCP | SSE | 11 | ⬜ План |
| 4 | Docker MCP | SSE | 12 | ⬜ План |

## Безопасность
MCP расширяет attack surface. Prompt injection через poisoned README/issue может вызвать tool calls. Митигация: версии >= 2025.12.18, approval в Agent mode, denylist в rules.

