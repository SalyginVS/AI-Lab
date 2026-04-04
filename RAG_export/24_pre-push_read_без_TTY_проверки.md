---
tags: [грабли, git-hooks, bash, tty, pre-push]
дата: 2026-03-27
этап: "8D"
компонент: pre-push
статус: решено
---

# Грабли — pre-push read без TTY проверки

## Симптом

В STRICT_REVIEW=1 режиме хук выводил вопрос `Proceed with push? [y/N]:`, но ответить было невозможно. `read` получал EOF немедленно, поведение — неочевидное (иногда push проходил, иногда нет).

## Причина

Git hook получает данные refs от git через stdin (стандартный ввод). Когда хук вызывал `read -r ANSWER` для интерактивного подтверждения, stdin уже был занят git hook protocol — это не TTY (terminal), а pipe (канал). `read` читал EOF и вёл себя непредсказуемо.

## Решение

Перед интерактивным `read` проверять, является ли stdin TTY:

```bash
if [[ -t 0 ]]; then
    # Stdin — TTY, можно читать с /dev/tty напрямую
    echo "Proceed with push? [y/N]: " >&2
    read -r ANSWER < /dev/tty
    ...
else
    # Non-TTY (CI/CD, SSH без PTY): fail-closed
    echo "STRICT_REVIEW=1 but no interactive TTY — failing closed." >&2
    exit 1
fi
```

Ключевые детали:
- `-t 0` проверяет файловый дескриптор 0 (stdin) на TTY
- Интерактивный ввод читается с `/dev/tty` напрямую, не из stdin
- Fail-closed в non-TTY — намеренно безопасное поведение для CI/CD

## Правило

В git-хуках stdin занят протоколом. Любой интерактивный ввод — только через `/dev/tty` после проверки `-t 0`. При отсутствии TTY — безопасный дефолт (fail-closed для блокирующих хуков).

## Связано

[[Этап008D]] · [[ADR-xxx pre-push STRICT fail-closed non-TTY]]
