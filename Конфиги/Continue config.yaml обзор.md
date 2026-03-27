---
tags: [конфиг, continue]
дата: 2026-03-19
---

# Continue.dev config.yaml — обзор

Файл: `%USERPROFILE%\.continue\config.yaml`

## Структура
- **8 моделей**: 1 embed (transformers.js) + 1 autocomplete (qwen2.5-coder:7b) + 6 chat-capable
- **11 context providers**: code, repo-map, file, currentFile, open, diff, terminal, tree, problems, clipboard, os
- **6 prompts**: review, explain, refactor, docstring, test, security
- **Rules**: 2 глобальных (general, coding) + проектные

## Модели и роли
| Модель | Provider | Роли |
|--------|----------|------|
| qwen2.5-coder:7b | ollama напрямую | autocomplete |
| all-MiniLM-L6-v2 | transformers.js | embeddings |
| qwen3.5:9b | openai (шлюз) | chat, edit, apply |
| qwen3-coder:30b | openai (шлюз) | chat, edit, apply |
| glm-4.7-flash | openai (шлюз) | chat, edit, apply |
| deepseek-r1:32b | openai (шлюз) | chat |
| qwen3.5:35b | openai (шлюз) | chat, edit |
| qwen3-vl:8b | openai (шлюз) | chat (vision) |

## Ключевые грабли
- [[03 Continue timeout миллисекунды]]
- [[04 extraBodyProperties внутри requestOptions]]
- [[05 context секция сбрасывает дефолты]]
- [[10 YAML quirks Continue 1.2.17]]
- [[13 tabAutocompleteModel нет в YAML]]

