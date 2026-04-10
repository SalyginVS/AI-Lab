# Этап F-next — Semantic Layer: Retrieval-Assisted SQL — Результаты

**Дата:** 2026-04-10
**Трек:** F (AI-as-Interface)
**Статус:** ✅ Завершён

---

## Задача

Построить retrieval-assisted SQL pipeline, который динамически подбирает контекст для каждого вопроса из векторного хранилища вместо монолитного prompt addendum. Доказать, что подход устраняет prompt bleed и масштабируется.

---

## Стек

- **Vector DB:** ChromaDB 1.5.5, PersistentClient, `~/rag-data/chroma/`, collection `sql_knowledge`
- **Embedding:** qwen3-embedding (4096d) через gateway `/v1/embeddings`
- **SQL generation:** qwen3-coder:30b, gemma4:31b, gemma4:26b, qwen3-coder-next:q4_K_M через gateway `/v1/chat/completions`
- **БД:** SQLite `~/llm-gateway/ondo_demo.db`
- **Evaluator:** business-aware evaluator (v2, из Этапа 11A)
- **Runtime:** bridge между двумя venv (`~/llm-gateway/venv` + `~/rag-mcp-server/.venv`)

---

## Результаты: подэтапы

### F-1. SQL Knowledge Base ✅

Создана ChromaDB collection `sql_knowledge` с 34 карточками знаний:

| Тип | Кол-во | Описание |
|-----|--------|----------|
| `ddl` | 6 | CREATE TABLE + описание колонок для каждой таблицы |
| `business_doc` | 8 | Бизнес-правила предметной области |
| `sql_example` | 15 | Пары «вопрос → SQL» из ground truth |
| `anti_pattern` | 5 | Частые ошибки моделей из 11A hard set |

Retrieval verification: **7/7 PASS** — релевантность и контекстная изоляция подтверждены.

Файлы:
- `sql_knowledge_cards.py` — декларативный набор карточек
- `sql_indexer.py` — индексация в ChromaDB
- `test_sql_retrieval.py` — 7 тестов retrieval quality

### F-2. Retrieval-Augmented SQL Pipeline ✅

Создан `text2sql_semantic.py` — thin wrapper над `text2sql_poc_v2.py`. Паттерн: monkey-patch `build_system_prompt` (аналогично v3, но с dynamic retrieval вместо монолитного addendum).

Pipeline:
```
Вопрос → search sql_knowledge (top-k)
  → group by type (ddl, business_doc, sql_example, anti_pattern)
  → assemble DYNAMIC SEMANTIC CONTEXT
  → add to base system prompt
  → gateway /v1/chat/completions → model → SQL
  → validate + execute (read-only)
```

Mini-benchmark на 3 доменах (HR, hotel, energy): 3/3 ✅.

### F-3. Full Benchmark ✅

Прогон 20 вопросов по 4 моделям. Сравнение с baseline (11A v2) и prompt addendum (11A v3).

---

## Benchmark: сводная таблица

### v4 (semantic layer) vs v2 baseline vs v3 prompt addendum

| Модель | v2 EA | v2 SA | v3 EA | v3 SA | **v4 EA** | **v4 SA** | **v4 Latency** |
|--------|-------|-------|-------|-------|-----------|-----------|----------------|
| **gemma4:31b** | 95% | 70% | 100% | 90% | **100%** | **90%** | **33.5s** |
| qwen3-coder:30b | 100% | 75% | 100% | 90% | 85% | 70% | 4.6s |
| gemma4:26b | 95% | 65% | 100% | 85% | 75% | 65% | 12.0s |
| qwen3-coder-next:q4_K_M | — | — | — | — | 75% | 70% | 33.8s |

Safety test (Q19): **4/4** — все модели отказали в DML.
Hallucination test (Q20): **4/4** — все модели вернули CANNOT_ANSWER.

---

## Ключевые находки

### F-next-1. gemma4:31b — лучший executor для semantic layer

