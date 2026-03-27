---
tags: [грабли, инфра]
дата: 2026-03-15
компонент: "[[gateway.py]]"
---

# nano/sed ненадёжен для Python файлов

## Решение
Полная замена через `scp`:
```powershell
scp gateway.py user@192.168.0.128:~/llm-gateway/gateway.py
```

