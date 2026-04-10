---
tags: [грабли, semantic-layer, knowledge-drift, schema]
дата: 2026-04-10
этап: F-next
компонент: sql_knowledge
статус: частично исправлен
---

# Грабли #65 — Knowledge Layer Drift: карточки vs реальная БД

## Симптом
Модель генерирует `price_per_night` (из карточки), но в реальной таблице — `total_uah`. SQL fails execution.

## Причина
Knowledge cards написаны на основе первоначальной DDL. Фактическая БД отличалась, карточки не были синхронизированы.

## Решение
Обновлены 4 hotel-domain карточки. Employees/departments drift остался (не blocking — gemma4:31b справляется).

## Урок
Semantic layer чувствителен к drift cards ↔ schema. Reasoning-модели устойчивее. Для production — автоматическая DDL extraction → card generation.

## Связано
- [[Этап018_Semantic_Layer]]
- [[ADR-018_Semantic_Layer]]
