---
tags:
  - грабли
  - continue
  - embeddings
  - retrieval
дата: 2026-03-29
этап: 9B
компонент: Continue.dev
---

# 29 @Codebase deprecated

## Симптом

`@Codebase` в Continue Chat возвращает synthetic фрагменты кода, которых нет в реальных файлах проекта. Даже после clean reindex проблема сохраняется. Результаты нестабильны: иногда частичный hit по имени функции, но содержимое цитаты не совпадает с ground truth.

## Причина

`provider: codebase` (контекст-провайдер для `@Codebase`) помечен как **deprecated** в документации Continue.dev. Официальная рекомендация — переходить на Agent mode built-in tools (file exploration, search) и MCP-серверы.

Deprecated provider может:
- Некорректно подавать retrieval chunks модели
- Не обновляться и содержать баги
- Давать нестабильные результаты при смене embedding-модели

## Важно

Слабые результаты `@Codebase` **не являются доказательством** плохого качества embeddings (qwen3-embedding). Transport path и индексация работают корректно (подтверждено логами gateway). Проблема в deprecated retrieval frontend, не в embedding backend.

## Решение

1. **Не использовать `@Codebase` как benchmark** для оценки embedding quality
2. Для валидации embedding quality — direct similarity check через curl к gateway или инспекция `index.sqlite`
3. Для code retrieval в рабочих сценариях — Agent mode built-in tools
4. `provider: codebase` оставлен в конфиге для backward compatibility, но помечен комментарием как deprecated

## Методологический урок

**@Code и @Codebase — разные механизмы:**
- `@Code` (provider: code) — tree-sitter/AST по открытым файлам, не использует embeddings
- `@Codebase` (provider: codebase) — embeddings vector search по workspace (deprecated)

Baseline до миграции был через `@Code`, post-migration тесты через `@Codebase` — это не A/B сравнение, а сравнение двух разных retrieval контуров. Не тестировать новый backend через deprecated frontend.

## Связи

- [[Этап010]] (9B)
- [[28 Windows EBUSY Rebuild codebase index]]
- [[qwen3-embedding]]
