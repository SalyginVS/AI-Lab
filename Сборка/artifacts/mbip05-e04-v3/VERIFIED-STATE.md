# MBIP-05 — проверенное состояние на 27.11.2026

Статус: PARTIAL / DOCUMENTATION REVIEW. Фактическая клиентская конфигурация внедрена. MBIP-05 не закрыт. Снимок основан на E01–E04 evidence и дополнительной read-only сверке в ходе Canonical Documentation Closure. [Паспорт v47](../../../Паспорт_лаборатории_v47.md) · [Инструкция](DAILY.md).

## Внедрено и сверено

| Объект | Фактическое состояние |
|---|---|
| llm | kernel 6.8.0-147-generic, NVIDIA 595.99.02, RTX 3090 24 GiB, 300 W; текущий mode Strata |
| Inkling | Native SQ-20, loaded, 262144 effective, FP16 KV host On, 3072 experts VRAM по ledger E01-P, cap 14.66 GiB, drafting auto в JSON, effective draft off |
| Flash | Установленный UD-Q6_K_XL профиль 262144, int8 KV / resident 32768, resident-budget-gib 36, MTP включён; сейчас не загружен |
| Runtime | Strata active/static; Ollama, Gateway, RAG inactive/enabled. Boot policy Ollama не изменена. Guards и switcher неизменны |
| Ollama | 0.35.1; Q27 GSQ-RCO IQ3_S MTP третья целевая модель, Q6 резерв; сохранены шесть ранее принятых тегов |
| Клиент Lenovo | Pi 1.0.3, VS Code 1.148.0, pi0.pi-vscode 0.0.9; установленный путь IDE указывает на ailab-ide |
| SSH | Один проверенный master, loopback forward; новый key login и отдельный master/forward PASS; фактическое переподключение production listener NOT_RUN |
| Pi | Четыре точных ID, 262144 context; Strata 262136 maxTokens, Q27 262144, Q6 32768; compaction reserve 8192/12288/32768/32768, keep 20000; defaults max/high/medium/max соответственно. Глобальный default Q6/max сохранён |
| Helpers | Три установленных файла совпадают с поставкой по байтам; общий resolver, без forced thinking; неактивный backend возвращает код 3 при открытом G0 |

Точные, проверенные на отсутствие credentials конфигурационные файлы: [Inkling installed FP16](inkling-installed-profile.json), [Flash installed](flash-installed-profile.json). Это не приватные полные snapshots и не инструкция замены рабочего профиля. Хеши: Inkling d516f2b9b42704e9d62fe4a8b4b493a141ba1f9cee0745d6b0430698350c2b22; Flash 405f4d7afa40e7d6ebec2359bc77a4cf419e7a16413e6d706def583e676493d6. Switcher SHA-256 181569c830f2a73d07d476dba27b63a89122fdac228c1f965cd043c96744826e. [Thinking](thinking-selection.json) и [budget](output-budget.json) — проверенные поля клиентской конфигурации, без auth/user/session data.

## Подтверждённые результаты и ограничения evidence

| Этап | Подтверждено | Не подтверждено |
|---|---|---|
| E01 Flash | API long 257138 input / 160 output, markers; dependent agent и cache reuse | Повторный тепловой допуск открыт; live CLI/IDE long NOT_RUN / DEFERRED |
| E01 Inkling | Effective 262144, prompt 257105, prefill 450.3 t/s, 24 output; отмена по SW thermal flag | Ответ, markers, tools, reuse; E01 BLOCKED |
| E01-P | Offline planner, engine CLI capability, client candidate | FP8 actual placement/generation NOT_RUN / DEFERRED |
| E02-P | Четыре mock cases и четыре replay PASS | Четыре prolonged live client cases NOT_RUN / DEFERRED; IDE process resume NOT_RUN |
| E03-P/C | Offline switcher/boot fixtures, 15 транзакционных тестов на Lenovo и target systemd 255; root tmpfiles в изолированном systemd 257 | Privileged target root, реальное внедрение, reboot, functional postboot |
| E04 | SSH/current API readiness, exact model metadata, isolated IDE launch до thinking correction, 18 routing, 17 RPC + 2 TUI mock HTTP requests, Shift+Tab | Последний Extension Host replay, реальные переходы и новые ответы |
| Reserve | Прежние Q6/Q27/embedding 4096 smoke; health 20/20; F04 KNOWN | F07 REVALIDATE: 83 package changes, 23 sensitive linux-; целевой reserve cycle и disposition |

Приватные первичные протоколы остаются за пределами Git. Идентификаторы каталогов и SHA-256 их SHA256SUMS (Lenovo, MBIP-05 work directory) позволяют владельцу сверить источники; хеши не заменяют независимую приёмку.

| Evidence | SHA-256 манифеста |
|---|---|
| e01p.DUc5G2Sr | a6d5c8b706ba6df8a877e32eb55cc8337121a81dec8d724b4450d7f734b4937c |
| e02p.fsrbFhnJ | dfec6fcd900c8ca980967e07a6803dc0087f12b14038fd4ea827c36bde505e7c |
| e03p.GuUkyixI | 03f02187eb35be6db0ef0435b3acf51aa4f28d36da9906d3e433f117d3e9e02e |
| e03c.M0c2NpBB | fd7835ad6978e53ccf25ddb72aa71bd47ebd6c7c53fd3389a1886d4fa9f1e9e5 |
| e04.byndmeai | 00a4f71c8265f61d67333d629d00dc48bb3b6975436f68076ea60c7f69e57108 |
| e04v3.2wuopPps | 24ea96745854e3cd80e91b39f1cfd4def0bffaacc2072be015b8ebd522d07349 |
| e04-budget.bQz1028w | 72b92ce1be3c84e8eb157675479018173d1de7ce592c89b60d30bac6b90d5d57 |
| e04-thinking.LqapdTyR | 90b4530850826a0b4619f1dd8a6c51b747e0096551271b480b31c620721b5e16 |

## Кандидаты и открытые критерии

[FP8 On](../mbip05/deployment/stage/profiles/strata-mbip-inkling.json) — offline-кандидат, не установлен; SHA d5c02363eeb200e414940de3be05e2964136d356c8516174a6ca7021b64ac6df. E03-C default Strata/Inkling и installer/rollback — проверенная offline подготовка, не применённая boot policy. Перед будущим применением согласовать E03-C client intent с E04, не возвращать 4096/8192 и low.

G0 (квалифицированный допуск охлаждения GPU/GDDR6X и накопителей) остаётся блокером. Не менять 300 W, guards, quant и context самостоятельно. FP8 long validation и E02 long live NOT_RUN / DEFERRED, исключены из текущего scope; оригинальный E01 BLOCKED. Открыты G0, безопасный переход и необходимые короткие functional checks после отдельного допуска, reserve/F07 и independent owner acceptance. Исходный E03-C deployment, target privileged root ownership и controlled reboot/functional postboot NOT_RUN / DEFERRED; его gates неизменны. Не повторять уже принятые Flash API long/agent. Документационный PR фиксирует факты, не закрывает эти критерии и не разрешает запуск испытаний. Исторические baseline/evaluator и E03-C/E04 v2 источники сохраняются.
