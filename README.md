---
tags: [meta]
---

# AI Lab RTX 3090 — Knowledge Base

Каноническая документация локальной AI Coding Platform. Репозиторий содержит инженерные решения, проверяемые результаты испытаний, конфигурационные baselines и эксплуатационные процедуры.

**Последний подтверждённый снимок runtime: сервер 2026-10-17, клиент 2026-10-16, паспорт v40.** Исторические результаты ниже сохраняют свою дату и границы.

## Источники истины

- [Паспорт лаборатории v40](Паспорт_лаборатории_v40.md): свежий серверный снимок и датированные сведения клиента.
- [Целевая архитектура v1.22](Целевая_архитектура_AI_Coding_Platform_v1_22.md): актуальная схема слоёв, контрактов и ограничений.
- [Рабочий процесс](Meta/Рабочий%20процесс.md) и [Roadmap](Meta/Roadmap.md).
- [ADR-030](Решения/ADR-030_Client_Surface_Determines_Model_Operational_Fit.md): operational fit зависит от client surface.
- [ADR-031](Решения/ADR-031_Qwen38_Q6_Pi_Complex_Bounded_Executor_Deployment_Contract.md): Q6 + Pi, accepted deployment contract.
- [Pi long-context harness](Конфиги/pi_qwen38_q6_long_context_harness.md).
- [Qwen38 Quantization Study](Этапы/2026-09-26_Qwen38_Quantization_Study/Результаты.md): историческое сравнение Q5/Q6/Q8.
- [Q6 complex executor acceptance](Этапы/2026-10-06_Qwen38_Q6_Pi_Complex_Bounded_Executor/Результаты.md).

## Подтверждённый baseline 2026-10-06

| Компонент | Подтверждённое состояние |
|---|---|
| Сервер | Ubuntu 24.04.5 LTS; RTX 3090 24 GiB; RAM 62 GiB |
| Ollama | 0.35.1; `OLLAMA_CONTEXT_LENGTH=262144`; KV `q8_0` |
| Gateway | v0.12.0; последний `/health` PASS, 6 моделей / 1 pipeline |
| Client | Dell Precision 5560, VS Code, Pi 1.0.3, pi-vscode 0.0.9 |
| Qwen3.8 Q6 | Complex Bounded Engineering Executor через Pi; 61/61 owner evaluator PASS |
| Qwen3.8 Q5 | Ранее подтверждённый 262144 long-context baseline |
| Управление | Manual approval, scope lock, mandatory self-review, independent acceptance |

Q6-роль подтверждена **только** для конкретного Pi/Ollama deployment contract. Не равнозначна автономному агенту, архитектурному владельцу или гарантии превосходства над Q5.

## Документационные разделы

- `Решения/`: ADR и канонические архитектурные решения.
- `Этапы/`: результаты проверок, даты, acceptance evidence.
- `Грабли/`: подтверждённые failure modes, причины и исправления.
- `Конфиги/`: принятые baselines и образцы конфигураций.
- `Компоненты/`, `Модели/`: технические карточки (у старых карточек исторический статус).
- `Meta/`: процесс, Roadmap и глоссарий.
- `Briefings/`: исследовательские материалы.

`01_Операционный_справочник_v1.md`, `02_Gateway_техническая_спецификация_v1.md`, `03_Конфигурация_клиента_v1.md`, `04_Enterprise_Transfer_Brief_v1.md` и `Portability_Gap_Analysis.md` относятся к **апрельскому baseline**. Для текущего Pi/Ollama не применять устаревшие значения поверх паспорта v40 и ADR-031.

## Исторические материалы и воспроизводимость

Очистка 2026-10-16 удаляет из `main` экспортные копии, Obsidian/VS Code UI-state, устаревшие паспорта и raw benchmark assets. **Содержимое сохранено в отдельной архивной Git-ветке** `archive/pre-cleanup-2026-10-16` на исходном коммите.

Исследование Q5/Q6/Q8 в `main` сохраняет `Результаты.md` и SHA256-манифест архивных артефактов. Если нужен точный ретест, извлечь frozen fixtures/evidence из архивной ветки и сверить SHA256. Исторический hidden evaluator в публичном репозитории не подходит как секретный evaluator для новых тестов.

Локальная копия документации: `/home/vladimir/llm/AI-Lab`, remote `git@github.com:SalyginVS/AI-Lab.git`. Серверные runtime-директории не являются документационным Git source of truth.

## Изменения после 2026-10-06

По переписке запланирован security-стенд с Qwen3.8 CYBERSECURITY NVFP4, Strix и benchmark `AI_Lab_Qwen38_Security_Benchmark_v1_0_1`. Текущий runtime/installation/benchmark acceptance в этом репозитории **не подтверждён**. После live-сверки создать новый паспорт и отдельный этап с evidence, не переписывая успешные прошлые проверки.

## Сборка с нуля

Начать с [Сборка/00](Сборка/00_Порядок_сборки.md), сверяясь с [паспортом v40](Паспорт_лаборатории_v40.md).
Уровень D принят по завершённым этапам; уровень R (CLEAN_REBUILD_VERIFIED) не подтверждён, финальная приёмка D относится к RB-13.

RB-10.1 принят с ограничениями: пара RB-07.1 установлена, проверка после включения выполняется службой. Владелец принял ядро 147 как рабочую платформу 2026-10-17. Эталон новой сборки остаётся прежним; служба использует отдельный датированный эталон живой платформы.
