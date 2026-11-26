# Целевая архитектура AI Coding Platform v1.23

Редакция 2026-11-26. Verified implementation: [паспорт v45](Паспорт_лаборатории_v45.md), [MBIP](Этапы/2026-11-26_MBIP/Результаты.md). Supersedes v1.22 как текущая инструкция; [v1.22](Целевая_архитектура_AI_Coding_Platform_v1_22.md) и прежние acceptance сохраняются как исторический baseline. Depth over Speed остаётся; расширение не изменяет принятые Ollama context 262144 и KV q8_0. Для Q6 сохраняются output=32768, compaction reserve=32768/keep=20000, timeout=0, auto-retry OFF по исторически принятой конфигурации. При изменении runtime, harness, routing path, tool protocol, context или permission boundary требуется ревалидация deployment contract по ADR-030/031/032.

## 1. Слои

| Слой | Актуальное решение |
|---|---|
| Inference | Ollama 0.35.1 (основной), Strata 0.2.22 / engine 0.1.69 CUDA13 (альтернативный) на llm, RTX3090 24 GiB/300 W, RAM 62 GiB. Только один штатный режим. |
| Client / IDE | Lenovo Pi 1.0.3 с отдельными ailab-ollama и ailab-strata; Dell резервный. Остальные поверхности имеют исторический статус, не переоценены. |
| Tool / Apply | Клиентский permission boundary, tool protocol, workspace constraints; Strata проверена коротким read+continuation, не всеми инструментами. |
| Orchestration | Pi bounded execution, прежний Q6 H-1 и Q27 medium. Gateway остаётся Ollama-only. Ручной выбор backend владельцем, не scheduler/proxy. |
| Knowledge / Context | GitHub main, Obsidian vault, ADR, паспорта, evidence, RAG; runtime-директории не источник истины. |
| Governance | Принятый deployment contract = model + quant + backend + harness + routing + tools + permissions. Нельзя переносить модельный verdict между поверхностями. |
| Observability | T-FAST, разрешённые T-MED/T-LONG, logs, hashes, first-pass, self-review, regression repair. Результаты MBIP имеют функциональный scope. |

## 2. Два режима

Ollama: Pi напрямую на LAN 11434, шесть live тегов, включая Q6/Q27, Gateway/RAG доступны. Default после загрузки. Q6 принят как Complex Bounded Engineering Executor (ADR-031), Q27 как исполнитель готового DESIGN (ADR-032); Q5/KAT — исторические, сейчас отсутствуют.

Strata: Pi → SSH forward → loopback 18081 → Strata, один профиль Qwen3.6-35B-A3B UD-Q4_K_XL. Context 32768 настроено, text-only, parallel=1, вывод Pi 8192. Gateway/RAG/Ollama временно остановлены. Прямые provider endpoints сохраняются. Q6/Q27 не перенесены: штатный setup Q6_K отказал, dense Q27 не поддержан штатно. Модельные файлы прежних backend сохранены.

Владелец выбирает режим через mbip-backend после завершения запросов и запрета новых. Команда с локальным lock, readiness и освобождением ресурсов; systemd guards отклоняют прямые последовательные старты конкурирующих units. Не гарантия от намеренного обхода root или произвольных конкурентных запусков. Подробности [ADR-033](Решения/operational/ADR-033_MBIP_Manual_Backend_Selection.md) и [runbook 55](Сборка/55_Strata_и_переключение_backend.md).

## 3. Инварианты и приёмка

Прежний cycle: confirmed evidence → TASK/spec → scope/invariants → bounded execution → first-pass → self-review → repair → tests → final diff → READY_FOR_REVIEW → owner/reviewer acceptance. Модель не принимает собственный результат. Сохранены [ADR-030](Решения/ADR-030_Client_Surface_Determines_Model_Operational_Fit.md), [ADR-031](Решения/ADR-031_Qwen38_Q6_Pi_Complex_Bounded_Executor_Deployment_Contract.md), [ADR-032](Решения/operational/ADR-032_Qwen38_27B_GSQ_RCO_Executor.md).
Новый backend не даёт автоматического допуска к инженерным задачам; Qwen3.6 прошла функциональную проверку, верх окна/clean rebuild/reboot NOT_RUN. Security-направление сохраняет статус непроверенного в scope v1.22, MBIP не изменяет его.
