---
tags: [модель, qwen, embeddings]
---

# qwen3-embedding

Embedding-модель для будущего RAG. Пока в резерве — текущие embeddings через transformers.js.

| Параметр | Значение |
|----------|----------|
| Размер | 4.7 ГБ |
| Роль | Embeddings (резерв, Этап 9B) |
| Статус | На диске, не используется активно |

## Планируемая миграция
Этап 9A: gateway.py /v1/embeddings. Этап 9B: миграция с transformers.js на qwen3-embedding.
Решение: [[ADR-004 transformers.js вместо Ollama embeddings]]

