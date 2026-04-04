---
tags: [adr, решение]
дата: 2026-03-20
статус: принято
---

# ADR-005: ChromaDB для RAG PoC

## Контекст
Нужна vector DB для RAG-сервера (Этап 11). Варианты: ChromaDB (embedded), Qdrant (server), SQLite+faiss (manual).

## Решение
**ChromaDB в embedded режиме** для PoC. SQLite backend, zero-config, Python API.

## Последствия
- Ограничение ~100K документов — достаточно для лаборатории
- При масштабировании — миграция на Qdrant
- Этап 11
