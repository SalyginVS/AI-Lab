# Q27 — MTP activation on Ollama 0.40.18

2026-11-27, 18:33–18:38 EET. Owner requested activation. Native Modelfile settings, no runner/server code modification. Embedded GGUF metadata qwen35.nextn_predict_layers=1; Ollama 0.40.18 opts.DraftNumPredict must be explicitly positive for embedded MTP. [Pinned upstream implementation](https://github.com/ollama/ollama/blob/v0.40.18/llm/llama_server.go).

## Installed delta

- Working tag: `qwen3.8-27b-gsq-rco:iq3s-mtp-262k`, digest `b4d232e15f4116f18f1897bcf2a82710e7fd8fbef1eae16f1c2ae638016affa0`. Identical GGUF blob sha256-58fd826723939933dc86f45b7fe04545cbc2de1c70f6fe2cdd3858c87a98c12f, renderer qwen3.8, parser qwen3.5, context 262144, target KV Q8_0. draft_num_predict=2, num_batch=256. New manifest; no new weights.
- Backup tag: `qwen3.8-27b-gsq-rco:iq3s-mtp-262k-no-draft-backup-20261127`, original digest `9842917e7505f86e85be81940a3aef0244fba14b86034f3a2087ed4e84793fa2`. Candidate duplicate removed; seven tags remain, one extra backup. Pi still exposes exactly three working model choices.
- Lenovo ailab-mode inventory guard pinned to full new digest; previous helper backed up as ~/.local/bin/ailab-mode.before-q27-mtp-20261127. Exact deployed helper snapshot [ailab-mode](ailab-mode); SHA256 5d323c22d7fc69614519613b43c5f0038b9ea9a4460bf8e8a72b59ff3dc7946b. No loosening of inventory/endpoint checks. ailab-mode current, ailab-pi q27 --check PASS.
- Same server backend controller, service configuration, Ollama 0.40.18, 300 W limit, boot policy. No changes to other model profiles.

## Evidence

Identical 41-token Fibonacci request, temperature 0, seed 42, max 96 generated tokens, think=false, identical 66-token completion. Baseline already resident, candidate cold start; timings from API eval_duration. Not a statistically controlled throughput benchmark or long-context qualification.

| Profile | GPU layers | Decode tokens/s | Prefill duration | Result |
|---|---:|---:|---:|---|
| MTP off, batch 512 | 66/66 | 45.10 | 136.779 ms | baseline |
| MTP 2, batch 512 | 63/66 | 6.57 | 12017.826 ms | rejected |
| MTP 2, batch 256 | 66/66 | 84.48 | 580.117 ms | selected |

Runner default fit target 1024 MiB: batch 512 projected 23044 MiB vs free 23859 MiB, 209 MiB deficit; batch 256 projected 22704 MiB. No forced offload, reserve reduction, or thermal guard bypass. Candidate draft accepted 43/46 = 93.48%; actual tool round trips on promoted working tag passed native /api/chat and /v1/chat/completions, both including tool result ALPHA-42; logs confirmed draft-mtp and 20/22 cumulative accepted drafts in each round trip. After deleting duplicate alias runner was unloaded; final OpenAI-compatible test reloaded canonical tag. 18:37:54 final resident: 66/66 layers GPU, API context_length 262144, 23244 MiB used/882 MiB free, 48 C idle, short test sampled peak 58 C, limit 300 W, no observed thermal slowdown. Memory figures from nvidia-smi, not unreliable /api/ps allocation totals for speculative runner.

Raw local server evidence ~/ollama-mtp-20261127/ (original.Modelfile, original.tags.json, baseline.json, draft2-batch512.json, draft2-batch256.json, working-tool-call.json, working-tool-result.json, openai-tool-call.json, openai-tool-result.json).

## Limitations and rollback

Short native and OpenAI-compatible tool workflow PASS; subsequent live Pi user workflow also PASS in bounded scope (see addendum below). Long input prefill effect of batch 256, sustained decode speed, full 262144 live context, thermal G0, F07, postboot, reverse backend transition after Ollama upgrade not accepted. The observed ~87% decode gain is for one 66-token completion; not a promised universal speedup. MTP is enabled persistently in manifest.

Rollback only when no requests are running: stop working tag, verify /api/ps empty and GPU released; copy the backup tag to working tag (ollama cp), restore prior Lenovo ailab-mode pin/helper together, verify old digest, /api/tags equality and ailab-mode current. Do not delete backup. [Passport v51](../../../Паспорт_лаборатории_v51.md).

## Addendum — live VS Code / Pi, 18:39–18:42 EET

Owner ran practical statistics module assignment in existing isolated fixture. Created statistics.cjs and statistics.test.cjs, four functions, 23 tests. Independent file review and node --test statistics.test.cjs calculator.test.cjs: 25/25 PASS; existing calculator hashes match, remaining fixture files retain prior mtimes. Additional checks of all four functions on empty/invalid/sparse inputs and frozen ordinary arrays PASS. Numerical limitation: repeated Number.MAX_VALUE gives Infinity for mean, median and variance, though mathematically mean/median should equal MAX_VALUE and variance zero. Not a production numerical library acceptance; no source correction requested or made.

Server journal 16:40:02–16:41:27 UTC: six HTTP 200 completions for this task; no truncation; eval counts 146,72,3799,1065,51,1011; total 6144 tokens / 84.88847 s = 72.38 t/s weighted decode. Per-request runner speeds 70.16,74.84,72.37,80.30,76.02,65.23 t/s. Draft acceptance 3779/4724 (~80.0%), excluding earlier probes. Final context 14065 tokens in slot, configured 262144. GPU 23248 MiB used / 878 MiB free in post-task snapshot. This confirms live Pi workflow with MTP; no matched no-MTP run of this agent task, long-context or thermal qualification.
