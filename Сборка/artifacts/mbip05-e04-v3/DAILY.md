# Ежедневная работа с AI Lab на Lenovo

27.11.2026. Фактическая конфигурация E04 v3, включая корректировки SSH, output budget и thinking. Это инструкция текущего контура, не разрешение на нагрузку и не завершение MBIP-05. [Паспорт v47](../../../Паспорт_лаборатории_v47.md) · [техническое описание E04](README.md).

## 1. Подключение и состояние

В терминале Lenovo:

```bash
ailab-mode connect
ailab-mode status
ailab-mode current
ailab-pi current --check
```

Один SSH master управляет loopback forward Strata 127.0.0.1:18081. Новый вход по ключу проверен отдельно от существующего master. При отсутствии master и свободном порте connect создаёт новый приватный socket. Чужой listener не удаляется. Если ключ заблокирован, разблокировать его штатно в локальной сессии; не отключать проверку host key.

Сейчас на llm загружена Inkling SQ-20 FP16 On, context 262144. Strata active/static, Ollama/Gateway/RAG inactive/enabled. Boot policy остаётся Ollama. G0 открыт: новые нагрузки и переходы на другой backend не допущены. В этом состоянии использовать команды проверки, не отправлять задания модели. Ошибка выбора другого backend с кодом 3 ожидаема.

## 2. Выбор модели и запуск Pi

| Модель | Имя в helper | Стартовый thinking | Context / max output / reserve |
|---|---|---|---|
| Strata Inkling SQ-20 | inkling | max | 262144 / 262136 / 8192 |
| Strata Flash-Next Q6 | flash | high (wire xhigh) | 262144 / 262136 / 12288 |
| Ollama Q27 GSQ-RCO MTP | q27 | medium | 262144 / 262144 / 32768 |
| Ollama Q6 резерв | q6 | max | 262144 / 32768 / 32768 |

Для выбора использовать ailab-mode MODEL (проверка соответствия текущему backend) и ailab-pi MODEL --check. MODEL — одно из имён таблицы; current в ailab-pi выбирает фактический backend, а ollama — псевдоним q27. Helper не переключает неактивный backend при открытом G0 и не обходит guard. Реальное переключение остаётся отдельным незакрытым критерием; прямой вызов switcher не является обходным путём.

После отдельного безопасного допуска к работе с уже активной моделью: из каталога проекта запустить ailab-pi MODEL либо ailab-pi current без --check. Это штатный запуск, а не подтверждение допуска сейчас. Для VS Code открыть проект, при необходимости Developer: Reload Window, затем Pi: Open. IDE запускает ailab-ide → ailab-pi current → pinned Pi 1.0.3; отдельный Pi 1.5.0 не используется. При Ollama IDE выбирает Q27. Для резервного Q6 в Ollama mode явный CLI selector q6.

Не применять /model для смены серверного backend: команда меняет только модель клиента. Новую сессию начинать после штатного, отдельно допущенного переключения. Не редактировать JSON для повседневного выбора.

## 3. Thinking и compaction

Shift+Tab циклически меняет доступный уровень; /thinking открывает выбор уровня. В CLI и IDE стартовый уровень берётся из per-model settings, не из принудительного аргумента launcher. Inkling имеет off/minimal/low/medium/high/xhigh/max (off передаёт none, xhigh и max соответствуют 0.99); Flash off/low/medium/high (high передаёт xhigh). Ollama map сохранён: minimal/low → low, medium → medium, high/xhigh/max → xhigh; off недоступен. KeepRecentTokens = 20000. Pi снижает max_tokens исходя из оценки занятого контекста и запаса 4096; Strata проверяет фактический бюджет со slack 8. Значения maxTokens не гарантируют генерацию ответа такой длины. Compaction включён, Strata thresholds 253952/249856; Q27/Q6 229376. Глобальный Pi default остаётся Q6/max, helpers выбирают явный model ID. [Машиночитаемая карта](thinking-selection.json) и [output budget](output-budget.json).

## 4. Что проверено и что ещё нет

Фактические текущие SSH/API readiness и метаданные Pi проверены. 18/18 helper tests, 17 RPC и 2 TUI mock HTTP-запроса, Shift+Tab max → off подтверждены; mock не доказывает генерацию. Предыдущий isolated Extension Host launch проверен до последней корректировки thinking; повтор этой IDE проверки NOT_RUN. Исторические Flash long API/agent PASS и Ollama Q6/Q27/embedding smoke сохранены. Inkling E01 BLOCKED, FP8 только offline-кандидат. FP8 long validation и четыре длительных E02 cases NOT_RUN / DEFERRED, вне текущего scope. G0 и F07 открыты; только необходимые короткие проверки и переходы после отдельного безопасного допуска. Исходный deployment/reboot/functional postboot NOT_RUN / DEFERRED, gates неизменны. 300 W, MTP, guards, Gateway/RAG и rollback сохраняются. [Карта допуска E03-P](../mbip05/E03-P.md).

Не применять исторические E03-C client defaults вместо E04 v3. Поставочный E03-C boot/client installer не внедрён; перед будущим согласованным внедрением требуется согласовать его client intent с E04 и повторно проверить затронутую транзакцию. При неполадке сначала status, затем [runbook восстановления](../../80_Восстановление_и_апгрейд.md). Не перезапускать службы или менять защиты ради восстановления доступа.
