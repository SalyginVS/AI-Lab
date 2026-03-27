---
tags: [компонент, continue]
---

# Continue.dev

Open-source AI coding assistant для VS Code. Основной agent runtime платформы: [[ADR-002 Continue-first]].

## Текущее состояние

| Параметр | Значение |
|----------|----------|
| Версия | **v1.2.17** |
| IDE | VS Code 1.112 (Windows 11) |
| Конфиг | `%USERPROFILE%\.continue\config.yaml` |
| Формат | YAML schema v1 |

## Режимы работы

| Режим | Модель | Статус |
|-------|--------|--------|
| **Chat** | Любая из 6 chat-моделей | ✅ Работает |
| **Edit** | qwen3-coder:30b, glm-4.7-flash | ✅ Работает |
| **Agent** (tools) | qwen3-coder:30b, glm-4.7-flash | ✅ Работает |
| **Apply** | qwen3-coder:30b, glm-4.7-flash | ✅ Работает |
| **Autocomplete** (FIM) | qwen2.5-coder:7b → Ollama напрямую | ✅ Работает |
| **Vision** | qwen3-vl:8b | ✅ Работает |

## Конфигурация

- **8 моделей** в `models` массиве (вкл. autocomplete и embed)
- **11 context providers** (code, repo-map, file, currentFile, open, diff, terminal, tree, problems, clipboard, os)
- **6 prompts** (review, explain, refactor, docstring, test, security)
- **Rules**: 2 глобальных + проектные (3 уровня)
- **MCP**: `.continue/mcpServers/` (Этап 8A)

Обзор: [[Continue config.yaml обзор]]

## Ключевое ограничение
**MCP серверы работают ТОЛЬКО в Agent mode.** Не в Chat, не в Edit.

## Известные грабли
- [[03 Continue timeout миллисекунды]]
- [[04 extraBodyProperties внутри requestOptions]]
- [[05 context секция сбрасывает дефолты]]
- [[10 YAML quirks Continue 1.2.17]]
- [[13 tabAutocompleteModel нет в YAML]]

