# Q6 runtime: wrapper и reasoning repair

Статус: ACCEPTED RB-05, 2026-10-16.
Назначение: восстановить принятый профиль Q6 и alias reasoning effort на чистой площадке.
Порядок: импорт Q6 по `30_Модели.md`, preflight, установка, проверка файлов, поведенческая проверка.
В RB-05 выполнены только офлайн-тесты на Dell. Команды целевой установки ниже в этом этапе не выполнялись.

## Решение и граница воспроизводимости

Основание: A.2 пакета RB-05 и `Решения/ADR-031_Qwen38_Q6_Pi_Complex_Bounded_Executor_Deployment_Contract.md`.
Новый ADR не создаётся. Роль Q6 остаётся Complex Bounded Engineering Executor.
Результаты accepted deployment contract ADR-031 не переоцениваются этим этапом.

`llama-server.wrapper.in` получен из захваченного wrapper заменой ровно двух значений.
`@REAL@` заменяет путь настоящего runner.
`@Q6_ID@` заменяет первые 12 hex-символов digest модели, включая вхождение в имени шаблона.
Подстановка выполняется только через точные строки этих двух маркеров.
Bash-конструкции с `@` сохраняются.

Профиль Q6: `LLAMA_ARG_N_CPU_MOE=43`, `LLAMA_ARG_OVERRIDE_TENSOR=per_layer_token_embd=CPU`,
`LLAMA_ARG_LAZY_MODE=on`, `LLAMA_ARG_LOAD_MODE=mmap`.
Wrapper обнуляет эти четыре переменные для других моделей.
Параметры Ollama context 262144, KV q8_0 и Flash Attention задаёт базовая платформа RB-06.
Этот пакет их не изменяет. Клиентский конфликт reasoning_effort из RB-03 остаётся в RB-08.

Chat template извлекается из метаданных первого GGUF-шарда.
Данные тензоров не читаются и не копируются.
К исходным 8952 байтам добавляются 147 байт `reasoning-alias.prefix` без перевода строки.
Префикс переводит `max` в `xhigh`. Готовый chat template в git не хранится.

| Проверяемый объект | SHA256 |
|---|---|
| Wrapper при исходных REAL и Q6_ID | `a20b9923b872faba2fb56fb0148cd60547a3e7516869cd0a9ad56773802fc1c6` |
| Исходный chat template, 8952 B | `c3cf9e34abf4f9e36c2d72165aa9c132d3e2a725b6c2586aaa3a8af9d7a81041` |
| Готовый chat template, 9099 B | `051e7fd833cbe38640057f6d9870cf59c118d939071fae4c3cf24714c516c3d0` |

Тесты T1 и T2 сравнивают и хеши, и полные байты с RB-02.
Тождество доказано для исходных значений REAL и Q6_ID.
Другой digest меняет только две подстановки wrapper. Сам digest всегда берётся из `/api/tags`.
Для новой версии Ollama тождество wrapper не доказывает совместимость нового runner.
После обновления обязательны проверки поведения из этого runbook и правила ревалидации ADR-031.

## Переменные и зависимости

Нужны Bash, Python 3.11+ со стандартной библиотекой, Ollama и logger из util-linux.
Для выполнения примеров нужны curl и systemd journal.
Для офлайн-проверки shell-скриптов нужен ShellCheck.
Дополнительные Python-пакеты не требуются.

Используйте переменные площадки D-6, заданные при получении модели.
`LAB_Q6_PACKAGE` указывает на абсолютный путь к `Сборка/artifacts/q6`.
`LAB_OLLAMA_BIN` указывает на целевой executable Ollama.
`Q6_GGUF_FIRST` указывает на первый проверенный шард из RB-04.
`LAB_OLLAMA_URL` должен вести на daemon чистой площадки.

```bash
: "${LAB_MODELS_DIR:?Set model directory}"
: "${LAB_EVIDENCE_DIR:?Set evidence directory}"
: "${LAB_OLLAMA_URL:?Set target Ollama URL}"
: "${LAB_Q6_PACKAGE:?Set absolute path to artifacts/q6}"
export LAB_OLLAMA_BIN="${LAB_OLLAMA_BIN:-/usr/local/bin/ollama}"
export Q6_MODEL='qwen3.8-flash-next:125b-a6b-q6_K-ab-262k'
export Q6_GGUF_FIRST="${LAB_MODELS_DIR}/Q6/Qwen3.8-Flash-Next-Q6_K-00001-of-00005.gguf"
export LAB_OLLAMA_URL LAB_Q6_PACKAGE LAB_EVIDENCE_DIR
mkdir -p "${LAB_EVIDENCE_DIR}/Q6-runtime"
```

