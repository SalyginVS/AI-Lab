---
tags: [решение, adr, git-hooks, pre-push, ci-cd, безопасность]
дата: 2026-03-27
этап: "8D"
компонент: pre-push
статус: принято
---

# ADR-xxx — pre-push: STRICT_REVIEW=1 fail-closed в non-TTY окружениях

## Контекст

`pre-push` хук в STRICT-режиме должен запрашивать подтверждение пользователя. Но git hooks вызываются в разных контекстах: интерактивный терминал, SSH-сессия без PTY (pseudo-terminal), CI/CD pipeline (GitHub Actions, GitLab CI). В неинтерактивных контекстах stdin — не TTY.

## Варианты

**A. Всегда спрашивать подтверждение, игнорировать тип stdin**  
Минус: в non-TTY `read` получает EOF немедленно → непредсказуемое поведение (как правило, push проходит). Небезопасно.

**B. Fail-open в non-TTY (push всегда продолжается)**  
Минус: в CI/CD STRICT-режим теряет смысл. Создаёт ложное ощущение безопасности.

**C. Fail-closed в non-TTY (выбрано)**  
Плюс: предсказуемое поведение, явный лог причины. В CI/CD STRICT_REVIEW=1 = блокировка push без исключений. Безопасный дефолт.

## Решение

Вариант **C**. Проверка через `[[ -t 0 ]]` (file descriptor 0 = stdin is TTY):

```bash
if [[ "$STRICT" == "1" ]]; then
    if [[ -t 0 ]]; then
        # TTY: интерактивный вопрос через /dev/tty
        read -r ANSWER < /dev/tty
        [[ "$ANSWER" =~ ^[yY] ]] && exit 0 || exit 1
    else
        # Non-TTY: fail-closed
        echo "STRICT_REVIEW=1 but no TTY — failing closed." >&2
        exit 1
    fi
fi
```

Интерактивный ввод — через `/dev/tty` напрямую, не из stdin (stdin занят git hook protocol).

## Последствия

- Default режим (STRICT не задан): push всегда проходит — не замедляет обычный workflow.
- CI/CD с STRICT_REVIEW=1: push заблокирован без TTY — как и ожидается для строгого контроля.
- SSH без PTY: аналогично CI/CD — fail-closed.
- Документировать в onboarding: `STRICT_REVIEW=1` требует интерактивного терминала.

## Связано

[[Этап008D]] · [[Грабли — pre-push read без TTY проверки]] · [[pre-push]]
