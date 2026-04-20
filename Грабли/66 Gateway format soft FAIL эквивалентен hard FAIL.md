---
tags: [грабли, методология, benchmark, quality-gate]
дата: 2026-04-17
этап: Post-R
компонент: Benchmark methodology
статус: Active
---

# 75 Gateway format soft FAIL эквивалентен hard FAIL

## Симптом

Gateway-бенчмарк модели `qwen36-35b-a3b-q4km-fix:latest` прошёл 10 шагов со следующим распределением:

| Шаг | Результат |
|-----|-----------|
| 1 (health) | PASS |
| 2 (smoke) | PASS |
| 3 (3-bullet format) | semantic PASS, format soft FAIL (`*` вместо `-`) |
| 4 (bounded rewrite) | PASS |
| 5 (minimal bug fix) | semantic PASS, output-discipline soft FAIL (fenced block) |
| 6 (minimal refactor) | semantic PASS, output-discipline soft FAIL (fenced block) |
| 7 (3-bullet review) | PASS with caveat |
| 8 (one-word classification) | semantic PASS, strict-format soft FAIL (leading whitespace) |
| 9 (spacing-only fix) | semantic PASS, output-discipline soft FAIL (fenced block) |
| 10 (minified JSON) | PASS |

Итоговая интерпретация на момент gateway-фазы: **"conditionally promising"**, модель допущена к IDE-тесту.

IDE-тест провалился полностью (см. [[74 Open-file context ingestion failure MoE]]): context ingestion failure, thinking stall, weak defect prioritization. Модель reject для IDE path.

## Факт

В ретроспективе видно: **5 из 10 шагов gateway-теста имели soft FAIL на output discipline**. Это 50%. Ярлык "soft" создавал ощущение, что это косметика — на деле каждый такой случай был симптомом того, что модель не контролирует output envelope под инструкцией формата.

Ровно эта черта (неконтролируемый формат) позже проявилась в IDE как:
- лишние артефакты `Javascript` / `Apply` в ответе
- fenced blocks там, где просили raw code
- reasoning leakage в "thinking off" режиме

IDE-провал был не внезапным — он был предсказуем из gateway soft FAIL pattern. Проблема в **калибровке gating**: soft FAIL считался проходимым, потому что "semantic в порядке". Но для IDE-роли формат и есть половина контракта: Continue.dev применяет patches, parses fenced blocks, распознаёт bullet points. Модель, которая "в целом смысл передаёт, но формат пляшет", в IDE становится источником невидимой деградации.

Gateway smoke не должен игнорировать output envelope. Это не косметика, это контрактный атрибут.

## Решение

1. **Пересчёт soft FAIL как full FAIL в gateway benchmark.** Убрать градацию "semantic PASS / format soft FAIL". Формат либо соблюдён, либо нет.
2. **Пороги промоции для IDE-роли:**
   - Gateway: минимум 8 из 10 шагов PASS по hard-критерию (semantic + format)
   - Любой шаг с форматным нарушением — FAIL, не soft
   - Если модель даёт semantic корректно, но не соблюдает формат ≥ 3 шагов — модель не допускается к IDE-тесту и остаётся в экспериментальном статусе
3. **Отдельный протокол output-envelope discipline** для A3B-MoE моделей (см. [[ADR-023 A3B MoE output envelope risk]]): более агрессивные тесты на строгий формат (ровно N bullet points конкретного символа, raw code без fenced block, one-word answer без whitespace).
4. Этот критерий внести в [[ADR-022 Mandatory IDE validation gate]] как pre-condition: без gateway hard-PASS нет допуска к IDE-тесту.

## Урок

Ярлык "soft" в качестве метрики пройдя/не прошёл — это epistemic failure. "Soft" ощущается как "почти прошёл", но фактически означает "не прошёл контракт, который был задан промптом". Если benchmark допускает "soft FAIL — всё равно pass", он перестаёт быть gating и становится театром проверки.

Для IDE-роли это особенно критично: **формат = половина контракта**. Review прошёл с правильным содержанием, но не в 3 bullet points? Pipeline, которая ждёт 3 bullet для парсинга, сломается. Bug fix исправлен, но возвращён в fenced block? Continue.dev Apply не наложит патч. В этих условиях семантика без формата бесполезна.

Правильная формулировка: модель, которая не может стабильно удержать формат в 50% тестов, не имеет права участвовать в pipeline, где формат — часть контракта. Её место — chat-роль с человеком-арбитром, а не IDE с автоматическим applyer.

## Связанные

- [[73 Tool obedience under soft constraint]] — родственный паттерн false positive в capability assessment
- [[74 Open-file context ingestion failure MoE]] — провал, который был предсказуем из soft FAIL pattern
- [[ADR-022 Mandatory IDE validation gate]]
- [[ADR-023 A3B MoE output envelope risk]]
- Отчёт `today_full_report_for_claude_qwen36_qwen35_ide_gateway.md` §4 (gateway-фаза)
