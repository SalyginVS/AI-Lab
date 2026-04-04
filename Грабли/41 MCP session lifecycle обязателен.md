---
tags:
  - грабли
  - mcp
  - streamable-http
дата: 2026-04-04
этап: "011"
компонент: rag-mcp-server
---

# 41 MCP session lifecycle обязателен

## Симптом

`tools/list` и `tools/call` без предварительного initialize возвращают ошибку.

## Причина

MCP streamable-http требует полный session lifecycle.

## Решение

Обязательная последовательность:
1. `initialize` (POST /mcp)
2. `notifications/initialized` (с Mcp-Session-Id)
3. `tools/list` / `tools/call` (с Mcp-Session-Id)

## Примечание

Continue.dev управляет lifecycle автоматически. Проблема только при curl-тестировании.

## Связи

- [[Этап 011]]
- [[40 streamable-http требует Accept header]]
