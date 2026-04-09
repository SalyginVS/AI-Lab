---
tags: [adr, решение, mcp]
дата: 2026-03-20
статус: принято
---

# ADR-003: STDIO транспорт по умолчанию для локальных MCP-серверов

## Контекст
MCP поддерживает три транспорта: STDIO, SSE, streamable-http. MCP-серверы запускаются на стороне клиента (Windows), т.к. Continue — VS Code extension.

## Решение
**STDIO по умолчанию** для всех локальных инструментов. SSE/streamable-http — только для серверных (Docker MCP на Ubuntu, RAG с Ollama embeddings).

## Альтернативы
| Транспорт | Плюсы | Минусы |
|-----------|-------|--------|
| **STDIO** | Минимальная задержка, нет портов, лучшая безопасность | Только локально |
| SSE | Удалённые серверы | Открытые порты, HTTP overhead |
| streamable-http | Стандартный HTTP | Больший overhead |

## Последствия
- Git MCP → STDIO на Windows (uvx)
- Terminal MCP → нативный Continue (встроенный)
- Docker MCP → SSE на Ubuntu (DOCKER_HOST=ssh://...)
- RAG MCP → SSE на Ubuntu (Ollama embeddings на GPU)

