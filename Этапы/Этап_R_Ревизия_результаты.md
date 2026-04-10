---
tags: [этап, ревизия, tech-debt, cleanup]
дата: 2026-04-10
этап: R
компонент: Платформа (все слои)
статус: завершён
---

# Этап R — Ревизия / Tech Debt Sweep

## Суть

Полный аудит стенда после завершения всех треков A–F. Зачистка моделей, синхронизация knowledge layer, обновление operational checks, фиксация transitional architecture decisions.

## Результат

- 17→12 моделей (−5 reserve/legacy, ~45 ГБ освобождено)
- `health-check.sh` обновлён: models_count=12, gateway=0.12.0, Bearer auth в embeddings check. 11/11 PASS.
- `setup-check.sh` расширен: 66 проверок (+Docker MCP, +Semantic Layer, +ADR-017/018). 66/0/1.
- `sql_knowledge_cards.py` полностью синхронизирован с фактической SQLite schema (системный drift исправлен).
- RAG corpus: +ADR-017, +ADR-018. Теперь 14 файлов / 18 chunks.
- `orchestrator.py` подтверждён Active (headless scripts зависимость).
- `datetime.utcnow()` подтверждён уже исправленным (Грабли #34 закрыты).
- `pipelines.yaml` — чист, ссылок на удалённые модели нет.

## Ключевые находки

- Schema drift в knowledge cards был системным (DDL, business, examples, anti-patterns — все секции), а не точечным
- Operational checks (`health-check.sh`, `setup-check.sh`) падали из-за устаревших ожиданий, не из-за runtime defects
- Dual orchestration path (CLI + HTTP) — transitional state, не мёртвый код
- Ollama 0.20.4 upgrade заблокирован: FA bug на gemma4:31b (hang >3-4K tokens)
- Continue.dev pivot на CI/CD checks — weak signal для стратегического мониторинга

## Удалённые модели

| Модель | Причина |
|--------|---------|
| qwen3:30b | Reserve, Planner отдан gemma4:31b |
| qwen3:14b | Reserve, нет уникальной роли |
| deepseek-r1:14b | Reserve, есть deepseek-r1:32b |
| qwen2.5-coder:1.5b | Reserve, fallback не нужен |
| qwen3-vl:8b | Reserve, vision покрыт Gemma 4 |

## Осознанно оставлены (wave 2 pending)

- `gemma4:e4b` — PoC edge candidate
- `glm-4.7-flash` — reserve, кандидат на удаление
- `qwen3.5:35b` — legacy, tools сломаны
- `qwen3-coder-next:q4_K_M` — PoC, SA 70%
- `gpt-oss:20b` — обнаружена при ревизии, не оценивалась

## Изменённые файлы

- `~/llm-gateway/scripts/health-check.sh` — обновлён
- `~/llm-gateway/scripts/setup-check.sh` — обновлён (52→66 проверок)
- `~/llm-gateway/scripts/sql_knowledge_cards.py` — полная замена
- `~/rag-mcp-server/docs/adr-canonical/ADR-017-docker-mcp-policy-model.md` — добавлен
- `~/rag-mcp-server/docs/adr-canonical/ADR-018_Semantic_Layer_Architecture.md` — добавлен

## Связанные документы

- [[Паспорт_лаборатории_v28]]
- [[Целевая_архитектура_v1_14]]
- [[Этап018_Semantic_Layer]] (F-next, выполнен в тот же день)
- [[Грабли065_Knowledge_Layer_Drift]]
- [[Грабли066_Runtime_Bridge]]
- [[Грабли067_Auth_Env_Mismatch]]
- [[Грабли068_Gateway_URL]]
- [[Грабли069_Passport_Drift_Models]]
