# 60. Клиент Dell: воспроизводимая установка Pi и VS Code

Статус: ACCEPTED RB-08, 2026-10-17.
Назначение: восстановить обязательный клиент принятого Q6 execution surface на новом или переустановленном Dell.
Порядок: ОС и драйвер, проверенные дистрибутивы, Pi по lock, VS Code, конфигурация, проверки.
Команды установки предназначены для нового клиента. На обследуемом Dell в RB-08 они не выполнялись.
В RB-08 npm, Pi и Code запускались из временных каталогов с временным HOME.
Сервер лаборатории не опрашивался. Реальный запрос к Q6 относится к последующей приёмке.

## 1. Подтверждённая конфигурация и границы

| Компонент | Принятое состояние и источник |
|---|---|
| ОС | Живая Ubuntu 26.04.1, ядро 7.0.0-38-generic. Установочный media-info: Ubuntu 26.04 от 20260423.1 |
| Носитель | ubuntu-26.04-desktop-amd64.iso; SHA256 487f87faaf547ea30e0aba4d5b53346292571256b25333a978db1692bcee9dd2 |
| NVIDIA | 595.99.02, RTX A2000. Пакеты и модули текущего ядра закреплены в key-packages.tsv |
| Node / npm | 22.22.1 / 9.2.0, пакеты Ubuntu |
| Pi | @earendil-works/pi-coding-agent 1.0.3; 120 внешних пакетов, всего 121 пакет в lock |
| VS Code | 1.142.0; commit 6d62b1d5dace93a33b3a6d3eca1317bd5e15bcb1. На живом клиенте snap rev 270 |
| Расширение | pi0.pi-vscode 0.0.9 из VSIX; другие расширения и личные настройки не входят в baseline |
| fd / rg | fd 10.5.0 / ripgrep 15.2.0, x86_64 Linux musl, официальные релизы |
| Clipboard | wl-clipboard 2.2.1-2build1 |

Пакет находится в ``Сборка/artifacts/client/``.
Точное дерево зависимостей Pi задаёт ``package-lock.json``, а не глобальная установка npm.
Внешних зависимостей 120. Одного bundle для воспроизведения живой установки недостаточно.

Снимок Ubuntu: ``20261016T120000Z``. В подписанных индексах найдены 37/37 выбранных пакетов в установленных версиях.
Остальная настольная система, BIOS, личные расширения и настройки VS Code не закрепляются.
Это граница маршрута. Полное тождество всей ОС не заявляется.
Старые ядра не входят в выбранный набор. Пакеты i386 драйвера включены, поскольку они установлены на клиенте.

## 2. ОС, снимок пакетов и драйвер

Цель: установить ОС из того же исходного носителя и получить закреплённые ключевые версии.
Подпись ``SHA256SUMS`` проверена ключом Ubuntu CD Image Automatic Signing Key (2012).
В RB-08 ISO целиком не загружался. До записи носителя на новой машине скачанный ISO обязательно проверяется.

Задайте параметры из ``Сборка/site.example.env``:
``LAB_CLIENT_PACKAGE`` указывает на каталог артефактов клиента;
``LAB_CLIENT_ASSETS`` на каталог загрузок;
``LAB_SERVER_HOST`` на адрес новой площадки.
``LAB_CLIENT_HOME`` указывает на домашний каталог пользователя нового клиента.
Параметры площадки хранятся в приватном файле. Команды ниже предполагают, что они уже экспортированы.

```bash
gpgv --keyring /usr/share/keyrings/ubuntu-archive-keyring.gpg \
  "$LAB_CLIENT_PACKAGE/ubuntu-SHA256SUMS.gpg" "$LAB_CLIENT_PACKAGE/ubuntu-SHA256SUMS"
(
  cd "$LAB_CLIENT_ASSETS" || exit
  curl -fL -o ubuntu-26.04-desktop-amd64.iso \
    https://releases.ubuntu.com/26.04/ubuntu-26.04-desktop-amd64.iso
  grep ' \*ubuntu-26.04-desktop-amd64.iso$' "$LAB_CLIENT_PACKAGE/ubuntu-SHA256SUMS" | sha256sum -c -
)
```

Ожидается корректная подпись и ``OK`` у ISO. При расхождении установку остановить.
Установите Ubuntu Desktop с этого носителя обычным установщиком.
Разметка диска выбирается на новой машине. Эта инструкция не задаёт разрушительных команд записи диска.

