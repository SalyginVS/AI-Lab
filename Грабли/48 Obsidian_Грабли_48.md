---
tags: [грабли, security, auth, regression, rag-mcp]
дата: 2026-04-07
этап: 14B
компонент: gateway, rag-mcp
---

# 48 Mandatory auth ломает server-to-server RAG MCP

## Симптом

После перехода gateway auth из optional в mandatory, Continue Agent mode + RAG MCP перестаёт работать. `search_docs` → 401 Unauthorized на `/v1/embeddings`.

## Причина

`~/rag-mcp-server/gateway_embeddings.py` вызывал gateway embeddings endpoint через httpx **без Authorization header**. При optional auth (v0.10.0) это работало. При mandatory auth (v0.11.0) → 401.

Дополнительно: `rag-mcp.service` не имел `EnvironmentFile=` → env `LLM_GATEWAY_TOKENS` не виден процессу даже после патча кода.

## Классификация

**Cascading regression** — security hardening одного слоя (gateway) влияет на server-to-server вызовы соседнего слоя (rag-mcp). Типичная enterprise-проблема при ужесточении auth policy.

## Решение

1. Патч `gateway_embeddings.py`: загрузка первого токена из `LLM_GATEWAY_TOKENS`, отправка `Authorization: Bearer {token}`
2. `systemctl edit rag-mcp` → `EnvironmentFile=/home/vladimir/llm-gateway/.env`
3. `systemctl restart rag-mcp`
4. VS Code → Developer: Reload Window (обновление MCP session)

## Предотвращение

При ЛЮБОМ изменении auth policy — проверять ВСЕ server-to-server вызовы:
- gateway ← Continue.dev (client)
- gateway ← orchestrator.py (headless)
- gateway ← rag-mcp (server-to-server embeddings)
- gateway ← health-check.sh (если будет использовать protected endpoints)

## Связано

- [[Этапы/Этап14B]]
- [[Решения/ADR-015 Per-user token storage ENV-based JSON]]
