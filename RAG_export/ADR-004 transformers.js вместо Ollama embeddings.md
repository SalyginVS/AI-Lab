---
tags: [adr, решение]
дата: 2026-03-19
статус: принято
---

# ADR-004: transformers.js для embeddings (вместо Ollama)

## Контекст
Нужны embeddings для индексации кодовой базы (@Code, @Repository Map). OLLAMA_NUM_PARALLEL=1 — один запрос за раз.

## Решение
**transformers.js** (all-MiniLM-L6-v2), встроенный в VS Code extension host. Нулевая нагрузка на Ollama, не блокирует chat/agent/autocomplete.

## Альтернативы
| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| **transformers.js** | Параллельно с Ollama, zero-config | Модель маленькая, нет русского |
| qwen3-embedding через Ollama | Лучше качество, русский | Блокирует GPU при индексации |

## Последствия
- Индексация не мешает работе с моделями
- Качество embeddings базовое (code search — достаточно)
- Миграция на qwen3-embedding запланирована на Этап 9B (через /v1/embeddings)