После установки настройте временный источник APT на снимок.
Используются штатные ключи Ubuntu. Отключение проверки подписи недопустимо.
Опции ``Dir::Etc`` ниже ограничивают именно эти операции выбранным источником.

```bash
sudo dpkg --add-architecture i386
sudo tee /etc/apt/sources.list.d/ailab-rb08.sources >/dev/null <<'SOURCES'
Types: deb
URIs: https://snapshot.ubuntu.com/ubuntu/20261016T120000Z/
Suites: resolute resolute-updates resolute-security
Components: main restricted universe
Architectures: amd64 i386
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
SOURCES

APT_PIN=(-o Dir::Etc::sourcelist=/etc/apt/sources.list.d/ailab-rb08.sources -o Dir::Etc::sourceparts=-)
sudo apt-get "${APT_PIN[@]}" update
mapfile -t PACKAGES < <(python3 -I -c \
  'import csv,sys; print("\n".join(r["PACKAGE"]+"="+r["INSTALLED"] for r in csv.DictReader(open(sys.argv[1]),delimiter="\t")))' \
  "$LAB_CLIENT_PACKAGE/key-packages.tsv")
sudo apt-get "${APT_PIN[@]}" --simulate install "${PACKAGES[@]}"
```

Сначала изучите симуляцию. Если она предлагает неожиданные удаления или не находит версию, фактическую установку остановить.
После успешной проверки симуляции выполните:

```bash
sudo apt-get "${APT_PIN[@]}" install "${PACKAGES[@]}"
```
После установки перезагрузите новый клиент и проверьте ``uname -r`` и ``nvidia-smi``.
Ожидаются 7.0.0-38-generic и 595.99.02.
Сверьте ``dpkg-query -W`` с каждой строкой ``key-packages.tsv``.
Выполнение этих команд на новой ОС и проверка GPU не входили в офлайн-испытания RB-08.

После установки удалите временный ``ailab-rb08.sources``, если дальнейшие обновления должны идти из штатных источников новой ОС.
Автоматические обновления могут изменить закреплённые версии.
Политика обновлений клиента здесь не принимается. Дрейф фиксируется перед приёмкой.

## 3. Получение проверенных клиентских файлов

Цель: получить конкретные версии, а не latest.
Скрипт использует URL и SHA256 из ``sources.json`` и ``pi-source.json``.
Он проверяет все пять архивов. Несовпадение прекращает процедуру.

```bash
python3 -I "$LAB_CLIENT_PACKAGE/fetch_assets.py" --assets "$LAB_CLIENT_ASSETS"
```

Ожидается ``ASSETS_VERIFIED=5``.
SHA256 VS Code взят из version API Microsoft.
SHA256 VSIX опубликован отдельным файлом Open VSX. Байты VSIX из Microsoft Marketplace совпали с Open VSX.
SHA256 fd опубликован в официальном списке assets GitHub, rg в официальном файле .sha256.
Для Pi дополнительно проверены registry dist.integrity SHA512 и dist.shasum SHA1.
Криптографические подписи npm provenance и VSIX отдельно не проверялись; это не заменяет выполненную проверку хешей.

## 4. Pi по lock и инструменты fd/rg

Цель: установить точное дерево в отдельный versioned prefix.
Глобальный ``npm install -g`` не используется.
HOME и кэш npm ниже временные. Результат установки находится в целевом prefix нового пользователя.

```bash
CLIENT_TMP=$(mktemp -d)
mkdir -p "$CLIENT_TMP/home" "$CLIENT_TMP/work"
PI_PREFIX="$LAB_CLIENT_HOME/.local/opt/pi/1.0.3"
mkdir -p "$PI_PREFIX" "$LAB_CLIENT_HOME/.local/bin"
cp "$LAB_CLIENT_PACKAGE/package.json" "$LAB_CLIENT_PACKAGE/package-lock.json" "$PI_PREFIX/"
(
  cd "$CLIENT_TMP/work" || exit
  HOME="$CLIENT_TMP/home" npm_config_cache="$CLIENT_TMP/npm-cache" \
    npm ci --prefix "$PI_PREFIX" --no-audit --no-fund
  HOME="$CLIENT_TMP/home" "$PI_PREFIX/node_modules/.bin/pi" --offline --version
)
ln -s "$PI_PREFIX/node_modules/.bin/pi" "$LAB_CLIENT_HOME/.local/bin/pi"
```

