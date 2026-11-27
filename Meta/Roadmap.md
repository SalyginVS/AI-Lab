---
tags: [meta]
---

# Roadmap — AI Lab RTX 3090

**Редакция:** 2026-11-27.
**Последний проверенный runtime snapshot:** сервер и Lenovo 2026-11-27, [паспорт v49](../Паспорт_лаборатории_v49.md); предыдущий v48 и исторические E04 v47 и принятый v45 сохранены.
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
- Отмечать текущий проверенный снимок отдельно от прежних принятых паспортов. Датированные снимки и принятые результаты не переписывать задним числом.
- После отдельной live-сверки подготовить следующий паспорт. Не объявлять новый runtime статус по одной переписке.
- Синхронизировать architecture и runbooks без обнуления accepted long-context/Q6 results.

## Эксплуатационный режим 27.11.2026

По решению владельца испытания MBIP-05 прекращены как текущий приоритет, лаборатория работает в ежедневном VS Code/Pi режиме. Три рабочих профиля: Inkling SQ-20 и Flash-Next UD-Q6_K_XL на Strata; Qwen 27B IQ3_S на Ollama. Установлен ограниченный sudoers для трёх точных команд переключения; native /model, полный цикл Inkling → Flash → Q27 → Inkling, bounded IDE edit/test всех трёх моделей PASS. [Паспорт v49](../Паспорт_лаборатории_v49.md), [ADR-035](../Решения/operational/ADR-035_Three_Model_Daily_IDE_Operation.md), [runbook 56](../Сборка/56_VSCode_Pi_Три_модели_ежедневная_работа.md).

Ниже сохранена **историческая программа MBIP-05 и открытые риски**, а не действующий запрет на разрешённые владельцем короткие рабочие задачи. Длинные Inkling E01/E02, thermal G0, F07, default boot и postboot не завершены.

## MBIP-05 — исторический scope и отложенная приёмка

Решение владельца 27.11.2026: продолжительные испытания, сравнительные исследования контекстов, квантизаций и производительности исключены из текущего scope. Незавершённые long-context/agent/compaction испытания — NOT_RUN / DEFERRED; исторический прерванный Inkling E01 остаётся BLOCKED, не PASS. Только отдельно допущенные необходимые короткие функциональные проверки могут входить в дальнейшую эксплуатационную приёмку. G0, 300 W, guards, drain/release, rollback и требования безопасного postboot сохраняются; это не разрешение на нагрузку или внедрение.

| Этап | Статус |
|---|---|
| E01-P | Offline preparation PASS; FP8 On — кандидат |
| E02-P | Mock PASS, не model acceptance |
| E03-P / E03-C | Offline integration и транзакционный пакет проверены, privileged target root и live deployment NOT_RUN |
| E04 v3 | Клиентская дельта установлена; SSH, текущий API, 18 routing / 17 RPC / 2 TUI mock PASS |
| G0 | BLOCKED: квалифицированный допуск охлаждения |
| E01 / E02 live | Inkling E01 BLOCKED (исторический результат); FP8 long validation и четыре длинных клиентских сценария NOT_RUN / DEFERRED, вне текущего scope |
| Reserve / F07 | F07 REVALIDATE; disposition и необходимые короткие проверки после G0 открыты |
| Boot / postboot | NOT_RUN / DEFERRED; прежний boot Ollama, исторический installer не допущен |
| Canonical documentation | Review PR; merge только после разрешения владельца |

[Единая инструкция](../Сборка/artifacts/mbip05-e04-v3/DAILY.md), [карта evidence](../Сборка/artifacts/mbip05-e04-v3/VERIFIED-STATE.md), [ADR-034](../Решения/operational/ADR-034_MBIP05_Strata_Dual_Model_Default.md). 300 W фиксированы; исследование мощности прекращено. Не повторять принятые Flash long API/agent результаты. Документационная приёмка не является разрешением на inference.

## Открытый security track

Запросы 7–8 октября: bounded methodological repair существующего `qwen38-security-review-v1` и подготовка Ollama + CYBERSECURITY NVFP4 + VS Code + Pi + Strix. На 2026-10-16 нет подтверждённого в GitHub acceptance соответствующего стенда и benchmark. Статус: **LIVE VALIDATION REQUIRED**, не DONE.

## Governance

`паспорт verified-state → ADR/evidence → архитектура → Roadmap`. Историческое событие не становится активным состоянием без нового теста.

## Платформа 147, 2026-10-17

Рабочая платформа принята владельцем после T-MED RB-10.1. Историческое подтверждение: [паспорт v41](../Паспорт_лаборатории_v41.md). Служба после включения и два эталона описаны в [90](../Сборка/90_Acceptance_suite.md). Полная ревалидация роли сверх T-MED владельцем не требуется.

## Постоянный лимит мощности GPU, 2026-10-18

[Паспорт v41](../Паспорт_лаборатории_v41.md) отражает рабочую политику RTX 3090: `ailab-gpu-power.service`, постоянные 300 Вт, 30 минут полной нагрузки PASS. При 420 Вт возник `HW Thermal Slowdown`; 350 Вт остались INVALID. T-MED повторён полностью: 10 PASS / 2 INFO. Сборка содержит unit, установку, диагностику, F09 и новый эталон. Развёртывание новой версии postboot на сервере не включено в PR.

## MBIP 2026-11-26
Техническая интеграция Strata с ручным переключением и Pi завершена, ACCEPTED_WITH_LIMITATIONS. [Паспорт v45](../Паспорт_лаборатории_v45.md), [ADR-033](../Решения/operational/ADR-033_MBIP_Manual_Backend_Selection.md), [результаты](../Этапы/2026-11-26_MBIP/Результаты.md). Сравнения качества/скорости и автоматическая маршрутизация не входят в scope. Reboot, clean rebuild, Dell и верхняя граница окна остаются NOT_RUN.
