---
tags: [adr]
дата: 2026-04-03
этап: 10C
статус: Accepted
---

# ADR-012: Gemma 4 Model Integration — Tier-based Routing

## Контекст

Gemma 4 (31B Dense #3 Arena, 26B MoE #6 Arena) доступны в Ollama 0.20.0 с подтверждённым function calling (generic + semantic), multi-step chaining, thinking mode и vision. Необходимо определить роли Gemma 4 относительно существующих моделей (qwen3-coder:30b, qwen3:30b, deepseek-r1:32b).

## Решение

Трёхуровневая система (Tier 1 / Tier 2 / Tier 3):

**Tier 1 — Primary:**
- gemma4:31b — Quality-first Agent / Planner / Reviewer. Требует thin policy prompt для стабильного tool selection.
- gemma4:26b — Fast Semantic Agent / Fast Executor. Лучший zero-shot semantic tool selector.
- qwen3-coder:30b — Stable Generic Executor / Best SQL Executor. Надёжный function calling, лучшая latency для code-gen.

**Tier 2 — Specialized:**
- deepseek-r1:32b — Deep reasoning / Math.
- qwen3.5:9b — Fast chat / Vision (tool calling восстановлен в Ollama 0.20.0).

**Tier 3 — Reserve / Legacy:**
- qwen3:30b, glm-4.7-flash, qwen3-vl:8b и другие.

Не бинарное деление «Gemma semantic / Qwen generic», а ролевое: Gemma — quality-first для agent/planner/reviewer, Qwen — stable generic executor. Дополнение после 11A: qwen3-coder:30b — лучший Text-to-SQL executor (SA 75%, latency 0.4s).

## Альтернативы

- Полная замена qwen3-coder на Gemma 4 — отклонено: qwen3-coder стабильнее для generic tool calling и быстрее для code-gen.
- Оставить qwen3-coder как primary — отклонено: Gemma 4 превосходит по quality в code review и planning задачах.

## Следствия

config.yaml реорганизован по тирам. pipelines.yaml обновлён (execute-review: gemma4:26b→31b, plan-execute-review: 31b→26b→31b). deepseek-coder-v2:16b → Deprecated → удалена.
