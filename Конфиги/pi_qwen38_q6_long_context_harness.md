# Pi 1.0.3 + Qwen3.8 Q6 — long-context executor harness baseline

**Дата:** 2026-10-06
**Статус:** Accepted baseline
**Назначение:** serious local executor runs на 262144 context.

## Scope

Этот baseline относится к Pi + `ailab-ollama` и Qwen3.8 Flash-Next Q5/Q6 long-context lanes.

## Pi

```text
Pi 1.0.3
pi-vscode 0.0.9
binary: /home/vladimir/.local/bin/pi
```

## Global settings contract

Критические значения `~/.pi/agent/settings.json`:

```json
{
  "compaction": {
    "enabled": true,
    "reserveTokens": 32768,
    "keepRecentTokens": 20000
  },
  "httpIdleTimeoutMs": 0,
  "retry": {
    "enabled": false,
    "maxRetries": 0,
    "provider": {
      "maxRetries": 0
    }
  }
}
```

Для long-context моделей рекомендуется model-specific override тех же `32768/20000`, чтобы случайный project-wide fallback не вернул Pi default `16384`.

`retry.provider.timeoutMs` должен отсутствовать.

### Rationale

- `reserveTokens=16384` запускает compaction примерно на 93.75% 262K окна.
- `reserveTokens=32768` переносит threshold примерно на 87.5%.
- локальный Q6 prefill может быть многочасовым;
- arbitrary client wall-clock timeout не отличает медленный полезный inference от stall;
- automatic retry после многочасового failure может почти удвоить вычислительные затраты.

Policy:

```text
long-running inference allowed
automatic expensive retry forbidden
manual operator cancel remains available
```

## Q6 model contract

`~/.pi/agent/models.json`:

```json
{
  "id": "qwen3.8-flash-next:125b-a6b-q6_K-ab-262k",
  "reasoning": true,
  "contextWindow": 262144,
  "maxTokens": 32768,
  "thinkingLevelMap": {
    "off": null,
    "minimal": "low",
    "low": "low",
    "medium": "medium",
    "high": "xhigh",
    "xhigh": "xhigh",
    "max": "xhigh"
  }
}
```

Не использовать принудительный:

```json
"samplingParams": {
  "reasoning_effort": "xhigh"
}
```

Он больше не нужен после серверного reasoning compatibility repair и может перекрывать пользовательский thinking selection.

## Уточнение 2026-10-16 (H-1)

Владелец решил восстанавливать `models.json` Pi как на клиенте.
Override Q6 `modelOverrides.samplingParams.reasoning_effort = "xhigh"` присутствовал при приёмке Q6 6 октября и входит в принятую конфигурацию (RB-03, раздел 6).
Слова «удалён» в прежнем тексте описывали намерение, а не фактическое состояние.
Прежняя рекомендация не использовать принудительный override не изменяет состав принятой конфигурации.
Удаление override возможно отдельной задачей с ревалидацией Q6.
Фактические параметры запроса Pi, включая поведение при выборе `low`, фиксируются тестом RB-08 T7.

## Server runtime prerequisites

```text
Ollama                      0.35.1
OLLAMA_CONTEXT_LENGTH       262144
OLLAMA_FLASH_ATTENTION      1
OLLAMA_KV_CACHE_TYPE        q8_0
OLLAMA_NUM_PARALLEL         1
Q6 model id                 09b8aff72a79
Q6 N_CPU_MOE                43
Q6 per_layer_token_embd     CPU
Q6 lazy                     on
Q6 load                     mmap
```

Q6 runner profile должен быть model-scoped; Q5 не должен наследовать Q6 CPU-MoE/PLE overrides.

## Reasoning compatibility

Для Q6 подтверждён compatibility repair:

```text
max render   PASS
xhigh render PASS
max/xhigh render identical PASS
OpenAI inference PASS
model id unchanged PASS
```

Pi `max` отображается в Q6 как `xhigh`.

## Preflight

Перед serious executor run:

```bash
pi --version

jq '.compaction,.httpIdleTimeoutMs,.retry' ~/.pi/agent/settings.json

pi --list-models qwen3.8-flash-next
```

Проверить:

```text
Pi expected version
Q5/Q6 context 262.1K
max-out 32.8K
Q6 thinking=yes
reserve=32768
keepRecent=20000
http timeout disabled
auto retry disabled
provider retry disabled
```

Если workspace имеет `.pi/settings.json`, его нужно отдельно проверить на конфликт с global baseline.

## Short acceptance

CLI:

```bash
pi \
  --print \
  --no-session \
  --no-tools \
  --provider ailab-ollama \
  --model 'qwen3.8-flash-next:125b-a6b-q6_K-ab-262k' \
  --thinking max \
  'Ответь только: OK'
```

Ожидается `OK`.

Server evidence:

```bash
ollama ps
journalctl -t ollama-q6-profile --since "20 min ago" --no-pager
```

IDE acceptance:

```text
VS Code + Pi Code
Q6 selected
thinking=max
Ответь только: OK
```

Только после CLI + IDE PASS запускать длительную executor-задачу.

## Clipboard dependency on Precision-5560

Для `/copy` Pi в Wayland session установлен:

```text
wl-clipboard
/usr/bin/wl-copy
/usr/bin/wl-paste
```

Это системная dependency Pi clipboard path, не project workaround.

## Task contract

Для complex bounded executor см. ADR-031 и `Meta/Рабочий процесс.md`.
