---
tags: [грабли, continue]
дата: 2026-03-16
этап: "[[Этап07A — Continue Agent]]"
компонент: "[[Continue.dev]]"
---

# YAML quirks Continue 1.2.17 — сборник

- **YAML anchors** (`<<: *defaults`) — не поддерживаются
- **Имена с скобками** — `"model (reasoning)"` → `Invalid input`. Простые имена только
- **roles: [agent]** — невалидная роль. Валидные: chat, edit, apply, autocomplete
- **debounce** → правильно `debounceDelay`
- **Prompts** — через `prompts:` в config.yaml, НЕ через `rules/`
- **capabilities: [tool_use]** — НЕ требуется, Continue автодетектит
- **Проектные rules** — требуют `Developer: Reload Window` при первом создании
- **YAML comments с двоеточиями** — вызывают parse errors
