# Strata и ручное переключение inference backend

Статус: техническая интеграция ACCEPTED_WITH_LIMITATIONS (2026-11-26). Живой цикл проверен; чистая установка и перезагрузка NOT_RUN. Основной режим — Ollama. Решение: [ADR-033](../Решения/operational/ADR-033_MBIP_Manual_Backend_Selection.md); [результаты](../Этапы/2026-11-26_MBIP/Результаты.md).

## 1. Состав и условия

- Сервер llm: Ubuntu 24.04.5, ядро 6.8.0-147, NVIDIA 595.99.02, RTX 3090 300 W, RAM 62,73 GiB. CUDA13 engine требует драйвер >=580.65, SM 8.6 поддержан.
- Strata Terminal 0.2.22, Control и engine 0.1.69, сборка a5bfe0369bfb+cuda13.0; [релиз](https://github.com/Niko1221/Strata/releases/tag/v0.2.22). Код /opt/mbip-strata/0.2.22, состояние /var/lib/mbip-strata, пользователь mbip-strata, static unit mbip-strata.service, loopback 18081, offline.
- GGUF: unsloth/Qwen3.6-35B-A3B-MTP-GGUF ревизия 5bc3e238d916f48a861bac2f8a1990a0e9b7e98d, Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf, 22853663008 B, SHA-256 55983c5a75a1ab969824077b3bb3de4146e82a9234072b48ad4e8f92ad3fe9f1. Путь /srv/ai-test/mbip-strata-models. Один исходный файл, производный токенизатор 9843846 B при повторном экспорте.
- Профиль /var/lib/mbip-strata/profile/strata-mbip-qwen36.json, model ID qwen3.6-35b-a3b-ud-q4_k_xl, text-only, 32768, parallel=1, встроенный MTP, lazy load. SHA принятого живого профиля ae984c8874a318155b3279e59b95ef3dbef57ec45b3d5d0f1ff6501b27c4e570. Верхняя граница контекста не испытана; запас GPU 646 MiB при пилоте, не запускать параллельную модель.
- Q6 и Q27 остаются только в Ollama; исходники не трогать, успешный import plan не заменяет реальную проверку setup.

## 2. Эксплуатация

После завершения всех запросов и фоновых задач обеспечить отсутствие новых. Вход на сервер штатным SSH. Владелец явно инициирует смену:

```bash
mbip-backend status
sudo mbip-backend strata --drained
```

Ожидается MBIP_MODE strata или MBIP_NOOP strata. Gateway/RAG/Ollama остановлены, Strata active/loaded. На Lenovo отдельная вкладка с SSH forward:

```bash
ssh -N -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=yes -o UpdateHostKeys=no   -L 127.0.0.1:18081:127.0.0.1:18081 llm
```

В другой вкладке:

```bash
pi --model ailab-strata/qwen3.6-35b-a3b-ud-q4_k_xl --thinking low
```

Не требуется менять defaultModel. Провайдер установлен только на Lenovo. По завершении закрыть запросы и forward (Ctrl+C); на llm:

```bash
sudo mbip-backend ollama --drained
mbip-backend status
```

Ожидаются MBIP_MODE ollama, Ollama/Gateway/RAG active, Strata inactive, порт 18081 закрыт. При отказе не обходить guard: статус и журнал `journalctl -u mbip-strata.service -n 50`. Команда ждёт readiness, проверяет освобождение GPU/RAM, блокирует переключение при неизвестном состоянии. При 409 от Strata оставляет её работающей. Проверка простоя не заменяет ответственность оператора: новые запросы должны быть исключены на время перехода. Системные guards покрывают штатные последовательные старты units; прямой запуск бинарника и параллельный обход управления не входят в гарантии.

## 3. Чистая сборка и откат

Полный комплект [artifacts/mbip](artifacts/mbip/README.md) и его [SHA256SUMS](artifacts/mbip/SHA256SUMS). Использовать только на согласованной чистой площадке после runbooks 10/20/30/40/50, при принятом GPU power 300 W. Живой llm уже установлен, повторно не выполнять.

```bash
cd Сборка/artifacts/mbip
sha256sum -c SHA256SUMS
python3 -IB test-local.py
./rebuild-strata.sh fetch "$HOME/mbip-strata-staging"
sudo ./rebuild-strata.sh install "$HOME/mbip-strata-staging"
```

Архивы и GGUF сверяются с [SHA256SUMS.upstream](artifacts/mbip/SHA256SUMS.upstream); пакет engine также проверяется по подписи. Для clean rebuild сверить новый профиль по семантическим инвариантам (пути, арх, model ID, окно, MTP, no vision, one slot, loopback, lazy/offline), затем установить точные mbip-backend и четыре drop-in по README комплекта. На текущем llm installer guards проверяет хеш живого профиля; не подгонять этот хеш для другой площадки. Принятый чистый рецепт статически проверен, не испытан целиком. Установка Pi по [60](60_Клиент_Dell.md), затем `python3 -IB configure-pi.py` в каталоге пакета; не менять auth/default/Q6/Q27.

Rollback: сначала штатно вернуть здоровый Ollama mode; удалить только MBIP drop-in, daemon-reload, затем управляющую команду; удалить только provider ailab-strata либо восстановить models.json при совпадении хеша, по README. Исходные веса и units сохраняются. После rollback проверить старый T-FAST и короткие Q6/Q27/embedding. Приватные копии и параметры не публиковать.

## 4. Проверки

Живые проверки: явный цикл, API normal/SSE, Pi short/reasoning/read/tool continuation, отклонение прямых стартов в обоих режимах, unload и readiness, короткие Q6/Q27 и embedding, T-FAST. Полный T-MED, T-LONG, reboot, верхняя граница Strata, Dell и чистый rebuild NOT_RUN. Не изменять прежние baselines или переносить model acceptance между backend.
