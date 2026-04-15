---
tags: [грабли, gateway, bottleneck, diagnostics]
дата: 2026-04-15
этап: Post-R
компонент: Gateway
статус: Закрыт
---

# 71 Gateway default num_ctx как невидимый потолок

## Суть

`DEFAULT_NUM_CTX = 8192` тихо ограничивал все запросы без явного `num_ctx`. Потолок маскировался под upstream баги (SWA stall, FA bug). Root cause — в integration layer, не в Ollama/llama.cpp.

## Правило

При изменении capability ceiling (MAX) обязательно пересматривать default. Расхождение MAX vs DEFAULT = invisible bottleneck. Проверять не только upper bound, но и fallback path.

## Связанные

- [[ADR-020 Gateway Context Default Policy]]
