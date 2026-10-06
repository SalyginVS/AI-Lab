# 086 — Pi long-context harness baseline не был глобальным

## Симптом

Новый Q6 LeaseFlow workspace дошёл до:

```text
93.8% / 262k
Request timed out
Auto-compaction failed: Turn prefix summarization failed: Request timed out
```

После failure Pi автоматически начал ещё один дорогой long-prefill.

## Причина

Ранее проверенный профиль:

```text
reserveTokens=32768
keepRecentTokens=20000
```

жил только в project-local:

```text
/home/vladimir/projects/opsboard/.pi/settings.json
```

В новом workspace `.pi/settings.json` отсутствовал, а global settings сохраняли Pi default:

```text
reserveTokens=16384
```

Дополнительно:

```text
httpIdleTimeoutMs=7200000
retry.provider.timeoutMs=7200000
retry.maxRetries=1
```

Для Q6 long-prefill это создало две проблемы:

1. compaction запускался слишком поздно;
2. timeout + automatic retry превращали медленный полезный inference в повторные многочасовые вычисления.

Server journal показал, что inference реально прогрессировал, то есть это был harness failure, а не доказанный model stall.

## Исправление

Pi обновлён `0.87.0 -> 1.0.3`.

Принят global/model-scoped baseline:

```text
reserveTokens=32768
keepRecentTokens=20000
httpIdleTimeoutMs=0
retry.enabled=false
retry.maxRetries=0
provider.maxRetries=0
provider.timeoutMs absent
```

Q6 `samplingParams.reasoning_effort=xhigh` удалён; используется `thinkingLevelMap max -> xhigh`.

CLI runtime smoke и VS Code Pi gate после ремонта — PASS.

## Правило

Перед любой serious executor task:

```text
restore project evidence
-> inspect effective Pi global/project settings
-> verify model config
-> verify server runtime
-> only then start task
```

Новый workspace не считается наследующим старый harness только потому, что модель/provider те же.

## Prevention

Mandatory preflight:

- Pi version;
- global `settings.json`;
- project `.pi/settings.json` if present;
- context/maxTokens;
- compaction reserve/keepRecent;
- timeout/retry policy;
- thinking mapping;
- Ollama health;
- Q6 wrapper activation.
