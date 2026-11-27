# ADR-034: Strata с двумя профилями, Ollama как резерв

Дата: 2026-11-27. Статус: DRAFT — E04 client delta внедрена, E03-C offline validated; E01 BLOCKED, live E02 и внедрение boot policy NOT_RUN. Документационный PR не является live acceptance.

## Контекст

ADR-033 и MBIP-03 подтвердили ручное переключение backend. MBIP-05 требует Strata с Qwen3.8 Flash-Next 125B UD-Q6_K_XL и Inkling 2 Mini native SQ-20, с сохранением Ollama Q27 MTP как третьей целевой модели, Q6 как резерва, Gateway/RAG в Ollama mode.

## Решение

Один Strata service, два явных профиля, root-owned runtime pointer в /run/mbip05. Смена режима и профиля только после дренирования запросов, с проверкой guards, освобождения ресурсов, readiness и точного model ID. Нет автоматической маршрутизации запросов или одновременной загрузки моделей. Strata API слушает loopback; клиент использует штатную SSH-аутентификацию.

Владелец 2026-11-27 разрешил назначить Strata основным boot mode, Inkling SQ-20 первым профилем и Ollama резервом, включая согласованную перезагрузку после проверок. Ручной выбор runtime не изменяет boot policy. До завершения контекстных испытаний и проверки после reboot эта политика не считается внедрённой.

Текущий целевой контекст MBIP-05: 262144 для обеих моделей (первоначальный план Inkling 1048576 не является результатом испытания). Flash long API/agent PASS; Inkling FP16 effective 262144 подтверждён, длинный ответ отменён по тепловому guard, маркеры/agent/KV reuse не приняты. Первый кандидат Inkling SQ-20 FP8 On, 14.66 GiB expert cap, draft off, 262144; только offline. Не снижать контекст и не менять квантизацию без доказанной необходимости. Исторический E01-P Pi: Flash 8192 output/12288 reserve, Inkling 4096/8192. E04 v3 completion: установлено maxTokens 262136 для обеих Strata (Inkling live declaration; Flash installed runtime formula), context 262144, прежние reserve 12288/8192, keep 20000. E04 thinking correction: native Inkling max (0.99), Flash high (xhigh), Q27 medium; CLI/IDE shared selector, без forced thinking. 17 RPC + 2 TUI mock HTTP requests и 18 routing tests PASS; live generation NOT_RUN. Максимум генерации не измерен. E03-C исторический клиентский кандидат требует согласования с этой дельтой. E02-P mock не является live-допуском. Итоговый кандидат default Inkling проверен на копии; live default пока Ollama.

PWR-01: сохранять 300 W. 420 W вызывали HW Thermal Slowdown, 350 W INVALID и не приняты. Strata startup зависит от службы лимита мощности, доступности хранилищ и отсутствия конкурирующих backend.

## Границы

ADR-030/031/032 и их историческое evidence не изменяются; технический smoke новой поверхности не переносит автоматически инженерные роли. Ollama T-FAST и прежние baseline/evaluator сохраняются. Postboot Strata проверяет фактическое состояние отдельным функциональным контролем. F04 KNOWN, F07 классифицировать по неизменённому оценщику.

E03-P: владелец зафиксировал 300 W и прекратил исследование оптимальной мощности; все защиты сохраняются. Boot enablement и rollback проверены в private systemd root; tmpfiles ownership и reboot остаются открыты. Кандидат read-only readiness не выполняет автоматическую нагрузку; обязательный отдельный guarded functional postboot, unattended smoke требует решения о безопасном мониторинге. Последний Ollama T-FAST F07 REVALIDATE (83 package changes, 23 sensitive linux-); не маскировать baseline. Подробная [карта evidence и последовательность live](../../Сборка/artifacts/mbip05/E03-P.md). E03-C: [deployment package](../../Сборка/artifacts/mbip05/deployment/README.md) содержит server/client installer и conflict-aware rollback; действующие профили, guards и power не меняются транзакцией. Привилегированный live apply/reboot/functional postboot остаются открыты. [Паспорт v46](../../Паспорт_лаборатории_v46.md), [архитектура v1.24 DRAFT](../../Целевая_архитектура_AI_Coding_Platform_v1_24.md). E04 v3 с последующими budget/thinking correction: выполнена клиентская дельта, без применения E03-C boot transaction. [Фактический v47](../../Паспорт_лаборатории_v47.md), [единая инструкция](../../Сборка/artifacts/mbip05-e04-v3/DAILY.md), [verified state](../../Сборка/artifacts/mbip05-e04-v3/VERIFIED-STATE.md). SSH current master, fresh key login, independent master/forward и IDE Pi 1.0.3 readiness PASS; live переходы/генерация BLOCKED по G0. Публиковать документационный PR с явным DRAFT/PARTIAL статусом. Merge только после отдельного разрешения; документационная приёмка не разрешает live deployment. E03-C client intent требуется согласовать с актуальной E04 дельтой перед его будущим внедрением.
