# Ежедневная работа: VS Code / Pi, три модели

**При добавлении/замене моделей:** действовать по [ADR-036](../Решения/operational/ADR-036_Empirical_Model_Operation_Policy.md): сбор информации, минимальная проверка работоспособности через рабочий контур, затем эксплуатация. Отдельные испытания и бенчмарки не проводить.

**Дата:** 27.11.2026. **Статус:** installed, bounded IDE functional acceptance PASS. Действует вместо исторического [E04 v3 daily](artifacts/mbip05-e04-v3/DAILY.md). Основание: [ADR-035](../Решения/operational/ADR-035_Three_Model_Daily_IDE_Operation.md), [паспорт v51](../Паспорт_лаборатории_v51.md).

## Native `/model` — обновление 27.11.2026

Установлено клиентское расширение [pi-model-switch](artifacts/daily-ide-native-model-2026-11-27/README.md). После однократного закрытия старой вкладки Pi и открытия новой через `Ctrl+Alt+3` штатная команда `/model` вызывает переключение серверного профиля внутри текущей простаивающей сессии. Проверить статус `AI Lab READY: inkling/flash/q27` и `/lab-status` (сверка Pi и backend). Во время перехода не отправлять запросы и не запускать другие Pi. Закрывать текущую сессию при каждом выборе больше не требуется. 27.11 mock 12/12, negative native TUI (другая сессия, отказ, возврат Inkling) и положительный цикл Inkling → Flash → Q27 → Inkling PASS. Все три модели прошли практическое edit/test задание в VS Code. [Протокол приёмки](artifacts/daily-ide-native-model-2026-11-27/ACCEPTANCE.md). Старый путь ниже сохраняется как резервный.

## Резервный путь: выбор через VS Code task без SSH и ручного sudo

1. Открыть проект в VS Code на Lenovo.
2. Для текущей Inkling нажать **Ctrl+Alt+3** (`Pi: Open`) и работать.
3. Для другой модели **сначала завершить сессию Pi**, нажать **Ctrl+Alt+M** и выбрать профиль. Дождаться `MODEL_READY` и снова **Ctrl+Alt+3**.
4. Если сочетание не работает: `Ctrl+Shift+P` → `Tasks: Run Task` → `AI Lab: Select model`. JSON и PTY-путь проверены; сам графический keypress не тестировался.

| Выбор | Модель / quant / backend | Context, Pi maxTokens | Thinking | KV-cache / параметры |
|---|---|---|---|---|
| Inkling | native SQ-20, Strata | 262144 / 262136 | max | FP16 + offload on; experts VRAM 14.66 GB, effective draft off |
| Flash | UD-Q6_K_XL, Strata | 262144 / 262136 | high | INT8, KV-resident 32768; spec 4, MTP |
| Q27 | IQ3_S, Ollama | 262144 / 262144 | medium | Q8_0, Flash Attention, parallel=1; MTP 2, batch 256 |

Контекст 262144 — **настроенный лимит**, не гарантированное end-to-end long-context acceptance. Pi compaction: keepRecentTokens 20000, reserve Inkling 8192 / Flash 12288 / Q27 32768. Значения maxTokens являются metadata Pi, не измеренным размером ответа.

## Как работает переключение

`~/.local/bin/ailab-select-model` проверяет текущий backend и отсутствие других Pi (при внешнем выборе — всех Pi), через SSH инициирует только штатный `sudo -n /usr/local/sbin/mbip-backend … --drained`, затем проверяет готовность и сохраняет предпочтение. Ограниченный `sudoers` разрешает три точных действия; общий root-доступ не открывался. `ailab-ide` запускает Pi для выбранного model ID. Никогда не менять движок во время активной генерации/фоновой задачи. В случае отказа прочитать статус и не обходить systemd guards. Все переключения ручные, один inference backend одновременно.

Backend Strata слушает localhost `127.0.0.1:18081` (SSH forward), Ollama `192.168.0.128:11434`. Gateway/RAG доступны только с Ollama. Power GPU 300 W сохранён.

**Boot caveat:** последний снимок — Ollama 0.40.18/Q27. После перезагрузки сервер по-прежнему стартует в **Ollama mode**, независимо от последнего выбранного профиля. Boot-policy и postboot validation для Inkling НЕ внедрены. Сначала проверить состояние, при необходимости выбрать модель заново.

Ollama обновлена до 0.40.18: [протокол](artifacts/ollama-upgrade-0.40.18-2026-11-27/README.md). Короткий Q27 read/tool PASS; обратный переход после обновления ещё не проверен. MTP активирован через Modelfile, draft_num_predict=2 и num_batch=256, full GPU; [протокол и актуальный снимок ailab-mode](artifacts/q27-mtp-2026-11-27/README.md). Не восстанавливать старый digest pin без восстановления старого model manifest.

## Проверка и диагностика

```bash
ailab-mode status         # read-only диагностика
ailab-mode current        # активный model ID
ailab-pi inkling --check  # без генерации; только если Inkling активна
ailab-pi flash --check    # аналогично Flash
ailab-pi q27 --check      # аналогично Ollama/Q27
```

Явный выбор из интерактивного терминала VS Code: `ailab-select-model inkling`, `ailab-select-model flash` или `ailab-select-model q27`. Команда `ailab-pi MODEL` запускает Pi для **уже работающего** backend, сама его не переключает. `q6` запрещён как выбор Ollama Flash-Next. Файлы моделей на сервере сохранены.

**Пройдено:** три real Pi short responses, Inkling tool read, возврат в исходный runtime, переходы с точным sudoers, PTY selector, native /model и IDE edit/test всех трёх моделей. **Не принято:** отдельная приёмка резервного hotkey, cold boot, long/thermal acceptance. Исторические Flash long API/agent PASS; Inkling E01 BLOCKED, F07 REVALIDATE. Не обходить термозащиты, не объявлять полный 262k подтверждённым по одному API smoke.

[Снимок клиентских скриптов без секретов](artifacts/daily-ide-2026-11-27/README.md) · [Исторический runbook 55](55_Strata_и_переключение_backend.md).
