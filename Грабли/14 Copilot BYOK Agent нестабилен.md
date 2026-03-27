---
tags: [грабли, copilot]
дата: 2026-03-19
этап: "[[Этап07D — Copilot BYOK]]"
компонент: "[[Copilot BYOK]]"
---

# Copilot BYOK Agent mode нестабилен с локальными моделями

## Симптом
«Болтовня» вместо tool_calls. Зацикливание.

## Причина
Copilot Agent uses own tool protocol. 30B models не дисциплинированы для него.

## Решение
Copilot BYOK — только plain chat. Agent mode — только Continue.dev. Неисправим на стороне шлюза.
