# Qwen3.6-35B-A3B UD-Q4_K_XL — Strata

Статус на 2026-11-26: техническая совместимость API/Pi подтверждена (MBIP-02/03), роль engineering executor не установлена.

Источник: unsloth/Qwen3.6-35B-A3B-MTP-GGUF @ 5bc3e238d916f48a861bac2f8a1990a0e9b7e98d; Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf, 22853663008 B, SHA-256 55983c5a75a1ab969824077b3bb3de4146e82a9234072b48ad4e8f92ad3fe9f1. Архитектура qwen35moe, MTP в GGUF; Strata 0.2.22 / engine 0.1.69 CUDA13.

Pi provider ailab-strata, model qwen3.6-35b-a3b-ud-q4_k_xl, configured contextWindow=32768, maxTokens=8192, text-only. Принят короткий ответ с low, reasoning, SSE, локальный read и продолжение после tool result. Верх окна не испытан. Не считать полным повтором Q6/Q27 acceptance. Не использовать как default Q6 без отдельного решения.

См. [runbook 55](../Сборка/55_Strata_и_переключение_backend.md), [результаты](../Этапы/2026-11-26_MBIP/Результаты.md).
