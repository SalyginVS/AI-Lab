---
tags: [adr, решение, opencode, terminal-agent, repo-write, governance]
дата: 2026-05-15
статус: accepted
---

# ADR-029 — OpenCode Controlled Terminal-Agent Lane

## Контекст

В AI Lab RTX 3090 проверен OpenCode v1.15.0 как controlled terminal-agent contour для работы через локальный `llm-gateway` и модель `qwen3.6:27b`.

Цель проверки не состояла в разрешении автономного repo-agent режима. Проверялась только возможность безопасно использовать OpenCode для ограниченных read-only и small scoped documentation edit сценариев внутри AI-Lab documentation repo.

Канонический documentation/source-of-truth контур:

```text
/home/vladimir/llm/AI-Lab
git@github.com:SalyginVS/AI-Lab.git
branch: main
```

Серверный runtime filesystem не является source-of-truth для проектной документации.

## Решение

Принять OpenCode как **controlled terminal-agent lane** с двумя wrapper-профилями:

```text
oc-ailab-readonly
oc-ailab-edit
```

Итоговый repo-write статус:

```text
REPO_WRITE_SMOKE=PASS
OPEN_CODE_REPO_WRITE_MODE=allowed_only_for_small_scoped_docs_edits_with_manual_review
AUTONOMOUS_AGENT_READY=no
```

## Разрешено

`oc-ailab-readonly` разрешён для:

- read-only анализа AI-Lab repo;
- чтения документации;
- поиска по файлам внутри explicit `--dir`;
- подготовки summary без записи.

`oc-ailab-edit` разрешён только для:

- small scoped documentation edits;
- заранее указанной директории через wrapper argument / `--dir`;
- одного небольшого change set за run;
- ручного review результата;
- commit/push только после post-checks.

Обязательные post-checks после write-run:

```bash
pgrep -af 'opencode' || echo "NO_OPENCODE_PROCESS_FOUND"
git status --short --branch
git diff
git diff --check
grep -RInE 'sk-lab-[0-9a-fA-F]{20,}|Bearer[[:space:]]+sk-|LLM_GATEWAY_TOKENS=' <changed-path> || true
```

## Запрещено

Запрещено:

- использовать OpenCode как autonomous repo agent;
- включать `bash`;
- включать `task` / subagent;
- включать `webfetch` / `websearch`;
- включать `external_directory`;
- использовать `edit=ask` в scripted `opencode run`;
- использовать `--dangerously-skip-permissions`;
- выполнять repo-wide write без явного scope;
- принимать `exit code 0` как доказательство успешной правки без filesystem/git verification.

## Evidence

### Wrapper validation

`oc-ailab-edit` validated with:

```text
read/glob/grep/list = allow
edit = allow
bash/task/webfetch/websearch/external_directory = deny
```

`oc-ailab-readonly` validated with:

```text
read/glob/grep/list = allow
edit/bash/task/webfetch/websearch/external_directory = deny
```

### Repo-write smoke

Controlled repo-write smoke выполнен на disposable path:

```text
Этапы/2026-05-15_OpenCode_Controlled_Terminal_Agent/repo_write_probe/README.md
```

Evidence commit:

```text
adee92f test: validate OpenCode bounded repo write
```

Documentation sync commit:

```text
d8613c4 docs: record OpenCode repo write validation
```

## Tool boundary wording

Корректная формулировка:

```text
No successful use of bash/task/web/external_directory was observed.
These tools are denied by wrapper policy.
Visible OpenCode trace showed only read/edit operations inside scoped directory.
Post-state checks showed no boundary breach.
```

Это не является raw internal tool-call audit log. Не формулировать как абсолютное доказательство, что модель никогда не пыталась вызвать запрещённый tool.

## Последствия

OpenCode добавляется в AI Coding Platform как controlled terminal-agent lane, но не как autonomous agent layer.

Promotion path в более высокий режим возможен только через отдельный validation gate:

```text
small scoped docs edit
  -> bounded multi-file docs edit
  -> policy-gated repo agent candidate
  -> autonomous agent consideration
```

На текущем этапе promotion остановлен на уровне:

```text
small scoped documentation edits with manual review
```

## Связанные документы

- [[Этап — OpenCode controlled terminal-agent lane]]
- [[Конфиги/opencode_ailab_wrappers]]
- [[083_opencode_run_edit_ask_auto_reject_exit_zero]]
- [[084_opencode_wrapper_not_in_path]]
