---
tags: [грабли, orchestrator, yaml, pipelines]
дата: 2026-03-27
этап: "8D"
компонент: orchestrator
статус: решено
---

# Грабли — load_pipelines плоский словарь

## Симптом

```bash
./venv/bin/python orchestrator.py --list
# Available pipelines:
# - pipelines (0 steps)   ← неверно, должны быть smoke, execute-review, ...
```

Pipeline не находился по имени при `--pipeline smoke`.

## Причина

`pipelines.yaml` имеет структуру:

```yaml
pipelines:
  smoke:
    steps: [...]
  execute-review:
    steps: [...]
```

Первая версия `load_pipelines()` читала весь файл как плоский словарь `{"pipelines": {...}}` и возвращала его целиком. При поиске по имени `smoke` ключ не находился — был только ключ `pipelines`.

## Решение

```python
def load_pipelines():
    with PIPELINES_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    # Явно извлекаем вложенный словарь под ключом "pipelines"
    if "pipelines" in data and isinstance(data["pipelines"], dict):
        return data["pipelines"]
    return data  # fallback: плоская схема без обёртки
```

## Правило

При чтении YAML с обёрточным ключом (`pipelines:`, `models:`, `steps:`) — всегда явно проверять и извлекать вложенную структуру. Не полагаться на то, что `yaml.safe_load` вернёт «правильный» уровень.

## Связано

[[Этап008D]] · [[orchestrator.py]] · [[pipelines.yaml]]
