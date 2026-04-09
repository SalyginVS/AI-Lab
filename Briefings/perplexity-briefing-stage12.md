# Perplexity Briefing: Этап 12 — Docker MCP Server

## Контекст для Perplexity

Мы строим custom MCP-сервер (Model Context Protocol) для управления Docker Engine.
Сервер работает на Ubuntu 24.04, Python 3.12+, Docker Engine 28.2.2.
Предыдущий аналогичный сервер (RAG MCP) использовал: mcp 1.27.0 (FastMCP), streamable-http транспорт, systemd deployment.

## Вопросы для исследования

### 1. Docker SDK for Python — текущее состояние (апрель 2026)

- Какая актуальная версия `docker` Python SDK (PyPI package `docker`)?
- Совместим ли текущий SDK с Docker Engine 28.x?
- Есть ли breaking changes в последних версиях?
- Поддерживает ли SDK asyncio (async client) или только sync? Если async — стабилен ли?
- Правильный import: `import docker; client = docker.from_env()` — всё ещё актуален?

### 2. FastMCP / mcp SDK — текущая версия и streamable-http

- Какая актуальная версия PyPI package `mcp` (FastMCP)?
- Есть ли breaking changes между 1.27.0 и текущей?
- streamable-http транспорт — API изменился? Конструкция `mcp.run(transport="streamable-http", host="0.0.0.0", port=8200)` всё ещё корректна?
- Есть ли новые best practices для FastMCP tool definitions (декораторы, type hints)?

### 3. Docker SDK + FastMCP — интеграция

- Можно ли безопасно использовать sync Docker SDK внутри async FastMCP tool handlers?
  (RAG MCP использовал httpx async для gateway calls — здесь Docker SDK sync)
- Нужен ли `asyncio.to_thread()` или `run_in_executor()` для sync Docker calls в async контексте?
- Есть ли примеры Docker MCP серверов на FastMCP в open source?

### 4. Security considerations

- Docker SDK: есть ли built-in timeout для API calls? Как настроить?
- Есть ли рекомендации по ограничению Docker socket access для Python-приложений (не root)?
- docker group membership vs rootless Docker — что рекомендуется для server-side automation?

### 5. systemd + Docker socket

- Docker MCP сервер должен работать как systemd service от пользователя `vladimir` (в группе docker).
- Нужно ли что-то особенное в systemd unit для доступа к /var/run/docker.sock?
- Или `docker.from_env()` подхватит socket автоматически если user в группе docker?

## Формат ответа

Для каждого вопроса:
- Конкретный ответ с версиями и примерами кода
- Если есть gotchas или известные проблемы — указать
- Если информация неуверенная — пометить [U]
