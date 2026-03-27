---
tags: [грабли, ollama, gpu]
дата: 2026-03-16
этап: "[[Этап07A — Continue Agent]]"
компонент: "[[Ollama]]"
---

# CUDA graph capture crash → GGML_CUDA_NO_GRAPHS=1

## Симптом
Ollama SIGABRT при быстрой последовательности запросов (Agent mode).

## Решение
```ini
Environment="GGML_CUDA_NO_GRAPHS=1"
```