Ожидается Pi 1.0.3. Версии и расположение всех 121 пакета проверяются T4.
Если ссылка уже существует, не заменяйте её молча. Сначала сохраните прежний versioned prefix для отката.
Добавьте ``$HOME/.local/bin`` в PATH нового пользователя штатным способом.
Живой Pi при RB-08 не запускался.

Pi содержит загрузчик fd/rg из sharkdp/fd и BurntSushi/ripgrep.
Проверенные бинарники совпали с файлами ``~/.pi/agent/bin`` по SHA256.
История конкретного запуска загрузчика не установлена.
Чтобы избежать обращения к latest при восстановлении, установите закреплённые бинарники явно:

```bash
mkdir -p "$CLIENT_TMP/fd" "$CLIENT_TMP/rg" "$LAB_CLIENT_HOME/.pi/agent/bin"
tar -xzf "$LAB_CLIENT_ASSETS/fd.tar.gz" -C "$CLIENT_TMP/fd"
tar -xzf "$LAB_CLIENT_ASSETS/rg.tar.gz" -C "$CLIENT_TMP/rg"
install -m 0755 "$CLIENT_TMP/fd/fd-v10.5.0-x86_64-unknown-linux-musl/fd" "$LAB_CLIENT_HOME/.pi/agent/bin/fd"
install -m 0755 "$CLIENT_TMP/rg/ripgrep-15.2.0-x86_64-unknown-linux-musl/rg" "$LAB_CLIENT_HOME/.pi/agent/bin/rg"
"$LAB_CLIENT_HOME/.pi/agent/bin/fd" --version
"$LAB_CLIENT_HOME/.pi/agent/bin/rg" --version
```

Ожидаются fd 10.5.0 и ripgrep 15.2.0.
Зависимость ``wl-clipboard`` уже включена в ключевые пакеты ОС. Она нужна для ``/copy`` в Wayland.

## 5. VS Code и расширение Pi

Цель: установить официальную сборку той же версии и commit.
Snap rev 270 фиксируется как живой факт. Воспроизводимость старой snap-ревизии не заявляется.
Архив Microsoft является выбранным маршрутом A.3.4.

```bash
CODE_PREFIX="$LAB_CLIENT_HOME/.local/opt/vscode/1.142.0"
mkdir -p "$CODE_PREFIX"
tar -xzf "$LAB_CLIENT_ASSETS/vscode.tar.gz" -C "$CODE_PREFIX"
ln -s "$CODE_PREFIX/VSCode-linux-x64/bin/code" "$LAB_CLIENT_HOME/.local/bin/code"
(
  cd "$CLIENT_TMP/work" || exit
  HOME="$CLIENT_TMP/home" "$LAB_CLIENT_HOME/.local/bin/code" \
    --user-data-dir "$LAB_CLIENT_HOME/.config/Code" --extensions-dir "$LAB_CLIENT_HOME/.vscode/extensions" --version
  HOME="$CLIENT_TMP/home" "$LAB_CLIENT_HOME/.local/bin/code" \
    --user-data-dir "$LAB_CLIENT_HOME/.config/Code" --extensions-dir "$LAB_CLIENT_HOME/.vscode/extensions" \
    --install-extension "$LAB_CLIENT_ASSETS/pi-vscode-openvsx.vsix"
  HOME="$CLIENT_TMP/home" "$LAB_CLIENT_HOME/.local/bin/code" \
    --user-data-dir "$LAB_CLIENT_HOME/.config/Code" --extensions-dir "$LAB_CLIENT_HOME/.vscode/extensions" \
    --list-extensions --show-versions
)
```

Ожидаются 1.142.0, commit 6d62b1d5dace93a33b3a6d3eca1317bd5e15bcb1 и pi0.pi-vscode@0.0.9.
Эта последовательность проверена во временном HOME с отдельными user-data-dir и extensions-dir.
Другие расширения и личные настройки не устанавливаются.

Расхождения T5 записаны в ``sources.json``:
у VSIX 9/10 файлов совпали байт в байт.
Установленный package.json содержит дополнительный ``__metadata``; без него JSON совпадает.
Также VS Code создал ``.vsixmanifest``.
У архива VS Code 2504 файла resources/app совпали со snap.
Ряд нативных файлов отличается, семь файлов из архива отсутствуют в snap.
Это наблюдение, причина не установлена. Тождество всех байтов двух форматов поставки не заявляется.

## 6. Конфигурация Pi: baseline и опциональная RVN

Цель: восстановить принятый Q6 harness и исключить только согласованные записи.
Источник смысла настроек: ``Конфиги/pi_qwen38_q6_long_context_harness.md`` и ADR-031 с уточнением H-1.

