---
tags: [adr]
дата: 2026-04-04
этап: 11
статус: Accepted
---

# ADR-014: Streamable-HTTP для серверных MCP-серверов

## Контекст

RAG MCP server нуждается в доступе к ChromaDB и документам на Ubuntu-сервере. Continue.dev MCP STDIO серверы запускаются на стороне клиента (Windows). Необходимо выбрать транспорт для серверных MCP, которые работают на Ubuntu и должны быть доступны из Windows IDE.

## Решение

Использовать streamable-http транспорт для всех серверных MCP-серверов. Сервер слушает на Ubuntu (порт 8100 для RAG), Continue подключается по сети (type: streamable-http, url: http://192.168.0.128:8100/mcp). STDIO — для клиентских MCP-серверов (mcp-server-git на Windows).

## Альтернативы

- STDIO для RAG — отклонено: запустился бы на Windows, нет доступа к серверным ресурсам (ChromaDB, docs).
- SSE (Server-Sent Events) — отклонено: deprecated в MCP spec 2025-03-26, будет удалён. Не использовать для новых серверов.

## Следствия

Все будущие серверные MCP (Docker — этап 12) используют тот же паттерн: FastMCP + streamable-http + systemd + UFW LAN-only. Это унифицирует deployment и security model.
