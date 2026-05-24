# ADR-030: Client Surface Determines Model Operational Fit

Дата: 2026-05-24
Статус: Accepted
Контур: AI Lab RTX3090

## Context

В ходе эксплуатации AI Lab RTX3090 обнаружен важный фактор: одна и та же модель может показывать существенно разное качество агентского поведения в разных client/execution surfaces.

Конкретный сигнал:

- VS Code built-in Chat/Copilot, настроенный напрямую на Ollama, показал существенно лучшую стабильность, скорость и предсказуемость tool application в agent mode.
- Модель `GLM4.7`, ранее оценённая негативно в другом контуре, в новом surface показала диаметрально лучший результат.
- В сообществе пользователя Pi и OpenCode сейчас являются двумя основными terminal-agent направлениями; лидеры сообщества ищут универсальный, model-agnostic подход, совместимый не только с proprietary models.

## Decision

Модельные verdicts в AI Lab больше не считаются полноценными без указания execution surface.

Новый обязательный атрибут оценки:

```text
evaluated_surface = client/harness + routing path + tool protocol + context packaging + apply mechanism + permission boundary
```

Примеры surfaces:

- VS Code built-in Chat/Copilot -> Ollama direct
- Continue.dev -> gateway/Ollama
- OpenCode -> gateway/Ollama
- Pi -> gateway/Ollama
- Ollama Codex App
- vLLM MTP lane -> gateway -> IDE client

## Consequences

### 1. GLM4.7

`GLM4.7` переводится из фактически rejected/limited статуса в:

```text
GLM47_STATUS=revalidation_required_surface_dependent
```

Предыдущие негативные выводы остаются исторически валидными только для старого deployment contract.

### 2. VS Code built-in Chat/Copilot direct Ollama

Новый статус:

```text
VSCODE_BUILTIN_CHAT_OLLAMA_DIRECT=candidate_primary_daily_agent_lane
```

Не считается production decision без повторяемого validation pass, но получает высокий приоритет.

### 3. Pi

Новый статус:

```text
PI_STATUS=mandatory_evaluation_candidate
```

Причина: strong community signal + fit с model-agnostic/local-compatible terminal harness направлением.

### 4. OpenCode

OpenCode сохраняется как terminal-agent candidate и comparison baseline.

```text
OPENCODE_STATUS=keep_as_terminal_agent_candidate
```

### 5. Continue.dev

Continue остаётся важным IDE-контуром, но должен быть пересравнен с VS Code built-in direct Ollama lane.

```text
CONTINUE_STATUS=keep_but_recompare_against_vscode_direct
```

## Evaluation rule

Любой будущий отчёт по модели должен фиксировать:

- model id;
- quantization;
- runtime backend;
- client/harness;
- routing path;
- context source;
- tool protocol;
- permission model;
- task type;
- pass/fail;
- observed failure mode;
- whether the verdict is model-level or surface-specific.

## Non-goals

Этот ADR не утверждает:

- что VS Code built-in Chat/Copilot лучше всегда;
- что GLM4.7 полностью реабилитирована;
- что Pi лучше OpenCode;
- что Continue нужно удалить;
- что Codex App готов к использованию.

Решение только фиксирует: model operational fit зависит от client surface и должен валидироваться как deployment contract, а не как абстрактная способность модели.