``settings.json.in`` совпадает с захваченным файлом байт в байт.
В ``models.json.in`` только два вхождения адреса заменены на ``@LAB_SERVER_HOST@`` в baseUrl.
Шаблоны хранят историческую конфигурацию, включая исключённые модели.
Для новой установки применяется генератор baseline, а не прямое копирование исторических шаблонов.

```bash
python3 -I "$LAB_CLIENT_PACKAGE/generate_config.py" \
  --output "$CLIENT_TMP/generated" --host "$LAB_SERVER_HOST"
install -m 0600 "$CLIENT_TMP/generated/settings.json" "$LAB_CLIENT_HOME/.pi/agent/settings.json"
install -m 0600 "$CLIENT_TMP/generated/models.json" "$LAB_CLIENT_HOME/.pi/agent/models.json"
install -m 0644 "$LAB_CLIENT_PACKAGE/AGENTS.md" "$LAB_CLIENT_HOME/.pi/agent/AGENTS.md"
install -m 0600 "$LAB_CLIENT_PACKAGE/models-store.json" "$LAB_CLIENT_HOME/.pi/agent/models-store.json"
```

Baseline изменяет defaultModel на Q6.
Из modelThinkingLevels и compaction.modelOverrides удаляются только Q5, kat-coder и опциональная RVN.
Провайдер ailab-gateway выделяется в ``rvn.optional.json``.
Все остальные поля сохраняются. Генератор сохраняет порядок ключей и ширину отступов исходных файлов.
Каталог ``baseline/`` содержит автоматически сгенерированный пример: в шаблонах `.in` стоит маркер `@LAB_SERVER_HOST@`, а в примере допустимое имя хоста `LAB-SERVER-HOST`, подставленное генератором вместо адреса.
При установке его нужно регенерировать с реальным host.

Если RVN действительно установлена, повторите генерацию с ``--with-rvn`` перед копированием.
Этот флаг подключает тот же опциональный фрагмент.
RVN по D-8 не восстанавливается из открытых источников.
Выбор опции не выполняет установку самой модели или gateway.

Прямой Q6 использует ailab-ollama, порт 11434, без серверной авторизации.
Исходный auth.json не копируется и не публикуется.
Для Pi создайте новую локальную API-key запись со значением-заполнителем; это не серверный секрет.
T7 использовал такую новую запись во временном HOME и выбирал Q6 из defaultModel.
Пример для обязательного Q6 без RVN:

```bash
python3 -I - "$LAB_CLIENT_HOME/.pi/agent/auth.json" <<'PYAUTH'
import json, os, sys
fd = os.open(sys.argv[1], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as f:
    json.dump({"ailab-ollama": {"type": "api_key", "key": "ollama-local"}}, f)
PYAUTH
```

Существующий auth.json этим примером не перезаписывается.
Для RVN создайте новый приватный auth.json по ``auth.example.json``.
Для соответствующей записи установите ``type`` в ``api_key``, а ``key`` в новый токен из LLM_GATEWAY_TOKENS по runbook 50.
Не переносите пустые type из example как готовую рабочую конфигурацию.
Запись ailab-ollama не требует реального токена. Пример сохраняет структуру обоих исходных провайдеров с пустыми значениями.
Выдайте файлу права 0600. Значения ключей не включаются в evidence.

trust.json не переносится. При defaultProjectTrust=ask доверие запрашивается на новой машине.
models-store.json воспроизводится как пустой JSON-объект.
Pi AGENTS.md опубликован байт в байт после проверки содержимого.

## 7. Проверки harness и фактического запроса

Ожидаемые инварианты:
contextWindow 262144; maxTokens 32768;
compaction.enabled true; reserveTokens 32768; keepRecentTokens 20000;
httpIdleTimeoutMs 0; retry.enabled false; maxRetries 0; provider.maxRetries 0; provider.timeoutMs отсутствует.
Q6 thinkingLevelMap сохраняется целиком: off=null, minimal/low=low, medium=medium, high/xhigh/max=xhigh.
В modelOverrides остаётся samplingParams.reasoning_effort=xhigh по H-1.

T7 запускал Pi из npm ci во временном HOME.
Оба запроса уходили только в локальную заглушку 127.0.0.1:11434/v1/chat/completions.
Она возвращала OK, а тела запросов записаны в rb08_pi_requests.json.

