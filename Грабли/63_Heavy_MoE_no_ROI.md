---
tags: [грабли, модели, MoE, ROI]
дата: 2026-04-15
этап: Post-R
компонент: Model Management
статус: Закрыт
---

# 72 Тяжёлые MoE (80B+) нет ROI на single RTX 3090

## Суть

`qwen3-next:80b-a3b-thinking` (MoE 80B, active ~3B) загружена, проверена, удалена. Storage/runtime overhead непропорционален выигрышу. Не вытеснила gemma4:31b.

## Правило

Кандидаты >50B total parameters на single GPU (24 ГБ VRAM, MAX_LOADED=2) требуют предварительной оценки disk, VRAM, cold start, вытеснения. ROI обосновывать до загрузки.

## Связанные

- Отчёт: Lab_RTX3090_Incremental_Engineering_Report_for_Claude_2026-04-15.md
