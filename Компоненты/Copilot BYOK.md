---
tags: [компонент, copilot]
---

# Copilot BYOK

GitHub Copilot с подключением собственных моделей (Bring Your Own Key). Дополнительный канал доступа к локальным моделям.

## Текущее состояние

| Параметр | Значение |
|----------|----------|
| VS Code | 1.112 |
| План | Free |
| Статус | **Secondary — только plain chat** |

## Два рабочих пути

**Путь A — Встроенный Ollama провайдер:**
```json
"github.copilot.chat.byok.ollamaEndpoint": "http://192.168.0.128:11434"
```
Идёт напрямую в Ollama, минуя шлюз.

**Путь C — OAI Compatible extension (через шлюз):**
Extension `johnny-zhao.oai-compatible-copilot` → gateway.py :8000.

## Что работает / не работает

| Функция | Статус |
|---------|--------|
| Plain chat | ✅ |
| Streaming | ✅ |
| Agent mode (tools) | ❌ Нестабилен |

## Почему Agent не работает
Copilot Agent использует собственный промпт-формат для tools. Локальные модели 30B-класса не обучены под этот формат. Неисправим на стороне шлюза.

Подробнее: [[14 Copilot BYOK Agent нестабилен]]

## Связано с
- [[ADR-002 Continue-first]] — Copilot зафиксирован как secondary
