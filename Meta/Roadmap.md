---
tags: [meta]
---

# Roadmap — AI Lab RTX 3090

**Редакция:** 2026-10-18.
**Последний проверенный runtime snapshot:** сервер 2026-10-17, клиент 2026-10-16, [паспорт v41](../Паспорт_лаборатории_v41.md).
Roadmap — навигация и приоритеты, не самостоятельное свидетельство работоспособности сервера.

## Закрытые подтверждённые этапы

| Дата/эпоха | Итог | Evidence |
|---|---|---|
| Март–май 2026 | Gateway, MCP, Continue, Observability, Security и RAG-платформа | `Этапы/`, `Решения/`, историческая архитектура v1.21 в Git history |
| 2026-05-15 | OpenCode controlled terminal-agent, scoped docs edits | ADR-029 и соответствующий этап |
| 2026-05-24 | ADR-030: verdict модели зависит от client surface | ADR-030 |
| 2026-09-24 | Qwen3.8 Q5 direct Ollama, 262144 long context (до ~224929 tokens) | Паспорт v38 |
| 2026-09-26 | Q5/Q6/Q8 study, исторический benchmark CLOSED | `Этапы/2026-09-26_Qwen38_Quantization_Study/Результаты.md` |
| 2026-10-06 | Q6 + Pi Complex Bounded Engineering Executor ACCEPTED, 61/61 external evaluator | ADR-031, Pi harness, LeaseFlow stage |

## Актуальная документационная работа

- Cleanup GitHub/Obsidian: убрать экспортные дубликаты, локальное editor state и устаревшие root snapshots; raw quantization assets сохранить в archive branch.
- Поддерживать только последнюю фактически подтверждённую версию паспорта в `main`; старые снимки доступны из Git history.
- После отдельной live-сверки подготовить следующий паспорт. Не объявлять новый runtime статус по одной переписке.
- Синхронизировать architecture и runbooks без обнуления accepted long-context/Q6 results.

## Открытый security track

Запросы 7–8 октября: bounded methodological repair существующего `qwen38-security-review-v1` и подготовка Ollama + CYBERSECURITY NVFP4 + VS Code + Pi + Strix. На 2026-10-16 нет подтверждённого в GitHub acceptance соответствующего стенда и benchmark. Статус: **LIVE VALIDATION REQUIRED**, не DONE.

## Governance

`паспорт verified-state → ADR/evidence → архитектура → Roadmap`. Историческое событие не становится активным состоянием без нового теста.

## Платформа 147, 2026-10-17

Рабочая платформа принята владельцем после T-MED RB-10.1. Актуален [паспорт v41](../Паспорт_лаборатории_v41.md). Служба после включения и два эталона описаны в [90](../Сборка/90_Acceptance_suite.md). Полная ревалидация роли сверх T-MED владельцем не требуется.

## Постоянный лимит мощности GPU, 2026-10-18

[Паспорт v41](../Паспорт_лаборатории_v41.md) отражает рабочую политику RTX 3090: `ailab-gpu-power.service`, постоянные 300 Вт, 30 минут полной нагрузки PASS. При 420 Вт возник `HW Thermal Slowdown`; 350 Вт остались INVALID. T-MED повторён полностью: 10 PASS / 2 INFO. Сборка содержит unit, установку, диагностику, F09 и новый эталон. Развёртывание новой версии postboot на сервере не включено в PR.
