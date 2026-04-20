---
tags: [грабли, модели, continue-dev, ide-context, moe, a3b]
дата: 2026-04-17
этап: Post-R
компонент: Continue.dev / IDE context providers
статус: Active
---

# 74 Open-file context ingestion failure MoE

## Симптом

Модель `qwen36-35b-a3b-q4km-fix:latest` (MoE, A3B-архитектура) в Continue.dev IDE mode на запрос "review currently open file" ответила:
- не может получить доступ к файлу
- явно запросила содержимое/путь

При этом файл был открыт в редакторе, Continue.dev передавал его содержимое через системный промпт / context provider `currentFile`. Другие модели (`qwen3.5:35b`, `qwen3-coder:30b`) на том же файле с той же конфигурацией Continue видели контент и делали review.

Связанное наблюдение: Nemotron (тоже MoE A3B) демонстрировал похожие format-artifact проблемы и неконтролируемый reasoning leakage. Закономерность между двумя независимыми моделями одной архитектуры — сигнал, а не случайность.

## Факт

Continue.dev передаёт содержимое открытого файла через системный промпт и/или user message с конкретной структурой — обычно блок вида "The currently open file is: `<path>`" плюс fenced code block с содержимым. Модели, обученные с другой структурой context handling, могут:

- не распознавать этот блок как "контент, доступный для анализа"
- интерпретировать его как часть метаданных и игнорировать
- требовать явного указания "вот файл, читай его"

MoE-модели с A3B-архитектурой (active 3B из ~30B total) могут быть особенно чувствительны к формату системного промпта. Активные эксперты выбираются роутером на основе токенов — если формат контекста непривычен, может активироваться "не тот" эксперт, отвечающий за meta-dialog, а не за code-review.

Это **не баг Continue.dev и не баг модели в изолированном смысле** — это mismatch между training distribution модели и конкретным форматом context provider в IDE wrapper. Capability в принципе есть (модель умеет читать код, как показали gateway-тесты), но в этом конкретном конвейере она не срабатывает.

## Решение

1. **Не промоцировать A3B-MoE модели в Active routing без IDE-теста.** Gateway PASS — недостаточное основание. См. [[ADR-022 Mandatory IDE validation gate]].
2. **Для будущих A3B-кандидатов** — перед отказом проверить обходной путь: в Continue.dev rules (например, `03-security.md` или новом `04-context-hint.md` alwaysApply) добавить явный маркер вида:
   ```
   When the user asks about "the open file" or "this file", the file content is provided in the system context above, marked as "currentFile" or in a fenced code block. Read it from there.
   ```
   Если после этого модель начинает видеть файл — проблема была в training distribution, модель usable. Если нет — reject final.
3. **Если модель по-прежнему нужна** в каком-то сценарии, где IDE context provider не используется (например, headless scripts через gateway с явной передачей файла в prompt) — она может оставаться как experimental для этого пути.

## Урок

MoE A3B-архитектура под Ollama имеет паттерн нарушения output envelope и context ingestion. Это зафиксировано на двух независимых моделях (Qwen3.6, Nemotron3-Nano). Гипотеза: **архитектурный риск, а не свойство конкретной модели**. Для следующего A3B-кандидата — начинать с IDE-теста + теста на format discipline, а не с gateway smoke. Это перевёрнутый порядок по сравнению с dense-моделями, но для A3B он экономит время.

Отдельно: если A3B-модель не проходит IDE, это не делает её бесполезной глобально — она может работать в pipeline-режиме через explicit prompt payload. Но в IDE-роль её ставить нельзя.

## Связанные

- [[73 Tool obedience under soft constraint]] — родственный класс false positive
- [[75 Gateway format soft FAIL эквивалентен hard FAIL]] — сопутствующая слабость A3B
- [[ADR-022 Mandatory IDE validation gate]]
- [[ADR-023 A3B MoE output envelope risk]]
- Отчёт `today_full_report_for_claude_qwen36_qwen35_ide_gateway.md` §8.3