Пути целевых файлов должны быть абсолютными и не содержать `..`.
Символические ссылки в путях целевых файлов отклоняются.
Layout `/usr/local/lib/ollama` и `/usr/local/share/ollama/templates` сохранён из принятого wrapper.
Перенос layout потребует другого решения архитектора: третья подстановка здесь не добавлена.

## Preflight целевой площадки

Импорт Q6 и проверка всех пяти шардов должны завершиться по `30_Модели.md`.
Выберите окно обслуживания без запросов клиентов.
До установки выгрузите модели через Ollama и убедитесь, что активных runners нет.
Daemon оставьте доступным для чтения `/api/tags` и определения версии.

```bash
curl --fail --silent --show-error "${LAB_OLLAMA_URL}/api/tags"
curl --fail --silent --show-error "${LAB_OLLAMA_URL}/api/ps"
"${LAB_OLLAMA_BIN}" --version
cd "${LAB_Q6_PACKAGE}"
sha256sum --check SHA256SUMS
```

Ожидается наличие Q6 с полным 64-символьным digest и пустой список моделей в `/api/ps`.
Если модель загружена, завершите её использование и выгрузите штатной командой `ollama stop`.
`sha256sum --check` проверяет файлы пакета. Комментарии `# reference` содержат эталоны захвата RB-02.
Любое несовпадение хеша, неопределённая версия или отсутствие Q6 означает STOP.
Распознавание настоящего runner требует executable ELF, то есть бинарного исполняемого файла Linux.
SHA256 дистрибутива Ollama относится к RB-06; этот пакет записывает фактический хеш ELF для последующего контроля.

## Установка

Эта команда предназначена только для будущей целевой площадки.
Она переименовывает ELF, ставит wrapper и создаёт шаблон и запись состояния.
Значения всех переменных передаются явно, поскольку sudo может очищать окружение.

```bash
set -o pipefail
sudo bash "${LAB_Q6_PACKAGE}/install_q6_runtime.sh" \
  --root / \
  --model "${Q6_MODEL}" \
  --gguf-first "${Q6_GGUF_FIRST}" \
  --ollama-bin "${LAB_OLLAMA_BIN}" \
  --ollama-url "${LAB_OLLAMA_URL}" \
  | tee "${LAB_EVIDENCE_DIR}/Q6-runtime/install.log"
```

Ожидается `INSTALL=PASS`, Q6_ID, версия и SHA256 установленных файлов.
Повторный запуск с теми же входами выдаёт `INSTALL=UNCHANGED`.
При повторе сохраняются байты, режимы и времена изменения файлов.

ID нельзя задать вместо чтения API.
Необязательный `--q6-id` является только дополнительным утверждением.
Его несовпадение с первыми 12 символами digest приводит к отказу до записи.

Все проверки пакета, исходного шаблона, версии, ID и существующих целевых файлов выполняются до изменений.
Существующий посторонний wrapper или повреждённый шаблон не перезаписывается.
При наличии принятого wrapper его `.real-*` не переименовывается и не переписывается.
Для захваченного wrapper без записи установщика поддерживается принятие под управление после проверки байтов.

Установленные файлы:

| Путь | Назначение |
|---|---|
| `/usr/local/lib/ollama/llama-server` | Wrapper, режим 0755 |
| `/usr/local/lib/ollama/llama-server.real-<version>` | Сохранённый executable ELF |
| `/usr/local/share/ollama/templates/q6-<ID>-reasoning-compat.jinja` | Chat template, режим 0644 |
| `/var/lib/ai-lab/q6-runtime.json` | Версия, digest, пути и SHA256, режим 0644 |

Запись состояния нужна для verify и отката.
Проверка и откат используют ту же реализацию, что и установщик.
Отдельные shell-entrypoints фиксируют режим через `--action`.

## Проверка файлов после установки

