# Ежедневная работа: VS Code / Pi, три модели

**Дата:** 27.11.2026. **Статус:** installed, short smoke PASS. Действует вместо исторического [E04 v3 daily](artifacts/mbip05-e04-v3/DAILY.md). Основание: [ADR-035](../Решения/operational/ADR-035_Three_Model_Daily_IDE_Operation.md), [паспорт v48](../Паспорт_лаборатории_v48.md).

## Обычная работа без SSH и ручного sudo

1. Открыть проект в VS Code на Lenovo.
2. Для текущей Inkling нажать **Ctrl+Alt+3** (`Pi: Open`) и работать.
3. Для другой модели **сначала завершить сессию Pi**, нажать **Ctrl+Alt+M** и выбрать профиль. Дождаться `MODEL_READY` и снова **Ctrl+Alt+3**.
4. Если сочетание не работает: `Ctrl+Shift+P` → `Tasks: Run Task` → `AI Lab: Select model`. JSON и PTY-путь проверены; сам графический keypress не тестировался.

| Выбор | Модель / quant / backend | Context, Pi maxTokens | Thinking | KV-cache / параметры |
|---|---|---|---|---|
| Inkling | native SQ-20, Strata | 262144 / 262136 | max | FP16 + offload on; experts VRAM 14.66 GB, effective draft off |
| Flash | UD-Q6_K_XL, Strata | 262144 / 262136 | high | INT8, KV-resident 32768; spec 4, MTP |
| Q27 | IQ3_S, Ollama | 262144 / 262144 | medium | Q8_0, Flash Attention, parallel=1 |

Контекст 262144 — **настроенный лимит**, не гарантированное end-to-end long-context acceptance. Pi compaction: keepRecentTokens 20000, reserve Inkling 8192 / Flash 12288 / Q27 32768. Значения maxTokens являются metadata Pi, не измеренным размером ответа.

## Как работает переключение

`~/.local/bin/ailab-select-model` проверяет текущий backend и отсутствие Pi, через SSH инициирует только штатный `sudo -n /usr/local/sbin/mbip-backend … --drained`, затем проверяет готовность и сохраняет предпочтение. Ограниченный `sudoers` разрешает три точных действия; общий root-доступ не открывался. `ailab-ide` запускает Pi для выбранного model ID. Никогда не менять движок во время активной генерации/фоновой задачи. В случае отказа прочитать статус и не обходить systemd guards. Все переключения ручные, один inference backend одновременно.

Backend Strata слушает localhost `127.0.0.1:18081` (SSH forward), Ollama `192.168.0.128:11434`. Gateway/RAG доступны только с Ollama. Power GPU 300 W сохранён.

**Boot caveat:** сейчас **Strata/Inkling**, но после перезагрузки сервер по-прежнему стартует в **Ollama mode**. Boot-policy и postboot validation для Inkling НЕ внедрены. Сначала проверить состояние, при необходимости выбрать модель заново.

## Проверка и диагностика

```bash
ailab-mode status         # read-only диагностика
ailab-mode current        # активный model ID
ailab-pi inkling --check  # без генерации; только если Inkling активна
ailab-pi flash --check    # аналогично Flash
ailab-pi q27 --check      # аналогично Ollama/Q27
```

Явный выбор из интерактивного терминала VS Code: `ailab-select-model inkling`, `ailab-select-model flash` или `ailab-select-model q27`. Команда `ailab-pi MODEL` запускает Pi для **уже работающего** backend, сама его не переключает. `q6` запрещён как выбор Ollama Flash-Next. Файлы моделей на сервере сохранены.

**Пройдено:** три real Pi short responses, Inkling tool read, возврат в исходный runtime, переходы с точным sudoers, PTY selector. **Не пройдено:** графические hotkeys, IDE edit/test workflow, cold boot, long/thermal acceptance. Исторические Flash long API/agent PASS; Inkling E01 BLOCKED, F07 REVALIDATE. Не обходить термозащиты, не объявлять полный 262k подтверждённым по одному API smoke.

[Снимок клиентских скриптов без секретов](artifacts/daily-ide-2026-11-27/README.md) · [Исторический runbook 55](55_Strata_и_переключение_backend.md).
