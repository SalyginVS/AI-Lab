# Восстановление Gateway, MCP, RAG и SearXNG

Назначение: восстановить сервисы принятого baseline из проверенных исходников и закреплённых зависимостей.
Статус: документационная поставка RB-07. Проверки настоящего сервера после восстановления относятся к RB-10/RB-14.
Использование: после `20_Ollama.md`, `30_Модели.md` и `40_Q6_runtime.md`. Команды установки ниже в RB-07 на сервере не выполнялись.

## 1. Состав и условия

Исходники взяты из захвата RB-02. Код не изменён, включая старые комментарии, пути и списки моделей.
SHA256 каждого опубликованного файла совпадает с захватом. Состав указан в `artifacts/services/SOURCE_SET.tsv`.
Граф импортов и операции с файлами указаны в `artifacts/services/import-graph.json` и `runtime-files.json`.

| Набор | Файлов в src | Содержание |
|---|---:|---|
| gateway | 15 | run.py, пакет gateway, pipelines.yaml, cron health-check |
| rag-mcp | 18 | server, embedding adapter, reindexer, chunker, 14 документов корпуса |
| docker-mcp | 3 | server, policy, docker-policy.yaml |
| searxng-mcp | 1 | server.py |

Все сервисы сохраняют запуск от оператора из домашнего каталога.
Код RAG содержит абсолютные пути. Cron health-check выбирает токен пользователя `vladimir`.
Для полного воспроизведения этой версии домашний каталог должен быть `/home/vladimir`, оператор должен называться `vladimir`.
Шаблоны unit допускают другое размещение, но сами исходники от этого не становятся переносимыми.
Изменение путей и идентификаторов внутри кода требует новой версии вне RB-07.

`LAB_SERVICE_ROOT` означает домашний каталог оператора, а не общий каталог всех файлов.
Задайте его и `LAB_OPERATOR` в локальной копии `site.example.env`.
Задайте `LAB_SERVICES_PACKAGE` как абсолютный путь к `Сборка/artifacts/services` из выбранной поставки.
Проверьте `python3.12 --version`: требуется CPython 3.12, обследованная версия 3.12.3.

```bash
: "${LAB_SERVICE_ROOT:?}" "${LAB_OPERATOR:?}" "${LAB_SERVICES_PACKAGE:?}"
test -d "$LAB_SERVICES_PACKAGE/gateway/src"
cd "$LAB_SERVICES_PACKAGE" || exit
sha256sum -c SHA256SUMS
```

При несовпадении хеша установку не продолжайте. Не смешивайте исходники и lock разных поставок.

## 2. Размещение и Python

На новой системе каталоги назначения должны быть новыми. Не накладывайте эту процедуру поверх работающей лаборатории.
Скопируйте исходники под оператором. Chroma, журналы, .env и резервные копии в поставку не входят.

```bash
mkdir -p "$LAB_SERVICE_ROOT/llm-gateway" "$LAB_SERVICE_ROOT/rag-mcp-server"
mkdir -p "$LAB_SERVICE_ROOT/docker-mcp-server" "$LAB_SERVICE_ROOT/searxng-mcp"
cp -a "$LAB_SERVICES_PACKAGE/gateway/src/." "$LAB_SERVICE_ROOT/llm-gateway/"
cp -a "$LAB_SERVICES_PACKAGE/rag-mcp/src/." "$LAB_SERVICE_ROOT/rag-mcp-server/"
cp -a "$LAB_SERVICES_PACKAGE/docker-mcp/src/." "$LAB_SERVICE_ROOT/docker-mcp-server/"
cp -a "$LAB_SERVICES_PACKAGE/searxng-mcp/src/." "$LAB_SERVICE_ROOT/searxng-mcp/"
mkdir -p "$LAB_SERVICE_ROOT/llm-gateway/logs" "$LAB_SERVICE_ROOT/rag-data"
python3.12 -I -m venv "$LAB_SERVICE_ROOT/llm-gateway/venv"
python3.12 -I -m venv "$LAB_SERVICE_ROOT/rag-mcp-server/.venv"
python3.12 -I -m venv "$LAB_SERVICE_ROOT/docker-mcp-server/.venv"
python3.12 -I -m venv "$LAB_SERVICE_ROOT/searxng-mcp/.venv"
```

