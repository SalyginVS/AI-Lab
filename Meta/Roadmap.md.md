---
tags: [meta]
---

# Roadmap: 16 этапов, 5 треков

## Статус этапов

| Этап | Название | Статус |
|------|----------|--------|
| 1–6 | Gateway v0.1.0 → v0.7.0 | ✅ Завершены |
| 7A | Continue Agent mode | ✅ Завершён |
| 7B | Autocomplete + Ollama 0.18 | ✅ Завершён |
| 7C | Context + Rules + Prompts | ✅ Завершён |
| 7D | Copilot BYOK | ✅ Завершён |
| **8A** | **MCP: Git Server** | **🔄 В работе** |
| 8B | MCP: Terminal + Policy | ⬜ План |
| 8C | Orchestrator PoC | ⬜ План |
| 8D | Headless Automation | ⬜ План |
| 9A | gateway /v1/embeddings | ⬜ План |
| 9B | Embeddings миграция | ⬜ План |
| 10A | Structured Logging | ⬜ План |
| 10B | Metrics Endpoint | ⬜ План |
| 11 | MCP: RAG/Docs | ⬜ План |
| 12 | MCP: Docker | ⬜ План |
| 13 | Knowledge Layer | ⬜ План |
| 14 | Security Hardening | ⬜ План |
| 15 | Benchmark Matrix | ⬜ План |
| 16 | gateway /v1/orchestrate | ⬜ План |

## Параллельные треки
```
A (MCP Tools):      8A → 8B ────────────────→ 11 → 12
B (Backend):        9A → 9B    10A → 10B
C (Knowledge):      ──────────────→ 13
D (Ops/Security):   ────────────────→ 14 → 15
E (Orchestration):  8C → 8D ──────────────────→ 16
```
