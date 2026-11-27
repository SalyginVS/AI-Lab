# Целевая архитектура AI Coding Platform v1.24 — DRAFT

Редакция 2026-11-27, MBIP-05. [v1.23](Целевая_архитектура_AI_Coding_Platform_v1_23.md) сохраняется как исторически принятая редакция. [Паспорт v47](Паспорт_лаборатории_v47.md) описывает фактическое состояние; [v46](Паспорт_лаборатории_v46.md) — историческая дельта E03-C. Эта редакция не supersedes v1.23 до owner acceptance.

## Слои и инварианты
| Слой | Целевой вариант / граница evidence |
|---|---|
| Inference | Один backend: Strata 0.2.22/engine 0.1.69 CUDA13, два явных профиля Inkling SQ-20 и Flash-Next UD-Q6_K_XL, 262144; Ollama 0.35.1: Q27 MTP — третья рабочая целевая модель, Q6 — резерв. Live Inkling FP16, Strata static; boot по-прежнему Ollama. |
| Resource governance | 300 W фиксирован; существующие guards и drain/release/readiness. Сохраняется mount/power ordering. Thermal admission G0 открыт, не считать idle или planner подтверждением охлаждения. |
| Client / IDE | Lenovo Pi 1.0.3 и pi-vscode 0.0.9, отдельные providers и model overrides; default Inkling только кандидат; SSH loopback Strata, Ollama provider сохранён. |
| Tool / Apply | Принятый permission boundary и exact correlated tool calls; mock validates client mechanics, не model reasoning. |
| Orchestration | Manual owner selection, один switcher с lock, без автоматической маршрутизации или одновременного backend. Gateway/RAG работают в Ollama mode. |
| Knowledge | GitHub main — canonical source, рабочая draft-ветка отдельно; runtime и private evidence не source of truth. |
| Governance | Deployment contract связывает модель, quant, runtime, harness, tools, permissions, context. ADR-030/031/032 остаются неизменными, роли Q6/Q27 не переносятся автоматически на Strata. |
| Observability | Exact profile/hash, effective context, actual input/output, cache reuse, resource guards, original T-FAST/evaluator; F07 REVALIDATE не маскировать. |

E04 v3 operational delta: [единая инструкция](Сборка/artifacts/mbip05-e04-v3/DAILY.md) и [проверенный снимок](Сборка/artifacts/mbip05-e04-v3/VERIFIED-STATE.md). IDE launcher выбирает текущий backend/model, global default и boot policy сохранены. Strata maxTokens=262136 для обеих моделей, динамический clamp Pi с запасом 4096, независимые compaction reserve Flash 12288/Inkling 8192. Runtime-derived maxima, не генерационная приёмка. Native thinking map Inkling max / Flash high (wire xhigh) / Q27 medium; CLI/IDE shared resolver, Shift+Tab, wire verification 17 RPC + 2 TUI mock. G0 refusal preserved. SSH fresh socket recovery проверен синтетически, fresh key authentication и независимый master/forward подтверждены реально; production port cutover не выполнялся. Live backend transitions остаются открытыми.

## Boot и rollback
Цель: после boot power service (300 W), доступные mounts, tmpfiles root-owned pointer на Inkling, Strata enabled; Ollama/Gateway/RAG disabled только по boot policy. Ручной выбор runtime не меняет boot policy. Read-only postboot проверяет state, exact profile, context when loaded, loopback и power/thermal; READY_PENDING_FUNCTIONAL, не inference PASS. Функциональный postboot после согласованного reboot обязателен в контролируемом контуре. Unattended load не принят. Переход с проверенного v1.23 через [ADR-034](Решения/operational/ADR-034_MBIP05_Strata_Dual_Model_Default.md); транзакции server/client раздельны, private before/after journal и conflict-aware rollback, не автоматическое распределённое изменение.

## Приёмка
E01-P placement/CLI capability/planner PASS offline; FP8 On 4.125 GiB global KV estimate. Flash API long/agent PASS, Inkling E01 BLOCKED. E02-P четыре комбинации mock PASS и replay PASS; live NOT_RUN. E03-P/С offline integration и deployment preparation, не live acceptance. Минимальная последовательность G0, Inkling FP8 E01, Inkling CLI/IDE, Flash CLI/IDE, reserve F07, deploy/reboot/postboot, review live acceptance. Документационная публикация выполняется отдельно и не закрывает live acceptance. Не повторять принятый Flash API long/agent; не снижать target 262144 или SQ-20 без отдельного обоснованного решения. Детали [E03-P](Сборка/artifacts/mbip05/E03-P.md) и [deployment](Сборка/artifacts/mbip05/deployment/README.md).
