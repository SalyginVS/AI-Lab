# MBIP-05/E02-P — mock and future live acceptance procedure
Дата: 27.11.2026. Scope: client preparation only.
No real inference, server/profile change, or live client installation in E02-P.

Owner decision 27.11.2026: all four prolonged live cases below are NOT_RUN / DEFERRED, excluded from the current scope. The protocol is preserved as historical acceptance criteria, not a current execution instruction. No thresholds or guards are waived; no live PASS is inferred from mock. A future run requires separate safe admission and authorization, and reconciliation with installed E04 settings.

## Evidence and reproducibility

Prerequisite: accepted E01-P manifest a6d5c8b706ba6df8a877e32eb55cc8337121a81dec8d724b4450d7f734b4937c.
Run mock only:
    ./run-mock.sh
It creates a new private directory, checks E01-P and installed versions, uses a loopback mock at 127.0.0.1:18762 with no real backend in isolated models.json, starts CLI via RPC and VS Code Extension Development Host via the installed pi0.pi-vscode 0.0.9, and verifies raw HTTP payloads and session JSONL. It requires a valid graphical session for IDE. Do not reuse the live client agent directory. It stops only its own mock. Verify output E02P_REPLAY_PASS and exit code 0.
Primary run: verification.json; verify.log. Replay: ../e02p-replay.fFInbBzr/verification.json and verify.log.
Attempt directories preserve failed harness iterations. They are not PASS evidence.
The mock supplies artificial usage counts and artificial summary/answers. It is evidence of client mechanics only, not model tokenization, reasoning, semantic compaction, inference, or GPU performance.

## Live fixture preparation (offline only)

Each live-fixtures/{cli-flash,cli-inkling,ide-flash,ide-inkling}/ contains workspace, prompts/01-start.txt through 04-after.txt, expected.json outside workspace. Use a fresh copy per test. Do not send expected.json to the model. The first read must supply the second filename, which is not given in the chain prompt; the second read supplies the independent VALUE. RECENT is independent of VALUE.
The live fixture sizes are starting calibration candidates, not exact token counts. No claim of actual 262144-window use follows from character length. Do not use mock usage for a live verdict.

## Live admission gates (not satisfied by E02-P)

Only a separate explicit live execution contract may authorize a run. E01 must satisfy its real-engine acceptance and unresolved thermal safety admission must be closed by appropriate diagnostics. Keep all existing protections and power settings. No parallel backend, no automatic model switching, no retries that bypass guards. Use the already approved monitored contour and abort safely on any guard event, error, or invalid resource state. All steps below are acceptance definitions, not authorization to start.
Before each case, confirm correct loaded model and actual native/effective 262144, exact accepted server profile, idle request counters, guard active through all requests and compaction, and original client files preserved. Use the E01-P Pi candidate on a copy; restrict the provider to the selected live endpoint only in that copy. Verify Pi settings and exact model ID. No mock process or endpoint may be used in the live run.

## Historical four-case acceptance matrix (NOT_RUN / DEFERRED)

C1 CLI Flash, C2 CLI Inkling, C3 actual VS Code extension Flash, C4 actual VS Code extension Inkling.
For CLI use Pi's installed RPC mode and a persistent private session dir, as in run-cli.py (replace mock prompt sequence by the live prompt files in the separately authorized run). For IDE use the isolated Extension Development Host pattern in ide-test.js with the actual installed extension and bridge. Do not substitute CLI for IDE. Keep the same contextWindow, maxTokens, modelOverrides, thinkingLevelMap, and low thinking override from E01-P.
Record real request/response or equivalent inspectable server protocol and client session JSONL for all phases. A session file alone is not proof of complete outbound payload or actual engine token usage.

1. LONG: supply 01-start.txt in one input, no tools. Expect JSON exact BEGIN/MIDDLE/END. Confirm full outbound input (including system and tool overhead) and actual prompt tokens; calibrate using actual tokenizer / usage, not mock counts. For a near-window long-context acceptance witness use the existing MBIP-05 95% target (at least 249037 actual input tokens) while keeping the response reserve and actual request within 262144. Flash threshold 249856, Inkling 253952; do not claim a 262144-token user prompt can fit in addition to system, tools, and response.
2. AGENT: in the same session submit 02-chain.txt. Require sequential successful read(first.txt), then read(second filename from first result), unique correlated call/result IDs, exact VALUE and all three original markers. IDE additionally requires real vscode_get_editor_state on the actual workspace and correlated success. Verify real engine usage/cache reuse when comparable stable prefix is available; report no reuse honestly, and record why prefix changes. Do not rerun the accepted Flash API long-context/agent experiment as a substitute.
3. COMPACTION: submit 03-pressure.txt only after calibrating actual prior usage and next-turn token budget, or use a separately sized recent-turn fixture with the same marker and enough recent history for a valid cut point. Require a completed normal response containing RECENT and an actual automatic compaction entry with tokensBefore above the configured threshold, a valid firstKeptEntryId, preserved raw history, a full recent turn and summary in the following outbound payload. No silent truncation. Pi can dynamically reduce max_tokens; record the actual sent cap. If the remaining cap cannot support the task or no valid cut point exists, record FAIL/BLOCKED, not PASS. Manual compaction is a separate diagnostic, not evidence of automatic compaction.
4. CONTINUATION: submit 04-after.txt; require exact five values without reading files again, correct model/provider, normal stop, full recent retained input. For CLI reopen the same persisted session and test the continuation in that session. For IDE verify continuation in the actual extension and saved session; test explicit IDE reopen/resume separately if required by the final acceptance contract (mock proved IDE persistence, not IDE restart/resume).

Verify each case against expected.json and actual traces. For LONG and AGENT use actual prompt and generated tokens, request IDs, tool-result correlation, raw payload length/hash, exact markers; for COMPACTION capture actual pre-compaction usage, cut point, summary, new request, recent tail and output cap; for CONTINUATION compare session ID, exact final answer and persisted records. Retain raw evidence plus SHA256. Record request-by-request prefill/decode/wall and cache metrics and resource guard outcome from the real server. No evidence -> NOT_RUN/BLOCKED, not PASS. Use original MBIP-05 criteria without lowering thresholds. The prepared fixtures and verification protocol do not imply that all real requests will fit at their initial sizes.

## E02-P conclusion boundary

Mock: 4/4 primary + 4/4 replay, 30 requests each. No live model acceptance. CLI same-ID process resume verified; IDE actual extension bridge + continuation + full persisted history verified, not IDE process restart.
Observed negative cases: short retained tail -> no usable compaction cut point; overlarge new turn -> actual max_tokens=1. Those findings must not be hidden by fixed mock usage or by treating manual compaction as equivalent. The final pressure scenario yielded Flash 5449 CLI/5450 IDE, Inkling 4096, within configured upper caps. Do not claim the full 8192 is invariant.
Historical E01 remains BLOCKED; all prolonged live E02 cases NOT_RUN / DEFERRED. No change to Pi live settings, server profiles or inference request counters. No transition to actual E02.