В каждом venv установите весь lock без разрешения зависимостей. Lock закрепляет весь живой набор, включая транзитивные пакеты и pip.

```bash
"$LAB_SERVICE_ROOT/llm-gateway/venv/bin/python" -I -m pip install --require-hashes --no-deps -r "$LAB_SERVICES_PACKAGE/gateway/requirements.lock"
"$LAB_SERVICE_ROOT/rag-mcp-server/.venv/bin/python" -I -m pip install --require-hashes --no-deps -r "$LAB_SERVICES_PACKAGE/rag-mcp/requirements.lock"
"$LAB_SERVICE_ROOT/docker-mcp-server/.venv/bin/python" -I -m pip install --require-hashes --no-deps -r "$LAB_SERVICES_PACKAGE/docker-mcp/requirements.lock"
"$LAB_SERVICE_ROOT/searxng-mcp/.venv/bin/python" -I -m pip install --require-hashes --no-deps -r "$LAB_SERVICES_PACKAGE/searxng-mcp/requirements.lock"
"$LAB_SERVICE_ROOT/llm-gateway/venv/bin/python" -I -m pip check
"$LAB_SERVICE_ROOT/rag-mcp-server/.venv/bin/python" -I -m pip check
"$LAB_SERVICE_ROOT/docker-mcp-server/.venv/bin/python" -I -m pip check
"$LAB_SERVICE_ROOT/searxng-mcp/.venv/bin/python" -I -m pip check
```

Ожидается успешная установка и отсутствие конфликтов. Версии: 31 пакет gateway, 86 RAG, 35 Docker MCP, 32 SearXNG MCP.
Пакеты с direct_url.json не обнаружены. Неподходящую версию не заменять ближайшей.
Для RAG строгая загрузка с `--platform manylinux2014_x86_64` не проходит; подробности в ограничениях.
Обычная установка того же lock на CPython 3.12 Linux прошла на Dell, хеши сохранены.

## 3. Новые токены

`gateway/env.example` содержит только имена и описание формата.
`LLM_GATEWAY_TOKENS` содержит непустой JSON-объект `{token: user_id}`.
`LLM_ORCHESTRATOR_TOKEN` должен быть одним из ключей этого объекта.
RAG использует первый ключ. Генератор создаёт три разных токена: оператор, клиент и orchestrator.

```bash
umask 077
python3 -I "$LAB_SERVICES_PACKAGE/render.py" credentials \
  --output "$LAB_SERVICE_ROOT/llm-gateway/.env" --operator "$LAB_OPERATOR"
test "$(stat -c %a "$LAB_SERVICE_ROOT/llm-gateway/.env")" = 600
```

Генератор не печатает значения и не перезаписывает существующий файл.
Новые значения не коммитить. Передача клиентам относится к RB-08; хранение и ротация к RB-09.
Оба EnvironmentFile ссылаются на один файл gateway/.env, как на принятой системе.

## 4. Unit и gateway

Заполнение шаблонов меняет только `@LAB_SERVICE_ROOT@` и `@LAB_OPERATOR@`.
В живых значениях все шесть файлов, строка cron и compose восстановлены байт в байт.

