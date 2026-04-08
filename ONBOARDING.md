# Lab RTX3090 — Восстановление стека с нуля

**Версия:** 1.0
**Дата:** 2026-04-08
**Паспорт стенда:** v25 (2026-04-07)
**Целевая архитектура:** v1.11

> Этот документ — навигатор по восстановлению лаборатории после полной переустановки или на новом оборудовании. Он ссылается на конкретные секции Паспорта лаборатории (source of truth) и не дублирует его содержимое.

---

## 1. Предпосылки

### Оборудование

GPU с ≥24 ГБ VRAM, ≥62 ГБ RAM, SSD ≥1 ТБ. Точные характеристики: Паспорт, секция 2.

### Программное обеспечение

| Компонент | Где взять | Примечание |
|-----------|----------|-----------|
| Ubuntu Server 22.04 | ubuntu.com/download/server | Headless установка |
| NVIDIA Driver + CUDA | `sudo apt install nvidia-driver-590` или свежий | Паспорт, секция 4 |
| Docker Engine + NVIDIA Toolkit | docs.docker.com/engine/install/ubuntu | Паспорт, секция 4 |
| Ollama | ollama.com/download/linux | Следовать SOP: `~/llm-gateway/docs/SOP_Ollama_Upgrade.md` |
| Python 3.10+ | Предустановлен в Ubuntu 22.04 | — |
| Windows: VS Code | code.visualstudio.com | + расширение Continue.dev |
| Windows: uv/uvx | docs.astral.sh/uv | Для mcp-server-git (STDIO) |

---

## 2. Серверная часть (порядок установки)

Выполнять строго последовательно. После каждого шага — проверка.

### 2.1. Ollama

1. Установить Ollama: `curl -fsSL https://ollama.com/install.sh | sh`
2. Создать override: `/etc/systemd/system/ollama.service.d/override.conf` — параметры из Паспорт, секция 5.1.
3. `sudo systemctl daemon-reload && sudo systemctl restart ollama`
4. Загрузить 15 моделей: `ollama pull <model>` для каждой из Паспорт, секция 5.2.
5. Проверка: `ollama list | wc -l` → 16 строк (15 моделей + header).

### 2.2. Gateway

1. Клонировать / скопировать `~/llm-gateway/` (gateway/ пакет, run.py, orchestrator.py, pipelines.yaml, scripts/, .githooks/, docs/).
2. `cd ~/llm-gateway && python3 -m venv venv && source venv/bin/activate && pip install fastapi uvicorn httpx openai pydantic`
3. Создать `~/llm-gateway/.env` — формат из Паспорт, секция 6.2. Три пользователя: vladimir, roadwarrior, orchestrator. `chmod 600 .env`.
4. Установить systemd unit: `/etc/systemd/system/llm-gateway.service` с `EnvironmentFile=/home/vladimir/llm-gateway/.env`. Паспорт, секция 12.
5. `sudo systemctl daemon-reload && sudo systemctl enable --now llm-gateway`
6. Проверка: `curl -s http://localhost:8000/health | jq .` — gateway ok, version 0.12.0.

### 2.3. RAG MCP Server

1. Клонировать / скопировать `~/rag-mcp-server/` (server.py, gateway_embeddings.py, chunker.py, indexer.py).
2. `cd ~/rag-mcp-server && python3 -m venv venv && source venv/bin/activate && pip install "mcp[cli]" chromadb httpx`
3. Скопировать документы для индексации в `~/rag-mcp-server/docs/` (минимум: gateway code, scripts, .md документация).
4. Запустить индексацию: `source venv/bin/activate && python indexer.py`
5. Проверка: `cat index_status.json | jq '.chunks_indexed'` → >0.
6. Установить systemd unit: `/etc/systemd/system/rag-mcp.service` с `EnvironmentFile=/home/vladimir/llm-gateway/.env`. Паспорт, секция 12.
7. `sudo systemctl daemon-reload && sudo systemctl enable --now rag-mcp`
8. Проверка: `curl -s http://localhost:8100/mcp` → ответ сервера.

### 2.4. UFW

1. Настроить правила: Паспорт, секция 3 (8 правил: SSH, gateway, Ollama, RAG × LAN+WG).
2. `sudo ufw enable`
3. Проверка: `sudo ufw status numbered` — 8 правил.

### 2.5. Cron + Health-Check