| Поле | Уровень по умолчанию (max) | Явный low |
|---|---|---|
| model | qwen3.8-flash-next:125b-a6b-q6_K-ab-262k | та же Q6 |
| reasoning_effort | xhigh | xhigh |
| max_tokens | 32768 | 32768 |
| temperature / top_p | 1 / 0.95 | 1 / 0.95 |
| presence_penalty / top_k | 0 / 20 | 0 / 20 |

Вывод из T7: в этой конфигурации override перекрывает выбор low.
Это поведение клиента; поведение генерации реальной Q6 заглушка не проверяет.
Удалять override без отдельной задачи и ревалидации запрещает решение H-1.

После развёртывания новой площадки проверьте версию Pi и список моделей.
Первый реальный запрос выполняет оператор последующей приёмки, а не исполнитель RB-08.
Ожидаются Q6, контекст 262.1K, выход 32.8K и thinking=yes.
Для короткой проверки запрос «Ответь только: OK» должен вернуть OK.
CLI- и IDE-проверка проводятся по harness. Отдельно проверяется отсутствие конфликтующих project-local .pi/settings.json.

Ограничение: input Q6 сохранён как ["text","image"] по A.3.1.
Ollama в RB-00 не заявил у Q6 поддержку изображений.
Такая запись не доказывает работоспособность vision. В базовом маршруте проверяется текст.

## 8. Офлайн-проверки и evidence

Порядок повторной проверки:
проверить хеши входов RB-01;
получить закреплённые архивы;
выполнить npm ci в prefix под /tmp с временными HOME и кэшем;
затем запустить тесты.
Архивы, бинарники, приватный захват и данные auth в git не включаются.

```bash
python3 -I "$LAB_CLIENT_TESTS/test_client.py" \
  --package "$LAB_CLIENT_PACKAGE" --capture "$LAB_CLIENT_CAPTURE" \
  --evidence "$LAB_CLIENT_EVIDENCE" --downloads "$LAB_CLIENT_ASSETS" \
  --prefix "$LAB_CLIENT_TEST_PREFIX" --snapshot "$LAB_CLIENT_SNAPSHOT_DIR"
```

T1: шаблоны дают захваченные файлы байт в байт.
T2: изменение JSON равно ровно A.3.1, с опциональной RVN восстанавливаются все разрешённые поля.
T3: registry integrity и 1248 файлов Pi совпали.
T4: npm ci и 121/121 пакетов, Pi 1.0.3.
T5: исходные хеши совпали; расхождения snap/архива и служебных полей VSIX раскрыты.
T6: подписи InRelease и ISO SHA256SUMS проверены; 37/37 ключевых пакетов найдены.
T7: два реальных клиентских запроса в локальную заглушку записаны.

Подписанные индексы снимка и скачанные архивы остаются во временном каталоге, указанном в rb08_temp_root.txt.
Для повторного офлайн-теста их нужно сохранить до завершения приёмки.
Приватный evidence: ~/ailab-rebuild-evidence/RB-08/.
В review bundle нет tarball Pi, VSIX, архивов дистрибутивов или бинарников.
Локальный git format-patch подготовлен от входного HEAD RB-07. Push не выполняется.

## 9. Обновление и откат

Новая версия Pi или VS Code требует нового закреплённого набора и повторной проверки.
Нельзя обновлять глобальный пакет Pi командой без lock.
До обновления сохраните прежний versioned prefix, проверенные источники, lock и приватную копию конфигурации.
Новый набор устанавливается в другой prefix. Ссылки pi/code переключаются после проверки.

Откат означает повторную установку прежнего проверенного набора по его lock и receipts.
Затем восстановите соответствующие ссылки и приватную конфигурацию.
Шаблоны этой поставки не являются резервной копией будущих личных изменений.
После отката повторите проверки harness и короткую CLI/IDE-приёмку.
Изменение Pi behavior, routing или контекстной политики требует ревалидации Q6 по ADR-031.

## Рабочая папка Obsidian

