---
tags:
  - решение
  - adr
  - mcp
  - streamable-http
дата: 2026-04-04
этап: "011"
компонент: rag-mcp-server
статус: принято
---

# ADR-014 streamable-http для серверных MCP

## Контекст

RAG MCP server нуждается в доступе к ChromaDB и документам на Ubuntu-сервере (192.168.0.128). Continue.dev MCP STDIO серверы запускаются на стороне клиента (Windows) — это не подходит для серверных ресурсов.

MCP spec 2025-03-26 пометил SSE как deprecated в пользу streamable-http.

## Решение

Для всех MCP-серверов, которым нужен доступ к серверным ресурсам (файлы, БД, Docker, GPU), использовать **streamable-http** транспорт:
- Сервер слушает на Ubuntu (порт 8100+)
- Continue подключается по сети (`type: streamable-http`)
- systemd сервис для lifecycle management

## Альтернативы

| Вариант | Почему отклонён |
|---------|----------------|
| STDIO | Запускается на Windows, нет доступа к серверным ресурсам |
| SSE | Deprecated в MCP spec, будет удалён |

## Следствие

- Docker MCP (этап 12) → streamable-http по тому же паттерну
- Любой будущий серверный MCP → streamable-http
- STDIO остаётся только для клиентских MCP (mcp-server-git и аналоги)

## Связи

- [[Этап 011]]
- [[Этап 008A]] (STDIO паттерн для клиентских MCP)
- [[Этап 012]] (Docker MCP — тот же паттерн)
