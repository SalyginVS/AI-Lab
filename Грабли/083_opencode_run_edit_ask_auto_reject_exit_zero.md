---
tags: [грабли, opencode, permissions, terminal-agent]
дата: 2026-05-15
компонент: OpenCode
этап: "[[Этап — OpenCode controlled terminal-agent lane]]"
---

# OpenCode `edit=ask` в `opencode run` auto-reject и exit code 0

## Симптом

В scripted `opencode run` при permission profile:

```json
{
  "edit": "ask",
  "bash": "deny",
  "task": "deny",
  "webfetch": "deny",
  "websearch": "deny"
}
```

OpenCode не открыл интерактивный approval prompt для пользователя. Вместо этого он автоматически отклонил edit:

```text
permission requested: edit (.../permission_probe.txt); auto-rejecting
Edit permission_probe.txt failed
Error: The user rejected permission to use this specific tool call.
```

При этом процесс завершился с:

```text
OPENCODE_RUN_EXIT_CODE=0
```

Файл остался неизменным:

```text
EDIT_ASK_RESULT=FILE_UNCHANGED_APPROVAL_NOT_COMPLETED_OR_DENIED
```

## Причина

Рабочее объяснение:

```text
opencode run в текущем scripted/non-interactive контуре не обеспечивает нормальный интерактивный approval-dialog для `edit=ask`.
```

Возможный дополнительный фактор:

```text
stdout/stderr pipeline через sed/timeout может усиливать non-interactive behavior.
```

Но operational conclusion не зависит от причины: `edit=ask` в текущем `opencode run` не является рабочим bounded-edit режимом.

## Почему это опасно

`exit code 0` может создать ложное ощущение успешного выполнения.

Неправильная проверка:

```bash
opencode run ...
echo $?
# 0
```

не доказывает, что edit был выполнен.

## Правильная проверка

После каждого scripted OpenCode run нужно проверять минимум одно из:

```bash
git diff -- <file>
cat <file>
sha256sum <file>
grep -qx '<expected content>' <file>
```

Для repo-workflow обязательно:

```bash
git status --short
git diff --check
git diff -- <expected files>
```

## Решение

Для scripted `opencode run` использовать два режима.

### Read-only

```json
{
  "edit": "deny",
  "bash": "deny",
  "task": "deny",
  "webfetch": "deny",
  "websearch": "deny",
  "external_directory": "deny"
}
```

### Bounded edit

```json
{
  "edit": "allow",
  "bash": "deny",
  "task": "deny",
  "webfetch": "deny",
  "websearch": "deny",
  "external_directory": "deny"
}
```

`edit=ask` оставить для отдельной проверки в true interactive TUI mode.

## Дополнительная грабля: self-report tools ненадёжен

Модель несколько раз неверно описывала доступные tools. Например, в одном ответе она утверждала, что `Bash` доступен, хотя tool-level probe показал:

```text
Invalid Tool
Model tried to call unavailable tool 'bash'.
Available tools: edit, glob, grep, invalid, read, todowrite, write.
```

Правило:

```text
Не считать self-report модели о tools источником истины.
```

Источники истины:

- `Invalid Tool`;
- actual tool call output;
- filesystem state;
- `git diff`;
- gateway logs;
- metrics;
- post-run process check.

## Operational rule

Перед сменой профиля или сценария:

```bash
pgrep -af 'opencode' || echo "NO_OPENCODE_PROCESS_FOUND"
pkill -u "$USER" -f '/.opencode/.*/opencode' 2>/dev/null || true
pgrep -af 'opencode' || echo "NO_OPENCODE_PROCESS_FOUND"
```

Не давать агенту противоречивые задачи:

```text
Wrong:
"Modify file" + edit=deny

Correct:
Read-only task + edit=deny
Bounded edit task + edit=allow + bash/task/web/external_directory=deny
```

## Статус

```text
GOTCHA_STATUS=confirmed
MITIGATION=use readonly/edit wrappers and post-state verification
```
