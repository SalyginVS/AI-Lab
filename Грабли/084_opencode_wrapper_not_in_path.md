---
tags: [грабли, opencode, wrapper, path, process]
дата: 2026-05-15
этап: "[[Этап — OpenCode controlled terminal-agent lane]]"
компонент: "[[OpenCode]]"
---

# OpenCode wrapper не найден из-за PATH

## Симптом

При запуске repo-write smoke команда завершилась без запуска OpenCode:

```text
timeout: failed to run command ‘oc-ailab-edit’: No such file or directory
OPENCODE_RUN_EXIT_CODE=127
```

Файл не изменился, `opencode` процессов не осталось.

## Причина

User-local wrapper существовал и был executable:

```text
/home/vladimir/.local/bin/oc-ailab-edit
```

Но shell не находил короткое имя `oc-ailab-edit`, потому что `~/.local/bin` не был доступен в текущем `PATH` / execution context.

## Решение

Для критичных scripted validation steps использовать абсолютный путь:

```bash
/home/vladimir/.local/bin/oc-ailab-edit <dir> "<prompt>"
```

Либо явно проверить PATH перед использованием короткого имени:

```bash
command -v oc-ailab-edit
echo "$PATH" | tr ':' '\n' | grep -Fx "$HOME/.local/bin"
```

## Operational rule

Перед OpenCode run проверять wrapper как отдельный preflight:

```bash
WRAPPER="$HOME/.local/bin/oc-ailab-edit"
ls -l "$WRAPPER"
test -x "$WRAPPER"
```

Код `127` трактовать как **NOT_EXECUTED / INCONCLUSIVE**, а не как model/tool failure.

## Связанные документы

- [[ADR-029_OpenCode_Controlled_Terminal_Agent_Lane]]
- [[Конфиги/opencode_ailab_wrappers]]
