---
tags:
  - решение
  - ADR
  - embeddings
  - gateway
  - continue
дата: 2026-03-29
этап: 9B
компонент: Continue.dev, gateway.py, qwen3-embedding
статус: принято
---

# ADR-010 Embeddings через gateway, не напрямую в Ollama

## Статус

Принято. Реализовано в этапе 9B.

## Контекст

При миграции Continue.dev embeddings с transformers.js на qwen3-embedding возникает выбор пути:

- **Вариант A (provider: ollama):** Continue → Ollama :11434 напрямую. Аналогично FIM autocomplete.
- **Вариант B (provider: openai):** Continue → gateway :8000/v1/embeddings → Ollama. Через policy layer.

FIM autocomplete сознательно идёт напрямую ([[Этап 7B]]) — для минимальной latency на каждом нажатии. Embeddings имеют другой профиль: запросы батчевые, при индексации, не real-time.

## Решение

**Вариант B: provider: openai через gateway.**

```yaml
- name: qwen3-embedding
  provider: openai
  apiBase: http://192.168.0.128:8000/v1
  model: qwen3-embedding
  roles:
    - embed
```

## Обоснование

1. **Единый policy layer.** Все non-FIM запросы проходят через gateway — chat, edit, agent, теперь и embeddings. Одна точка для logging, validation, allowlist, auth, будущих метрик.

2. **Allowlist enforcement.** Gateway проверяет модель по allowlist до отправки в Ollama. При `provider: ollama` клиент может вызвать любую модель.

3. **Observability.** Embedding-запросы логируются в тот же systemd journal, что и chat. Одна команда `journalctl -u llm-gateway` показывает всё.

4. **Будущий RAG MCP (этап 11).** RAG-сервер тоже будет ходить в gateway за embeddings. Единый endpoint для всех потребителей.

5. **Контракт стандартизирован.** OpenAI-compatible `/v1/embeddings` — любой будущий клиент (headless script, другой IDE, RAG pipeline) подключается без адаптации.

## Компромиссы

- **Дополнительный hop:** Continue → gateway → Ollama вместо Continue → Ollama. Для embedding-запросов (батчевые, не real-time) latency overhead пренебрежимо мал.
- **apiKey заглушка:** `provider: openai` в Continue требует непустой `apiKey`. Решение: `apiKey: ollama` (грабля зафиксирована — [[27 apiKey заглушка для openai provider]]).
- **encoding_format:** OpenAI SDK шлёт несовместимый дефолт. Решение: двухуровневый fix — client-side `encoding_format: float` + gateway silent coerce ([[26 encoding_format float обязателен]]).

## Исключение

FIM autocomplete по-прежнему идёт напрямую в Ollama (provider: ollama, :11434, /api/generate). Это сознательное исключение — FIM требует минимальной latency на каждое нажатие клавиши, policy layer для него избыточен.

## Связи

- [[Этап010]] (9B)
- [[Этап009]] (9A — backend endpoint)
- [[ADR-008 Модуляризация gateway]]
- [[26 encoding_format float обязателен]]
- [[27 apiKey заглушка для openai provider]]
