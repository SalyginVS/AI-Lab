---
tags:
  - грабли
  - gemma4
  - ollama
  - long-context
  - upstream
дата: 2026-04-05
этап: "015"
компонент: ollama
---

# 43 Gemma 4 long-context stall в Ollama 0.20.0

## Симптом

gemma4:31b и gemma4:26b при num_ctx ≥ 65536: модель загружается, runner стартует (4–8 сек), но GPU utilization = 0%, генерация не начинается. Запрос зависает бесконечно.

## Причина

Upstream bug в llama.cpp. Gemma 4 использует Sliding Window Attention (SWA) с гибридной архитектурой памяти. Context-shift механизм llama.cpp не полностью поддерживает эту архитектуру — при больших контекстах «forcing full prompt re-processing due to lack of cache data» (llama.cpp issue #21379).

## Масштаб

Hardware-agnostic. Воспроизводится на:
- RTX 5090 (Ollama #15237)
- RTX 3090 multi-GPU (Ollama #15284)
- DGX Spark / Blackwell GB10 128 ГБ (Ollama #15318)
- M1 Max 64 ГБ (Ollama #15286)
- ROCm (llama.cpp #21416)

Gemma 4 выпущена 2 апреля 2026. Ollama 0.20.0 — release-day support. Ранний, незрелый runtime path.

## Workaround

Использовать Gemma 4 с ctx ≤ 32768 (стабильно). Для long-context задач — non-Gemma модели (qwen3-coder, deepseek-r1).

## Статус

Blocked/External. Отслеживать: Ollama 0.20.1+, llama.cpp #21379.

## Связи

- [[Этап 015]]
- [[44 Gateway MAX_NUM_CTX потолок 32768]]
- [[45 Gateway HTTPX_TIMEOUT 600s недостаточен]]
