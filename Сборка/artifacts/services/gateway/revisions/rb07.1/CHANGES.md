# RB-07.1: ревизия по решению H-6

Статус: READY_FOR_REVIEW. Применять поверх захваченного gateway 0.12.0 по runbook 50.
Исходники gateway/src не изменяются.

C1: одна обязательная LLM Q6.
C2: подпись Required LLMs вместо Three primary LLMs.
C3: минимальный models_count равен числу REQUIRED_LLM_MODELS плюс embedding; передаётся аргументом Python.
C4: проверка smoke ожидает Q6.
C5: переменная CONTEXT_WINDOW удалена. Литералы проверки контекста gateway сохранены.
C6: все встроенные Python-вызовы используют -I. В исходнике десять вызовов python3 и один venv/bin/python, всего одиннадцать.
C7: комментарий с ревизией, датой и H-6.
PIPELINE_MODEL: изменена только строка модели executor smoke.

Риск: max_tokens=256 может не хватить Q6 с рассуждением для видимого ответа. Проверка на настоящей модели относится к RB-10.

## Номера строк до и после

| Правка | Файл | До | После |
|---|---|---|---|
| C7 | scripts/health-check.sh | 2..1 | 2..2 |
| C5 | scripts/health-check.sh | 8..8 | 9..9 |
| C1 | scripts/health-check.sh | 11..13 | 12..12 |
| C6 | scripts/health-check.sh | 52..52 | 51..51 |
| C6 | scripts/health-check.sh | 152..152 | 151..151 |
| C3, C6 | scripts/health-check.sh | 237..237 | 236..236 |
| C3 | scripts/health-check.sh | 248..248 | 247..247 |
| C6 | scripts/health-check.sh | 271..271 | 270..270 |
| C6 | scripts/health-check.sh | 279..279 | 278..278 |
| C6 | scripts/health-check.sh | 314..314 | 313..313 |
| C6 | scripts/health-check.sh | 350..350 | 349..349 |
| C6 | scripts/health-check.sh | 415..415 | 414..414 |
| C6 | scripts/health-check.sh | 441..441 | 440..440 |
| C4 | scripts/health-check.sh | 462..462 | 461..461 |
| C6 | scripts/health-check.sh | 482..482 | 481..481 |
| C6 | scripts/health-check.sh | 521..521 | 520..520 |
| C2 | scripts/health-check.sh | 590..590 | 589..589 |
| PIPELINE_MODEL | pipelines.yaml | 7..7 | 7..7 |
