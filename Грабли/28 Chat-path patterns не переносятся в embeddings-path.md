---
tags: [грабли, архитектура, gateway]
дата: 2026-03-28
этап: "9A"
компонент: gateway.py
статус: зафиксировано
---

# 24 Chat-path patterns не переносятся в embeddings-path

## Проблема

В gateway.py уже есть хорошо отработанный chat-path: retry, streaming, tool_calls conversion, reasoning policy, OOM detection. Соблазн — механически применить те же паттерны к embeddings-path.

## Что оказалось

Upstream contracts принципиально разные:

| Аспект | Chat-path (`/api/chat`) | Embeddings-path (`/api/embed`) |
|--------|------------------------|-------------------------------|
| Стриминг | Обязателен (TTFT критичен) | Не нужен (один синхронный ответ) |
| Ответ | `message.content` + `tool_calls` + `thinking` | `embeddings[][]` + `prompt_eval_count` |
| Retry логика | Cold-start retry (модель не загружена) | Другие условия retry |
| Response mapping | Сложная конвертация tool_calls | Простое перекладывание векторов |
| Reasoning policy | 4 уровня effort → think | Не применимо |

Попытка переиспользовать streaming-генератор или build_openai_response() из chat-path напрямую в embeddings — неправильная абстракция.

## Правило

Каждый новый тип endpoint в gateway.py требует **собственного staged pipeline** с нуля. Переиспользовать можно только utility-функции (auth, error classification, httpx client).

## Связь

[[Этапы/Этап009|Этап 9A]], [[Решения/ADR-008 Embeddings без модуляризации|ADR-008]]
