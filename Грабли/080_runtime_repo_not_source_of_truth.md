---
tags: [грабли, process, git, source-of-truth]
дата: 2026-05-08
этап: "[[Этап — Qwen3.6 27B MTP / Continue bounded lane]]"
компонент: "[[AI-Lab Knowledge Base]]"
---

# Runtime repo был ошибочно принят за source of truth

## Симптом

После MTP/Continue integration работа ушла в server-side repo hygiene `/home/vladimir/llm-gateway`: staging, commit, push attempt, hook debugging. Это не соответствовало реальной цели — обновить Obsidian/GitHub документацию AI-Lab.

## Причина

Были смешаны два разных контура:

```text
Documentation/source-of-truth:
  /home/vladimir/llm/AI-Lab
  git@github.com:SalyginVS/AI-Lab.git

Server runtime filesystem:
  /home/vladimir/llm-gateway
```

Server runtime repo начал восприниматься как canonical history, хотя durable knowledge должен жить в Obsidian/GitHub.

## Решение

Server-side Git metadata удалены:

```text
/home/vladimir/llm-gateway/.git
/home/vladimir/git-remotes/llm-gateway.git
/home/vladimir/git-remotes
```

Правило: любые результаты технической работы сначала классифицируются по placement map:

```text
факт → паспорт / архитектура / ADR / грабля / этап / конфиг / не документировать
```

Новые файлы создаются только если нет подходящего существующего слоя.
