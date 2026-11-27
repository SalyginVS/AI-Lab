# Lenovo Pi selector snapshot, 27.11.2026

This folder records the deployed **three-model daily-use client configuration**. It is a reproducibility snapshot, **not an unattended installer**. No credential-bearing Pi models.json, SSH keys, server profiles, or private evidence are included.

- `ailab-mode`: verifies SSH master/loopback forward, runtime state, exact model ID and context.
- `ailab-select-model`: three-choice interactive selector; drains via root-owned MBIP controller; verifies before persisting preference.
- `ailab-ide`: Pi VS Code extension entrypoint, reads saved choice.
- `ailab-pi`: explicit verified model ID and pinned Pi execution.
- `vscode-tasks.json`: user-level `AI Lab: Select model` task; `vscode-keybindings.json`: only the task-specific `Ctrl+Alt+M` mapping.

Installed scripts are in `~/.local/bin/` on Lenovo, VS Code config under `~/.config/Code/User/`. Private Pi providers are under `~/.pi/agent/`. Hard-coded local paths and SSH alias `llm` make these files machine-specific; inspect before copying to a new client. The server-owned `/etc/sudoers.d/ailab-model-switch` was installed with `root:root 0440` after a separate owner password entry and `visudo` validation, allowing only three exact backend transition commands.

Current operational contract: [runbook 56](../../56_VSCode_Pi_Три_модели_ежедневная_работа.md), [ADR-035](../../../Решения/operational/ADR-035_Three_Model_Daily_IDE_Operation.md). Historical MBIP-05 acceptance, G0/thermal limits and original ADR contracts remain in force for anything outside short owner-authorized daily-use tasks.
