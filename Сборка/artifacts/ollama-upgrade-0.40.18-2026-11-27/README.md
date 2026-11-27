# Ollama 0.40.18 — обновление и короткая функциональная приёмка

27.11.2026, 18:18–18:30 EET. По запросу владельца обновлена установленная 0.35.1. Официальный latest stable GitHub API: v0.40.18, published 2026-11-24T04:18:13Z, prerelease=false.
- Release: https://github.com/ollama/ollama/releases/tag/v0.40.18
- Linux amd64 archive 1648243083 bytes; SHA256 b82649006cb5b54ed1237fa2d1a26a7f939a4fd03150033759acbff7ff315adf; проверены полная загрузка, SHA256, zstd -t и структура.
- Установка пользователем через sudo, с lock контроллера и проверками неактивности Ollama/Gateway/RAG. Strata PID 76927 не изменился при установке. Сохранён прежний bin/lib/controller: /var/backups/ailab/ollama-0.35.1-20261127T162235Z. Файлы моделей не заменялись.
- Обе точные version gates в live mbip-backend изменены с 0.35.1 на 0.40.18, остальные guards и sudoers не изменялись. Существующий Q6 wrapper перенаправлен на новый ELF после проверки наличия его CLI/env интерфейсов; Q6 inference на новом runner NOT_RUN.
- Дефект установки: umask 077 при создании корня lib/ollama дал 0700. Владелец исправил chmod 755 до запуска службы. Проверка каталогов/чтения, symlink targets и runner --help PASS. Не использовать неизменённый первоначальный installer для новой установки.
- Live native /model Inkling → Q27 PASS, /lab-status ID совпали, /api/version 0.40.18. Gateway /health OK, шесть тегов сохранены, RAG service active; полноценный RAG запрос NOT_RUN. Boot policy Ollama неизменна.
- В 18:28 три POST /v1/chat/completions HTTP 200, tool-read/analyze calculator.cjs по отчёту владельца PASS; файлы original/test сохранили baseline SHA256, calculator.cjs сохранён в состоянии предыдущего исправления. /api/ps: digest 9842917e7505f86e85be81940a3aef0244fba14b86034f3a2087ed4e84793fa2, size=size_vram=22088515583, context_length=262144, runner llamacpp. Log: 66/66 layers GPU, CUDA0 model buffer 10827.36 MiB, KV 8704 MiB. GPU resident 21594 MiB used/2532 MiB free; 41 C idle; 300 W limit. First prefill 77.71 t/s (6417 tokens), final decode 41.96 t/s (287 tokens), LCP cache reused. Not comparative benchmark. Log: no implementations specified for speculative decoding; MTP not active.
- Final state: Ollama/Gateway/RAG active, Strata inactive, preferred q27. Reverse transition on new version NOT_RUN. Long context, thermal, F07, boot/postboot remain open; no new role acceptance.

Live SHA256:
```
73af1097ab335a18600a3937b4e41f16fd29ee341978fa5b3b9ef220f3ec04cd  /usr/local/bin/ollama
283532fc035b4f5437599fdbf5e2a5a1b9e3b384dd8f8419882571462737210f  /usr/local/sbin/mbip-backend
a3262034307bf9b2d15307fba924ed0f3fa4f05ce2f39a1e5eda7b80afad26eb  /usr/local/lib/ollama/llama-server
233365c647e462fa783d479565ce0e08c81654503b8024cb607f51b696ea9a81  /usr/local/lib/ollama/llama-server.real-0.40.18
```

Rollback: first return to healthy idle Strata via standard selector, drain all clients; use the original preserved backup under root control, restoring bin/lib/controller together (not mixing old libraries with new binary). The prepared script has rollback mode for that backup; requires sudo and careful review. Do not run rollback while Ollama active. [Passport v50](../../../Паспорт_лаборатории_v50.md).