```bash
rendered_services="$(mktemp -d)"
python3 -I "$LAB_SERVICES_PACKAGE/render.py" templates --source "$LAB_SERVICES_PACKAGE" \
  --output "$rendered_services" --root "$LAB_SERVICE_ROOT" --operator "$LAB_OPERATOR"
sudo install -m 0644 "$rendered_services/units/llm-gateway.service" /etc/systemd/system/llm-gateway.service
sudo install -m 0644 "$rendered_services/units/rag-mcp.service" /etc/systemd/system/rag-mcp.service
sudo install -m 0644 "$rendered_services/units/docker-mcp.service" /etc/systemd/system/docker-mcp.service
sudo install -m 0644 "$rendered_services/units/searxng-mcp.service" /etc/systemd/system/searxng-mcp.service
sudo install -d /etc/systemd/system/llm-gateway.service.d /etc/systemd/system/rag-mcp.service.d
sudo install -m 0644 "$rendered_services/units/llm-gateway.service.d/override.conf" /etc/systemd/system/llm-gateway.service.d/override.conf
sudo install -m 0644 "$rendered_services/units/rag-mcp.service.d/override.conf" /etc/systemd/system/rag-mcp.service.d/override.conf
sudo systemctl daemon-reload
systemctl is-active ollama.service
sudo systemctl enable --now llm-gateway.service
systemctl is-active llm-gateway.service
curl -fsS http://127.0.0.1:8000/health | python3 -I -c 'import json,sys; d=json.load(sys.stdin); assert d["version"]=="0.12.0" and d["auth_enabled"] is True and d["user_count"]==3 and d["pipelines_count"]==1 and d["ollama"]=="ok"; print("GATEWAY_HEALTH=PASS")'
```

Gateway требует ollama.service. После старта ожидаются `active` и GATEWAY_HEALTH=PASS.
Если процесс завершился, смотрите `journalctl -u llm-gateway.service -n 80`.
Не обходите ошибку аутентификации отключением middleware.

## 5. SearXNG и Docker MCP

Исходный compose сохранён. Pin-файл перекрывает только два имени образов.
RepoDigests проверены HEAD-запросами Docker Hub. Списки манифестов и linux/amd64 закреплены в `images.json`.
Оба config digest совпали с ID работающих образов.
`lab-nginx` в состав не входит.

```bash
mkdir -p "$LAB_SERVICE_ROOT/searxng"
install -m 0644 "$rendered_services/docker-compose.yml" "$LAB_SERVICE_ROOT/searxng/docker-compose.yml"
install -m 0644 "$LAB_SERVICES_PACKAGE/searxng/docker-compose.pin.yml" "$LAB_SERVICE_ROOT/searxng/docker-compose.pin.yml"
install -m 0600 "$LAB_SERVICES_PACKAGE/searxng/env.example" "$LAB_SERVICE_ROOT/searxng/.env"
python3 -I "$LAB_SERVICES_PACKAGE/render.py" settings \
  --template "$LAB_SERVICES_PACKAGE/searxng/settings.yml.in" --output "$rendered_services/settings.yml"
sudo install -d -o 977 -g 977 -m 0755 "$LAB_SERVICE_ROOT/searxng/core-config"
sudo install -o 977 -g 977 -m 0600 "$rendered_services/settings.yml" "$LAB_SERVICE_ROOT/searxng/core-config/settings.yml"
cd "$LAB_SERVICE_ROOT/searxng" || exit
docker compose -f docker-compose.yml -f docker-compose.pin.yml config --images
docker compose -f docker-compose.yml -f docker-compose.pin.yml up -d
curl -fsS 'http://127.0.0.1:8080/search?q=Ollama+documentation&format=json' | python3 -I -c 'import json,sys; d=json.load(sys.stdin); assert isinstance(d.get("results"),list); print("SEARXNG_RESPONSE=PASS")'
sudo systemctl enable --now docker-mcp.service searxng-mcp.service
systemctl is-active docker-mcp.service searxng-mcp.service
python3 -I "$LAB_SERVICES_PACKAGE/probe_mcp.py" --url http://127.0.0.1:8200/mcp --tool system_info
python3 -I "$LAB_SERVICES_PACKAGE/probe_mcp.py" --url http://127.0.0.1:8300/mcp --tool web_search --arguments '{"query":"Ollama documentation","max_results":2}'
```

`config --images` должен показывать два `@sha256:` из pin-файла.
Compose не гарантирует готовность HTTP сразу после up; при первоначальном прогреве повторите проверку после просмотра журналов контейнеров.
По P-1 настройки принадлежали UID/GID 977 с режимом 0600; установка сохраняет эту модель доступа.
В шаблоне изменён только secret_key. Новый ключ генерируется при восстановлении.
Старый .env compose не захватывался. Новый файл содержит переменные подстановки исходного compose без переноса живых значений.
Неутверждённые environment overrides из старого .env не считаются воспроизведёнными.
Docker MCP требует docker.service и доступ оператора к Docker socket. Членство в группе docker сохраняется по baseline; оценка привилегий относится к RB-09.
Не используйте проверочные инструменты lifecycle или exec для проверки восстановления.

