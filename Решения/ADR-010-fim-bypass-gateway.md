---
tags: [adr]
дата: 2026-03-28
этап: 7B
статус: Accepted
---

# ADR-010: FIM Autocomplete минует Gateway

## Контекст

FIM (Fill-In-the-Middle) autocomplete в Continue.dev требует минимальной latency (<200ms до первого токена). Gateway добавляет overhead (auth middleware, logging, httpx proxy). Autocomplete использует endpoint Ollama `/api/generate` (не OpenAI-совместимый `/v1/chat/completions`), который gateway не проксирует.

## Решение

FIM autocomplete (qwen2.5-coder:7b) подключается напрямую к Ollama (порт 11434) через provider: ollama в Continue config.yaml. Это единственное исключение из правила «все запросы через gateway». UFW разрешает порт 11434 только для конкретных клиентов (192.168.0.164, 10.10.10.2).

## Альтернативы

- Проксировать FIM через gateway — отклонено: потребовало бы реализацию `/api/generate` endpoint в gateway, дополнительная латентность для latency-critical сценария.
- Переключить autocomplete на gateway /v1/chat/completions — отклонено: FIM формат (prefix+suffix→middle) несовместим с chat completions API.

## Следствия

Autocomplete запросы не проходят через auth и structured logging gateway. Это приемлемый компромисс: autocomplete — read-only, не мутирует данные, выполняется от имени конкретного IDE-клиента. UFW обеспечивает network-level контроль доступа к Ollama.
