---
tags: [грабли, runtime, venv, python]
дата: 2026-04-10
этап: F-next
компонент: text2sql_semantic
статус: workaround
---

# Грабли #66 — Runtime Bridge: два venv в одном процессе

## Симптом
`ImportError: No module named 'chromadb'` (llm-gateway venv) или `No module named 'openai'` (rag-mcp venv).

## Причина
`text2sql_semantic.py` — первый скрипт, требующий зависимости из обоих venv.

## Решение (workaround)
```bash
cd ~/llm-gateway/scripts
RAG_SITE=$(~/rag-mcp-server/.venv/bin/python -c "import site; paths=[p for p in site.getsitepackages() if 'site-packages' in p]; print(paths[0] if paths else '')")
PYTHONPATH="$RAG_SITE:$PYTHONPATH" llmrun ~/llm-gateway/venv/bin/python text2sql_semantic.py
```

## Статус
Tech debt. Для production: единый venv или контейнеризация.

## Связано
- [[Этап018_Semantic_Layer]]
