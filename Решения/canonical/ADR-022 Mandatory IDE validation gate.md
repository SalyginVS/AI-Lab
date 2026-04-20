---
tags: [adr, canonical, methodology, benchmark, governance]
дата: 2026-04-17
этап: Post-R
статус: Accepted
компонент: Model promotion methodology
---

# ADR-022: Mandatory IDE validation gate

## Контекст

Методология промоции моделей в active routing до 2026-04-17 строилась на gateway-benchmark как основном quality gate:
- 10 шагов через `/v1/chat/completions` c различными prompt-шаблонами (smoke, format, rewrite, bug fix, review, classification, JSON)
- Если ≥ 7-8 шагов PASS — модель считалась готовой к промоции

Сессия 2026-04-17 с моделью `qwen36-35b-a3b-q4km-fix:latest` показала, что это **неадекватный gate**:

- Модель прошла gateway-тест (10/10 с оговорками "semantic PASS, format soft FAIL")
- Была классифицирована как "conditionally promising" replacement candidate для gemma4:26b
- При IDE-валидации провалилась катастрофически: open-file context failure, thinking stall, weak defect prioritization

Gateway false positive был не исключением, а **системным mismatch между syntactic контрактом теста и semantic контрактом целевой роли**. Gateway проверяет, "умеет ли модель отвечать через API". IDE-роль требует ещё:

- адекватное потребление context provider payloads (currentFile, code, repo-map, diff)
- стабильная output envelope discipline для Continue.dev Apply
- приоритизация correctness > style в review
- предсказуемое поведение thinking mode
- отсутствие format artifacts (`Javascript`, `Apply`, stray fences)

Все эти свойства **не измеряются gateway-тестом**. Модель может быть технически исправной на уровне API и при этом нерабочей в IDE.

Отдельно: session показала, что модель `qwen3.5:35b` — противоположный паттерн. Gateway-тест был слабее (первый-pass review mediocre, soft tool obedience FAIL), но при правильном narrow-prompt контракте в IDE она работает как bounded executor. То есть gateway-сигнал и IDE-ценность могут быть рассогласованы в обе стороны.

## Решение

Введён **обязательный IDE validation gate** для промоции модели в active routing. Gateway-тест больше не является достаточным условием.

**Новый протокол промоции (в порядке):**

**Фаза 1 — Gateway hard-pass (pre-condition для фазы 2):**
- 10 шагов по hard-критерию (semantic + format, без "soft FAIL" градации, см. [[75 Gateway format soft FAIL эквивалентен hard FAIL]])
- Минимум 8 из 10 PASS
- Soft tool obedience шаг обязателен (см. [[73 Tool obedience under soft constraint]])
- Failed → модель остаётся experimental, не допускается к фазе 2

**Фаза 2 — IDE validation (необходимое условие промоции):**
- Сценарии, привязанные к целевой роли:

| Целевая роль | IDE-тесты |
|--------------|-----------|
| First-pass reviewer | Open-file review → 5 defects → приоритизация correctness, попадание в 3+ главных bugs на подготовленном файле |
| Bounded executor | Narrow prompt bug-fix → code-only output → соблюдение запрета на robustness extras |
| Agent | tool_choice: auto + задача, требующая MCP tool → фактический tool call, не симуляция |
| Planner | Multi-step задача в Continue Agent → генерация плана без stall |

- Обязательно на реальном файле, не на synthetic snippet
- Thinking mode on/off проверяется отдельно для моделей с thinking capability

**Фаза 3 — Comparative check (для replacement candidate):**
- A/B с текущей Active моделью той же роли на одинаковом файле, одинаковом промпте
- Замена допустима только если новая модель ≥ existing по delivery + format, при сопоставимом latency

**Только после всех трёх фаз** модель получает статус Active в новой роли. Gateway-only промоция запрещена.

**Исключения:** Embeddings модели, FIM autocomplete модели — они не используются в IDE-контуре в chat-смысле, для них gateway-тест остаётся основным gate.

## Принцип

**Benchmark contract must match deployment contract.** Gateway-тест проверяет API-контракт (ответил ли через `/v1/chat/completions`). Деплой-контракт IDE включает context providers, output format discipline для Apply, приоритизацию defects. Если benchmark не покрывает deployment-специфичные свойства — он даёт false positive.

Этот принцип параллелен ADR-020 (Integration layer defaults must match platform capability) и ADR-019 (retention = role-driven). Все три — про **соответствие измерения фактической функции**.

## Следствия

- **Паспорт v31:** все новые модели проходят IDE gate перед Active-статусом.
- **Архитектура v1.17 §2.1:** добавлен принцип "IDE gate mandatory для IDE-роли".
- **benchmark.py:** расширить или добавить `ide_benchmark.py` (обёртка вокруг Continue.dev CLI / sendChatToModel тестов). Это tech debt.
- **Health-check:** существующие скрипты не покрывают IDE-поведение. Добавить как отдельный `ide-check.sh` — запускается по требованию, не в health loop.
- **Для wave 2 моделей** (qwen3-coder-next, gpt-oss:20b, gemma4:e4b, glm-4.7-flash) — если будут возвращаться к рассмотрению, прогнать через полный новый протокол.

## Tech debt

- Формализация IDE-теста: Continue.dev не даёт API для автоматического tests-runner. Сейчас IDE-тест — ручной. Это ограничение.
- Подготовленные test files с заведомо известными defects и expected reviewer output — нужно собрать отдельный набор (5–7 файлов) как эталон IDE-тестирования.
- Отчёт 2026-04-17 использовал JS-файл с t02, t03, t06, t08 как defect probes — этот файл можно сделать первым в эталонном наборе.

## Связанные

- [[ADR-019 Model retention role-driven]] — governance родитель
- [[ADR-020 Gateway Context Default Policy]] — родственный принцип "measurement matches capability"
- [[ADR-021 Bounded executor role for qwen3.5-35b]] — конкретный случай применения
- [[ADR-023 A3B MoE output envelope risk]] — частный случай риска
- [[73 Tool obedience under soft constraint]]
- [[74 Open-file context ingestion failure MoE]]
- [[75 Gateway format soft FAIL эквивалентен hard FAIL]]
- Отчёт `today_full_report_for_claude_qwen36_qwen35_ide_gateway.md` §12.4
