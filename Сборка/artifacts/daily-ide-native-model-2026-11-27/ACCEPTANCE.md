# VS Code / Pi — bounded functional acceptance

Дата: 27.11.2026 (Europe/Kyiv). Вердикт: PASS в границах короткого IDE workflow и ручного переключения. Оператор лично выполнял задания в VS Code; управляющий диалог проверял файловый результат и реальный backend через Lenovo/SSH. Не performance benchmark и не новый допуск инженерной роли.

## Условия и методика

Изолированный каталог AI-Lab-IDE-Check-20261127. До каждого прогона reset.sh восстанавливает calculator.cjs из намеренно дефектного calculator.original.cjs (a - b). Одинаковые две инструкции: сначала прочитать calculator.cjs и calculator.test.cjs, объяснить оба падения без исправления; затем изменить только calculator.cjs инструментом редактирования, запустить node --test calculator.test.cjs и сообщить результат. Контрольная база неизменна.

| Модель | Анализ и инструментальная работа (отчёт оператора/Pi) | Независимый контроль результата |
|---|---|---|
| Inkling SQ-20 / Strata | PASS: read, diagnosis, edit, tests | Оператор заменён на +, комментарий сохранён; 2 pass / 0 fail |
| Flash-Next UD-Q6_K_XL / Strata | PASS: read, diagnosis, edit, tests; VS Code diagnostics по отчёту модели | Оператор заменён на +, устаревший комментарий удалён; 17:38 EET, 2 pass / 0 fail |
| Qwen 27B IQ3_S / Ollama | PASS: read, diagnosis, edit, tests | Оператор заменён на +, устаревший комментарий удалён; 17:47 EET, 2 pass / 0 fail |

Независимая проверка: diff рабочего файла с original, повторный node --test, SHA256 контрольных файлов. Не независимый повтор агентного прогона. Контрольные SHA256 для всех трёх:
- calculator.original.cjs: 2f656c7a4ac14def3deb876281adac63ef14d6f2863844dc414c0559888b3600
- calculator.test.cjs: 03bdf4b56cb54d32809f9109e37f1ab26cf1a1c599d2047dc2c325023ed9931c

## Native /model

12/12 mock tests PASS, реальный отрицательный TUI тест (другая Pi → отказ и восстановление Inkling) PASS. Положительные переключения через штатную команду /model:

| Переход | Evidence | Результат |
|---|---|---|
| Inkling → Flash | 17:24: сервер loaded=true, preferred flash; 17:26 оператор подтвердил совпадение /lab-status | PASS |
| Flash → Q27 | 17:44 оператор сообщил совпадающие ID Pi/Backend; 17:47 независимая проверка ailab-mode current и preferred q27 | PASS |
| Q27 → Inkling | 18:14 оператор сообщил совпадающие ID Pi/Backend; независимая проверка SSH, actual model, service states, preferred inkling | PASS |

Проверен маршрут переходов и согласованность выбранных ID, а не неизменность PID Pi на протяжении всех испытаний. Внешний task остаётся fallback. При отказе ориентироваться на AI Lab READY и /lab-status, не на промежуточное встроенное сообщение Pi.

Финальный snapshot: Strata active, Inkling SQ-20 loaded=true, Ollama/Gateway/RAG inactive, только loopback :18081, VRAM 21210 MiB used / 2916 MiB free, power.limit=300 W. Клиентский SSH forward готов. Сохранённый профиль inkling. Снимки wrappers/extension совпадают с установленными файлами.

Границы: сложные задачи, нагрузочные показатели, long-context 262144 Inkling/Q27, F07, thermal G0, E01/E02 live и cold boot/postboot не приняты этим испытанием. Ранее принятое Flash long API/agent evidence сохраняется. Boot policy остаётся Ollama. Drain других клиентов обязателен; native адаптер не является глобальным арбитром запросов. Никакие дополнительные inference-тесты, настройки движка или серверные изменения при закрытии не производились.
