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
| Ollama inference lane | Active | Основной локальный model backend; `0.24.0` controlled archive upgrade PASS |
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

---

## 2026-05-24 - Ollama 0.24.0 controlled archive upgrade

Ollama runtime обновлён `0.23.4 -> 0.24.0` через controlled archive path без pipe-installer.

Статус:

- Ollama runtime: PASS.
- CUDA v13 / RTX 3090: PASS.
- Direct Ollama smoke: PASS.
- Gateway health/models/chat regression: PASS.
- Backup: `/home/vladimir/ollama_runtime_backup_before_0.24.0_20260524_080312`.

Артефакты:

- `Этапы/2026-05-24_Ollama_0240_Controlled_Upgrade/Результаты.md`
- `Конфиги/ollama_0240_controlled_archive_upgrade.md`
- `Паспорт_лаборатории_v37.md`


## 2026-05-15 — OpenCode controlled terminal-agent lane

Статус: завершено.

Результат:

```text
REPO_WRITE_SMOKE=PASS
OPEN_CODE_REPO_WRITE_MODE=allowed_only_for_small_scoped_docs_edits_with_manual_review
AUTONOMOUS_AGENT_READY=no
```

OpenCode принят не как autonomous repo agent, а как controlled terminal-agent lane для read-only анализа и малых scoped documentation edits с ручным review.

Связанные артефакты:

- `Решения/ADR-029_OpenCode_Controlled_Terminal_Agent_Lane.md`
- `Грабли/084_opencode_wrapper_not_in_path.md`
- `Конфиги/opencode_ailab_wrappers.md`
- `Этапы/2026-05-15_OpenCode_Controlled_Terminal_Agent/Результаты.md`
