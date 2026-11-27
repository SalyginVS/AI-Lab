---
tags: [adr, inference, эксплуатация, vscode, pi]
дата: 2026-11-27
статус: Implemented — bounded daily use
---

# ADR-035: ежедневная работа с тремя моделями через VS Code / Pi

## Контекст и решение владельца

27.11.2026 владелец отменил текущие испытания MBIP-05 как рабочий приоритет и разрешил повседневную работу. Не завершённые E01/E02, thermal G0, boot/postboot и F07 не превратились в PASS. Прежние ADR-033/034 сохраняются как историческое основание.

Рабочий состав **только трёх профилей**:

| Имя в меню | Движок | Модель / quant |
|---|---|---|
| Inkling | Strata | `inkling-2-mini-sq-20`, native SQ-20 |
| Flash | Strata | `qwen3.8-flash-next-ud-q6_k_xl`, GGUF UD-Q6_K_XL |
| Q27 | Ollama | `qwen3.8-27b-gsq-rco:iq3s-mtp-262k`, GGUF IQ3_S |

Flash-Next 125B Q6 **на Ollama** исключена из Pi models, default, меню и wrappers; файлы весов/исторический evidence на сервере не удалялись.

## Принятое исполнение

Единая поверхность: Lenovo Ubuntu, VS Code 1.148.0, pi-vscode 0.0.9 и pinned Pi 1.0.3. `Ctrl+Alt+M` связан с user task `AI Lab: Select model` → `~/.local/bin/ailab-select-model` → existing `mbip-backend` при необходимости. `Ctrl+Alt+3` открывает Pi через `ailab-ide` и сохранённое значение `~/.config/ailab-mbip05/preferred-model`.

Переключение engine выполняет штатный `mbip-backend` с `--drained`, lock, service guards, проверкой соединений и освобождения VRAM/RAM; нельзя менять backend во время активной Pi-сессии. Один RTX 3090, один engine за раз, без автоматической маршрутизации. Power 300 W и thermal guards не менялись.

Серверное правило `/etc/sudoers.d/ailab-model-switch` имеет `root:root 0440` и позволяет пользователю `vladimir` **ровно три беспарольных вызова** `/usr/local/sbin/mbip-backend`: `ollama --drained`, `strata --profile inkling --drained`, `strata --profile flash --drained`. `visudo` PASS; контрольная сумма SHA256: `4de845f3af1fb2f02acc9e5e936a817e74daeaefb304314328e8d5403d15416c`. `sudo -n /usr/local/sbin/mbip-backend status` без пароля отказано. Общее passwordless sudo не введено.

Runtime на завершение: **Strata/Inkling active**, Ollama/Gateway/RAG inactive. **Boot policy остаётся Ollama**; Strata default boot/reboot из DRAFT ADR-034 не внедрялся. SSH master и loopback forward Strata сохранены.

## Проверка 27.11.2026

- Exact sudoers; реальные переключения Inkling → Ollama → Flash/Strata → Inkling; восстановление прежнего профиля: PASS.
- Short Pi inference: Inkling `READY`, Q27 `ГОТОВО`, Flash/Strata `READY`, финальная Inkling `READY`, exit 0.
- Pi tool `read` тестового файла с `ALPHA-42`: PASS; изолированный выбор через PTY: PASS; shell/JSON конфигурации и запрет `q6`: PASS.
- В реальном VS Code **не проверены** нажатия хоткеев и полный цикл изменения кода/тестов; postboot, 262144 long-context Inkling/Q27, thermal acceptance также НЕ приняты.
- Ранее подтверждённый Flash long API/agent/cache reuse не пересматривается; Inkling E01 thermal BLOCKED, FP8 long NOT_RUN и F07 REVALIDATE остаются историческими и актуальными рисками. Короткая повседневная работа разрешена отдельно, без снятия защит.

## Документы

[Runbook 56](../../Сборка/56_VSCode_Pi_Три_модели_ежедневная_работа.md), [паспорт v48](../../Паспорт_лаборатории_v48.md), [ADR-033](ADR-033_MBIP_Manual_Backend_Selection.md), [ADR-034 DRAFT](ADR-034_MBIP05_Strata_Dual_Model_Default.md). Нельзя приравнивать short smoke модели к приёмке инженерной роли по ADR-030/031/032.
