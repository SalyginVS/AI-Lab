---
tags: [модель, qwen, исполнитель]
дата: 2026-10-21
статус: Accepted with limitations
---

# Qwen3.8-27B GSQ-RCO IQ3_S + MTP — локальный исполнитель

**Роль:** исполнение технических заданий по готовому DESIGN в Pi; архитектура, выбор требований и независимая приёмка остаются за Claude/ChatGPT и владельцем. Решение — [ADR-032](../Решения/operational/ADR-032_Qwen38_27B_GSQ_RCO_Executor.md).

| Параметр | Подтверждённое значение |
|---|---|
| Источник | [ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF](https://huggingface.co/ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF), ревизия `d562806dbafae37109975e970aae91b43e73b440` |
| Базовая модель | `Qwen/Qwen3.8-27B` |
| Файл | `Qwen3.8-27B-GSQ-RCO-IQ3_S-mtp.gguf`, IQ3_S + GSQ/RCO, MTP head |
| GGUF SHA256 | `58fd826723939933dc86f45b7fe04545cbc2de1c70f6fe2cdd3858c87a98c12f` |
| Ollama | `qwen3.8-27b-gsq-rco:iq3s-mtp-262k` (отдельный тег 128k сохраняется) |
| Modelfile M2 | `RENDERER qwen3.8`, `PARSER qwen3.5`, `PARAMETER num_ctx 262144` |
| Окно контекста | 262144, подтверждено с размещением 100% GPU RTX 3090 (24 GiB) |
| Клиент | Pi на Dell; `pi-q27`, `--thinking medium`, `maxTokens=262144` |
| Мощность | Постоянный лимит RTX 3090 **300 Вт**, одна большая модель одновременно |

## Скорость E0 при 300 Вт

В E0 run5, P03 (медианы трёх замеров):

| Prompt tokens | Prefill, tok/s | Decode, tok/s |
|---:|---:|---:|
| 8192 | 1207.804 | 40.085 |
| 32768 | 1088.368 | 34.596 |
| 100000 | 827.884 | 24.648 |

Эти показатели измерены на конкретном стенде и не гарантируют такую же скорость другого задания.

## Правила работы

Использовать [как ставить задачи](qwen3.8-27b-gsq-rco_как_ставить_задачи.md): DESIGN + правила размещения тестов, пограничные случаи, контролируемая самопроверка. Не принимать по отчёту модели: проверять тесты и дифф независимым оценщиком. Для владельца — [простыми словами](qwen3.8-27b-gsq-rco_простыми_словами.md).

## Evidence

На Dell, вне Git: `~/ailab-rebuild-evidence/Q27-E0-run5/`, `~/ailab-rebuild-evidence/Q27-E1B/`, `~/ailab-rebuild-evidence/Q27-E1C/part1/`, `~/ailab-rebuild-evidence/Q27-E1C/part2/`. Исходный Modelfile с сервера сохранён в `Q27-E3/client/ollama-show-modelfile.txt`. См. [результаты Q27](../Этапы/2026-10-21_Q27/Q27_результаты.md).
