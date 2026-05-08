---
tags: [грабли, vllm, ollama, gpu, vram, continue, mtp]
дата: 2026-05-08
статус: active
---

# 082 — vLLM MTP 128K vs Ollama VRAM contention

## Симптом

После запуска vLLM Qwen3.6 27B MTP 128K старые Ollama-модели в Continue могут падать с ошибкой:

```text
502 Ollama internal error (HTTP 500): model failed to load
```

или:

```text
model failed to load, this may be due to resource limitations
```

## Причина

vLLM MTP 128K service держит значительную часть ресурсов RTX 3090 и RAM/offload path:

```text
vllm-qwen36-mtp.service
--max-model-len 131072
--cpu-offload-gb 12
--max-num-seqs 1
```

Ollama heavy models пытаются загрузиться в ту же RTX 3090 24GB VRAM.

Даже если vLLM не генерирует токены, его service держит runtime/model/KV/offload resources.

## Быстрая диагностика

На сервере `llm`:

```bash
systemctl status vllm-qwen36-mtp.service --no-pager -l
nvidia-smi
ollama ps
curl -s http://127.0.0.1:8000/health | python3 -m json.tool | head -80
```

## Решение

Перед работой с Ollama heavy models:

```bash
sudo systemctl stop vllm-qwen36-mtp.service
sudo systemctl restart ollama
```

Перед работой с vLLM MTP 128K:

```bash
sudo systemctl restart ollama
sudo systemctl start vllm-qwen36-mtp.service
```

## Операционный принцип

На одной RTX 3090:

```text
Ollama heavy lane
и
vLLM MTP 128K lane
```

считаются взаимоисключающими heavy lanes.

Нужен explicit lane switch.

## Проверка после возврата в Ollama default lane

Ожидаемо:

```text
GPU memory около 1 MiB / 24576 MiB
ollama ps пустой или без heavy loaded models
gateway /health = ok
Continue smoke = PASS
```

## Проверка после включения vLLM MTP 128K

Ожидаемо:

```text
/v1/models на 127.0.0.1:8027 показывает max_model_len = 131072
gateway smoke через model qwen3.6-27b-lorbus-mtp-triton-ctx4k = PASS
Continue profile использует historical routed model id
```