1. Проверить: `~/llm-gateway/scripts/health-check.sh` существует и `chmod +x`.
2. Настроить sudoers: `/etc/sudoers.d/health-check` для UFW-команды без пароля.
3. Добавить cron: `crontab -e` → `0 3 * * * bash ~/llm-gateway/scripts/health-check.sh >> ~/llm-gateway/logs/nightly-health.log 2>&1`
4. `mkdir -p ~/llm-gateway/logs`
5. Проверка: `bash ~/llm-gateway/scripts/health-check.sh` → 11/11 passed.

### 2.6. Git hooks

1. `cd ~/llm-gateway && git config core.hooksPath .githooks`
2. `chmod +x .githooks/pre-push`
3. Проверка: `git -C ~/llm-gateway config core.hooksPath` → `.githooks`.

---

## 3. Клиентская часть (Windows)

### 3.1. Continue.dev

1. Установить расширение Continue из VS Code Marketplace.
2. Разместить `config.yaml` в `%USERPROFILE%\.continue\config.yaml` — 10 моделей, 12 context providers, 6 prompts. Паспорт, секция 7.
3. Заменить `apiKey: sk-lab-EXAMPLE` на реальный токен пользователя vladimir (из `.env` на сервере).
4. Разместить rules: `%USERPROFILE%\.continue\rules\` — `01-general.md`, `02-coding.md`, `03-security.md`.
5. Разместить mcpServers: `%USERPROFILE%\.continue\mcpServers\` — `git.yaml`, `rag.yaml`.
6. `Developer: Reload Window` в VS Code.
7. Проверка: в Chat mode выбрать модель, отправить тестовое сообщение.

### 3.2. Copilot BYOK

Настроить `settings.json`: `ollamaEndpoint` → `http://192.168.0.128:8000/v1`. Паспорт, секция 7.5. Статус: plain chat only (Agent mode нестабилен, не развивать).

### 3.3. Obsidian vault

Клонировать или скопировать vault лаборатории. Структура папок: Грабли/, Компоненты/, Конфиги/, Модели/, Решения/, Этапы/, Briefings/, Meta/.

---

## 4. Верификация

### 4.1. Серверная проверка

```bash
bash ~/llm-gateway/scripts/setup-check.sh
```

Ожидание: все проверки PASS. Если FAIL — см. описание конкретной проверки.

### 4.2. Клиентская проверка

```powershell
powershell -ExecutionPolicy Bypass -File "%USERPROFILE%\.continue\scripts\setup-check.ps1"
```

### 4.3. Smoke-тесты

```bash
# Orchestrator CLI
cd ~/llm-gateway
./venv/bin/python orchestrator.py --pipeline smoke --task "Hello onboarding" --stdout

# Gateway orchestrate API
TOKEN=$(python3 -c "import json,os; print(list(json.loads(os.environ['LLM_GATEWAY_TOKENS']).keys())[0])")
curl -sf -X POST http://localhost:8000/v1/orchestrate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"pipeline":"smoke","task":"Hello onboarding"}' | jq '.steps[0].output[:100]'
```

---

## 5. Известные грабли (Top-5 критичных)

| # | Грабли | Суть | Решение |
|---|--------|------|---------|
| #33 | Override.conf backup | Ollama upgrade перезаписывает override.conf | Бэкап ПЕРЕД каждым upgrade |
| #42 | UFW was inactive | UFW может быть выключен по умолчанию | Проверять `sudo ufw status` после установки |
| #48 | RAG MCP auth regression | Смена auth policy ломает server-to-server вызовы | EnvironmentFile + проверка после любых auth-изменений |
| #49 | Shell .env JSON quoting | JSON-значения в .env нужны в single quotes | Проверить: `systemctl show llm-gateway -p Environment` |
| #32 | File deployment mismatch | scp отдельных файлов может промахнуться | Проверять каждый файл после деплоя перед restart |

Полный список: Obsidian vault → Грабли/.

---

## 6. Ссылки

| Документ | Расположение |
|----------|-------------|
| Паспорт лаборатории | `Паспорт_лаборатории_v25.md` (Obsidian vault) |
| Целевая архитектура | `Целевая_архитектура_AI_Coding_Platform_v1.11.md` |
| SOP Ollama Upgrade | `~/llm-gateway/docs/SOP_Ollama_Upgrade.md` |
| ADR (архитектурные решения) | Obsidian vault → Решения/ + RAG MCP index |
