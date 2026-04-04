---
tags:
  - грабли
  - mcp
  - streamable-http
дата: 2026-04-04
этап: "011"
компонент: rag-mcp-server
---

# 40 streamable-http требует Accept header

## Симптом

MCP server отвечает ошибкой negotiation при curl без правильного Accept.

## Решение

Обязательный заголовок: `Accept: application/json, text/event-stream`.

## Примечание

Continue.dev делает это автоматически. Проблема только при ручном curl-тестировании.

## Связи

- [[Этап 011]]
- [[41 MCP session lifecycle обязателен]]
