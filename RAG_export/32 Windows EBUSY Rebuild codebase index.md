---
tags:
  - грабли
  - continue
  - windows
  - embeddings
дата: 2026-03-29
этап: 9B
компонент: Continue.dev, Windows
---

# 28 Windows EBUSY Rebuild codebase index

## Симптом

Команда `Continue: Rebuild codebase index` в VS Code на Windows завершается ошибкой:
```
EBUSY: resource busy or locked, unlink
C:\Users\Vladimir\.continue\index\index.sqlite
```

Индекс не перестраивается. Повторные попытки не помогают.

## Причина

Файл `index.sqlite` заблокирован процессом VS Code (или расширением Continue). Windows не позволяет удалить заблокированный файл, в отличие от Linux.

## Решение

**Надёжный путь (рекомендуемый):**
1. Полностью закрыть VS Code (не Reload Window, а именно закрыть)
2. Переименовать каталог `%USERPROFILE%\.continue\index\` → `index_backup_YYYYMMDD`
3. Запустить VS Code
4. Continue автоматически создаст новый индекс и начнёт индексацию через gateway
5. Проверить: `journalctl -u llm-gateway -f` — серии `POST /v1/embeddings 200`
6. После подтверждения — удалить `index_backup_*`

**Ненадёжный путь (не рекомендуется):**
- `Continue: Rebuild codebase index` → EBUSY
- `Developer: Reload Window` → иногда помогает, иногда нет

## Урок

На Windows для операций с индексом Continue — всегда использовать cold restart VS Code. Manual rebuild через команду ненадёжен. Automatic reindex при cold restart работает стабильно.

## Связи

- [[Этап010]] (9B)
- [[29 @Codebase deprecated]]
