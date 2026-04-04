---
tags:
  - грабли
  - chromadb
дата: 2026-04-04
этап: "011"
компонент: indexer
---

# 38 ChromaDB delete where пустой несовместим с v1.5.5

## Симптом

`indexer.py` падает при переиндексации на вызове `collection.delete(where={})`.

## Причина

ChromaDB 1.5.5 не принимает пустой `where={}` для mass-delete всех документов в коллекции.

## Решение

Удалять коллекцию целиком и пересоздавать:

```python
chroma_client.delete_collection("lab_docs")
collection = chroma_client.get_or_create_collection(
    name="lab_docs",
    embedding_function=embedding_fn,
)
```

## Связи

- [[Этап 011]]
