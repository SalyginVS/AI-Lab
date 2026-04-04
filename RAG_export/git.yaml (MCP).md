---
tags: [конфиг, mcp]
дата: 2026-03-20
---

# MCP Git Server — конфигурация

Файл: `%USERPROFILE%\.continue\mcpServers\git.yaml`

```yaml
name: Git MCP Server
version: 0.0.1
schema: v1

mcpServers:
  - name: git
    type: stdio
    command: uvx
    args:
      - "mcp-server-git"
```

Без `--repository` — работает с любым репозиторием, путь через `repo_path` в каждом tool call.
