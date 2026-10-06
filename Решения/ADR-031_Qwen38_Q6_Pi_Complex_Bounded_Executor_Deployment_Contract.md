# ADR-031: Qwen3.8 Flash-Next Q6_K + Pi — Complex Bounded Engineering Executor Deployment Contract

**Дата:** 2026-10-06
**Статус:** Accepted
**Контур:** AI Lab RTX 3090
**Связанное решение:** ADR-030 — model operational fit зависит от execution surface.

## Context

В AI Lab ранее было подтверждено, что сильная локальная модель может выполнять bounded engineering tasks, но её operational verdict нельзя отделять от client/harness, routing path, context packaging и verification discipline.

Для Qwen3.8 Flash-Next Q6_K проведён длительный реальный executor-run `Q6-EXEC-LEASEFLOW-v1` на существующем многомодульном Python/SQLite проекте. Задача включала:

- транзакции и rollback;
- durable idempotency;
- dependency graph;
- leases, fencing и retry semantics;
- crash recovery;
- schema migration;
- multi-process concurrency;
- legacy facade;
- JSONL CLI;
- обязательную self-review;
- regression repair;
- отдельный owner evaluator.

Во время run отдельно выявлены и исправлены проблемы Pi harness: поздний compaction, искусственный request timeout и дорогой automatic retry.

## Evaluated surface

```text
Machine:
  Dell Precision 5560
  Ubuntu
  VS Code + pi-vscode 0.0.9

Harness:
  Pi 1.0.3

Provider:
  ailab-ollama
  http://192.168.0.128:11434/v1

Model:
  qwen3.8-flash-next:125b-a6b-q6_K-ab-262k

Pi thinking:
  max -> xhigh

Context:
  262144

Output cap:
  32768

Server:
  Ollama 0.35.1
  RTX 3090 24 GiB
  ~62 GiB RAM

Q6 runtime profile:
  N_CPU_MOE=43
  per_layer_token_embd=CPU
  lazy=on
  load=mmap
  KV=q8_0
  Flash Attention=ON
```

Q6-specific runner wrapper сохраняет обычный native placement для других моделей.

## Decision

На указанном execution surface Qwen3.8 Flash-Next Q6_K получает роль:

```text
Q6_ROLE=COMPLEX_BOUNDED_ENGINEERING_EXECUTOR
Q6_ROLE_STATUS=ACCEPTED
AUTONOMOUS_ARCHITECTURE_OWNER=NO
UNBOUNDED_AUTONOMOUS_AGENT=NO
```

Это расширяет роль локального executor относительно narrow/small-edit сценариев: Q6 разрешены сложные многомодульные инженерные задачи при наличии жёсткого execution contract и внешнего acceptance.

Решение является **deployment-contract verdict**, а не абстрактным утверждением о модели вне Pi/Ollama surface.

## Evidence

### First pass

Независимая повторная проверка сохранённого `first-pass.zip`:

```text
protected/integrity   PASS
owner evaluator       61/61 PASS
public tests          18/18 PASS
model local tests     219/219 PASS
```

### Final after mandatory self-review

Независимая повторная проверка `final.zip`:

```text
protected/integrity   PASS
owner evaluator       61/61 PASS
public tests          18/18 PASS
model local tests     232/232 PASS
```

Submission:

```text
sha256 = 65f3e7ffa6ab21698e843caaa07d3f171184e3336ef18a3e40140e622b382ff2
```

### Self-review value

Первая реализация уже проходила owner evaluator, но обязательная self-review нашла дополнительные реальные дефекты за пределами этого evaluator. В частности:

1. explicit `null` в optional command keys принимался вместо `INVALID_ARGUMENT`;
2. race при одновременной migration v1 -> v2;
3. invalid UTF-8 мог оборвать JSONL CLI;
4. lone surrogate мог выйти raw `UnicodeEncodeError`;
5. legacy `leased` row с `lease_until=NULL` мог вызвать `TypeError`;
6. `snapshot()` допускал torn read между SELECT;
7. contention/read path мог отдавать raw `sqlite3.OperationalError`, включая `events()`.

Для найденных дефектов были добавлены regression tests; local suite вырос `219 -> 232`.

## Mandatory task contract for this role

Complex bounded task для Q6 должна задаваться не свободным prompt, а execution contract.

Обязательные элементы:

1. конечный результат;
2. подтверждённый baseline;
3. source-of-truth и приоритет источников;
4. разрешённые/запрещённые изменения;
5. инварианты;
6. acceptance gates;
7. формат evidence;
8. спецификация в workspace (`TASK.md`, `spec/*`, исходный код);
9. обязательный first-pass checkpoint, если важна трассируемость;
10. обязательная финальная self-review;
11. regression test для каждого найденного реального дефекта;
12. повтор полного gate после исправлений;
13. final diff review;
14. результат модели = `READY_FOR_REVIEW`, а не `ACCEPTED`;
15. независимый reviewer/control plane принимает окончательное решение.

Модели нельзя заранее сообщать ожидаемое число дефектов self-review.

## Pi harness baseline

Для 262K local executor lane принят следующий baseline:

```text
contextWindow              262144
maxTokens                  32768

compaction.enabled         true
compaction.reserveTokens   32768
compaction.keepRecentTokens 20000

httpIdleTimeoutMs          0
retry.enabled              false
retry.maxRetries           0
retry.provider.maxRetries  0
retry.provider.timeoutMs   absent

Q6 thinking map:
  off      -> null
  minimal  -> low
  low      -> low
  medium   -> medium
  high     -> xhigh
  xhigh    -> xhigh
  max      -> xhigh
```

`samplingParams.reasoning_effort=xhigh` как принудительный workaround удалён. Thinking level должен управляться Pi через `thinkingLevelMap`.

## Harness preflight gate

Перед каждой серьёзной Q6 executor-задачей проверить:

```text
Pi version / executable
effective global + project settings
Q6 contextWindow=262144
Q6 maxTokens=32768
compaction reserve=32768
keepRecent=20000
client timeout disabled
agent/provider auto-retry disabled
thinking max -> xhigh
Ollama health
Q6 model-scoped wrapper activation
workspace source-of-truth / scope
```

Новый workspace не должен неявно возвращаться к Pi defaults или старым project-local settings.

## Consequences

### Разрешено

- complex multi-file implementation;
- transactional/stateful backend logic;
- migrations;
- concurrency/recovery logic;
- tests and regression repair;
- CLI/integration work;
- bounded refactor within explicit scope.

### Не разрешено по умолчанию

- architecture ownership;
- product/strategic decisions;
- unbounded repository cleanup;
- production/systemd/gateway changes без отдельного approval;
- autonomous acceptance of its own result.

## Non-goals / limits

Этот ADR не доказывает:

- превосходство Q6 над Q5 без matched A/B;
- универсальную безошибочность Q6;
- autonomous-agent readiness;
- перенос verdict на другой client surface без revalidation;
- безусловную стабильность любой многосуточной сессии.

Run был прерван harness-инцидентом и продолжен из сохранённого workspace/first-pass evidence. Поэтому результат подтверждает executor quality и recovery discipline, но не является clean uninterrupted endurance-test.

## Supersession / revalidation

Повторная validation обязательна при существенном изменении любого из:

- model generation / quantization;
- Pi major behavior;
- context policy;
- Ollama template/parser behavior;
- routing path;
- tool protocol;
- permission boundary.