```bash
bash "${LAB_Q6_PACKAGE}/verify_q6_runtime.sh" \
  --root / \
  --model "${Q6_MODEL}" \
  --ollama-bin "${LAB_OLLAMA_BIN}" \
  --ollama-url "${LAB_OLLAMA_URL}" \
  | tee "${LAB_EVIDENCE_DIR}/Q6-runtime/verify.log"
```

Ожидается `VERIFY=PASS` и три SHA256: wrapper, template, настоящий ELF.
Verify только читает файлы и API.
Он проверяет текущий digest модели, имя и версию настоящего runner и `ollama --version`.
Также сверяется сохранённый SHA256 ELF.
Несовпадение любого условия даёт ненулевой код и `Q6_RUNTIME=FAIL`.

## Поведенческая проверка на будущей целевой системе

В RB-05 эти запросы не выполнялись.
Проверку выполняйте после установки файлов и перед возобновлением задач клиентов.
Сначала зафиксируйте время, затем отправьте отдельные запросы max и xhigh.
Пример сохраняет полные ответы для сравнения rendered prompt.

```bash
Q6_CHECK_SINCE="$(date --iso-8601=seconds)"
export Q6_CHECK_SINCE
for effort in max xhigh; do
  body="$(python3 - "${Q6_MODEL}" "${effort}" <<'PY'
import json, sys
print(json.dumps({
    "model": sys.argv[1],
    "messages": [{"role": "user", "content": "Ответь только: OK"}],
    "reasoning_effort": sys.argv[2],
    "stream": False, "keep_alive": "30m",
    "max_tokens": 1, "_debug_render_only": True
}, ensure_ascii=False))
PY
)"
  curl --fail --silent --show-error \
    --header 'Content-Type: application/json' \
    --data "${body}" \
    "${LAB_OLLAMA_URL}/v1/chat/completions" \
    > "${LAB_EVIDENCE_DIR}/Q6-runtime/render-${effort}.json"
done
python3 - "${LAB_EVIDENCE_DIR}/Q6-runtime" <<'PY'
import json, sys
from pathlib import Path
d = Path(sys.argv[1])
renders = []
for effort in ("max", "xhigh"):
    value = json.loads((d / ("render-" + effort + ".json")).read_bytes())
    assert not value.get("error"), value
    rendered = (value.get("_debug_info") or {}).get("rendered_template")
    assert isinstance(rendered, str) and rendered
    renders.append(rendered)
assert renders[0] == renders[1], "max/xhigh prompts differ"
print("MAX_XHIGH_RENDER_IDENTICAL=PASS")
PY
journalctl -t ollama-q6-profile --since "${Q6_CHECK_SINCE}" --no-pager \
  | tee "${LAB_EVIDENCE_DIR}/Q6-runtime/profile.log"
```

Ожидается `MAX_XHIGH_RENDER_IDENTICAL=PASS`.
В журнале должна появиться строка `Q6 profile applied` с текущим ID и `cpu_moe=43 ple=CPU lazy=on load=mmap`.
Отсутствие debug-render поля требует остановки и проверки совместимости runner/API.
Оно не считается подтверждением корректной работы alias.

Затем выполните реальный короткий inference с `reasoning_effort=xhigh`, `stream=false` и `max_tokens=1024`.
Используйте тот же запрос, убрав `_debug_render_only`.
Ожидается HTTP 200 и непустой `choices[0].message.content`.
Сохраните ответ и `/api/ps`.
У загруженной Q6 подтвердите `context_length=262144`.
Для другой модели не должно появляться её ID в строках применения профиля Q6.
Статическая изоляция других моделей отдельно доказана T3.
Эти проверки не заменяют длительные acceptance-тесты RB-10.

## После обновления Ollama

Принятый архивный способ из `20_Ollama.md` заменяет `/usr/local/lib/ollama` целиком.
Он удаляет прежний wrapper и все `.real-*` из рабочего дерева.
Они сохраняются только в резервной копии установщика Ollama.
Откат версии и библиотек выполняйте через `20_Ollama.md`.

