# Ollama: проверенный архив, unit, обновление и откат

Статус: READY_FOR_REVIEW, RB-06 1.0, 2026-10-16.
Назначение: установить Ollama 0.35.1 и восстановить захваченную конфигурацию systemd.
Порядок: платформа по 10, учётная запись, архив, установка, запуск, модели по 30, Q6 по 40, проверки.
Изменяющие команды ниже предназначены для будущей площадки. В RB-06 установщики запускались только с временным --root.

## Источник и доказательство

[Релиз Ollama v0.35.1](https://github.com/ollama/ollama/releases/tag/v0.35.1).
[Метаданные GitHub API](https://api.github.com/repos/ollama/ollama/releases/tags/v0.35.1).

| Объект | Размер, байт | SHA256 |
|---|---:|---|
| ollama-linux-amd64.tar.zst | 1439658961 | 9fcd79ac4575b2bd31b992eee18b1000c8ad126b451627c8f8cd091714cfbb10 |
| bin/ollama | 28627920 | 8fd655c8fde7b524dc3a64ae1006f9e8d0344dec93b1796fc9f87b7c5179fbb9 |
| lib/ollama/llama-server | 15096 | 234b05b2138264f8fb263c3205e85f4c290e8afe5067e280a4f6f90cdac5696b |

Digest GitHub совпал с SHA256 скачанного архива.
Оба ELF совпали с RB-00. На исходном сервере runner переименован в `llama-server.real-0.35.1` установщиком Q6.
Все захваченные обычные файлы дерева lib/ollama совпали по размеру.
Набор путей совпал после учёта Q6 wrapper и переименования runner.
RB-00:S07.03 не содержит целей символических ссылок. Для них совпали длины, но тождество целей не доказано.
Поэтому T2 имеет статус PARTIAL_RECORDED. Дополнительные чтения сервера для устранения этого пробела не выполнялись.
Хеш именно оставленного на сервере архива не вычислялся; внешнему архиву доказано тождество двух работающих ELF и размеров дерева.

`install.sh` не используется по решению A.3.1.
Он устанавливает поток без предварительной проверки SHA256, заменяет unit и переносит PATH оператора.
Принятый в репозитории архивный способ заменяет `/usr/local/lib/ollama` целиком.
Пакет RB-06 проверяет размер и SHA256 до изменений целевых файлов.

## Параметры и шаблоны

Задайте `LAB_OLLAMA_PACKAGE` как абсолютный путь к `Сборка/artifacts/ollama`.
`LAB_OLLAMA_ARCHIVE` указывает на скачанный архив.
`LAB_OLLAMA_BACKUP` задаёт новый каталог резервной копии.
`LAB_OLLAMA_BIND` и `LAB_OLLAMA_URL` задаются на площадке.
Все переменные описаны в `site.example.env`.

Подстановок ровно две:
`@OLLAMA_SERVICE_PATH@` в unit и `@LAB_OLLAMA_BIND@` в override.
`90-fn3090-keepalive.conf` переносится без изменения.
T1 восстанавливает три файла RB-02 байт в байт при исходных значениях.

Рекомендуемый `OLLAMA_SERVICE_PATH`:
`/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`.
Это осознанное отличие от исходного PATH с пользовательскими каталогами, оставленного install.sh.
Ollama и Q6 wrapper используют абсолютные пути для runner и logger.
Поведение с сокращённым PATH проверяется в RB-10.
Остальные строки unit и drop-ins не меняются.

Инварианты: context 262144, KV q8_0, Flash Attention 1.
Также сохраняются MAX_LOADED_MODELS=2, NUM_PARALLEL=1, CUDA_VISIBLE_DEVICES=0,
GGML_CUDA_NO_GRAPHS=1 и KEEP_ALIVE=30m.

## 1. Учётная запись и хранилище

Сначала завершите проверки ядра, драйвера и контейнерной платформы по `10_Сервер_ОС_и_драйвер.md`.
На исходном сервере ollama имеет uid 996, gid 988, домашний каталог /usr/share/ollama и shell /bin/false.
Числовые идентификаторы на новой площадке назначаются свободными системными значениями.
Владение задаётся именем ollama; чужие существующие UID/GID не переназначаются.

```bash
getent group ollama || sudo groupadd --system ollama
getent passwd ollama || sudo useradd --system --gid ollama \
  --home-dir /usr/share/ollama --shell /bin/false ollama
getent group video
getent group render || sudo groupadd --system render
sudo usermod -aG video,render ollama
sudo install -d -m 0750 -o ollama -g ollama /usr/share/ollama
sudo install -d -m 0755 -o ollama -g ollama \
  /usr/share/ollama/.ollama /usr/share/ollama/.ollama/models
getent passwd ollama
id ollama
stat -c '%U:%G %a %n' /usr/share/ollama /usr/share/ollama/.ollama/models
```

Ожидаются shell /bin/false, домашний каталог /usr/share/ollama и группы video, render.
При существующей несовместимой учётной записи остановитесь до установки.
Хранилище по умолчанию: `/usr/share/ollama/.ollama/models`.
`LAB_OLLAMA_MODELS` в runbook моделей указывает туда же; дополнительных подстановок unit не добавляется.
Данные моделей установщик runtime не трогает.

## 2. Получение и preflight

```bash
curl --fail --location --retry 3 \
  https://github.com/ollama/ollama/releases/download/v0.35.1/ollama-linux-amd64.tar.zst \
  --output "$LAB_OLLAMA_ARCHIVE"
printf '%s  %s\n' \
  9fcd79ac4575b2bd31b992eee18b1000c8ad126b451627c8f8cd091714cfbb10 \
  "$LAB_OLLAMA_ARCHIVE" | sha256sum --check -
test "$(stat -c %s "$LAB_OLLAMA_ARCHIVE")" = 1439658961
cd "$LAB_OLLAMA_PACKAGE"
grep -v '  ollama-linux-amd64.tar.zst$' SHA256SUMS | sha256sum --check -
```

Продолжать только при совпадении размера и SHA256.
В SHA256SUMS пакета строка `# archive-size` закрепляет размер внешнего архива.
Архив не хранится в git и не входит в review bundle.
Зависимости установщика: Bash, Python 3.12+, zstd, достаточно свободного места для распаковки и новой версии.
Текущая версия сохраняется в backup. Распаковка требует ещё примерно размера lib/ollama.
Оцените пространство через `df -h` и `du -sh /usr/local/lib/ollama` перед обслуживанием.

Перед обновлением прекратите задачи клиентов и выгрузите модели штатными командами Ollama.
Проверьте пустой список моделей в /api/ps, затем остановите daemon:

```bash
curl --fail --silent --show-error "$LAB_OLLAMA_URL/api/ps"
sudo systemctl stop ollama
```

На первой установке сервиса ещё нет: остановка не требуется.
Эти действия выполняет оператор. Установщик не вызывает systemctl и не создаёт пользователей.

## 3. Установка файлов

Укажите новый backup-каталог. Он не должен уже существовать или пересекаться с устанавливаемыми путями.
Для настоящей площадки команда ниже использует --root /.
В текущем этапе выполнялся только её вариант с --root /tmp/rb06-tests-.../root.

```bash
sudo bash "$LAB_OLLAMA_PACKAGE/install_ollama_runtime.sh" \
  --root / \
  --archive "$LAB_OLLAMA_ARCHIVE" \
  --backup-dir "$LAB_OLLAMA_BACKUP" \
  --service-path "$OLLAMA_SERVICE_PATH" \
  --bind "$LAB_OLLAMA_BIND"
```

Ожидается `INSTALL=PASS` и оба SHA256 из таблицы.
Повтор при тех же байтах выдаёт `INSTALL=UNCHANGED` и сохраняет байты, режимы и времена изменения.
Если Q6 wrapper уже наложен, runtime отличается от архива: повторная установка Ollama заменит его и создаст новую резервную копию.
Для такой операции нужен новый backup-каталог.

Установщик проверяет файлы пакета, размер архива, SHA256 и полный поток zstd/tar до записи в --root.
Он отклоняет выходящие за разрешённые каталоги пути и ссылки.
Существующие bin/ollama и lib/ollama целиком сохраняются в backup.
Также сохраняются заменяемые unit/drop-ins и существующие Q6 state/template для согласованного отката.
`backup.json` содержит контрольные отпечатки сохранённых файлов, режимов и ссылок.

Замена lib/ollama удаляет прежний wrapper и находившиеся там .real-*.
Эти файлы остаются только в резервной копии установщика.
Ошибки preflight оставляют целевой каталог без изменений.
Ошибка файловой транзакции вызывает восстановление. Устойчивость к отключению питания посреди замены в RB-06 не доказывалась.
Другие drop-ins systemd не удаляются; неизвестные дополнительные настройки требуют проверки перед запуском.

## 4. Запуск и проверка

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ollama
"$LAB_OLLAMA_BIN" --version
systemctl show ollama --property=Environment --property=User --property=Group --property=ExecStart
curl --fail --silent --show-error "$LAB_OLLAMA_URL/api/version"
```

Ожидается версия CLI и API 0.35.1.
User и Group: ollama. ExecStart: /usr/local/bin/ollama serve.
Проверьте фактические PATH и OLLAMA_HOST против параметров площадки.
В Environment должны присутствовать context 262144, KV q8_0, Flash Attention 1 и остальные инварианты выше.
При отличии остановитесь до импорта моделей.

Затем выполните `30_Модели.md`, а после импорта Q6 обязательно `40_Q6_runtime.md`.
После каждого обновления или отката Ollama повторяйте `40_Q6_runtime.md`.
До его verify и поведенческих проверок принятый профиль Q6 не восстановлен.
Остальные модели не должны получать профиль Q6.

## 5. Обновление

Другую версию сначала проверяют как отдельный релиз.
Зафиксируйте официальный asset, размер, опубликованный SHA256 и фактический SHA256 скачанного файла.
Создайте проверенную копию пакета с новым receipt в SHA256SUMS.
Нельзя просто заменять хеш фактически скачанного файла, если официальный источник не подтвердил его.
Размер записывается строкой `# archive-size имя размер`, SHA256 обычной строкой.
Контрольные суммы шаблонов и кода сохраняются.

После preflight выполните остановку daemon, установку с новым backup-каталогом, daemon-reload и запуск.
Повторите модели при необходимости, затем `40_Q6_runtime.md` и поведенческую ревалидацию ADR-031.
Совпадение файлов не доказывает совместимость новой версии runner.

## 6. Откат версии

Предпочтительный маршрут: повторная установка предыдущего проверенного архива тем же установщиком.
Используйте соответствующие ему SHA256SUMS и размер, новый backup-каталог и прежние параметры площадки.
После запуска повторите `40_Q6_runtime.md`.
T5 проверяет возврат обоих хешей 0.35.1 и успешное повторное наложение Q6.

Альтернатива: восстановить резервную копию установщика.
Прекратите задачи, выгрузите модели, остановите daemon и задайте `LAB_OLLAMA_RESTORE_FROM`.
Сначала проверьте все отпечатки, затем верните сохранённые файлы:

```bash
sudo python3 -I - "$LAB_OLLAMA_PACKAGE/runtime.py" "$LAB_OLLAMA_RESTORE_FROM" <<'PY'
import importlib.util, json, re, sys
from pathlib import Path
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("runtime", sys.argv[1])
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
backup = Path(sys.argv[2]).resolve(strict=True)
expected = json.loads((backup / "backup.json").read_text())
actual = {str(q.relative_to(backup)): runtime.fingerprint(q)
          for q in backup.iterdir() if q.name != "backup.json"}
assert json.dumps(actual, sort_keys=True) == json.dumps(expected, sort_keys=True)
logical = ["usr/local/bin/ollama", "usr/local/lib/ollama",
           "etc/systemd/system/ollama.service",
           "etc/systemd/system/ollama.service.d/override.conf",
           "etc/systemd/system/ollama.service.d/90-fn3090-keepalive.conf"]
state = backup / "var/lib/ai-lab/q6-runtime.json"
if state.exists():
    template = json.loads(state.read_text())["template"]
    assert re.fullmatch(r"/usr/local/share/ollama/templates/q6-[0-9a-f]{12}-reasoning-compat\.jinja", template)
    logical += ["var/lib/ai-lab/q6-runtime.json", template.lstrip("/")]
plan = [(backup / n, runtime.target(Path("/"), "/" + n)) for n in logical if (backup / n).exists()]
assert any(n == backup / "usr/local/bin/ollama" for n, _ in plan)
for source, destination in plan:
    destination.parent.mkdir(parents=True, exist_ok=True)
    runtime.remove(destination)
    runtime.copy(source, destination)
print("BACKUP_RESTORE=PASS")
PY
sudo systemctl daemon-reload
sudo systemctl start ollama
"$LAB_OLLAMA_BIN" --version
curl --fail --silent --show-error "$LAB_OLLAMA_URL/api/version"
```

При несовпадении backup.json восстановление не начинается.
Проверьте версию и снова выполните `40_Q6_runtime.md`.
Для backup с Q6 восстанавливаются его runner, wrapper, template и state.
T5 дополнительно проверяет согласованное восстановление такой копии и verify Q6.
Если backup не содержит Q6, установите Q6 заново.
Файловое восстановление backup в примере не является транзакцией при аппаратном сбое.
Не возобновляйте задачи до проверок файлов и поведения.

## Офлайн-проверки RB-06

На Dell используются только временные каталоги и фиктивные API/GGUF для Q6.
Настоящий Ollama daemon не запускается, веса не загружаются.
CLI для определения версии в интеграционных тестах Q6 является фикстурой.
Хеши реально установленных ELF проверяются отдельно.

```bash
python3 -I "$LAB_BUILD_ROOT/Сборка/tests/ollama/test_ollama_runtime.py" \
  --extract "$LAB_CAPTURE_ROOT" \
  --archive "$LAB_OLLAMA_ARCHIVE" \
  --evidence "$LAB_EVIDENCE_DIR"
```

T1, T3, T4, T5, T6, T7: PASS.
T2: PARTIAL_RECORDED из-за отсутствия целей ссылок в RB-00.
Живые испытания и сокращённый PATH проверяются в RB-10/RB-14.
