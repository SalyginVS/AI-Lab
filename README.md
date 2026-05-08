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

- **[[Паспорт лаборатории]]** — фактическое состояние стенда; актуальная версия: `Паспорт_лаборатории_v34.md`.
- **[[Целевая архитектура]]** — архитектурные принципы и целевое состояние; актуальная версия: `Целевая_архитектура_AI_Coding_Platform_v1_20.md`.
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
| Ollama lane | Active |
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
