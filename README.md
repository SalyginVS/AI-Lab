---
tags: [meta]
---

# AI Lab Knowledge Base

Obsidian vault для домашней AI Coding Platform на базе локального LLM-сервера RTX 3090.

## Source of truth

Канонический контур документации:

```text
/home/vladimir/llm/AI-Lab
remote: git@github.com:SalyginVS/AI-Lab.git
```

Сервер `192.168.0.128` — runtime filesystem. Он не является Git/source-of-truth контуром для документации, ADR, паспортов или архитектурных решений.

## Навигация

- **[[Паспорт лаборатории]]** — фактическое состояние стенда; актуальная версия: `Паспорт_лаборатории_v37.md`.
- **[[Целевая архитектура]]** — архитектурные принципы и целевое состояние; актуальная версия: `Целевая_архитектура_AI_Coding_Platform_v1_21.md`.
- **[[Meta/Roadmap]]** — состояние этапов и треков.
- **Этапы/** — хронология: один каталог/файл на завершённый технический этап.
- **Грабли/** — найденные проблемы в формате симптом → причина → решение.
- **Решения/** — ADR (Architecture Decision Records — документы архитектурных решений).
- **Конфиги/** — эталонные конфигурации с комментариями.
- **Briefings/** — переносимые briefing-блоки для внешних AI/research tools.

## Инфраструктурный snapshot

Версионная таблица в README не является source of truth. Актуальные версии фиксируются в паспорте лаборатории.

Короткий статус на 2026-05-08:

| Контур | Статус |
|---|---|
| Documentation | `/home/vladimir/llm/AI-Lab` + GitHub |
| Server runtime | `192.168.0.128`, `/home/vladimir/llm-gateway`, no Git repo |
| Gateway | Active, `/health=200`, version `0.12.0` |
| Ollama lane | Active, Ollama `0.24.0` controlled archive upgrade PASS |
| vLLM MTP lane | PoC / bounded active для `qwen36-27b-mtp-bounded` |
| Strategy | Depth over Speed + controlled bounded execution |

## Полный пакет переносимости

Вместе с паспортом и целевой архитектурой используется пакет переносимости:

1. `Portability_Gap_Analysis.md` — анализ пробелов переносимости.
2. `01_Операционный_справочник_v1.md` — эксплуатация, восстановление, диагностика.
3. `02_Gateway_техническая_спецификация_v1.md` — внутренняя реализация gateway.
4. `03_Конфигурация_клиента_v1.md` — Continue / MCP / rules / client setup.
5. `04_Enterprise_Transfer_Brief_v1.md` — переносимость паттернов в enterprise context.

## Рекомендуемые плагины Obsidian

Dataview, Templater, Calendar, Graph Analysis.

---

## OpenCode controlled terminal-agent lane

Статус: accepted / bounded active for small scoped documentation edits.

Ключевое решение:

```text
REPO_WRITE_SMOKE=PASS
OPEN_CODE_REPO_WRITE_MODE=allowed_only_for_small_scoped_docs_edits_with_manual_review
AUTONOMOUS_AGENT_READY=no
```

Главные документы:

- `Решения/ADR-029_OpenCode_Controlled_Terminal_Agent_Lane.md`
- `Конфиги/opencode_ailab_wrappers.md`
- `Грабли/083_opencode_run_edit_ask_auto_reject_exit_zero.md`
- `Грабли/084_opencode_wrapper_not_in_path.md`
- `Этапы/2026-05-15_OpenCode_Controlled_Terminal_Agent/Результаты.md`


## Recent runtime update

### 2026-05-24 - Ollama 0.24.0 controlled archive upgrade

Ollama runtime upgraded from `0.23.4` to `0.24.0` via controlled `.tar.zst` archive path. Direct Ollama smoke, CUDA backend, gateway `/health`, `/v1/models`, and `/v1/chat/completions` regression passed. See `Этапы/2026-05-24_Ollama_0240_Controlled_Upgrade/Результаты.md`.