## 6. RAG: основная процедура и приватный запасной путь

Основная процедура повторно индексирует опубликованный корпус `rag-mcp/src/docs`.
Это 14 Markdown-документов ADR. `chunker.py` использует MAX_CHARS=2000, OVERLAP=200 и последовательные Markdown-разделители.
OVERLAP применяется к длинным неразделённым фрагментам, а не ко всем соседним chunks.
`indexer.py` сортирует пути. Идентификаторы имеют вид `relative_path::chunk::index`.
Эмбеддинги получаются через gateway `/v1/embeddings`, модель `qwen3-embedding`.
Токен берётся из первого элемента JSON-объекта LLM_GATEWAY_TOKENS.
До индексации проверьте импорт embedding-модели по runbook 30 и доступность gateway.

Индексатор удаляет и создаёт заново только коллекцию `lab_docs`.
Перед запуском на существующем хранилище остановите RAG и создайте приватную копию всего каталога Chroma.
На новой сборке используйте пустой каталог, не импортируйте SQL-корпус из исключённых файлов.

```bash
set -a
# shellcheck source=/dev/null
. "$LAB_SERVICE_ROOT/llm-gateway/.env"
set +a
"$LAB_SERVICE_ROOT/rag-mcp-server/.venv/bin/python" -I -c 'import runpy,sys; from pathlib import Path; p=Path(sys.argv.pop(1)).resolve(); sys.path.insert(0,str(p)); runpy.run_path(str(p/"indexer.py"),run_name="__main__")' \
  "$LAB_SERVICE_ROOT/rag-mcp-server" --docs-dir "$LAB_SERVICE_ROOT/rag-mcp-server/docs" --chroma-dir "$LAB_SERVICE_ROOT/rag-data/chroma"
sudo systemctl enable --now rag-mcp.service
systemctl is-active rag-mcp.service
python3 -I "$LAB_SERVICES_PACKAGE/probe_mcp.py" --url http://127.0.0.1:8100/mcp --tool list_collections
python3 -I "$LAB_SERVICES_PACKAGE/probe_mcp.py" --url http://127.0.0.1:8100/mcp --tool index_status
```

Локальные импорты индексатора доступны через явное добавление проверенного каталога в sys.path. Сам исходник не меняется.
Ожидаются 14 файлов и 18 chunks коллекции lab_docs. Размерность 4096 взята из захваченной SQLite.
Полный snapshot содержит две коллекции: lab_docs=18 и sql_knowledge=34, обе dimension=4096.
В SQLite embedding_function помечена legacy; имя модели из этой метки установить нельзя. Оно установлено по адаптеру и indexer.
Повторная индексация этого корпуса создаёт одну коллекцию lab_docs. Равенство всей базы из 52 записей не заявляется.
Источники sql_knowledge в минимальный runtime-набор не входят. Её сохранение возможно только запасным приватным путём.
Качество поиска, тождество embedding после импорта и сравнение старой/новой базы относятся к RB-10.

Запасной путь: при остановленном rag-mcp скопировать из приватного захвата RB-02 весь каталог `rag-data/chroma` в место назначения.
Перед копированием проверьте его по исходному манифесту; одного chroma.sqlite3 недостаточно, нужны все сегменты и служебные файлы.
Ожидаются обе коллекции с указанными счётчиками. Согласованность захвата работающего хранилища не подтверждена испытанием восстановления.
Копию Chroma и её документы не загружать в публичный репозиторий.

## 7. Ночная проверка

После готовности сервисов установите заполненную строку cron в crontab оператора.
Сохраните существующий crontab приватно. Замените только прежнюю строку health-check.sh, не дублируйте её.
Источник новой строки: `$rendered_services/cron`. Время выполнения сохраняется: 03:00 по часовому поясу cron-хоста.
Проверьте результат через `crontab -l`, наличие logs и права записи оператора.

