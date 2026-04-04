---
tags:
  - грабли
  - mcp
дата: 2026-04-04
этап: "011"
компонент: rag-mcp-server
---

# 39 mcp version не работает в 1.27.0

## Симптом

`mcp.__version__` → `AttributeError: module 'mcp' has no attribute '__version__'`.

## Решение

```python
from importlib.metadata import version
print(version("mcp"))  # → 1.27.0
```

## Связи

- [[Этап 011]]
