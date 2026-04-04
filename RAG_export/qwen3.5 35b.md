---
tags: [модель, qwen]
---

# qwen3.5:35b

Экспериментальная reasoning-модель. MoE-архитектура. **Tool calling СЛОМАН — не использовать для Agent mode.**

| Параметр | Значение |
|----------|----------|
| Размер | 23 ГБ (Q4_K_M) |
| Архитектура | qwen35moe (MoE) |
| Параметры | 36B |
| Контекст | 262144 (максимум), 8192 (наш дефолт) |
| Capabilities | completion, vision, tools (сломано), thinking |

## Роли в платформе
- **Experimental reasoning** — сложные текстовые задачи (без tools)
- **Planner** в orchestrator pipeline (Этап 8C) — текстовый output, tools не нужны

## ⚠️ Критическое ограничение
**Никогда не использовать для Agent mode / function calling.** Подробнее: [[02 qwen3.5 tool calling сломан]]

## История проблем
- Ollama 0.17.4: crash при GPU+CPU offload, бесконечные повторы без presence_penalty
- Ollama 0.17.6: fix parser pipeline (Hermes JSON → Qwen-Coder XML), но tools по-прежнему ненадёжны
- Ollama 0.18.0: re-pull помог с crash и repeats, tool calling остался сломан