Скрипт сохранён без изменений. Он всё ещё требует Q5, kat-coder и RVN, а не текущий обязательный набор моделей.
Первые две модели исключены владельцем, RVN остаётся OPTIONAL.
Поэтому итоговый FAIL этой исторической проверки ожидаем даже при исправных обязательных сервисах.
Не используйте её общий exit code как критерий приёмки нового baseline. Ремонт алгоритма требует отдельного изменения принятого кода.
Скрипт может отправлять запросы моделям; здесь он офлайн проверен только bash -n и shellcheck.
Встроенный Python исходного скрипта не использует -I. Исходник сохранён байт в байт; изменение относится к следующей версии.

## 8. Обновление, откат и проверка поставки

Новая версия сервисов означает новый проверенный набор исходников, lock, digest и шаблонов.
Не выполнять pip upgrade внутри принятого venv и не полагаться на изменяемый Docker tag.
Для обновления сначала сохраните прежнюю поставку и приватные конфиги, остановите четыре unit и стек Compose.
Создайте новые каталоги сервисов с venv по процедуре выше и переключите их на прежние места размещения.
Не удаляйте Chroma и Docker volumes. Генератор credentials при обновлении не запускать поверх существующего .env.
При откате остановите новую версию, верните прежние каталоги и шаблоны unit, затем прежний compose pin и приватные конфиги.
После daemon-reload запускайте в порядке: Docker/Valkey/SearXNG, Ollama, gateway, RAG и MCP.
Повторите проверки разделов 4–6. Откат схемы данных Chroma отдельно не доказан; используйте соответствующую приватную копию.

Офлайн-проверки запускаются на Dell с evidence RB-00/RB-02/P-1:

```bash
python3.12 -I "$LAB_SERVICES_TESTS/test_services.py" \
  --artifacts "$LAB_SERVICES_PACKAGE" --evidence "$LAB_SERVICES_EVIDENCE" \
  --capture "$LAB_CAPTURE_ROOT" --venvs "$LAB_SERVICES_TEST_VENVS"
```

T4 в этом запуске сверяет lock с живыми версиями и сохранённым результатом фактической загрузки.
Для новой независимой загрузки каждого lock используйте команду пакета RB-07 T4 с новым временным каталогом.
T5 проверялся по HTTP-ответам реестра при подготовке evidence; последующая доступность источника может измениться.
T7 использует настоящие пакеты из lock, локальные заглушки внешних сервисов и временную Chroma.
Тестовая обвязка меняет только адреса зависимостей и привязку сокетов в памяти. Файлы исходников не переписываются.
Полное выполнение unit, настоящие GPU/модели, публичный поиск, reboot и восстановление данных проверяются в RB-10/RB-14.

## 9. Зафиксированные ограничения

Строгий T4 manylinux2014 не проходит для части RAG wheel. Первая ошибка pip: numpy==2.4.4.
Полный список несовместимых с этим platform tag пакетов указан в `artifacts/services/DEPENDENCY_GAPS.md`.
Версии не заменялись. Тот же lock установлен без ошибок на CPython 3.12 Linux с более новым glibc tag; pip check чист.
Это не доказательство установки на новой Ubuntu 24.04.4. Проверка настоящей платформы остаётся в RB-10/RB-14.

Pipeline smoke сохранён с kat-coder. Наличие pipelines_count=1 подтверждает загрузку конфигурации, но не работоспособность отсутствующей модели.
Исторический cron не соответствует новому baseline моделей. Его поведение сохранено и не выдается за успешную приёмку.
Запуск от оператора, группа docker, сетевые доступы и политика хранения секретов переданы в RB-09.
Сводная карта портов, firewall и SSH в этот runbook не входят.

При проверке неизменённого health-check.sh ShellCheck выдал SC2034: CONTEXT_WINDOW объявлена, но не используется.
Также получено 20 сообщений info SC2329 о функциях, вызываемых косвенно через check.
Это незакрытое отклонение от G8 «без предупреждений». Исходник не исправлялся и диагностика не подавлялась.
Новые команды runbook проходят bash -n и shellcheck отдельно от принятого исходника.
