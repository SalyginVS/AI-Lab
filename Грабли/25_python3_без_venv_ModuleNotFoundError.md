---
tags: [грабли, orchestrator, python, venv]
дата: 2026-03-27
этап: "8D"
компонент: orchestrator
статус: решено
---

# Грабли — python3 без venv ModuleNotFoundError openai

## Симптом

```bash
python3 ~/llm-gateway/orchestrator.py --help
# ModuleNotFoundError: No module named 'openai'
```

## Причина

`orchestrator.py` использует `from openai import OpenAI`. Пакет `openai` установлен только в `~/llm-gateway/venv` (тот же venv, что использует `gateway.py` через systemd). В системном Python3 пакета нет.

## Решение

Жёстко использовать интерпретатор из venv:

```bash
~/llm-gateway/venv/bin/python orchestrator.py --help
```

Во всех shell-скриптах:

```bash
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ORCH_PY="$ROOT_DIR/venv/bin/python"
"$ORCH_PY" "$ROOT_DIR/orchestrator.py" ...
```

## Правило

**Никогда не вызывать `python3 orchestrator.py` напрямую.** Всегда через `venv/bin/python`. Зафиксировано в [[ADR-xxx Venv-только для orchestrator]].

## Связано

[[Этап008D]] · [[orchestrator.py]]
