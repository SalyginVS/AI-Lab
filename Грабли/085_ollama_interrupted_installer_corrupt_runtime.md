# Грабли #085: Ollama interrupted installer corrupts runtime

## Симптом

После попытки обновления Ollama до `0.23.4` через официальный installer:

- скачивание оборвалось на большом archive artifact;
- binary частично заменился;
- service начал падать;
- наблюдались `Permission denied`, `Segmentation fault`, restart loop;
- GPU discovery/runtime состояние стало недостоверным.

## Причина

Installer удаляет/заменяет части runtime layout и распаковывает большой archive artifact. Если поток скачивания/распаковки обрывается, можно получить частично установленный runtime:

```text
new /usr/local/bin/ollama + incomplete /usr/local/lib/ollama
```

Это хуже обычного failed install, потому что версия может выглядеть обновлённой, но binary/runtime фактически повреждены.

## Неверный путь

Не продолжать smoke-тесты gateway/Continue, пока не подтверждён GPU backend.

Не считать `ollama --version` достаточным proof-of-health.

## Рабочее решение

Использовать deterministic repair path:

1. Скачать artifact напрямую через `aria2c`.
2. Проверить `zstd -t`.
3. Проверить `tar -tf`.
4. Остановить service.
5. Сохранить backup повреждённого runtime.
6. Удалить `/usr/local/lib/ollama`.
7. Распаковать archive в `/usr/local`.
8. Восстановить права binary.
9. Перезапустить service.
10. Проверить CUDA backend и `ollama ps`.

## Prevention

Для больших Ollama upgrades/repairs на нестабильном канале:

- избегать pipe installer как единственного пути;
- предпочитать resumable download (`aria2c` или `curl -C -`);
- всегда делать rollback snapshot;
- всегда выполнять archive integrity test перед распаковкой;
- не запускать Continue/gateway smoke до подтверждения GPU path.
