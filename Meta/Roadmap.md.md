---
tags: [meta]
---

# Roadmap: AI Lab RTX 3090

## Текущий статус

На 2026-05-08 базовая AI Coding Platform находится в эксплуатации. Этапы 1–16 закрыты в паспорте v33/v34. Текущий фокус смещён с построения базового стека на эксплуатационное управление, model routing, safety boundaries, portability и enterprise-transfer артефакты.

## Статус основных треков

| Трек | Статус | Комментарий |
|---|---|---|
| Gateway / OpenAI-compatible API | Active | Gateway v0.12.0, `/health`, `/metrics`, `/orchestrate`, embeddings |
| Ollama inference lane | Active | Основной локальный model backend |
| vLLM MTP inference lane | PoC / bounded active | `qwen36-27b-mtp-bounded`, не Agent |
| Continue / VS Code | Active | Chat/Edit/Apply/Agent profiles по role contract |
| MCP tools | Active | Git/RAG/Docker/related tool layer по паспортам/справочникам |
| Knowledge layer | Active | Obsidian/GitHub + RAG corpus + ADR/грабли/этапы |
| Security / governance | Active, evolving | Approval gates, source-of-truth discipline, model role-fit governance |
| Enterprise transfer | Active documentation | Passport + architecture + 5-document portability package |

## Новые post-v34 направления

| Направление | Статус | Next action |
|---|---|---|
| Qwen3.6 27B MTP lane | Integrated | Накопить bounded task evidence; не повышать до Agent без gate |
| Runtime de-git policy | Applied | Не восстанавливать Git на сервере без отдельного ADR |
| Documentation governance | Applied | Placement map перед созданием новых docs |
| Model executor role-fit | Active | Поддерживать roles через benchmark + real task evidence |
| Cloud/local lane coordination | Planned / selective | Только fit-for-purpose, без “царей” в стеке |

## Закрытые historical tracks

| Этап | Название | Статус |
|---|---|---|
| 1–6 | Gateway v0.1.0 → v0.7.0 | ✅ Завершены |
| 7A–7D | Continue / Autocomplete / Context / Copilot BYOK | ✅ Завершены |
| 8A–8D | MCP / Terminal Policy / Orchestrator / Headless Automation | ✅ Завершены |
| 9A–9B | `/v1/embeddings` / embeddings migration | ✅ Завершены |
| 10A–10B | Structured Logging / Metrics | ✅ Завершены |
| 11 | RAG / Docs MCP | ✅ Завершён |
| 12 | Docker MCP | ✅ Завершён |
| 13 | Knowledge Layer | ✅ Завершён |
| 14 | Security Hardening | ✅ Завершён |
| 15 | Benchmark Matrix | ✅ Завершён |
| 16 | `/v1/orchestrate` | ✅ Завершён |
| 2026-05-08 | Qwen3.6 27B MTP / Continue bounded lane | ✅ Завершён |

## Операционный принцип

Roadmap больше не должен выглядеть как “этап 8A в работе”, если паспорт и архитектура уже фиксируют платформу в эксплуатации. Источник фактического статуса — актуальный паспорт лаборатории; Roadmap является навигационной картой, а не независимой версией истины.
