# MBIP-05: две модели Strata

**Текущий статус 27.11.2026: [E03-P — Final integration preparation](E03-P.md), [E03-C — Deployment Package Closure](E03-C.md), [deployment candidate](deployment/README.md).** Поставочный комплект включает проверенные offline транзакции, точные профили, readiness и [client acceptance](client-acceptance/ACCEPTANCE.md). Не содержит private receipt/snapshots/logs; live не принят. Ниже исторический pilot/rebuild recipe. Для итогового boot/client deployment он не заменяет E03-P; не повторять установку и принятые тесты. Исторический E01 BLOCKED, FP8 long validation и live E02 NOT_RUN / DEFERRED; продолжительные испытания исключены из текущего scope. Исходный E03-C installer остаётся NOT_RUN / DEFERRED с неизменными gates. 300 W и все защиты неизменны.

Область: расширение проверенного MBIP-03, без переустановки старого Ollama. Исторический пакет ../mbip сохраняется. Используются Terminal 0.2.22, Control/engine 0.1.69 CUDA13, подписанный inkling2 engine. Не повторять установку на действующем llm. Полная чистая сборка этого рецепта не испытана.

## Подготовка на согласованной площадке

После выполнения исторического MBIP-03 проверить диски, свободную RAM, драйвер и 300 W GPU limit. STAGE расположен на NVMe, INK_STAGE — на том же SATA FS, что /srv/ai-test/mbip-strata-models; hardlink невозможен между FS. Исходные файлы не удаляются. Проверить свободное место, не запускать при активных задачах. Создать доступный оператору STAGE/control. Применить приватные резервные копии до изменения конфигурации.

```bash
sha256sum -c SHA256SUMS
python3 -IB test-mbip03-regression.py
python3 -IB test-profile.py
python3 -IB test-pi-v2.py
set -o pipefail
mkdir -p "$STAGE/control"
for phase in q6 ink mtp pack-q6 pack-mtp; do
  ./prepare-weights.sh "$STAGE" "$INK_STAGE" "$phase" 2>&1 | tee "$STAGE/control/$phase.log" || break
done
```

Проверить EXIT=0 каждого этапа, MTP_RAW_VERIFIED и MTP_PACK=PASS. Источники и SHA-256 в sources; MTP — 31 тензор исходного checkpoint, pinned revision и штатная verify. Установить подписанный Inkling engine по install-ink-engine.sh (проверить usage). Затем:

```bash
sudo ./prepare-profiles.sh "$STAGE" "$INK_STAGE" 2>&1 | tee "$STAGE/control/prepare-profiles.log"
mkdir -p "$STAGE/control/candidate/systemd/mbip-strata.service.d"
cp mbip-backend test-profile.py SHA256SUMS.candidate "$STAGE/control/candidate/"
cp systemd/mbip-strata.service.d/96-mbip05-profiles.conf "$STAGE/control/candidate/systemd/mbip-strata.service.d/"
sudo ./install-profile-switch.sh "$STAGE"
```

Сверить с profiles: путь, model ID, режимы, контекст, parallel=1, lazy/offline, text-only; MTP Flash, RAM budget 40 GiB, no experts.bin duplication. Не подгонять хеш старого принятого скрипта. Отдельно проверить живую смену профилей и режимов; наличие профиля не является PASS inference.

## Клиент и проверка

На Lenovo использовать Pi 1.0.3 и pi-vscode 0.0.9. Применить configure-pi-v2.py с отдельным приватным backup (см. --help); не менять ailab-ollama. ailab-mode устанавливается в ~/.local/bin с mode 0755, SSH alias llm и штатная аутентификация обязательны. После завершения запросов и запрета новых: ailab-mode flash --drained, ailab-mode inkling --drained, ailab-mode ollama --drained. Для соединения/контроля: ailab-mode connect/status. Выбор /model в Pi выполняется только после фактического выбора серверного профиля; проверять ID.

Живые тесты: test-strata-live.py flash/inkling; make-ide-probe.py и ide-probe-test.js — одноразовый Extension Development Host с реальным установленным расширением Pi, без изменения пользовательских проектов. Старые T-FAST и test-ollama-after.py исполняются в Ollama mode без изменения baseline. Контекст, указанный в профиле, не означает испытания его максимальной длины. Не переносить ADR-031/032 на Strata.

## Откат

Остановить собственные запросы, исключить новые. Вернуть Ollama штатным mbip-backend ollama --drained. После согласования восстановить прежний boot mode, если он менялся, и старый postboot. Восстановить старый mbip-backend из приватного rollback и удалить только добавленные MBIP-05 drop-in/boot-файлы; daemon-reload. Сверить состояние с историческим MBIP-03. Восстановить клиентские настройки из приватного backup при совпадении ожидаемых хешей либо адресно вернуть только изменения MBIP-05. Не удалять веса, исходные units, guards или пользовательские данные без отдельного подтверждения. Повторить старые живые smoke и T-FAST. При отказе перехода сохранить логи, не обходить guards.
