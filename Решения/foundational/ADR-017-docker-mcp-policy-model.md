# ADR-017: Docker MCP Policy Model

**Статус:** Proposed  
**Дата:** 2026-04-09  
**Этап:** 12 (MCP: Docker)  
**Слой:** L1 — Canonical  
**Компонент:** MCP Tool Layer (Слой 3), Security/Governance (Слой 6)

---

## Контекст

Этап 12 подключает Docker Engine на сервере как MCP tool для Continue Agent mode. Docker — инструмент с высоким blast radius: неограниченный доступ к Docker API позволяет удалить контейнеры, образы, volumes, выполнять произвольные команды внутри контейнеров, запускать привилегированные контейнеры.

Существующие MCP-серверы (git, RAG) не имели потребности в server-side policy enforcement: git работает с локальными репозиториями на Windows, RAG — read-only поиск. Docker MCP — первый MCP-сервер, требующий явной серверной политики ограничений.

Зависимость: Этап 14 (security boundary) завершён — UFW, mandatory auth, audit trail на месте.

## Решение

Реализовать **server-side policy enforcement** в Docker MCP server. MCP-сервер на уровне кода проверяет каждую операцию по YAML-файлу политики (`docker-policy.yaml`) **до** выполнения Docker API call. Клиент (Continue Agent) не является единственным барьером безопасности.

### Три слоя защиты (Defense in Depth)

| Слой | Где | Что контролирует |
|------|-----|-----------------|
| 1. Continue Agent approval | Клиент (Windows) | Показ tool call пользователю, ожидание подтверждения |
| 2. MCP Server policy | Сервер (Ubuntu) | Проверка операции по docker-policy.yaml: категория, allowlist, denylist, limits |
| 3. 03-security.md rule | Клиент (Continue) | Глобальные ограничения Agent mode (denylist путей, запрет токенов) |

### Категории инструментов

| Категория | Tools | Политика по умолчанию |
|-----------|-------|-----------------------|
| READ | list_containers, list_images, container_logs, container_inspect, container_stats, system_info | Всегда разрешены |
| LIFECYCLE | start_container, stop_container, restart_container | Разрешены, audit log обязателен |
| EXEC | exec_command | Command allowlist + denylist в policy, audit log обязателен |

### Явно исключённые операции (v1)

`docker run`, `docker build`, `docker rm`, `docker rmi`, `docker pull`, `docker push`, `docker volume rm`, `docker network rm` — не реализуются в первой версии. Добавление каждой операции требует отдельного решения с обоснованием.

### Технические решения

| Аспект | Решение | Обоснование |
|--------|---------|-------------|
| Docker API | Python `docker` SDK (не subprocess) | Типизированные объекты, proper error handling, enterprise-переносимый |
| Транспорт | streamable-http, порт 8200 | ADR-014, паттерн RAG MCP |
| Auth | Bearer token через EnvironmentFile (.env) | ADR-015, паттерн RAG MCP |
| Policy file | YAML, загрузка при старте сервера | Декларативная конфигурация, изменение без перекомпиляции |
| Logging | structured JSON, `logging.getLogger("uvicorn.error")` | Паттерн gateway + RAG MCP |
| Audit | Все LIFECYCLE и EXEC операции → отдельное поле `audit: true` в log event | Трассируемость для enterprise |
| systemd | docker-mcp.service, After=docker.service | Зависимость от Docker Engine |
| UFW | 8200/tcp — LAN + WireGuard | Паттерн gateway (8000) + RAG (8100) |

## Альтернативы отклонены

1. **Использование docker/mcp-server (official Docker MCP)** — не обеспечивает server-side policy enforcement, предоставляет полный неограниченный доступ к Docker API. Неприемлемо для enterprise-паттерна.

2. **STDIO транспорт (Docker CLI на Windows, DOCKER_HOST=ssh://...)** — работает, но: требует Docker CLI на клиенте, SSH tunnel setup, нет server-side policy. Отклонено по security и архитектурным соображениям.

3. **Без policy file (hardcoded ограничения)** — менее гибко, изменение политики требует правки кода и редеплоя. Отклонено.

## Последствия

- Docker MCP server содержит policy engine, загружающий `docker-policy.yaml` при старте.
- Каждый tool call проверяется по policy **до** вызова Docker API.
- Операция, не разрешённая policy, возвращает structured error с указанием причины отказа.
- Расширение набора tools (docker run, docker build) требует явного решения и обновления policy.
- При добавлении ADR-017 в RAG — reindex (canonical layer).
- `.env` shared между 3 сервисами: llm-gateway, rag-mcp, docker-mcp.

## Enterprise-переносимость

Паттерн «MCP server с server-side policy» тиражируется на любые опасные инструменты: Kubernetes API, cloud CLI, database admin. Policy file отделяет «что разрешено» от кода сервера — для enterprise достаточно заменить docker-policy.yaml на корпоративный вариант.
