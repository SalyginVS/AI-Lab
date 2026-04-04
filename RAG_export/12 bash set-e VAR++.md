---
tags: [грабли, инфра, bash]
дата: 2026-03-15
---

# bash set -e: ((VAR++)) при VAR=0 = silent exit

## Причина
`((0++))` возвращает exit code 1. С `set -e` — скрипт тихо умирает.

## Решение
```bash
COUNTER=$((COUNTER + 1))   # безопасно
```