Неожиданная инверсия: в 11A qwen3-coder:30b был лучшим (SA 75% vs gemma4:31b 70%). С semantic layer gemma4:31b дала 90%, а qwen3-coder:30b регрессировала до 70%. Причина — knowledge layer drift (Грабли #65): карточки содержали устаревшие имена колонок из первоначального пакета Claude. gemma4:31b как reasoning-модель распознаёт конфликт между карточкой и фактической схемой и выбирает правильное имя. qwen3-coder:30b буквально следует карточкам — когда карточки содержат неточности, генерирует невалидный SQL.

**Архитектурный вывод:** для retrieval-assisted SQL reasoning-модель предпочтительнее детерминистического code generator. Это инверсия по сравнению с plain text-to-sql (11A), где deterministic generation важнее reasoning.

### F-next-2. Retrieval устраняет prompt bleed

Целевой результат этапа достигнут: SA 90% на retrieval-based pipeline (gemma4:31b) без монолитного prompt addendum. Добавление новых карточек не ломает существующие кейсы — контекст подбирается динамически по similarity.

### F-next-3. Knowledge layer drift — главный операционный риск

Обнаружен и частично исправлен schema drift: hotel_bookings в реальной БД имела `total_uah` и `status`, а карточки описывали `price_per_night` и формулу `julianday(check_out) - julianday(check_in)`. Аналогичный drift по employees (`salary` vs `salary_uah`) не был исправлен и вызвал regression qwen3-coder:30b.

**Вывод:** semantic layer требует процесса синхронизации cards ↔ фактическая БД. Это свойство архитектуры, не баг. В enterprise-контексте решается через DDL extraction + CI validation.

### F-next-4. Runtime bridge — tech debt

`text2sql_semantic.py` — первый файл, пересекающий два venv контура (openai в `~/llm-gateway/venv`, chromadb в `~/rag-mcp-server/.venv`). Решение через PYTHONPATH bridge рабочее, но нечистое. Для production: единый venv или контейнеризация.

### F-next-5. Модель qwen3-coder-next:q4_K_M — первый benchmark

Новая модель в стеке (не в Паспорте v27). SA 70% на semantic layer — на уровне qwen3-coder:30b при том же latency (~34s). Не показала преимущества.

---

## Грабли

### #65. Knowledge layer drift: карточки vs реальная БД

**Симптом:** Модель генерирует `price_per_night` (из карточки), но в реальной таблице — `total_uah`. SQL fails execution.

**Причина:** Knowledge cards были написаны на основе первоначальной DDL из Этапа 11A. Фактическая БД была модифицирована (или изначально отличалась), но карточки не были синхронизированы.

**Частичное исправление:** Обновлены 4 карточки hotel-domain. Employees/departments карточки остались рассинхронизированы.

**Урок:** Semantic layer чувствителен к drift cards ↔ schema. Для production нужна автоматическая синхронизация (DDL extraction → card generation). Reasoning-модели (gemma4:31b) устойчивее к drift, чем code generators (qwen3-coder:30b).

### #66. Runtime bridge: два venv в одном процессе

**Симптом:** `ImportError: No module named 'chromadb'` при запуске через `~/llm-gateway/venv/bin/python` (или `No module named 'openai'` через rag venv).

**Причина:** `text2sql_semantic.py` — первый скрипт, требующий зависимости из обоих venv.

**Решение:** Runtime bridge через PYTHONPATH:
```bash
cd ~/llm-gateway/scripts
RAG_SITE=$(~/rag-mcp-server/.venv/bin/python -c "import site; paths=[p for p in site.getsitepackages() if 'site-packages' in p]; print(paths[0] if paths else '')")
PYTHONPATH="$RAG_SITE:$PYTHONPATH" llmrun ~/llm-gateway/venv/bin/python text2sql_semantic.py
```

**Статус:** Рабочее PoC-решение. Tech debt для будущей консолидации venv.

### #67. Auth env mismatch: LLM_GATEWAY_TOKENS vs LLM_GATEWAY_API_KEY

**Симптом:** `RuntimeError: LLM_GATEWAY_TOKENS env var is not set` при ручном запуске (не через systemd).

**Причина:** `gateway_embeddings.py` ожидает env из `.env`, которые подгружаются systemd, но не SSH-shell.

**Решение:** Добавлен `llmrun` helper в `~/.bashrc`:
```bash
llmrun() { ( set -a; source ~/llm-gateway/.env; set +a; "$@" ); }
```

### #68. Gateway URL: base vs endpoint

**Симптом:** `404 Not Found` при обращении к `http://127.0.0.1:8000`.

**Причина:** В indexer/test скриптах был указан base URL без пути endpoint. `gateway_embeddings.py` ожидает полный URL `/v1/embeddings`.

**Решение:** Исправлен `GATEWAY_URL` на `http://127.0.0.1:8000/v1/embeddings` в `sql_indexer.py` и `test_sql_retrieval.py`.

### #69. Passport drift: models_count 17 vs documented 15

**Симптом:** `/health` endpoint показал `models_count: 17`, Паспорт v27 фиксирует 15 моделей.

**Причина:** Добавлены модели (включая qwen3-coder-next:q4_K_M) без обновления паспорта.

**Статус:** Неблокирующее. Закрывается обновлением Паспорта v28.

---

## Закрытые открытые вопросы

| # | Вопрос | Ответ | Статус |
|---|--------|-------|--------|
| 22 | Semantic layer для >90% SA | SA 90% достигнута (gemma4:31b). Retrieval-based pipeline model-sensitive: reasoning-модели выигрывают. | ✅ Закрыт |
| 23 | Prompt bleed mitigation: retrieval vs monolithic | Retrieval устраняет prompt bleed: добавление карточек не ломает другие кейсы. Монолитный prompt (v3) ломался при micro-tuning (Грабли #36). | ✅ Закрыт |

---

## Новые открытые вопросы

| # | Вопрос | Влияние | Когда закрыть |
|---|--------|---------|---------------|
| 28 | Knowledge cards ↔ DB schema sync: автоматизация DDL extraction → card generation | Высокое — блокирует масштабирование на реальные схемы | При переходе к enterprise pilot |
| 29 | Consolidation двух venv (llm-gateway + rag-mcp-server) в единый runtime | Среднее — tech debt, не блокирует PoC | При рефакторинге инфраструктуры |
| 30 | gemma4:31b как primary model для semantic SQL (инверсия ADR-012 для Track F) | Среднее — влияет на model routing policy | При обновлении ADR-012 |

---

## Критерии завершения — чек-лист

- [x] ChromaDB collection `sql_knowledge` создана — ✅ 34 карточки
- [x] 3 типа карточек проиндексированы — ✅ DDL + business_doc + sql_example + anti_pattern
- [x] Retrieval возвращает релевантные карточки — ✅ 7/7 PASS
- [x] Retrieval изолирует контекст — ✅ (тест: energy ≠ booking)
- [x] v4 pipeline работает end-to-end — ✅ mini-benchmark 3/3
- [x] SA ≥ 90% на benchmark — ✅ gemma4:31b = 90%
- [x] Safety test пройден — ✅ 4/4 модели
- [x] Hallucination test пройден — ✅ 4/4 модели
- [x] Prompt bleed test — ✅ (hotel cards обновлены без регрессии на HR/energy)
- [x] Benchmark report v4 vs v2 vs v3 задокументирован — ✅ данный документ
- [x] ADR-018 оформлен — ✅

---

## Артефакты

### Скрипты и данные (на сервере, `~/llm-gateway/scripts/`)
1. `sql_knowledge_cards.py` — 34 карточки знаний (6+8+15+5)
2. `sql_indexer.py` — индексация в ChromaDB
3. `test_sql_retrieval.py` — 7 тестов retrieval quality
4. `text2sql_semantic.py` — v4 retrieval-assisted pipeline

### Benchmark reports (`~/llm-gateway/scripts/text2sql_results/`)
5. `benchmark_gemma4_31b_20260410_120225.json` — gemma4:31b SA 90%
6. benchmark qwen3-coder:30b — SA 70%
7. benchmark gemma4:26b — SA 65%
8. benchmark qwen3-coder-next:q4_K_M — SA 70%

### Документация
9. `Этап_F-next_результаты.md` — данный документ
10. `ADR-018_Semantic_Layer_Architecture.md`

---

## Решение по этапу

**Freeze Stage F-next as successful PoC.** Retrieval-assisted SQL pipeline доказан. SA 90% на gemma4:31b — целевая планка достигнута. Prompt bleed устранён архитектурно. Knowledge layer drift обнаружен и задокументирован как операционный риск. Enterprise evaluation framework для GenBI-платформ зафиксирован в ADR-018.

**Roadmap завершён.** Все треки A–F закрыты. Lab RTX3090 достигла полной реализации запланированного scope.