Остановите задачи клиентов и выгрузите модели.
Установите проверенный архив по `20_Ollama.md`, подтвердите новую версию CLI и API.
Повторите preflight и установку Q6 с теми же переменными площадки.
Установщик создаст `llama-server.real-<новая версия>` из нового ELF.
Старый runner в рабочем `lib/ollama` не сохраняется.
После установки обязательны verify и поведенческие проверки выше.
До их прохождения задачи Q6 не возобновляйте.
Если обновление затронуло существенные условия ADR-031, применяется его требование ревалидации.

Если `.real-<версия>` уже существует, установка Q6 откажется.
Сначала выясните происхождение обоих ELF. Не удаляйте backup автоматически.
Неизвестный wrapper тоже приводит к отказу.
Пакет Q6 не откатывает саму версию Ollama и её библиотеки.

## Откат

Остановите запросы клиентов и runners.
Для отката API и работающий daemon не требуются.
Используется сохранённое состояние установки.
До восстановления проверяются wrapper, chat template и SHA256 настоящего ELF.

```bash
sudo bash "${LAB_Q6_PACKAGE}/uninstall_q6_runtime.sh" --root / \
  | tee "${LAB_EVIDENCE_DIR}/Q6-runtime/uninstall.log"
```

Ожидается `UNINSTALL=PASS RESTORED_ELF_SHA256=...`.
Исходный ELF возвращается на место wrapper байт в байт.
Шаблон этой установки и запись состояния удаляются.
Каталоги и старые backups других версий не удаляются.
Повторный uninstall завершается отказом: управляемой установки больше нет.

Откат снимает и CPU-MoE/PLE профиль, и reasoning repair.
После него принятая Q6-конфигурация не действует.
Не возобновляйте Q6-задачи как принятый baseline до повторной установки и проверки.
Откат runtime package не является откатом обновления Ollama.

## Офлайн-тесты RB-05

На Dell запускается только этот набор.
Он сам создаёт и удаляет временные каталоги `/tmp/rb05-tests-*`.
Каждый вызов установщика, verify и uninstall передаёт `--root <tmp>`.
Фиктивный `/api/tags` читается из файла через `--tags-file`.
Этот режим запрещён для `--root /`.
GGUF fixture содержит только метаданные, исходный шаблон и нулевое число тензоров.
Сервер, модели, vault и реальная установка Dell не используются.

```bash
python3 -B Сборка/tests/q6/test_q6_runtime.py \
  --extract "${LAB_EVIDENCE_DIR}/RB-02/extract"
bash -n Сборка/artifacts/q6/install_q6_runtime.sh
bash -n Сборка/artifacts/q6/uninstall_q6_runtime.sh
bash -n Сборка/artifacts/q6/verify_q6_runtime.sh
shellcheck Сборка/artifacts/q6/*.sh
```

Ожидается `TESTS=7/7 PASS`, нулевые коды bash и ShellCheck.

| Тест | Проверяемое свойство |
|---|---|
| T1 | Две подстановки воспроизводят 1064 байта живого wrapper |
| T2 | Префикс и исходный шаблон воспроизводят 9099 байт repaired template |
| T3 | Только Q6 получает четыре переменные и аргумент chat-template-file |
| T4 | Переименование ELF, установка и полная идемпотентность |
| T5 | Отказ до записи при неверных хеше, ID, digest и неполном GGUF |
| T6 | Откат возвращает ELF байт в байт |
| T7 | Verify читает состояние и отклоняет порчу файлов, ID и версии |

Дополнительные ветви T4 проверяют захваченный wrapper без metadata, новый ID после импорта и обновление версии.
Отдельные отрицательные случаи T5 проверяют отсутствие модели и повреждение package prefix.
T7 сравнивает snapshot каталога до и после каждой проверки.

## Ограничения

Рабочие каталоги должны принадлежать доверенному оператору.
Установка и откат выполняются последовательно одним оператором, без конкурентной записи в эти пути.
Замена каждого файла атомарна. При обычном исключении восстанавливаются прежние файлы.
Группа замен не является транзакцией против отключения питания или SIGKILL.
Сохранённый ELF не удаляется при установке.
После аварийного прерывания сначала проверьте файлы и backups до повторных действий.

Офлайн-тесты подтверждают воспроизводимость файлов и механизмы управления пакетом.
Они не запускают настоящий runner, GPU или inference.
Реальный ELF в тестах заменён копией /bin/true.
Принятие результата RB-05 и решение о дальнейшей целевой установке выполняет приёмщик.