На Dell 2026-10-17 установлен deb-пакет `obsidian` версии 1.13.7, исполняемый файл `/opt/Obsidian/obsidian` (RB-12). Источник: [официальный дистрибутив Obsidian](https://obsidian.md/download). На новом клиенте получить официальный дистрибутив и установить приложение. Хеш дистрибутива в комплекте не закреплён; его побайтовое воспроизведение не заявляется. При первом открытии выбрать «Открыть папку как хранилище» и указать проверенную git-папку документов.

Рабочая папка является git-копией AI-Lab. Путь задаётся на устройстве и не хранится в публичных параметрах. Файлы владельца, которых нет в main, остаются только на устройстве. Отдельная локальная версия отслеживаемого файла тоже является файлом владельца: её нельзя заменять версией main без проверки.

Перед любым обновлением закрыть Obsidian. Сохранить полный архив папки вместе с .git и stash в отдельном приватном каталоге. Проверить читаемость архива, записать SHA256. Отдельно сохранить файлы владельца и их SHA256. Настройки .obsidian/ относятся к устройству, исключены через .gitignore и резервируются отдельно. Не включать файлы владельца или настройки в commit.

До обновления проверить HEAD, remote, status с игнорируемыми файлами, stash и blob-хеши файлов владельца. HEAD должен быть предком принятого main. Неожиданные изменения или запущенный Obsidian означают остановку. Не завершать процесс приложения принудительно.

Для обновления разрешены только git fetch и git merge --ff-only. reset --hard, clean, checkout -- и stash pop запрещены без отдельной проверки; stash apply/drop также не использовать. Если git сообщает конфликт или невозможность fast-forward, сохранить состояние и остановиться.

Ниже V задаёт абсолютный путь рабочей папки. Задать его приватно до запуска команды. Не применять команды к папке с неразобранными изменениями.

```bash
: "${V:?Set V to the private vault path}"
git -C "$V" fetch origin
git -C "$V" merge --ff-only origin/main
C=$(git -C "$V" rev-parse origin/main)
(cd "$V" && python3 -I Сборка/tests/repo/check_package.py --static-only --start "$C")
```

После обновления HEAD, origin/main и git ls-remote origin refs/heads/main должны совпасть. Все отслеживаемые файлы должны соответствовать main, кроме заранее сохранённой версии владельца. В status допустимы только заранее учтённые файлы владельца и .obsidian/, если он был или восстановлен. Blob-хеши владельца и stash@{0} должны остаться прежними. Static-проверка комплекта должна дать STATIC_PASS; полный K1–K10 выполняется на рабочей копии этапа до публикации.

При восстановлении настроек сначала проверить obsidian.json в конфигурации приложения. Копировать .obsidian/ из резервной копии через cp -a только если реестр указывает на эту рабочую папку, назначения ещё нет, а источник существует. Ничего не перезаписывать. При другом пути реестра сохранить его в приватном отчёте, решение принимает владелец. Если реестр отсутствует, привязка не подтверждена: настройки автоматически не копировать, резервную копию сохранить. Если настроек нет нигде, Obsidian создаст их при открытии.

На новом устройстве выполнить git clone принятого репозитория в выбранную папку. Сначала проверить HEAD и комплект, затем вернуть файлы владельца и .obsidian/ из резервной копии без перезаписи существующего содержимого. Проверить status и хеши. Наличие `.obsidian/` не является свидетельством, что приложение зарегистрировало или открыло именно эту папку.


## Q27-E3: 2026-10-21 — запуск исполнителя Q27

E3 добавляет модель в **Сборка/artifacts/client/models.json.in** (провайдер ailab-ollama), launcher **Сборка/artifacts/client/pi-q27**. Принятый baseline-генератор generate_config.py переносит запись Q27 автоматически. **В baseline defaultModel остаётся Q6; живой settings.json не меняется.**

Ключевые параметры модели: contextWindow=262144, maxTokens=262144, thinking medium, temperature=1.0, top_p=0.95, top_k=20, min_p=0, presence_penalty=0, repetition_penalty=1.0, нулевые costs. Запуск в каталоге проекта: pi-q27; на новом Dell установить launcher в ~/.local/bin с правами 0755, убедиться, что каталог присутствует в PATH.

Перед изменением живого профиля сохранить ~/.pi/agent/models.json и settings.json с SHA256. Менять только новую запись Q27. Проверить:
1. pi-q27 --print "Ответь одним словом: OK" — фактический ответ от Ollama.
2. По журналу запроса/реле — reasoning_effort=medium, max_tokens=262144.
3. pi --print без выбора модели — прежний defaultModel (не изменён).
4. После теста выгрузить модели через keep_alive: 0.

**Операционные ограничения:** одна большая модель одновременно, RTX 3090 ограничена постоянными 300 Вт; не менять Q6. Если тесты не пройдены, указывать реальный FAIL/UNVERIFIED и не считать deployment accepted. [ADR-032](../Решения/operational/ADR-032_Qwen38_27B_GSQ_RCO_Executor.md).
