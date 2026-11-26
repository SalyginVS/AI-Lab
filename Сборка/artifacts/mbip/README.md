# MBIP-03 · запуск и восстановление

Базовый режим после включения сервера — Ollama. Выбор режима выполняется вручную на `llm`. В Strata mode службы Ollama, Gateway и RAG временно недоступны. `mbip-strata.service` статический.

## Действующий сервер

```bash
mbip-backend status
```

Владелец завершает запросы Pi/API и фоновые задачи, исключает новые и затем выполняет на `llm` одну команду. Сценарий повторяет проверки соединений, связанных systemd jobs, процессов, GPU/RAM и HTTP.

```bash
sudo mbip-backend strata --drained
```

Ожидается `MBIP_MODE strata`. Повторный выбор здорового режима отвечает `MBIP_NOOP`. При `MBIP_REFUSED` проверить `mbip-backend status` и `journalctl -u mbip-strata.service -n 50`. Не запускать другой движок, пока старый ещё обслуживает запрос или ресурсы остаются заняты. При 409 от Strata управление оставляет сервер работающим до завершения запроса.

На Lenovo запустить SSH forward в отдельной вкладке, с уже известным ключом хоста. Для завершения forward нажать Ctrl+C в этой вкладке.

```bash
ssh -N -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=yes -o UpdateHostKeys=no \
  -L 127.0.0.1:18081:127.0.0.1:18081 llm
```

```bash
pi --model ailab-strata/qwen3.6-35b-a3b-ud-q4_k_xl --thinking low
```

Тот же профиль доступен через `/model`. `contextWindow=32768` — конфигурация, `maxTokens=8192` оставляет запас для входа. Профиль передаёт в Strata только `none/low/medium/high`. `apiKey: "none"` — заглушка SDK. HTTP Strata на loopback не проверяет пользователя. Граница удалённого доступа — SSH. Закройте клиентские запросы и forward до возвращения режима.

```bash
sudo mbip-backend ollama --drained
mbip-backend status
```

Ожидаются `MBIP_MODE ollama`, три старые службы active, `mbip-strata.service` inactive, серверный 18081 закрыт. Команда ждёт HTTP готовности Ollama до запуска Gateway/RAG. Gateway health проверяется по HTTP, RAG по активному unit и слушающему 8100. Проверка сервиса через произвольный запуск с root относится только к штатным systemd units. Намеренное снятие drop-in или запуск бинарника напрямую вне этой защиты.

## Комплект и восстановление

1. `sha256sum -c SHA256SUMS` и `python3 -IB test-local.py` проверяют пакет и изолированные проверки.
2. `rebuild-strata.sh fetch <staging>` и `sudo ./rebuild-strata.sh install <staging>` описывают чистое восстановление Strata 0.2.22, Control/engine 0.1.69 CUDA13 и одного утверждённого GGUF. `SHA256SUMS.upstream` фиксирует архивы и GGUF, версия engine проверяется подписью пакета. На рабочем сервере повторная загрузка не нужна. Rebuild подготовлен для чистого каталога, сохраняет исходный GGUF в одном месте, экспортирует только токенизатор, пишет профиль text-only 32768/parallel=1 с lazy load и ставит статический unit.
3. `install-guards.sh` устанавливает команду и четыре добавочных drop-in в здоровом Ollama mode. На действующем `llm` он сначала сверяет hash профиля MBIP-02. На чистой восстановленной площадке профиль сравнивают по semantic invariants и затем ставят те же `mbip-backend` и `systemd/*.service.d/95-mbip-mode-guard.conf` с правами root:root 0755/0644, проверяют units и вызывают `systemctl daemon-reload`. Команда не останавливает службы при установке защиты.
4. `python3 -IB configure-pi.py` добавляет шаблон `pi-provider.json`; второй одинаковый вызов идемпотентен. Команда хранит оригиналы `models.json`, `settings.json`, `pi-q27` и их хеши/режимы в приватном каталоге `~/.local/state/mbip03/pi-backups/`. Dell можно подготовить тем же шаблоном позже.
5. `pilot-start.sh` и `test-pi-strata.py` предназначены для явно согласованного испытания. Первый делает отрицательные проверки systemd и явный переход. Второй проверяет API/SSE, короткий Pi и локальный `read` в одноразовой папке. Возврат выполняется отдельной явной командой `sudo mbip-backend ollama --drained`.

### Откат

Вернуть Ollama штатной командой выше. Убедиться, что Strata inactive, порт 18081 закрыт, а `/api/tags` и Gateway health ответили. При откате самой интеграции удалить только четыре добавленных `95-mbip-mode-guard.conf` и выполнить `systemctl daemon-reload`. Скрипт `/usr/local/sbin/mbip-backend` можно убрать после удаления drop-in. Базовые units и веса оставить на месте.

На `llm`, после проверки здорового исходного режима:

```bash
for unit in ollama llm-gateway rag-mcp mbip-strata; do
  sudo rm -- "/etc/systemd/system/$unit.service.d/95-mbip-mode-guard.conf"
done
sudo systemctl daemon-reload
sudo rm -- /usr/local/sbin/mbip-backend
systemctl is-active ollama.service llm-gateway.service rag-mcp.service
curl -fsS http://127.0.0.1:11434/api/version
curl -fsS http://127.0.0.1:8000/health
```

На клиенте при отсутствии новых правок сверить SHA текущего `models.json` с `models_deployed_sha256` в manifest и восстановить `models.json` из приватной копии через временный файл в том же каталоге и `mv -T`. При иных правках удалить только `providers.ailab-strata`. `settings.json` и `pi-q27` остаются эталонными. Закрыть forward. Восстановление не требует reboot.

Для исходной копии Lenovo, созданной этим запуском MBIP-03:

```bash
set -e
backup="$HOME/.local/state/mbip03/pi-backups/20261126T181230Z-w4d3awa_"
target="$HOME/.pi/agent/models.json"
expected=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["models_deployed_sha256"])' "$backup/manifest.json")
printf '%s  %s\n' "$expected" "$target" | sha256sum -c -
tmp=$(mktemp "${target}.mbip-rollback.XXXXXXXX")
install -m 0600 "$backup/models.json" "$tmp"
mv -T "$tmp" "$target"
sha256sum "$target" "$backup/models.json"
```

Подтверждённые живые и стендовые проверки перечислены в отчёте MBIP-03. Веса, пароли и приватные конфиги в комплект не входят.
