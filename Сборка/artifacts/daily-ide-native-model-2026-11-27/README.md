# Native Pi /model integration — installed candidate (27.11.2026)

Owner requested switching the three approved models inside Pi without closing the current session each time. Installed on Lenovo. Pi 1.0.3 source and its bundled extension declarations inspected locally. The native `model_select` event is emitted **after** the client model changes and is awaited; it has no veto result. The runner catches handler errors, so throwing alone cannot block a provider call.

Implementation:
- `pi-model-switch.ts` loaded explicitly by `ailab-pi` from `~/.local/share/ailab/`. Native TUI selection, idle/no queued messages, three allowlisted models only; restore/RPC changes do not initiate a backend transition.
- Calls existing selector with `--from-pi` from the current Pi process. Parent process check, other-Pi check, local transition lock, same three exact sudoers commands, server guard/connection/resource/readiness checks. The current idle Pi is excluded from the other-session check; other clients must be drained by the operator. This is not a global admission arbiter.
- Rechecks actual backend, realigns to healthy model after refusal, ordinary input and manual compaction gated by model readiness; busy switch refused. Pi's native UI may still display the requested model in a status message after refusal: use extension status `AI Lab READY: ...` and `/lab-status` to verify.
- No changes to Pi distribution, server controller, sudoers, weights, context, boot or GPU limit. External VS Code task remains fallback.

Evidence: 12/12 Node mock tests PASS (`node --test test-model-switch.mjs`). Actual Pi 1.0.3 TUI loader and native `/model` refusal with another controlled Pi process PASS: selector denied transition, Pi restored Inkling, backend remained Inkling. Two initial PTY automation attempts did not submit the command (terminal input); corrected test used two Enter events. No successful live native backend transition claimed yet; positive VS Code acceptance pending. Client-side event hooks are not a guarantee of intercepting every provider request from arbitrary extensions or other hosts.

Deploy delta: copy the two wrappers to `~/.local/bin/` and extension to `~/.local/share/ailab/pi-model-switch.ts`, only after comparing live baseline and accepting scope. Backups created locally; restart the old Pi tab once for extension loading. No secrets included.
