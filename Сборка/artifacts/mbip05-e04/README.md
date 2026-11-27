# MBIP-05/E04 v2 — Operational Readiness

27.11.2026. PARTIAL / READY_FOR_REVIEW_WITH_BLOCKERS. E04 does not supersede E03-C acceptance gates. [E03-C](../mbip05/E03-C.md) remains byte-identical. No inference, load, reboot, server modification or publication during E04.

## Actual state and delta
Server: Inkling native SQ-20 FP16 global KV host On, 262144 effective, expert cap 14.66 GiB, draft off. Flash-Next 262144 profile unchanged, not loaded. Strata active/static; Ollama/Gateway/RAG inactive/enabled for boot. 300 W, guards unchanged. Current profile fingerprint d516f2b9b42704e9d62fe4a8b4b493a141ba1f9cee0745d6b0430698350c2b22; FP8 candidate not installed. Flash profile 405f4d7afa40e7d6ebec2359bc77a4cf419e7a16413e6d706def583e676493d6, switcher 181569c830f2a73d07d476dba27b63a89122fdac228c1f965cd043c96744826e. E01 G0 BLOCKED; F07 REVALIDATE remains. No new model quality verdict.

Lenovo: prior 18081 listener belonged to the established experiment SSH master; normal helper attempted to bind a second forward. Fresh BatchMode authentication failed. E04 adopts that exact user-owned socket by private master-path reference, verifies live master PID and single loopback listener, and compares remote/local API identity. Does not close existing admin master. No SSH key/host policy changes. Reconnect with interactive SSH through ailab-mode connect when needed; do not treat new-master auth as tested. Unknown listener or stale socket is refused, no killing other processes.

Pi CLI 1.0.3; VS Code 1.148.0 and pi0.pi-vscode 0.0.9. IDE path previously pointed to Pi 1.5.0; changed only pi-vscode.path to pinned ~/.local/bin/pi, separate 1.5.0 retained. E01-P client metadata applied, not long-session acceptance; global default remains previously accepted Ollama Q6/max, Q27 model override medium as ADR-032. All four model IDs configured, contextWindow 262144. Flash output/reserve 8192/12288, Inkling 4096/8192, Q27 262144/32768, reserve Q6 32768/32768. Keep 20000; Strata low, Q27 medium, Q6 max. Pi credentials, other provider fields and sessions unchanged. This is a limited E04 client delta, not a fabricated E03-C live receipt.

## Daily operation now (read-only checks)
Use Lenovo terminal:
    ailab-mode connect
    ailab-mode status
    ailab-pi inkling --check
    pi --offline --list-models
Status validates current backend and actual matching remote/local Strata API, or Ollama inventory when that mode is active. --check reports the selected provider/model/thinking without prompting. Current Inkling path succeeds. Commands ailab-mode flash, ailab-mode q27, ailab-mode q6 currently refuse with exit 3 if another mode is active. Historical --drained is accepted as an argument but DOES NOT initiate a transition in the E04 helper. This is intentional pending G0; the existing server switcher is not modified. Do not bypass the refusal or load models until cooling admission. Once independent admission is closed, validate and re-enable actual switching using the original guarded/drained switcher and explicit owner-approved transition procedure; E04 has not tested that live route. The helpers can start Pi for the already-active model but no inference is authorized or claimed by this stage.

VS Code: actual extension Pi: Open uses pinned CLI; after a settings reload/new window select the exact provider/model in /model. Never submit a request to an inactive backend. Read-only checking before work is recommended. Exact identifiers:
- Inkling: ailab-strata/inkling-2-mini-sq-20 (low)
- Flash: ailab-strata/qwen3.8-flash-next-ud-q6_k_xl (low)
- Q27: ailab-ollama/qwen3.8-27b-gsq-rco:iq3s-mtp-262k (medium)
- Q6 reserve: ailab-ollama/qwen3.8-flash-next:125b-a6b-q6_K-ab-262k (max)
API Strata uses existing loopback forward 127.0.0.1:18081/v1; GET /models or /status under /v1 are read-only. Ollama uses unchanged existing direct provider endpoint, only when Ollama mode active. Gateway/RAG are reserve services, not a concurrent Strata proxy.

## Evidence and remaining work
New helper logic tests 10/10 PASS (synthetic SSH/ss/API, exact model args all 4; refusal on unsafe/mismatched cases). Current actual SSH master and Inkling GET readiness, installed Pi ModelRuntime/SettingsManager and CLI listing PASS. Actual installed extension launch tested in isolated empty VS Code Extension Development Host, no real endpoint, no prompt; terminal configured launcher and bridge argument verified. Initial workspace-host attempt failed extension discovery; empty-window attempt PASS. Neither test proves actual user IDE inference. Prior E02-P mock preserved. Flash, Q27 and reserve Q6 switching and live inference NOT_RUN; blocked by G0. E04 success criterion not fully met: three-model operational cycle and actual generation unavailable until safe admission; no automatic boot/default change, F07 and full E01/E02 remain open.

Private evidence on Lenovo: e04.byndmeai in existing MBIP-05 work directory; before/ exact client backups, evidence/client-transaction.json (before/after hashes), stage/apply-client.py (conflict-aware rollback), mode-*.log, pi-runtime-final.log, ide-launch.jsonl, test-helpers.log, server-before/after.txt. Preserve backups outside repository. Rollback is separately authorized, only after closing Pi/IDE and checking hashes: run the private apply-client.py with rollback argument; it refuses unrelated edits and removes only E04 master reference. Restores both helper files and three client config files; does not terminate SSH master. Privileged server rollback not needed: no server changes.
