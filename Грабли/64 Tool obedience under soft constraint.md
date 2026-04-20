---
tags: [грабли, модели, tool-calling, routing]
дата: 2026-04-17
этап: Post-R
компонент: Routing / Model Capability Assessment
статус: Active
---

# 73 Tool obedience under soft constraint

## Симптом

Модель `qwen3.5:35b` при re-validation function calling после обновления Ollama прошла:
- plain chat
- basic tool call
- full tool loop
- forced `tool_choice` с конкретным именем функции

На шаге 6 тестового протокола (soft constraint): prompt `"Use the tool to calculate 15*17. Then answer in exactly one short sentence."` с тем же `calc` tool в payload — **модель проигнорировала инструкцию "Use the tool" и посчитала сама.** Вернула корректный числовой ответ в одном предложении. Tool call не был сделан.

На шаге 7 (forced mode) с `tool_choice: {"type":"function","function":{"name":"calc"}}` модель корректно вернула `tool_call`. То есть capability есть, **obedience под soft prompt — нет.**

## Факт

**Soft tool support ≠ agent-mode readiness.** В реальном Agent mode через Continue.dev `tool_choice` обычно выставлен в `auto`, а не принудительно. Модель сама решает, вызывать tool или нет. Если модель предпочитает отвечать "из головы" при auto-режиме, в agentic workflow она:

- не воспользуется RAG-поиском, хотя это было инструктировано
- не запустит MCP Git `status`, хотя просили проверить репозиторий
- не выполнит Docker `container_logs`, хотя это нужно для диагностики

Внешне будет выглядеть как корректный ответ, но без фактической верификации через tool. Это опаснее, чем явный отказ — ошибка не видна.

Тест с forced `tool_choice` — необходимое, но **не достаточное** условие для промоции модели в Agent mode. Нужен отдельный тест: soft instruction + `tool_choice: auto` + проверка, что tool_call фактически был сделан.

## Решение

1. В gateway benchmark matrix добавить отдельный шаг **"tool obedience under soft constraint"**: prompt вида "Use X tool to do Y", `tool_choice: auto`, pass = модель вызвала tool, fail = посчитала сама.
2. Routing policy: модели, у которых forced PASS но soft FAIL, **не допускаются в Agent mode**. Их роль — bounded executor или reviewer, где tool calling не ожидается.
3. `qwen3.5:35b` — именно такой случай. Используется как bounded executor (см. [[ADR-021 Bounded executor role for qwen3.5-35b]]), Agent mode остаётся за `qwen3-coder:30b`.

## Урок

Re-validation модели после upstream fix должна проверять не только наличие capability (работает ли tool calling в принципе), но и **дисциплину подчинения** (делает ли модель то, что просят). Это два разных свойства. Без второй проверки модель может получить false positive на "tools восстановлены" и быть промоцирована в роль, где она будет молча не пользоваться инструментами.

## Связанные

- [[73 Tool obedience under soft constraint]] — этот документ
- [[74 Open-file context ingestion failure MoE]] — похожий класс false positive
- [[75 Gateway format soft FAIL эквивалентен hard FAIL]] — родственная методология gating
- [[ADR-021 Bounded executor role for qwen3.5-35b]]
- [[ADR-022 Mandatory IDE validation gate]]
- Отчёт `report_gemma_qwen35_for_claude_2026-04-16.md` §4 Шаг 6
