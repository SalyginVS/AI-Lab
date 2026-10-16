# Исторические конфиги

Статус: справочник сверки RB-07. Эти файлы не являются источником установки сервисов.
Сами файлы не изменены и не удалены; окончательная уборка относится к RB-11.
Сверка выполнялась с захватом RB-02, а не с памятью или номером версии в заголовке.

| Файл | Результат | Замена в Сборка |
|---|---|---|
| Continue config.yaml обзор.md | устарел как источник серверной сборки; live-клиент здесь не сверялся | клиентский runbook RB-08, ещё не создан |
| __init__.py | устарел (байты отличаются от захвата) | artifacts/services/gateway/src/gateway/__init__.py |
| app.py | устарел (байты отличаются от захвата) | artifacts/services/gateway/src/gateway/app.py |
| chat.py | устарел (байты отличаются от захвата) | artifacts/services/gateway/src/gateway/chat.py |
| config.v2.yaml | устарел как источник серверной сборки; live-клиент здесь не сверялся | клиентский runbook RB-08, ещё не создан |
| config.yaml | устарел как источник серверной сборки; live-клиент здесь не сверялся | клиентский runbook RB-08, ещё не создан |
| docker-policy.yaml | устарел (байты отличаются от захвата) | artifacts/services/docker-mcp/src/docker-policy.yaml |
| embeddings.py | устарел (байты отличаются от захвата) | artifacts/services/gateway/src/gateway/embeddings.py |
| errors.py | совпадает с live (байты файла захвата) | artifacts/services/gateway/src/gateway/errors.py |
| gateway.py эндпоинты_bak.md | устарел (байты отличаются от захвата) | artifacts/services/gateway/src/gateway/ |
| gateway_v0_8_0.py | устарел (байты отличаются от захвата) | artifacts/services/gateway/src/gateway/ |
| listing.py | устарел (байты отличаются от захвата) | artifacts/services/gateway/src/gateway/listing.py |
| logging_config.py | совпадает с live (байты файла захвата) | artifacts/services/gateway/src/gateway/logging_config.py |
| models.py | устарел (байты отличаются от захвата) | artifacts/services/gateway/src/gateway/models.py |
| orchestrator.py | устарел (байты отличаются от захвата) | artifacts/services/gateway/src/gateway/orchestrate.py |
| pipelines.yaml | устарел (байты отличаются от захвата) | artifacts/services/gateway/src/pipelines.yaml |
| run.py | совпадает с live (байты файла захвата) | artifacts/services/gateway/src/run.py |
| systemd llm-gateway.service.md | устарел (байты отличаются от захвата) | artifacts/services/units/llm-gateway.service.in |
| upstream.py | совпадает с live (байты файла захвата) | artifacts/services/gateway/src/gateway/upstream.py |
