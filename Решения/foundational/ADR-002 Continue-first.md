---
tags: [adr, решение]
дата: 2026-03-16
статус: принято
---

# ADR-002: Continue.dev как единственный primary agent runtime

## Контекст
Нужен IDE agent runtime для Chat, Edit, Agent mode с tool calling. Варианты: Continue.dev, Copilot BYOK, Kilo Code.

## Решение
**Continue.dev** — единственный primary runtime. Copilot BYOK — secondary, только plain chat. Причины:
- Подтверждён для Chat, Edit, Agent, Apply, Context, Rules, Prompts
- Полностью локальный, YAML-конфигурируемый
- Поддерживает MCP стандарт
- Copilot Agent mode с локальными моделями **нестабилен** и неисправим на стороне шлюза

## Последствия
- Все MCP-серверы подключаются через Continue
- Copilot BYOK зафиксирован как «compatibility check only»
