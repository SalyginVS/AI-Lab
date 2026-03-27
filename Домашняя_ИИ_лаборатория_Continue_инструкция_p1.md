---
title: "Домашняя ИИ лаборатория с нуля"
subtitle: "От чистого сервера до AI-ассистента в IDE"
author: "На основе проекта Lab RTX3090 (Этапы 1–7D)"
date: "Версия 1.0 — 2026-03-20"
---

# Домашняя ИИ лаборатория с нуля: от чистого сервера до AI-ассистента в IDE

**Версия документа:** 1.0  
**Дата:** 2026-03-20  
**Основано на:** Этапы 1–7D проекта Lab RTX3090

---

# Часть 0 — Что мы строим

## 0.1. Цель и результат

На выходе вы получите полностью локальную систему AI-ассистента для разработки:

- **Сервер** с GPU, на котором крутятся LLM (Large Language Model — большие языковые модели) без облачных зависимостей.
- **HTTP-шлюз**, совместимый с OpenAI API, — единая точка входа для всех клиентов.
- **IDE-интеграция** (VS Code + Continue.dev) с чатом, автодополнением кода, агентным режимом, контекстом репозитория и slash-командами.
- **13 моделей** на сервере для разных задач: от быстрого автодополнения до глубокого reasoning и vision.

Все данные остаются на вашем сервере. Никакие запросы не уходят в облако. Вы контролируете каждый компонент.

## 0.2. Архитектурная схема

```
┌─────────────────────────────────────────────────────────────┐
│  Windows 11 — VS Code                                      │
│                                                             │
│  ┌─ Continue.dev v1.2.17 ─────────────────────────────────┐ │
│  │                                                         │ │
│  │  Chat / Edit / Agent ──┐                                │ │
│  │  Model list ───────────┤── gateway.py :8000 ──► Ollama  │ │
│  │  Vision ───────────────┘   /v1/chat/completions  :11434 │ │
│  │                            /v1/models                   │ │
│  │  Autocomplete (FIM) ─────► Ollama :11434 напрямую       │ │
│  │                            /api/generate                │ │
│  │  Embeddings ─────────────► transformers.js              │ │
│  │                            (внутри VS Code)             │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─ Copilot BYOK (опционально) ──────────────────────────┐ │
│  │  Plain chat ────────────► gateway.py :8000 или         │ │
│  │                           Ollama :11434 напрямую       │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                     Локальная сеть
                            │
┌─────────────────────────────────────────────────────────────┐
│  Ubuntu Server 22.04 (192.168.0.128)                       │
│                                                             │
│  ┌─ gateway.py (FastAPI) ─── порт 8000 ─────────────────┐  │
│  │  • Reasoning policy (effort → think)                  │  │
│  │  • Настоящий стриминг (TTFT 0.12s)                    │  │
│  │  • Валидация, OOM-детекция, retry                     │  │
│  │  • OpenAI SDK совместимость                           │  │
│  │  • Tool calls проброс (Ollama → OpenAI формат)        │  │
│  │  • Bearer auth (опционально)                          │  │
│  └───────────────────────────────────────────────────────┘  │
│                            │                                │
│  ┌─ Ollama 0.18.0 ──────── порт 11434 ──────────────────┐  │
│  │  13 моделей (chat, code, agent, vision, FIM, embed)   │  │
│  │  Flash Attention, KV cache q8_0                       │  │
│  │  MAX_LOADED_MODELS=2                                  │  │
│  └───────────────────────────────────────────────────────┘  │
│                            │                                │
│  ┌─ NVIDIA RTX 3090 ────── 24 ГБ VRAM ──────────────────┐  │
│  │  + 62 ГБ RAM (CPU offload) = ~86 ГБ суммарно         │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

Обратите внимание на два пути подключения:

- **Chat / Edit / Agent / Vision** идут через шлюз `gateway.py`. Шлюз добавляет reasoning policy, валидацию, обработку ошибок, конвертацию tool_calls из формата Ollama в формат OpenAI.
- **Autocomplete (FIM)** идёт напрямую в Ollama, минуя шлюз. Причина: FIM (Fill-in-the-Middle — заполнение середины кода) использует специальный эндпоинт `/api/generate` с токенами `<|fim_prefix|>`, `<|fim_suffix|>`, `<|fim_middle|>`, который шлюз не обрабатывает.
- **Embeddings** (векторные представления кода для поиска) работают внутри VS Code через `transformers.js`, не нагружая ни шлюз, ни Ollama.

## 0.3. Стратегия Depth over Speed

Ключевое архитектурное решение: **глубина контекста важнее скорости генерации**.

Что это значит на практике:

- **Системная RAM (62 ГБ) используется как расширение VRAM (24 ГБ)**. Когда модель не помещается целиком в видеопамять, часть слоёв переносится в оперативную память (CPU offload). Генерация замедляется (часть вычислений идёт на CPU), но модель работает с полным контекстом.
- **Суммарная доступная память — ~86 ГБ**. Это позволяет запускать модели на 30–35B параметров с контекстом 8192–32768 токенов, что невозможно в 24 ГБ VRAM без offload.
- **Дефолтное окно контекста — 8192 токенов** (настраивается до 32768 через API). Для сравнения: стандартный дефолт Ollama — 2048.
- **Скорость генерации — 5–15 tok/s для 30B-моделей** (вместо 20–30 tok/s при полном размещении в VRAM). Для задач IDE-ассистента это приемлемо: при чтении кода человек не успевает за 5 tok/s.

Следствия для настройки:

| Параметр | Значение | Зачем |
|---|---|---|
| `OLLAMA_FLASH_ATTENTION=1` | Flash Attention | Снижает расход VRAM на механизм внимания |
| `OLLAMA_KV_CACHE_TYPE=q8_0` | Квантизованный KV-кэш | Вдвое сжимает кэш внимания (ключи и значения) |
| `OLLAMA_MAX_LOADED_MODELS=2` | Две модели одновременно | FIM-модель для автодополнения + chat/agent модель |
| `OLLAMA_NUM_PARALLEL=1` | Один запрос одновременно | При NUM_PARALLEL>1 Ollama создаёт несколько KV-кэшей, удваивая расход памяти |
| `GGML_CUDA_NO_GRAPHS=1` | Без CUDA graph capture | Предотвращает SIGABRT-краш при быстрой смене запросов (Agent mode) |
| `DEFAULT_NUM_CTX=8192` | Дефолтный контекст | Баланс между глубиной и потреблением памяти |

## 0.4. Требования к железу

### Минимальные (работоспособная система)

| Компонент | Требование | Обоснование |
|---|---|---|
| GPU | NVIDIA с ≥ 12 ГБ VRAM (RTX 3060 12GB, RTX 4070) | Модели 7–14B помещаются целиком |
| RAM | ≥ 32 ГБ | CPU offload для моделей крупнее VRAM |
| CPU | 6+ ядер, x86_64 | CPU offload при генерации |
| SSD | ≥ 200 ГБ свободно | Модели занимают 5–23 ГБ каждая |
| ОС | Ubuntu 22.04+ Server (headless) | Ollama + NVIDIA driver |

При 12 ГБ VRAM + 32 ГБ RAM стратегия Depth over Speed всё ещё работает, но набор моделей будет скромнее: 7–14B для chat, 1.5B для FIM.

### Рекомендуемые (наша конфигурация)

| Компонент | Значение |
|---|---|
| GPU | NVIDIA RTX 3090 — 24 ГБ GDDR6X |
| RAM | 62 ГБ DDR4 |
| CPU | Intel Core i9-9900KF (8C/16T) |
| SSD | 1 ТБ (159 ГБ занято, 731 ГБ свободно) |
| ОС | Ubuntu Server 22.04 (headless) |
| Сеть | Локальная сеть, статический или DHCP IP |
| Драйвер | NVIDIA 590.48.01, CUDA 13.1 |

С 24 ГБ VRAM + 62 ГБ RAM можно запускать модели 30–35B с контекстом 8192 и одновременно держать FIM-модель 7B в памяти.

## 0.5. Что адаптировать под своё железо

При прохождении инструкции замените следующие значения:

| Параметр | Наше значение | Где используется | Что подставить |
|---|---|---|---|
| IP сервера | `192.168.0.128` | gateway.py конфиг, config.yaml Continue, curl-тесты | IP вашего сервера |
| VRAM | 24 ГБ | Выбор моделей, `num_ctx` | Если < 16 ГБ — убрать 30B+ модели |
| RAM | 62 ГБ | `MAX_LOADED_MODELS` | Если < 48 ГБ — поставить `MAX_LOADED_MODELS=1` |
| SSD | 1 ТБ | Количество моделей | Каждая модель 1–23 ГБ; считайте запас |
| GPU модель | RTX 3090 | `GGML_CUDA_NO_GRAPHS` | Для RTX 40xx/50xx может быть не нужен; тестируйте без него |

Если у вас AMD GPU — Ollama поддерживает ROCm, но настройка VRAM offload отличается. Эта инструкция написана для NVIDIA.

# Часть 1 — Сервер: Ubuntu + GPU + Ollama

## 1.1. Ubuntu Server (headless)

Установка Ubuntu Server выходит за рамки этой инструкции. Используйте официальную документацию: https://ubuntu.com/server/docs/installation

После установки убедитесь:

```bash
# ОС и ядро
lsb_release -a          # Ubuntu 22.04+
uname -r                # 5.15+ (для NVIDIA driver)

# Сеть
ip addr show            # Запомните IP-адрес сервера
ping -c 3 8.8.8.8       # Интернет доступен (нужен для установки пакетов и моделей)

# SSH
ssh user@<IP_СЕРВЕРА>   # Доступ с клиентской машины
```

⚠ **ГРАБЛИ:** Убедитесь, что SSH-доступ работает с вашей рабочей машины (Windows/Mac). Вся дальнейшая работа с сервером — через SSH-терминал.

## 1.2. NVIDIA-стек: драйвер + CUDA

### Установка драйвера

```bash
# Проверяем, видит ли система GPU
lspci | grep -i nvidia
# Ожидаем строку вида: NVIDIA Corporation GA102 [GeForce RTX 3090]

# Устанавливаем драйвер (рекомендуемый способ для Ubuntu)
sudo apt update
sudo apt install -y nvidia-driver-535
# Номер версии может отличаться. Для RTX 30xx/40xx: 535+. Для RTX 50xx: 570+.
# Актуальную версию проверяйте: apt list nvidia-driver-*

sudo reboot
```

### Проверка после перезагрузки

```bash
nvidia-smi
```

Ожидаемый вывод (ключевые поля):

```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 590.48.01    Driver Version: 590.48.01    CUDA Version: 13.1     |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
|   0  NVIDIA GeForce RTX 3090  | On           | Off                          |
+-------------------------------+----------------------+----------------------+
| GPU-Util      Memory-Usage                                                  |
|   0%          400MiB / 24576MiB                                             |
+-----------------------------------------------------------------------------+
```

Что проверять:
- **Driver Version** — число отображается (не `N/A`)
- **CUDA Version** — есть
- **Memory-Usage** — VRAM видна (24576 MiB для RTX 3090)
- **GPU-Util** — 0% в покое (если >0% при простое — что-то уже использует GPU)

⚠ **ГРАБЛИ:** Если `nvidia-smi` возвращает ошибку `NVIDIA-SMI has failed...` — драйвер не установился. Частые причины: Secure Boot включён в BIOS (нужно отключить или подписать модуль), конфликт с nouveau-драйвером (добавить `blacklist nouveau` в `/etc/modprobe.d/`).

## 1.3. Ollama: установка и настройка

### Установка

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Скрипт установит Ollama и создаст systemd-сервис `ollama.service`.

### Проверка базовой установки

```bash
systemctl status ollama
# Ожидаем: active (running)

ollama --version
# Ожидаем: ollama version 0.18.0 или выше

curl -s http://localhost:11434/api/tags | python3 -m json.tool
# Ожидаем: {"models": []} (пока пусто)
```

### Systemd override — оптимизация памяти

Создаём файл переопределений для Ollama:

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/override.conf > /dev/null << 'EOF'
[Service]
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
Environment="OLLAMA_MAX_LOADED_MODELS=2"
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="CUDA_VISIBLE_DEVICES=0"
Environment="GGML_CUDA_NO_GRAPHS=1"
EOF
```

Применяем:

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
systemctl status ollama
# Ожидаем: active (running)
```

**Что делает каждая строка:**

| Переменная | Значение | Назначение |
|---|---|---|
| `OLLAMA_FLASH_ATTENTION=1` | Включить | Flash Attention — алгоритм, снижающий расход VRAM на механизм внимания. Для моделей 30B+ экономит гигабайты |
| `OLLAMA_KV_CACHE_TYPE=q8_0` | 8-bit | KV cache (кэш ключей и значений внимания) квантизуется до 8 бит вместо 16. Вдвое меньше памяти на кэш |
| `OLLAMA_MAX_LOADED_MODELS=2` | 2 модели | Две модели одновременно в памяти: одна для chat/agent, вторая для FIM-автодополнения. При < 48 ГБ RAM поставьте `1` |
| `OLLAMA_HOST=0.0.0.0:11434` | Все интерфейсы | По умолчанию Ollama слушает только `127.0.0.1`. Для доступа с другой машины нужен `0.0.0.0` |
| `CUDA_VISIBLE_DEVICES=0` | GPU 0 | Если в системе несколько GPU — явно указываем, какой использовать |
| `GGML_CUDA_NO_GRAPHS=1` | Отключить | CUDA Graph Capture — оптимизация для повторяющихся вычислений. При быстрой последовательности запросов (Agent mode) вызывает SIGABRT-краш. Отключение безопасно: потеря ~5% скорости |

⚠ **ГРАБЛИ:** Параметр `OLLAMA_NUM_PARALLEL` не указан в override — значит он остаётся по умолчанию (1). Это **намеренно**: при `NUM_PARALLEL > 1` Ollama создаёт несколько KV-кэшей на одну модель, что удваивает расход памяти. Для одного пользователя `NUM_PARALLEL=1` — оптимально.

### Проверка, что override применился

```bash
# Убедиться, что Ollama слушает на 0.0.0.0
curl -s http://<IP_СЕРВЕРА>:11434/api/tags | python3 -m json.tool
# Если ответ есть — OLLAMA_HOST=0.0.0.0 работает
# Если "Connection refused" — override не применился, перепроверьте daemon-reload + restart
```

## 1.4. Скачивание моделей

Модели скачиваются из Ollama Hub. Каждая модель — квантизованная версия (Q4_K_M или подобная), оптимизированная для inference на потребительских GPU.

### Минимальный набор (3 модели, ~27 ГБ на диске)

Этого достаточно для рабочей системы:

```bash
ollama pull qwen3-coder:30b          # 18 ГБ — Agent + Code + Edit (основная рабочая модель)
ollama pull qwen2.5-coder:7b         # 4.7 ГБ — FIM-автодополнение (резидентная)
ollama pull qwen3.5:9b               # 6.6 ГБ — Быстрый повседневный чат + vision
```

### Полный набор (13 моделей, ~137 ГБ на диске)

```bash
# === ОСНОВНЫЕ (обязательные) ===
ollama pull qwen3-coder:30b          # 18 ГБ — Agent, Code, Edit. Надёжный function calling
ollama pull qwen2.5-coder:7b         # 4.7 ГБ — FIM autocomplete, основная
ollama pull qwen3.5:9b               # 6.6 ГБ — Повседневный чат, vision, tools (с оговорками)

# === AGENT (второй вариант) ===
ollama pull glm-4.7-flash            # 19 ГБ — MoE agentic coding (30B/3B активных). Tools работают

# === REASONING (глубокий анализ) ===
ollama pull deepseek-r1:32b          # 19 ГБ — Math/reasoning, глубокий анализ
ollama pull deepseek-r1:14b          # 9.0 ГБ — Math/reasoning, компактная версия

# === CHAT (резерв) ===
ollama pull qwen3:30b                # 18 ГБ — General chat
ollama pull qwen3:14b                # 9.3 ГБ — Chat резерв

# === EXPERIMENTAL ===
ollama pull qwen3.5:35b              # 23 ГБ — MoE reasoning (tools СЛОМАНЫ в Ollama, только chat)

# === СПЕЦИАЛИЗИРОВАННЫЕ ===
ollama pull qwen2.5-coder:1.5b       # 986 МБ — FIM fallback (если 7b мешает по памяти)
ollama pull deepseek-coder-v2:16b    # 8.9 ГБ — Code legacy
ollama pull qwen3-vl:8b              # 6.1 ГБ — Vision (анализ изображений)
ollama pull qwen3-embedding           # 4.7 ГБ — Embeddings (резерв для будущего RAG)
```

⚠ **ГРАБЛИ:** `qwen3.5:35b` — это MoE-модель (Mixture of Experts — архитектура, где активируется только часть параметров при каждом запросе). Она занимает 23 ГБ на диске, но при inference использует ~10 ГБ активных параметров. Однако **function calling (tool use) у неё сломан в Ollama** на март 2026 (issues #14493, #14745). Для Agent mode используйте `qwen3-coder:30b` или `glm-4.7-flash`.

### Роли моделей

| Модель | Размер | Роль в IDE | Почему именно она |
|---|---|---|---|
| `qwen3-coder:30b` | 18 ГБ | **Agent + Code + Edit** | Единственная 30B-модель с надёжным function calling в Ollama |
| `qwen2.5-coder:7b` | 4.7 ГБ | **FIM autocomplete** | Обучена на FIM-токенах, быстрая, резидентная в памяти |
| `qwen3.5:9b` | 6.6 ГБ | **Повседневный чат** | Dense-архитектура (не MoE), vision, быстрые ответы |
| `glm-4.7-flash` | 19 ГБ | **Agent альтернатива** | MoE (30B/3B), tools работают, MIT License |
| `deepseek-r1:32b` | 19 ГБ | **Reasoning** | Глубокий chain-of-thought для математики и анализа |
| `qwen3-vl:8b` | 6.1 ГБ | **Vision** | Анализ скриншотов, диаграмм, UI-макетов |
| `qwen2.5-coder:1.5b` | 986 МБ | **FIM fallback** | Если 7b-модель мешает по памяти |
| `qwen3.5:35b` | 23 ГБ | **Experimental** | Мощный reasoning, но tools сломаны — только chat |

## 1.5. Проверка

### Базовая проверка Ollama

```bash
# Список моделей
ollama list
# Ожидаем: таблицу с моделями, размерами, датами

# Количество моделей
curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; print(len(json.load(sys.stdin)['models']))"
# Ожидаем: 13 (или сколько скачали)
```

### Chat-тест (проверка inference)

```bash
# Быстрый тест на маленькой модели
curl -s http://localhost:11434/api/chat -d '{
  "model": "qwen3.5:9b",
  "messages": [{"role": "user", "content": "Reply with exactly: HELLO WORLD"}],
  "stream": false,
  "options": {"temperature": 0, "num_predict": 10}
}' | python3 -c "import sys,json; print(json.load(sys.stdin)['message']['content'])"
# Ожидаем: HELLO WORLD
```

⚠ **ГРАБЛИ:** Первый запрос к модели — холодный старт: Ollama загружает веса модели с диска в VRAM/RAM. Для 30B-модели это 8–30 секунд. Последующие запросы к той же модели — быстрые (модель уже в памяти).

### Проверка с удалённой машины

```bash
# С Windows-машины (PowerShell)
curl -s http://192.168.0.128:11434/api/tags | ConvertFrom-Json | Select-Object -ExpandProperty models | Format-Table name, size
```

Если получаете `Connection refused` — перепроверьте `OLLAMA_HOST=0.0.0.0:11434` в override и файрвол:

```bash
# На сервере: проверить, что порт слушается
sudo ss -tlnp | grep 11434
# Ожидаем: 0.0.0.0:11434 ... ollama

# Если файрвол включён
sudo ufw allow 11434/tcp
sudo ufw allow 8000/tcp     # Для будущего шлюза
```

# Часть 2 — Шлюз gateway.py

## 2.1. Зачем шлюз между Ollama и клиентами

Ollama предоставляет собственный API (`/api/chat`, `/api/generate`), а также OpenAI-совместимый эндпоинт (`/v1/chat/completions`). Почему бы не использовать его напрямую? Пять причин, каждая из которых проверена на практике:

**1. Reasoning policy.** Модели с thinking-способностями (deepseek-r1, qwen3.5) генерируют рассуждения (`thinking`) вместе с ответом. Без шлюза thinking утекает в `content` — клиент получает внутренние рассуждения модели вместо финального ответа. Шлюз разделяет `content` и `reasoning_content`, управляет включением/отключением thinking через параметр `reasoning_effort`.

**2. Настоящий стриминг.** Ollama OpenAI-эндпоинт отдаёт данные корректно, но наш шлюз добавляет SSE-совместимый (Server-Sent Events — протокол потоковой передачи данных поверх HTTP) формат с правильным протоколом: первый чанк с `role`, финальный с `usage`, маркер `[DONE]`. TTFT (Time To First Token — время до первого токена) = 0.12 сек.

**3. Tool calls конвертация.** Ollama возвращает `tool_calls` в своём формате (arguments как dict, index внутри function). IDE-клиенты (Continue.dev, Copilot) ожидают формат OpenAI (arguments как JSON-строка, index на верхнем уровне). Без конвертации Agent mode не работает.

**4. Обработка ошибок.** Ollama при ошибке возвращает произвольный формат. Шлюз классифицирует ошибки (OOM → 503, модель не найдена → 404, холодный старт → retry + 503) и отдаёт их в формате OpenAI API (`{"error": {"message":..., "type":..., "code":...}}`).

**5. Единая точка входа.** Один URL (`http://server:8000/v1`) для всех клиентов. Опциональная Bearer-аутентификация. Логирование каждого запроса (model, stream, effort) в systemd journal.

## 2.2. Деплой: Python venv, зависимости, systemd

### Подготовка окружения

```bash
# На сервере
mkdir -p ~/llm-gateway
cd ~/llm-gateway

# Создаём виртуальное окружение Python
python3 -m venv venv
source venv/bin/activate

# Устанавливаем зависимости
pip install fastapi uvicorn httpx pydantic
```

### Размещение gateway.py

Полный код gateway.py приведён в **Приложении A** (993 строки). Перенесите его на сервер:

```bash
# Вариант 1: scp с Windows (из PowerShell)
scp gateway.py user@192.168.0.128:~/llm-gateway/gateway.py

# Вариант 2: создать файл на сервере
nano ~/llm-gateway/gateway.py
# Вставить содержимое из Приложения A
```

⚠ **ГРАБЛИ:** При редактировании Python-файлов через `nano` или `sed` на сервере легко сломать отступы (смешать табы с пробелами). Рекомендуемый подход: редактировать файл локально на клиенте, затем копировать через `scp`. Это проверенный паттерн, который сэкономит часы отладки.

### Проверка запуска вручную

```bash
cd ~/llm-gateway
source venv/bin/activate
uvicorn gateway:app --host 0.0.0.0 --port 8000
```

В другом терминале:

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

Ожидаемый ответ:
```json
{
    "gateway": "ok",
    "version": "0.7.0",
    "ollama": "ok",
    "models_count": 13,
    "auth_enabled": false,
    "timestamp": 1710921234
}
```

Если `"ollama": "error: ..."` — Ollama не запущена или недоступна.

### Systemd unit для автозапуска

```bash
sudo tee /etc/systemd/system/llm-gateway.service > /dev/null << 'EOF'
[Unit]
Description=LLM Gateway (OpenAI-compatible proxy for Ollama)
After=network.target ollama.service
Requires=ollama.service

[Service]
Type=simple
User=<ВАШ_ПОЛЬЗОВАТЕЛЬ>
WorkingDirectory=/home/<ВАШ_ПОЛЬЗОВАТЕЛЬ>/llm-gateway
ExecStart=/home/<ВАШ_ПОЛЬЗОВАТЕЛЬ>/llm-gateway/venv/bin/uvicorn gateway:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
EOF
```

Замените `<ВАШ_ПОЛЬЗОВАТЕЛЬ>` на ваш username на сервере.

Для включения аутентификации добавьте строку в секцию `[Service]`:
```ini
Environment="LLM_GATEWAY_API_KEY=ваш-секретный-ключ"
```

Активация:

```bash
sudo systemctl daemon-reload
sudo systemctl enable llm-gateway
sudo systemctl start llm-gateway
systemctl status llm-gateway
# Ожидаем: active (running)
```

Проверка логов:

```bash
sudo journalctl -u llm-gateway -f
# Ожидаем: строки вида "INFO: Uvicorn running on http://0.0.0.0:8000"
```

## 2.3. Конфигурация шлюза

Шлюз настраивается через константы в начале `gateway.py` и переменные окружения.

### Константы (в коде)

| Константа | Значение | Назначение |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Адрес Ollama. Менять если Ollama на другом хосте |
| `HTTPX_TIMEOUT` | 600 сек | Таймаут HTTP-клиента. 10 минут — для тяжёлых моделей |
| `DEFAULT_NUM_CTX` | 8192 | Дефолтный контекст. Клиент может запросить до MAX_NUM_CTX |
| `MAX_NUM_CTX` | 32768 | Потолок контекста. Защита от OOM |
| `RETRY_MAX_ATTEMPTS` | 3 | Попытки при холодном старте (1 + 2 retry) |
| `RETRY_BACKOFF_BASE` | 2.0 сек | Экспоненциальный backoff (2с → 4с) |

### Переменные окружения

| Переменная | Обязательность | Описание |
|---|---|---|
| `LLM_GATEWAY_API_KEY` | Нет | Bearer-токен для аутентификации. Если не задана — доступ открыт |

### Логирование

Шлюз пишет логи через Python `logging` в logger `uvicorn.error`, который uvicorn направляет в stdout → systemd journal.

| Уровень | Что логируется |
|---|---|
| INFO | Каждый запрос: request_id, model, stream, effort |
| DEBUG | Полный dict `options`, отправленный в Ollama |
| WARNING | Модель не найдена; одновременный repeat_penalty + frequency/presence_penalty |
| ERROR | OOM, Ollama недоступна, неожиданные исключения |

Просмотр логов:

```bash
# Все логи шлюза
sudo journalctl -u llm-gateway --since "1 hour ago"

# Только запросы (фильтр по REQ)
sudo journalctl -u llm-gateway | grep REQ

# Включить DEBUG-уровень (в systemd unit):
# ExecStart=... --log-level debug
```

## 2.4. Эндпоинты и API-контракт

### POST /v1/chat/completions

Основной эндпоинт. Полностью совместим с OpenAI Chat Completions API.

**Стандартные параметры OpenAI (принимаются и пробрасываются):**

| Параметр | Тип | Диапазон | Маппинг в Ollama |
|---|---|---|---|
| `model` | string | — | `model` (top-level) |
| `messages` | array | — | `messages` (конвертация multimodal) |
| `stream` | bool | — | `stream` |
| `temperature` | float | 0.0–2.0 | `options.temperature` |
| `top_p` | float | 0.0–1.0 | `options.top_p` |
| `max_tokens` | int | ≥ 1 | `options.num_predict` |
| `frequency_penalty` | float | -2.0…2.0 | `options.frequency_penalty` |
| `presence_penalty` | float | -2.0…2.0 | `options.presence_penalty` |
| `seed` | int | ≥ 0 | `options.seed` |
| `stop` | string/array | — | `options.stop` |
| `tools` | array | — | `tools` (top-level, не в options) |
| `tool_choice` | string/dict | — | `tool_choice` (top-level) |

**Расширенные параметры (наши добавки):**

| Параметр | Тип | Где передавать | Назначение |
|---|---|---|---|
| `reasoning_effort` | string | top-level или `extraBodyProperties` | "none"/"low"/"medium"/"high" → `think: true/false` |
| `reasoning.effort` | string | top-level (объект) | Альтернативный формат (OpenAI-стиль) |
| `num_ctx` | int | top-level или `extraBodyProperties` | Размер контекстного окна (1–32768) |
| `num_gpu` | int | top-level | Количество слоёв на GPU (для ручного CPU offload) |
| `num_batch` | int | top-level | Размер batch для prompt evaluation |
| `repeat_penalty` | float | top-level | Ollama-native мультипликативный штраф (0.0–2.0) |

**Неизвестные параметры** (logprobs, logit_bias, n, user, response_format и пр.) — **молча игнорируются** (`extra="ignore"` в Pydantic). Это обеспечивает совместимость с OpenAI SDK, который передаёт дополнительные поля.

### GET /v1/models

Список моделей в формате OpenAI. Обёртка над Ollama `/api/tags`.

```json
{
  "object": "list",
  "data": [
    {
      "id": "qwen3-coder:30b",
      "object": "model",
      "created": 1710700000,
      "owned_by": "ollama"
    }
  ]
}
```

### GET /health

Состояние шлюза. Не требует аутентификации.

```json
{
  "gateway": "ok",
  "version": "0.7.0",
  "ollama": "ok",
  "models_count": 13,
  "auth_enabled": false,
  "timestamp": 1710921234
}
```

## 2.5. Проверка: curl-тесты

Выполните все тесты с сервера (или с клиентской машины, заменив `localhost` на IP сервера).

### Тест 1 — Health check

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
# Проверить: gateway=ok, ollama=ok, models_count>0
```

### Тест 2 — Список моделей

```bash
curl -s http://localhost:8000/v1/models | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data['data']:
    print(f\"  {m['id']}\")
print(f\"Всего: {len(data['data'])} моделей\")
"
```

### Тест 3 — Non-stream chat

```bash
curl -s http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d '{
  "model": "qwen3.5:9b",
  "messages": [{"role": "user", "content": "What is 2+2? Reply with one word."}],
  "stream": false,
  "temperature": 0,
  "reasoning_effort": "none"
}' | python3 -c "
import sys, json
r = json.load(sys.stdin)
print(f\"Content: {r['choices'][0]['message']['content']}\")
print(f\"Tokens: prompt={r['usage']['prompt_tokens']}, completion={r['usage']['completion_tokens']}\")
print(f\"system_fingerprint: {r.get('system_fingerprint')}\")
print(f\"service_tier: {r.get('service_tier')}\")
"
# Проверить: Content содержит ответ, system_fingerprint=None, service_tier=None
```

### Тест 4 — Stream chat (проверка TTFT)

```bash
time curl -s http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d '{
  "model": "qwen3.5:9b",
  "messages": [{"role": "user", "content": "Count from 1 to 10."}],
  "stream": true,
  "reasoning_effort": "none"
}' | head -3
# Проверить: первые 3 строки появляются за < 1 сек
# Первая строка: data: {"choices":[{"delta":{"role":"assistant"}...}]}
```

### Тест 5 — Tool calling (Agent mode)

```bash
curl -s http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d '{
  "model": "qwen3-coder:30b",
  "messages": [{"role": "user", "content": "List files in current directory"}],
  "stream": true,
  "tools": [{"type":"function","function":{"name":"run_terminal_command","description":"Run a shell command","parameters":{"type":"object","properties":{"command":{"type":"string"}}}}}],
  "reasoning_effort": "none"
}' 2>/dev/null | grep tool_calls
# Проверить: видим delta с tool_calls, arguments как JSON-строка
```

### Тест 6 — Модель не найдена → 404

```bash
curl -s -w "\nHTTP: %{http_code}\n" http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d '{
  "model": "nonexistent-model-42",
  "messages": [{"role": "user", "content": "test"}]
}'
# Проверить: HTTP 404, {"error": {"type": "not_found_error", "code": "model_not_found"}}
```

### Тест 7 — Невалидный параметр → 422

```bash
curl -s -w "\nHTTP: %{http_code}\n" http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d '{
  "model": "qwen3.5:9b",
  "messages": [{"role": "user", "content": "test"}],
  "temperature": 5.0
}'
# Проверить: HTTP 422, {"error": {"type": "invalid_request_error", "code": "validation_error"}}
```

## 2.6. Инженерные заметки — 8 решённых проблем

При разработке шлюза (Этапы 1–6) были обнаружены и решены 8 проблем. Каждая — реальная ситуация, которая ломала работу с клиентами.

### Проблема 1 — Фейковый стриминг (Этап 6)

**Суть:** Исходный шлюз использовал `httpx.AsyncClient.post()`, который читает весь ответ Ollama в память, а потом отдаёт строки. TTFT = полному времени генерации. Для 35B-модели — минуты до первого символа.

**Решение:** Паттерн «ручной streaming mode»: `client.build_request()` → `client.send(req, stream=True)` → `resp.aiter_lines()`. HTTP-response возвращается сразу после заголовков; body читается построчно по мере генерации. TTFT упал с ~TOTAL до **0.12 сек**.

**Урок:** В httpx `client.post()` всегда буферизует тело ответа. Для стриминга нужен явный `stream=True` через `client.send()`.

### Проблема 2 — Thinking утекает в content (Этап 2)

**Суть:** Thinking-модели (deepseek-r1, qwen3.5) заполняют поле `thinking` в ответе. Исходный шлюз при пустом `content` подставлял `thinking` как `content`. Клиент получал рассуждения модели вместо ответа.

**Решение:** Функция `extract_content_and_reasoning()` разделяет content и thinking. Thinking отдаётся в отдельном поле `reasoning_content` только при `effort >= medium`. Если content пуст, а thinking есть — thinking становится content (модель решила не отвечать кратко), но уже осознанно, а не случайно.

### Проблема 3 — Маппинг HTTP-кодов (Этап 4)

**Суть:** Любая ошибка Ollama → `502 Bad Gateway`. Модель не найдена? 502. OOM? 502. Невалидный запрос? 502.

**Решение:** Функция `classify_ollama_error()` парсит тело ответа Ollama и возвращает правильный HTTP-код: 404 для `model not found`, 503 + `Retry-After` для OOM, 400 для bad request. 8 паттернов для детекции OOM (`"out of memory"`, `"cuda out of memory"`, `"failed to allocate"` и др.).

### Проблема 4 — Холодный старт (Этап 4)

**Суть:** Первый запрос к модели — Ollama загружает веса с диска. httpx получал connection error с пустым сообщением. Клиент видел: `{"detail": "Ollama connection error: "}`.

**Решение:** `ollama_post_with_retry()` — retry с экспоненциальным backoff (2с → 4с, 3 попытки). После провала — проверка: жива ли Ollama (`GET /api/tags`). Если жива — ответ `503 "Model is loading into GPU memory (cold start)"`. Если мертва — `502 "Cannot connect to Ollama"`.

### Проблема 5 — Tool calls терялись в шлюзе (Этап 7A)

**Суть:** `stream_generator()` обрабатывал только `content` и `thinking`. Поле `tool_calls` в чанках Ollama игнорировалось. Continue Agent mode получал пустой ответ.

**Решение:** `convert_ollama_tool_calls_to_openai()` конвертирует формат: `arguments` dict → JSON-строка, `index` из function на верхний уровень, добавляет `type: "function"`. Проброс в stream (`delta.tool_calls`) и non-stream (`message.tool_calls`). `finish_reason: "tool_calls"` вместо `"stop"`.

### Проблема 6 — OpenAI SDK требует system_fingerprint (Этап 5)

**Суть:** OpenAI Python SDK парсит ответы через Pydantic и падает без `system_fingerprint`. Все зрелые прокси (LiteLLM, LM Studio, vLLM) возвращают его как `null`.

**Решение:** Добавлено `"system_fingerprint": null` и `"service_tier": null` в оба формата ответа (stream и non-stream).

### Проблема 7 — Penalties игнорировались Ollama (Этап 3 + 7B)

**Суть:** Документация на Этапе 1 ошибочно утверждала, что Ollama не поддерживает `frequency_penalty` и `presence_penalty`. На самом деле — поддерживает нативно в `options`. Но до Ollama 0.17.5 был баг: Go runner'ом penalties отбрасывались.

**Решение:** Прямой проброс 1:1 (без аппроксимации через `repeat_penalty`). Обновление Ollama до 0.18.0, где баг исправлен.

**Урок:** Всегда проверяйте поведение на живом сервере, а не доверяйте документации или предыдущим выводам.

### Проблема 8 — Защищённый парсинг ошибок (после Этапа 7D)

**Суть:** При `httpx.HTTPStatusError` шлюз вызывал `e.response.json()`. Если Ollama вернула невалидный JSON (HTML, пустой ответ) — возникало вторичное исключение, маскирующее исходную причину. Клиент получал «Internal gateway error» без деталей.

**Решение:** Try/except вокруг `e.response.json()`. При неудаче — подставляется строковое описание ошибки. Результат передаётся в `classify_ollama_error()`.

# Часть 3 — Continue.dev: основной IDE-инструмент

## 3.1. Установка и первый запуск

### Установка

В VS Code:
1. Откройте Extensions (`Ctrl+Shift+X`).
2. Найдите **Continue** (издатель: Continue).
3. Установите. Текущая версия: **1.2.17**.
4. После установки в левой панели появится иконка Continue (стрелка).

### Первый запуск

При первом открытии Continue предложит настроить провайдера. **Пропустите** этот диалог — мы создадим конфигурацию вручную.

Файл конфигурации: `%USERPROFILE%\.continue\config.yaml` (Windows) или `~/.continue/config.yaml` (Linux/Mac). Если файл не существует — создайте его.

⚠ **ГРАБЛИ:** Continue 1.2.17 использует YAML-формат (schema v1). Старый формат `config.json` — устаревший. Если при запуске возникают ошибки, проверьте: не осталось ли `config.json`, который конфликтует с `config.yaml`.

## 3.2. config.yaml — полная конфигурация

Полный файл приведён в **Приложении B**. Здесь — пояснения каждой секции.

### Заголовок

```yaml
name: Lab RTX3090
version: 0.0.1
schema: v1
```

- `name` — отображаемое имя конфигурации.
- `version` — версия вашей конфигурации (не Continue). `0.0.1` и `1.0.0` — оба валидны.
- `schema: v1` — обязательный маркер YAML-формата.

### Секция context

```yaml
context:
  - provider: code
  - provider: repo-map
  - provider: file
  # ... и далее
```

Список context providers (провайдеров контекста). Подробно — в разделе 3.6.

⚠ **ГРАБЛИ:** Если вы объявляете секцию `context:`, Continue **сбрасывает** все дефолтные провайдеры. Вы увидите только то, что перечислили явно. Поэтому нужно указать все 11 провайдеров, включая те, которые работали «из коробки» (file, currentFile, open и др.).

### Секция models

Каждая модель определяется как элемент массива `models`. Ключевые поля:

```yaml
models:
  - name: qwen3-coder              # Отображаемое имя в UI (без скобок и спецсимволов!)
    provider: openai                # Тип провайдера (openai = OpenAI-совместимый API)
    model: qwen3-coder:30b          # Точное имя модели в Ollama
    apiBase: http://192.168.0.128:8000/v1   # URL шлюза
    apiKey: ollama                  # Любая непустая строка (шлюз с auth=off принимает всё)
    roles:                          # Для каких задач доступна
      - chat
      - edit
      - apply
    defaultCompletionOptions:
      temperature: 0.3              # Для code — низкая temperature
    requestOptions:
      timeout: 600000               # МИЛЛИСЕКУНДЫ! 600000 = 10 минут
      extraBodyProperties:          # Дополнительные поля в JSON body запроса
        num_ctx: 8192
        reasoning_effort: "none"
```

**Критичные правила:**

| Правило | Что будет если нарушить |
|---|---|
| `timeout` в **миллисекундах** | `timeout: 600` = 0.6 сек → все запросы таймаутятся |
| `extraBodyProperties` **внутри** `requestOptions` | На уровне модели → Ollama возвращает 400 (невалидный JSON) |
| Имена моделей **без скобок** | `qwen3.5:35b (reasoning)` → `Invalid input` |
| `apiKey` **обязательный** при `provider: openai` | Без него Continue не отправляет запрос |
| YAML anchors (`<<: *defaults`) **не работают** | Парсер Continue их не понимает |

### Особая модель: autocomplete

```yaml
  - name: autocomplete
    provider: ollama                # НЕ openai! Прямой доступ к Ollama
    model: qwen2.5-coder:7b
    apiBase: http://192.168.0.128:11434   # Ollama напрямую, НЕ через шлюз
    roles:
      - autocomplete
    requestOptions:
      timeout: 30000                # 30 сек (только для холодного старта)
    autocompleteOptions:
      debounceDelay: 500            # Задержка перед запросом (мс)
      maxPromptTokens: 2048         # Максимум токенов в промпте FIM
      multilineCompletions: auto
      modelTimeout: 30000           # Таймаут самой модели
```

Почему `provider: ollama` вместо `openai` — объяснение в разделе 3.4.

### Особая модель: embeddings

```yaml
  - name: embedder
    provider: transformers.js
    model: all-MiniLM-L6-v2
    roles:
      - embed
```

Нет `apiBase` — модель работает внутри VS Code. Подробно — в разделе 3.5.

### Секция prompts

```yaml
prompts:
  - name: review
    description: Code review with actionable feedback
    prompt: |
      Review the provided code...
```

Определяет slash-команды (`/review`, `/refactor` и т.д.). Подробно — в разделе 3.8.

## 3.3. Модели и роли

### Таблица маршрутизации

| Роль в IDE | Модель | Provider | Подключение | Reasoning |
|---|---|---|---|---|
| Chat (повседневный) | qwen3.5:9b | openai | Шлюз :8000 | effort=none |
| Chat (reasoning) | deepseek-r1:32b | openai | Шлюз :8000 | effort=medium |
| Chat (experimental) | qwen3.5:35b | openai | Шлюз :8000 | effort=none |
| Edit / Refactor | qwen3-coder:30b | openai | Шлюз :8000 | effort=none |
| Agent (tools) | qwen3-coder:30b | openai | Шлюз :8000 | effort=none |
| Agent (tools, альтернатива) | glm-4.7-flash | openai | Шлюз :8000 | effort=none |
| Vision | qwen3-vl:8b | openai | Шлюз :8000 | effort=none |
| **Autocomplete (FIM)** | **qwen2.5-coder:7b** | **ollama** | **Ollama :11434** | — |
| **Embeddings** | **all-MiniLM-L6-v2** | **transformers.js** | **VS Code** | — |

### Роли в Continue 1.2.17

| Роль | Описание |
|---|---|
| `chat` | Доступна в чат-панели |
| `edit` | Доступна для inline edit (Ctrl+I) |
| `apply` | Может применять diff к существующим файлам |
| `autocomplete` | Tab-автодополнение (не видна в дропдауне чата) |
| `embed` | Индексация кода для @Code и @Repository Map |

⚠ **ГРАБЛИ:** Роль `agent` **не существует** в Continue 1.2.17. Agent mode использует ту модель, которая выбрана в UI. Модель для Agent — любая с ролями `chat` + `edit`, которая поддерживает function calling.

### Выбор модели для Agent mode

Agent mode в Continue отправляет `tools` в запросе. Модель должна вернуть `tool_calls` в ответе. Из наших моделей это умеют:

| Модель | Agent mode | Стиль работы |
|---|---|---|
| qwen3-coder:30b | ✅ Стабильный | Пакетные diff — несколько правок одним проходом |
| glm-4.7-flash | ✅ Стабильный | Пошаговые diff — по одному изменению за шаг |
| qwen3.5:35b | ❌ **Tools сломаны** | Генерирует текст вместо tool_calls. Не использовать |
| qwen3.5:9b | ⚠ С оговорками | Tools работают не всегда надёжно |

## 3.4. Autocomplete (FIM)

### Что такое FIM

FIM (Fill-in-the-Middle) — специальный режим генерации, при котором модель получает код **до** и **после** курсора и генерирует то, что должно быть **между** ними. Используются специальные токены:

```
<|fim_prefix|>def calculate_sum(a, b):
    <|fim_suffix|>
    return result<|fim_middle|>
```

Модель должна сгенерировать: `result = a + b`.

Обычные chat-модели (qwen3.5, deepseek-r1) **не обучены** на FIM-токенах и не подходят для автодополнения.

### Почему provider: ollama, а не openai

FIM-запросы идут через эндпоинт Ollama `/api/generate` (не `/v1/chat/completions`). Этот эндпоинт принимает `prompt` с FIM-токенами и `suffix`, возвращает `response` с заполнением. Шлюз gateway.py обрабатывает только `/v1/chat/completions`, поэтому FIM должен идти напрямую в Ollama.

Continue при `provider: ollama` автоматически формирует FIM-запрос с правильными токенами и отправляет его на `/api/generate`.

### Почему отдельная модель

- **Скорость.** Autocomplete должен отвечать за < 1 сек. Модель 7B в VRAM — мгновенный ответ. Модель 30B с CPU offload — 3–5 сек, неприемлемо для tab-completion.
- **Резидентность.** `OLLAMA_MAX_LOADED_MODELS=2` позволяет держать FIM-модель постоянно в памяти. При переключении chat-модели FIM-модель не выгружается.
- **FIM-обучение.** `qwen2.5-coder` обучена на FIM-данных. Обычные chat-модели — нет.

## 3.5. Embeddings: transformers.js vs серверная модель

### Зачем embeddings

Embeddings (векторные представления) нужны для context providers `@Code` и `@Repository Map`. Continue индексирует файлы проекта, вычисляет эмбеддинги для каждого фрагмента кода и сохраняет их локально. При запросе `@Code найди функцию calculate_sum` — Continue ищет по векторному сходству, не по grep.

### Почему transformers.js, а не серверная модель

Ключевое ограничение: `OLLAMA_NUM_PARALLEL=1` — Ollama обрабатывает **один запрос за раз**.

Если использовать серверную embed-модель (nomic-embed-text или qwen3-embedding), при индексации проекта Continue отправляет десятки–сотни запросов подряд. Каждый запрос блокирует Ollama. Пока идёт индексация — chat и agent не работают.

`transformers.js` (all-MiniLM-L6-v2) — это маленькая embed-модель (~22 МБ), работающая **внутри процесса VS Code** на CPU клиентской машины. Никакой нагрузки на сервер. Никакой конкуренции с chat/agent.

Качество embeddings достаточное для поиска по коду (не для RAG по огромной документации). Если в будущем потребуется качественнее — Этап 7E добавит серверную модель.

⚠ **ГРАБЛИ:** Поле `model: all-MiniLM-L6-v2` в config.yaml **обязательно**. Без него парсер Continue падает с `Invalid input`, хотя это встроенная модель.

## 3.6. Context Providers

Context providers определяют, какую информацию Continue может прикрепить к запросу. Вызываются через `@` в поле ввода чата.

### 11 провайдеров в нашей конфигурации

| Provider | `@` в чате | Что прикрепляет | Требует embeddings |
|---|---|---|---|
| `code` | @Code | Фрагменты кода по семантическому поиску | Да |
| `repo-map` | @Repository Map | Карта репозитория (файлы, классы, сигнатуры) | Да |
| `file` | @Files | Конкретный файл по имени | Нет |
| `currentFile` | @Current File | Текущий открытый файл | Нет |
| `open` | @Open Files | Все открытые вкладки | Нет |
| `diff` | @Git Diff | Незакоммиченные изменения (staged + unstaged) | Нет |
| `terminal` | @Terminal | Последний вывод терминала | Нет |
| `tree` | @File Tree | Дерево файлов проекта | Нет |
| `problems` | @Problems | Ошибки и предупреждения из панели Problems | Нет |
| `clipboard` | @Clipboard | Содержимое буфера обмена | Нет |
| `os` | @OS | Информация об ОС (для контекстно-зависимых ответов) | Нет |

### Примеры использования

- `@Code calculate_sum` — найти все реализации `calculate_sum` в проекте.
- `@Git Diff` → «Объясни что я изменил» — модель видит diff.
- `@Terminal` → «Почему эта ошибка?» — модель видит вывод терминала.
- `@Repository Map` → «Как устроен этот проект?» — модель видит карту с сигнатурами.

### Устаревшие провайдеры

В документации Continue могут упоминаться `@Codebase`, `@Docs`, `@Folder`, `@Url`, `@Search`. Они **deprecated** (устарели) в пользу MCP-серверов. Не добавляйте их в config.yaml.

## 3.7. Rules: три уровня

Rules — это инструкции, которые добавляются в system message каждого запроса к модели. Три уровня, от общего к частному:

### Уровень 1 — Встроенный (Continue)

Continue добавляет собственный system message для Agent mode (инструкции по использованию tools, формат ответа). Вы его не контролируете.

### Уровень 2 — Глобальные rules

Файлы в `%USERPROFILE%\.continue\rules\`. Применяются **ко всем проектам**.

**Файл `01-general.md`:**

```markdown
---
name: General Guidelines
alwaysApply: true
---

## Environment
- Server: Ubuntu 22.04, RTX 3090 (24 GB VRAM), 62 GB RAM
- Client: Windows 11, VS Code + Continue.dev
- Language: Respond in Russian by default. Use English for code, comments, and technical terms.

## Style
- Be concise and direct. Skip introductions and pleasantries.
- When suggesting changes, show the complete modified code, not fragments.
- Explain architectural decisions, not just "what to type".
- If uncertain, say so explicitly rather than guessing.
```

**Файл `02-coding.md`:**

```markdown
---
name: Coding Standards
alwaysApply: true
---

## Python
- Python 3.10+. Type hints for function signatures.
- Docstrings: Google style (Args, Returns, Raises).
- Logging via `logging` module, not `print()`.
- Error handling: specific exceptions, not bare `except`.

## General
- UTF-8 everywhere. LF line endings.
- Meaningful variable names. No single-letter names except loop counters.
- Comments explain "why", not "what".
- Functions: single responsibility, < 50 lines preferred.
```

### Уровень 3 — Проектные rules

Файл в `<workspace>\.continue\rules\`. Применяются **только к данному проекту**.

**Файл `.continue/rules/01-project.md` (пример):**

```markdown
---
name: Project Architecture
alwaysApply: true
---

## Stack
- Backend: FastAPI + httpx + Pydantic
- LLM: Ollama (local), accessed via gateway.py proxy
- Config: YAML (Continue config), INI (systemd overrides)

## Naming
- Python: snake_case for functions/variables, PascalCase for classes
- Files: lowercase with underscores
- Constants: UPPER_SNAKE_CASE

## Project structure
- gateway.py: single-file FastAPI application
- No ORM, no database — stateless proxy
```

### Формат rule-файлов

Каждый файл — Markdown с YAML frontmatter:

```markdown
---
name: Display Name
alwaysApply: true
---

Content here...
```

- `name` — отображаемое имя в UI (вкладка Rules в настройках Continue).
- `alwaysApply: true` — правило добавляется в каждый запрос. Если `false` — только по явному вызову.

⚠ **ГРАБЛИ:** Проектные rules (`<workspace>\.continue\rules\`) подхватываются только после `Developer: Reload Window` (`Ctrl+Shift+P` → `Developer: Reload Window`). Создали файл — перезагрузите окно.

## 3.8. Prompts: 6 slash-команд

Slash-команды вызываются через `/` в поле ввода чата Continue. Каждая команда подставляет свой промпт перед запросом к модели.

### /review — Code review

```
Review the provided code. For each issue found:
1. State the problem clearly.
2. Explain why it matters (bug, performance, readability, security).
3. Show the fix.
Focus on: bugs, error handling, edge cases, readability, naming.
Skip praise and generic advice. Only flag real issues.
```

### /refactor — Рефакторинг

```
Refactor the provided code. Requirements:
- Improve readability and structure without changing behavior.
- Extract repeated logic into functions if appropriate.
- Simplify conditionals and reduce nesting.
- Improve naming where it helps clarity.
Show the refactored code, then briefly list what changed and why.
```

### /docstring — Документация

```
Write documentation for the provided code:
- For Python: Google-style docstrings with Args, Returns, Raises sections.
- For JavaScript: JSDoc format with @param, @returns, @throws tags.
- For other languages: use the conventional doc format.
Include a one-line summary, then details only if the function is non-trivial.
Do not restate what is obvious from the signature.
```

### /commit — Commit message

```
Write a git commit message for the provided diff. Follow conventional commits format:
    type(scope): short description
    Optional body with details.
Types: feat, fix, refactor, docs, style, test, chore, perf.
Scope: the module or area affected.
Description: imperative mood, lowercase, no period at the end.
Output only the commit message, nothing else.
```

### /explain — Объяснение кода

```
Explain the provided code step by step:
1. What does this code do overall (one sentence).
2. Walk through the logic, explaining each significant block.
3. Note any non-obvious patterns, tricks, or potential pitfalls.
Assume the reader is a developer who understands the language but is new to this codebase.
```

### /tests — Генерация тестов

```
Write unit tests for the provided code:
- Focus on behavior, not implementation details.
- Cover both happy path and important edge cases.
- Use the existing testing framework if detectable, otherwise common style for the language.
- Group logically, clear test names, Arrange-Act-Assert structure.
After tests, briefly list what is covered and what edge cases could be added later.
```

⚠ **ГРАБЛИ:** Промпты определяются в секции `prompts:` файла `config.yaml` или как `.md`-файлы в папке `.continue/prompts/`. **Не в** `.continue/rules/` — это разные папки с разным назначением. Rules добавляются в system message, prompts — подставляются как пользовательский запрос.

## 3.9. Agent mode: модели, Apply, стили

### Как работает Agent mode

При включении Agent mode (кнопка в интерфейсе чата Continue) модель получает набор tools (инструментов): чтение файлов, запись файлов, запуск терминальных команд, поиск по коду. Модель возвращает `tool_calls` — шлюз конвертирует их из формата Ollama в формат OpenAI — Continue исполняет.

### Apply: наложение diff на существующие файлы

Apply — это способность Continue применить предложенные модели изменения к существующему файлу. Модель генерирует diff, Continue накладывает его. Для этого нужна роль `apply` у модели.

Обе Agent-модели поддерживают Apply, но с разным стилем:

| Аспект | qwen3-coder:30b | glm-4.7-flash |
|---|---|---|
| Создание файлов | ✅ | ✅ |
| Apply на существующем файле | ✅ | ✅ |
| Стиль diff | Пакетный — несколько правок одним проходом | Пошаговый — одно изменение за шаг |
| Скорость | Быстрее (меньше round-trip) | Медленнее (больше шагов) |
| Надёжность | Высокая | Высокая |
| Рекомендация | Основная модель для Agent | Альтернатива, если qwen3-coder выдаёт неточный diff |

⚠ **ГРАБЛИ:** `capabilities: [tool_use]` в config.yaml **не нужен** для qwen3-coder и glm-flash. Continue автоматически определяет поддержку tool use. Явное указание `capabilities` может сбить автодетекцию.

## 3.10. Проверка: чеклист «всё работает»

После настройки config.yaml и создания rule-файлов выполните проверки:

| # | Проверка | Как | Ожидаемый результат |
|---|---|---|---|
| 1 | Config без ошибок | Правый нижний угол VS Code — нет `⚠ Continue` | Нет ошибок |
| 2 | Chat работает | Написать «Hello» в чат Continue | Стримящийся ответ от qwen3.5:9b |
| 3 | Переключение моделей | Выбрать другую модель в дропдауне | Ответ от другой модели |
| 4 | Autocomplete | Открыть .py файл, начать набирать `def calc` | Серое предложение автодополнения |
| 5 | Agent mode | Включить Agent, попросить «create hello.py» | Модель вызывает tool для создания файла |
| 6 | @Code | Набрать `@Code` в чате | Список совпадений из проекта |
| 7 | @Repository Map | Набрать `@Repository Map` | Карта с сигнатурами файлов |
| 8 | /review | Выделить код, ввести `/review` | Структурированный code review |
| 9 | Rules в UI | Чат Continue → Settings → Rules | Видны 01-general, 02-coding |
| 10 | Vision | Вставить скриншот в чат (модель qwen3-vl) | Описание изображения |

Если какая-то проверка не прошла — обратитесь к **Приложению H** (грабли Continue 1.2.17).

# Часть 4 — Copilot BYOK (опционально)

## 4.1. Что это и зачем

BYOK (Bring Your Own Key — «подключи свою модель») — функция GitHub Copilot в VS Code, позволяющая использовать произвольные LLM вместо облачных GPT-4o / Claude. Доступна для планов **Free / Pro / Pro+**, **не** доступна для Business / Enterprise.

**Continue.dev остаётся основным инструментом.** Copilot BYOK — это дополнительный чат-интерфейс, полезный тем, кто привык к Copilot UI. Он **не заменяет** Continue ни в одном критическом сценарии: Agent mode, autocomplete, context providers, rules, prompts — всё это работает только в Continue.

## 4.2. Путь A: Ollama напрямую

Copilot подключается к Ollama без шлюза. Простейший вариант.

### Настройка

В VS Code `settings.json` (`Ctrl+,` → Open Settings JSON):

```json
{
  "github.copilot.chat.byok.ollamaEndpoint": "http://192.168.0.128:11434"
}
```

### Проверка

1. Откройте Copilot Chat (Ctrl+Shift+I или иконка Copilot).
2. В model picker — раздел **Ollama** с моделями вашего сервера.
3. Выберите `qwen3-coder:30b`, задайте вопрос.
4. Ожидайте: посимвольный стриминг ответа.

### Особенности

- Модели видны автоматически (Copilot запрашивает `/api/tags`).
- Данные **не** проходят через шлюз — нет логирования, reasoning policy, валидации.
- Стриминг работает.

## 4.3. Путь C: OAI Compatible extension через шлюз

Более контролируемый вариант: запросы идут через gateway.py. Логируются, валидируются, обрабатываются.

### Установка расширения

В VS Code Extensions найдите и установите: **OAI Compatible Provider for Copilot** (ID: `johnny-zhao.oai-compatible-copilot`).

### Настройка

В VS Code `settings.json`:

```json
{
  "oaicopilot.baseUrl": "http://192.168.0.128:8000/v1",
  "oaicopilot.models": [
    {
      "id": "qwen3-coder:30b",
      "owned_by": "ollama",
      "context_length": 8192,
      "temperature": 0.3
    },
    {
      "id": "qwen3.5:9b",
      "owned_by": "ollama",
      "context_length": 8192,
      "temperature": 0.7
    },
    {
      "id": "glm-4.7-flash",
      "owned_by": "ollama",
      "context_length": 8192,
      "temperature": 0.7
    }
  ]
}
```

### Проверка

1. Copilot Chat → model picker → раздел **OAI Compatible**.
2. Выберите `qwen3-coder:30b`.
3. Задайте вопрос → посимвольный стриминг.
4. На сервере: `sudo journalctl -u llm-gateway -f` — видите запросы.

## 4.4. Agent mode — почему не работает с локальными моделями

Copilot Agent mode (tools: workspace search, file read, terminal) **нестабилен** с локальными моделями 30B-класса. Протестировано с qwen3-coder:30b:

- Tools UI доступен (после `#` показывается список инструментов).
- При попытке tool calling модель **зацикливается**: генерирует текст о том, что «хочет» использовать инструмент, вместо `tool_call` JSON.
- GPU потребление растёт, требуется `ollama stop` для прерывания.

**Корневая причина:** Copilot Agent использует свой формат промптов для tools, оптимизированный под GPT-4o и Claude Sonnet, которые специально дообучены под протокол Copilot. Локальные модели не знают этот формат и не могут ему следовать.

Шлюз gateway.py исправно конвертирует `tool_calls` (подтверждено логами) — проблема на стороне модели, а не инфраструктуры.

## 4.5. Сравнительная таблица

| Критерий | Copilot BYOK | Continue.dev |
|---|---|---|
| Plain chat | ✅ | ✅ |
| Streaming | ✅ | ✅ |
| Agent mode (tools) | ❌ Нестабилен | ✅ Стабилен |
| Apply (edit файлов) | Не тестировалось | ✅ |
| Autocomplete (FIM) | ❌ BYOK не поддерживает | ✅ |
| Context providers | ❌ Tools не работают | ✅ 11 провайдеров |
| Rules / Prompts | Нет аналога | ✅ 3 уровня + 6 команд |
| Embeddings | Облачные (GitHub) | ✅ Локальные (transformers.js) |
| Приватность | ❌ Данные уходят в GitHub | ✅ Полностью локально |
| Inline suggestions | ❌ BYOK не поддерживает | ✅ FIM autocomplete |

**Вывод:** Copilot BYOK = дополнительный чат. Для реальной работы — Continue.dev.

# Часть 5 — Эксплуатация и диагностика

## 5.1. Ежедневные проверки

### Быстрый health check (одна команда)

```bash
curl -s http://192.168.0.128:8000/health | python3 -c "
import sys, json
h = json.load(sys.stdin)
status = '✅' if h['gateway'] == 'ok' and h['ollama'] == 'ok' else '❌'
print(f\"{status} Gateway: {h['gateway']}, Ollama: {h['ollama']}, Models: {h['models_count']}, Auth: {h['auth_enabled']}\")
"
```

### GPU состояние

```bash
nvidia-smi --query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits
# Пример вывода: 42, 0, 4521, 24576
# Значит: 42°C, 0% загрузки, 4.5 ГБ VRAM занято из 24 ГБ
```

### Какие модели загружены в память

```bash
curl -s http://192.168.0.128:11434/api/ps | python3 -m json.tool
# Показывает модели, загруженные в VRAM/RAM прямо сейчас
```

### Сервисы

```bash
systemctl is-active ollama llm-gateway
# Ожидаем: active active
```

## 5.2. Мониторинг логов

### Логи шлюза

```bash
# Последние 50 строк
sudo journalctl -u llm-gateway -n 50

# В реальном времени (follow)
sudo journalctl -u llm-gateway -f

# Только запросы
sudo journalctl -u llm-gateway | grep "REQ "

# Ошибки
sudo journalctl -u llm-gateway --priority=err
```

### Логи Ollama

```bash
sudo journalctl -u ollama -n 50

# Ошибки загрузки моделей
sudo journalctl -u ollama | grep -i "error\|fail\|oom"
```

### GPU мониторинг в реальном времени

```bash
# Обновление каждую секунду
watch -n 1 nvidia-smi

# Или компактный формат
watch -n 1 'nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader'
```

## 5.3. Типичные проблемы и решения

### OOM (Out of Memory — нехватка памяти GPU/RAM)

**Симптомы:** Шлюз возвращает HTTP 503 с `"code": "oom"`. В логах Ollama: `"out of memory"` или `"failed to allocate"`.

**Причины и решения:**

| Причина | Решение |
|---|---|
| Модель слишком большая для VRAM + RAM | Использовать модель меньшего размера |
| `num_ctx` слишком большой | Уменьшить `num_ctx` (в config.yaml `extraBodyProperties`) |
| Две большие модели одновременно | `MAX_LOADED_MODELS=1` или выгрузить модель: `ollama stop <model>` |
| Утечка памяти после долгой работы | `sudo systemctl restart ollama` |

### Холодный старт (Cold Start)

**Симптомы:** Первый запрос после смены модели — долгий (8–30 секунд). Шлюз может вернуть 503 `"code": "model_loading"`.

**Это нормальное поведение.** Ollama загружает веса модели с SSD в VRAM/RAM. Шлюз делает 3 попытки с backoff (2с → 4с). Обычно модель загружается за 2-ю или 3-ю попытку.

**Как смягчить:**
- Не переключать модели часто. Работать с одной chat-моделью в сессии.
- `MAX_LOADED_MODELS=2` — FIM-модель не выгружается при загрузке chat-модели.
- Таймаут в Continue: `timeout: 600000` (10 минут) — достаточно для холодного старта.

### Зацикливание Agent mode

**Симптомы:** Модель генерирует бесконечный текст, GPU загрузка 100%, ответ не приходит.

**Причины:**
- Модель не поддерживает function calling (qwen3.5:35b).
- Модель запуталась в контексте (слишком длинный разговор).

**Решения:**
- Остановить модель: `ollama stop <model>` на сервере.
- Использовать только проверенные Agent-модели: qwen3-coder:30b, glm-4.7-flash.
- При зацикливании — начать новый чат (кнопка «+» в Continue).
- Если проблема повторяется — уменьшить `num_ctx` (меньше контекста = меньше шансов запутаться).

### CUDA crash (SIGABRT)

**Симптомы:** Ollama падает. `systemctl status ollama` показывает `signal: SIGABRT`. В логах: `CUDA error`.

**Причина:** CUDA Graph Capture несовместим с быстрой сменой запросов (Agent mode).

**Решение:** `GGML_CUDA_NO_GRAPHS=1` в Ollama override (уже в нашей конфигурации). Если забыли добавить — модель падает при Agent mode.

### Continue не показывает модели / ошибки конфигурации

**Симптомы:** Дропдаун моделей пуст, или ошибка `⚠ Continue` в правом нижнем углу VS Code.

**Диагностика:**
1. Проверить `config.yaml` — часто проблема в YAML-синтаксисе (отступы, спецсимволы).
2. VS Code DevTools (`Ctrl+Shift+I`) → Console → фильтр `continuedev`.
3. Убедиться, что шлюз доступен: `curl http://192.168.0.128:8000/v1/models` с клиентской машины.
4. Перезагрузить окно: `Developer: Reload Window`.

## 5.4. Обновление Ollama и моделей

### Обновление Ollama

```bash
# Проверить текущую версию
ollama --version

# Обновить (тот же скрипт, что при установке)
curl -fsSL https://ollama.com/install.sh | sh

# Проверить, что override сохранился
cat /etc/systemd/system/ollama.service.d/override.conf
# Если файл пуст или отсутствует — пересоздайте (раздел 1.3)

# Перезапустить
sudo systemctl daemon-reload
sudo systemctl restart ollama

# Проверить
ollama --version
curl -s http://localhost:8000/health | python3 -m json.tool
```

⚠ **ГРАБЛИ:** Обновление Ollama может потребовать re-pull модели (если изменился формат квантизации или исправлены баги в модельном шаблоне). Особенно это касается thinking-моделей (qwen3.5, deepseek-r1). После обновления — протестируйте основные сценарии.

### Обновление модели

```bash
# Re-pull (скачает только если версия изменилась)
ollama pull qwen3-coder:30b

# Проверка
curl -s http://localhost:8000/v1/chat/completions -H "Content-Type: application/json" -d '{
  "model": "qwen3-coder:30b",
  "messages": [{"role": "user", "content": "Say OK"}],
  "stream": false,
  "reasoning_effort": "none"
}' | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

### Порядок обновления

1. Остановить шлюз: `sudo systemctl stop llm-gateway`
2. Обновить Ollama: `curl -fsSL https://ollama.com/install.sh | sh`
3. Проверить override: `cat /etc/systemd/system/ollama.service.d/override.conf`
4. Перезапустить Ollama: `sudo systemctl daemon-reload && sudo systemctl restart ollama`
5. Re-pull критичных моделей: `ollama pull qwen3-coder:30b`
6. Запустить шлюз: `sudo systemctl start llm-gateway`
7. Проверить: `curl -s http://localhost:8000/health`
8. Протестировать: chat, stream, tools (тесты из раздела 2.5)

## 5.5. Дальнейшее развитие

### Этап 7E — Embeddings через Ollama

Если `transformers.js` (all-MiniLM-L6-v2) недостаточно по качеству для поиска по коду, следующий шаг — добавить `/v1/embeddings` эндпоинт в gateway.py и подключить серверную embed-модель (qwen3-embedding или nomic-embed-text).

Предпосылка: `OLLAMA_NUM_PARALLEL` станет > 1 (или индексация будет запускаться в моменты простоя).

### Этап 8+ — Multi-model orchestration

Архитектура Planner-Executor: модель-планировщик (qwen3.5:35b — мощный reasoning) разбивает задачу на шаги, модель-исполнитель (qwen3-coder:30b — быстрый code) выполняет каждый шаг. Требует оркестрирующего слоя поверх gateway.py.

### Monitoring dashboard

Визуальная панель с метриками: GPU-загрузка, VRAM, температура, количество запросов, средний TTFT, ошибки. Реализуется через Grafana + Prometheus или простой HTML-дашборд на FastAPI.

# Приложения


## Приложение A — gateway.py v0.7.0

Полный исходный код шлюза (993 строки). Файл самодостаточен: все зависимости — стандартные Python-пакеты (`fastapi`, `uvicorn`, `httpx`, `pydantic`).

Размещение на сервере: `~/llm-gateway/gateway.py`.

```python
"""
LLM Gateway — OpenAI-compatible HTTP proxy for Ollama.

Версия: 0.7.0
Дата: 2026-03-16
Сервер: 192.168.0.128, RTX 3090 24 ГБ VRAM, 62 ГБ RAM.

Этап 7: Поддержка tool_calls (function calling).

  Проблема: Ollama возвращает tool_calls в message.tool_calls,
  но stream_generator() и build_openai_response() обрабатывали
  только content и thinking. Tool_calls терялись — Continue.dev
  Agent mode получал пустой ответ.

  Решение: convert_ollama_tool_calls_to_openai() конвертирует
  формат Ollama (arguments: dict, index внутри function) в формат
  OpenAI (arguments: JSON string, index на верхнем уровне).
  Проброс в stream (delta.tool_calls) и non-stream (message.tool_calls).
  finish_reason: "tool_calls" вместо "stop" при наличии tool_calls.

Этап 6: Настоящий стриминг (без изменений).
Этап 5: API-контракт и совместимость (без изменений).
Этап 4: Обработка ошибок (без изменений).
Этап 3: Валидация, penalties, seed, логирование (без изменений).
Этап 2: Reasoning policy, Depth-over-Speed, stream fixes (без изменений).

Требования к серверу Ollama (systemd env):
  OLLAMA_FLASH_ATTENTION=1
  OLLAMA_KV_CACHE_TYPE=q8_0
  OLLAMA_MAX_LOADED_MODELS=1
  GGML_CUDA_NO_GRAPHS=1

Запуск:
  cd ~/llm-gateway && source venv/bin/activate
  uvicorn gateway:app --host 0.0.0.0 --port 8000

Аутентификация (опционально):
  export LLM_GATEWAY_API_KEY="my-secret-key"
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Literal, Union, Any

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, ConfigDict
from starlette.background import BackgroundTask

# ---------------------------------------------------------------------------
# Логирование
# ---------------------------------------------------------------------------

logger = logging.getLogger("uvicorn.error")

# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_CHAT_URL = f"{OLLAMA_BASE_URL}/api/chat"
OLLAMA_TAGS_URL = f"{OLLAMA_BASE_URL}/api/tags"

HTTPX_TIMEOUT = httpx.Timeout(timeout=600.0)
DEFAULT_NUM_CTX = 8192
MAX_NUM_CTX = 32768
MAX_TEMPERATURE = 2.0
MAX_PENALTY = 2.0
MIN_PENALTY = -2.0
MAX_REPEAT_PENALTY = 2.0

# Обработка ошибок (Этап 4)
RETRY_MAX_ATTEMPTS = 3
RETRY_BACKOFF_BASE = 2.0
RETRY_AFTER_SECONDS = 30

OOM_PATTERNS = (
    "out of memory",
    "oom",
    "cuda out of memory",
    "not enough memory",
    "failed to allocate",
    "memory allocation failed",
    "ggml_cuda_op_mul_mat_cublas",
    "insufficient memory",
)

# Аутентификация (P7). Пустая строка = без проверки.
GATEWAY_API_KEY = os.environ.get("LLM_GATEWAY_API_KEY", "")

# ---------------------------------------------------------------------------
# HTTP-клиент (singleton)
# ---------------------------------------------------------------------------

client = httpx.AsyncClient(timeout=HTTPX_TIMEOUT)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="LLM Gateway",
    description="OpenAI-compatible proxy → Ollama (RTX 3090 Lab)",
    version="0.7.0",
)

# ---------------------------------------------------------------------------
# Аутентификация middleware (P7)
# ---------------------------------------------------------------------------


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """
    Bearer token проверка, если LLM_GATEWAY_API_KEY задана.
    /health освобождён — для мониторинга без ключа.
    """
    if GATEWAY_API_KEY and request.url.path != "/health":
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"error": {
                    "message": "Missing Authorization header. "
                               "Expected: Bearer <api_key>",
                    "type": "authentication_error",
                    "code": "missing_api_key",
                }},
            )
        token = auth_header[7:]
        if token != GATEWAY_API_KEY:
            return JSONResponse(
                status_code=401,
                content={"error": {
                    "message": "Invalid API key",
                    "type": "authentication_error",
                    "code": "invalid_api_key",
                }},
            )
    return await call_next(request)


# ---------------------------------------------------------------------------
# OpenAI-совместимый формат ошибок (Этап 4)
# ---------------------------------------------------------------------------


class GatewayError(HTTPException):
    def __init__(self, status_code: int, message: str,
                 error_type: str = "api_error",
                 error_code: Optional[str] = None):
        super().__init__(status_code=status_code, detail=message)
        self.message = message
        self.error_type = error_type
        self.error_code = error_code or str(status_code)


@app.exception_handler(GatewayError)
async def gateway_error_handler(request: Request, exc: GatewayError):
    headers = {}
    if exc.status_code == 503:
        headers["Retry-After"] = str(RETRY_AFTER_SECONDS)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {
            "message": exc.message,
            "type": exc.error_type,
            "code": exc.error_code,
        }},
        headers=headers,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {
            "message": (exc.detail if isinstance(exc.detail, str)
                        else str(exc.detail)),
            "type": ("invalid_request_error" if exc.status_code == 422
                     else "api_error"),
            "code": str(exc.status_code),
        }},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request,
                                   exc: RequestValidationError):
    messages = []
    for err in exc.errors():
        loc = " → ".join(str(x) for x in err.get("loc", []))
        messages.append(f"{loc}: {err.get('msg', 'invalid')}")
    return JSONResponse(
        status_code=422,
        content={"error": {
            "message": "; ".join(messages),
            "type": "invalid_request_error",
            "code": "validation_error",
        }},
    )


# ---------------------------------------------------------------------------
# Pydantic-модели запроса (P2, P3)
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    """
    Сообщение чата. extra="ignore" — неизвестные поля молча отбрасываются.
    content: str | list (multimodal vision) | None (tool_calls msg).
    """
    model_config = ConfigDict(extra="ignore")

    role: str
    content: Union[str, list, None] = None
    name: Optional[str] = None
    tool_calls: Optional[list] = None
    tool_call_id: Optional[str] = None


class ReasoningConfig(BaseModel):
    effort: Literal["none", "low", "medium", "high"] = "none"


class ChatCompletionRequest(BaseModel):
    """extra="ignore" — неизвестные параметры от клиента молча игнорируются."""
    model_config = ConfigDict(extra="ignore")

    model: str
    messages: list[ChatMessage]
    stream: bool = False

    temperature: Optional[float] = Field(
        default=None, ge=0.0, le=MAX_TEMPERATURE)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    frequency_penalty: Optional[float] = Field(
        default=None, ge=MIN_PENALTY, le=MAX_PENALTY)
    presence_penalty: Optional[float] = Field(
        default=None, ge=MIN_PENALTY, le=MAX_PENALTY)
    seed: Optional[int] = Field(default=None, ge=0)

    # P3: stop, tools, tool_choice
    stop: Union[str, list, None] = Field(default=None)
    tools: Optional[list] = Field(default=None)
    tool_choice: Union[str, dict, None] = Field(default=None)

    # Reasoning (Этап 2)
    reasoning: Optional[ReasoningConfig] = None
    reasoning_effort: Optional[str] = None

    # Depth-over-Speed (Этап 2)
    num_ctx: Optional[int] = Field(default=None, ge=1, le=MAX_NUM_CTX)
    num_gpu: Optional[int] = Field(default=None, ge=0)
    num_batch: Optional[int] = Field(default=None, ge=1)

    # Ollama-native (Этап 3)
    repeat_penalty: Optional[float] = Field(
        default=None, ge=0.0, le=MAX_REPEAT_PENALTY)
    repeat_last_n: Optional[int] = Field(default=None, ge=-1)


# ---------------------------------------------------------------------------
# Классификация ошибок (Этап 4)
# ---------------------------------------------------------------------------


def is_oom_error(error_text: str) -> bool:
    lower = error_text.lower()
    return any(p in lower for p in OOM_PATTERNS)


def classify_ollama_error(status_code: int, error_body: dict,
                          request_id: str) -> GatewayError:
    error_msg = error_body.get("error", "")

    if is_oom_error(error_msg):
        logger.error("REQ %s OOM detected: HTTP %d, error=%s",
                     request_id, status_code, error_msg)
        return GatewayError(
            503, f"GPU/RAM out of memory. Try a smaller model or reduce "
                 f"num_ctx. Ollama: {error_msg}",
            "server_error", "oom")

    if status_code == 404:
        logger.warning("REQ %s model not found: %s", request_id, error_msg)
        return GatewayError(
            404, error_msg or "Model not found in Ollama",
            "not_found_error", "model_not_found")

    if status_code == 400:
        logger.warning("REQ %s Ollama bad request: %s",
                       request_id, error_msg)
        return GatewayError(
            400, f"Ollama rejected request: {error_msg}",
            "invalid_request_error", "bad_request")

    if status_code >= 500:
        logger.error("REQ %s Ollama internal error: HTTP %d, error=%s",
                     request_id, status_code, error_msg)
        return GatewayError(
            502, f"Ollama internal error (HTTP {status_code}): {error_msg}",
            "server_error", "ollama_error")

    logger.warning("REQ %s Ollama HTTP %d: %s",
                   request_id, status_code, error_msg)
    return GatewayError(
        status_code, error_msg or f"Ollama returned HTTP {status_code}",
        "api_error", str(status_code))


async def check_ollama_alive() -> bool:
    try:
        resp = await client.get(OLLAMA_TAGS_URL,
                                timeout=httpx.Timeout(timeout=5.0))
        return resp.status_code == 200
    except Exception:
        return False


def build_connection_error(request_id: str, last_error: Exception,
                           ollama_alive: bool) -> GatewayError:
    error_name = type(last_error).__name__
    error_detail = str(last_error) or "(no details)"

    if ollama_alive:
        logger.warning(
            "REQ %s cold start suspected: Ollama alive but chat failed "
            "after %d attempts: %s: %s",
            request_id, RETRY_MAX_ATTEMPTS, error_name, error_detail)
        return GatewayError(
            503, "Model is loading into GPU memory (cold start). "
                 "Please retry shortly.",
            "server_error", "model_loading")
    else:
        logger.error(
            "REQ %s Ollama unreachable after %d attempts: %s: %s",
            request_id, RETRY_MAX_ATTEMPTS, error_name, error_detail)
        return GatewayError(
            502, f"Cannot connect to Ollama after {RETRY_MAX_ATTEMPTS} "
                 f"attempts. Last error: {error_name}: {error_detail}",
            "server_error", "ollama_unavailable")


# ---------------------------------------------------------------------------
# Retry-обёртка для non-stream (Этап 4, без изменений)
# ---------------------------------------------------------------------------


async def ollama_post_with_retry(url: str, payload: dict,
                                 request_id: str) -> httpx.Response:
    """
    Буферизованный POST для non-stream запросов.
    Читает весь ответ в память — для non-stream это нормально.
    """
    last_error: Optional[Exception] = None
    for attempt in range(RETRY_MAX_ATTEMPTS):
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError:
            raise
        except httpx.RequestError as e:
            last_error = e
            remaining = RETRY_MAX_ATTEMPTS - attempt - 1
            if remaining > 0:
                wait = RETRY_BACKOFF_BASE * (2 ** attempt)
                logger.warning(
                    "REQ %s attempt %d/%d failed: %s: %s — retrying in %.0fs",
                    request_id, attempt + 1, RETRY_MAX_ATTEMPTS,
                    type(e).__name__, str(e) or "(empty)", wait)
                await asyncio.sleep(wait)
            else:
                logger.error(
                    "REQ %s attempt %d/%d failed: %s: %s — no retries left",
                    request_id, attempt + 1, RETRY_MAX_ATTEMPTS,
                    type(e).__name__, str(e) or "(empty)")

    ollama_alive = await check_ollama_alive()
    raise build_connection_error(request_id, last_error, ollama_alive)


# ---------------------------------------------------------------------------
# Retry-обёртка для stream (Этап 6)
# ---------------------------------------------------------------------------


async def ollama_stream_with_retry(url: str, payload: dict,
                                   request_id: str) -> httpx.Response:
    """
    Streaming POST для stream-запросов.

    Использует client.send(req, stream=True) — httpx возвращает response
    сразу после получения HTTP headers, не читая body. Это даёт настоящий
    стриминг: body читается по мере поступления через aiter_lines().

    Retry — только на фазе установления соединения (RequestError).
    При HTTP-ошибке (status != 200): читаем error body, закрываем response,
    классифицируем ошибку через classify_ollama_error().
    При HTTP 200: возвращаем открытый response. Caller ОБЯЗАН закрыть его
    через resp.aclose() (используется BackgroundTask в chat_completions).
    """
    last_error: Optional[Exception] = None
    for attempt in range(RETRY_MAX_ATTEMPTS):
        try:
            req = client.build_request("POST", url, json=payload)
            resp = await client.send(req, stream=True)

            if resp.status_code != 200:
                # Читаем тело ошибки — response ещё открыт, body не прочитан
                await resp.aread()
                await resp.aclose()
                error_body = {}
                try:
                    error_body = resp.json()
                except Exception:
                    error_body = {"error": resp.text or str(resp.status_code)}
                raise classify_ollama_error(
                    resp.status_code, error_body, request_id)

            # HTTP 200 — возвращаем открытый streaming response
            return resp

        except GatewayError:
            raise
        except httpx.RequestError as e:
            last_error = e
            remaining = RETRY_MAX_ATTEMPTS - attempt - 1
            if remaining > 0:
                wait = RETRY_BACKOFF_BASE * (2 ** attempt)
                logger.warning(
                    "REQ %s stream attempt %d/%d failed: %s: %s "
                    "— retrying in %.0fs",
                    request_id, attempt + 1, RETRY_MAX_ATTEMPTS,
                    type(e).__name__, str(e) or "(empty)", wait)
                await asyncio.sleep(wait)
            else:
                logger.error(
                    "REQ %s stream attempt %d/%d failed: %s: %s "
                    "— no retries left",
                    request_id, attempt + 1, RETRY_MAX_ATTEMPTS,
                    type(e).__name__, str(e) or "(empty)")

    ollama_alive = await check_ollama_alive()
    raise build_connection_error(request_id, last_error, ollama_alive)


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------


def resolve_effort(request: ChatCompletionRequest) -> str:
    if request.reasoning and request.reasoning.effort:
        return request.reasoning.effort
    if request.reasoning_effort:
        raw = request.reasoning_effort.lower().strip()
        if raw in ("none", "low", "medium", "high"):
            return raw
    return "none"


def convert_message_for_ollama(msg: ChatMessage) -> dict:
    """
    Конвертер OpenAI message → Ollama /api/chat message.

    content str → as-is.
    content None → "" (Ollama не принимает null).
    content list → multimodal: text → content, image_url → images[].
    """
    ollama_msg: dict = {"role": msg.role}
    images: list[str] = []

    if msg.content is None:
        ollama_msg["content"] = ""
    elif isinstance(msg.content, str):
        ollama_msg["content"] = msg.content
    elif isinstance(msg.content, list):
        text_parts: list[str] = []
        for block in msg.content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            if btype == "text":
                text_parts.append(block.get("text", ""))
            elif btype == "image_url":
                url_obj = block.get("image_url", {})
                url = (url_obj.get("url", "")
                       if isinstance(url_obj, dict) else "")
                if url.startswith("data:"):
                    comma = url.find(",")
                    if comma != -1:
                        images.append(url[comma + 1:])
                elif url:
                    images.append(url)
        ollama_msg["content"] = "\n".join(text_parts)
    else:
        ollama_msg["content"] = str(msg.content)

    if images:
        ollama_msg["images"] = images
    if msg.name is not None:
        ollama_msg["name"] = msg.name
    if msg.tool_calls is not None:
        ollama_msg["tool_calls"] = msg.tool_calls
    if msg.tool_call_id is not None:
        ollama_msg["tool_call_id"] = msg.tool_call_id

    return ollama_msg


def build_ollama_payload(request: ChatCompletionRequest,
                         think_enabled: bool) -> dict:
    messages = [convert_message_for_ollama(m) for m in request.messages]
    options: dict = {}

    if request.temperature is not None:
        options["temperature"] = request.temperature
    if request.max_tokens is not None:
        options["num_predict"] = request.max_tokens
    if request.top_p is not None:
        options["top_p"] = request.top_p
    if request.frequency_penalty is not None:
        options["frequency_penalty"] = request.frequency_penalty
    if request.presence_penalty is not None:
        options["presence_penalty"] = request.presence_penalty
    if request.seed is not None:
        options["seed"] = request.seed

    if request.stop is not None:
        if isinstance(request.stop, str):
            options["stop"] = [request.stop]
        elif isinstance(request.stop, list):
            options["stop"] = request.stop

    if request.repeat_penalty is not None:
        options["repeat_penalty"] = request.repeat_penalty
    if request.repeat_last_n is not None:
        options["repeat_last_n"] = request.repeat_last_n

    num_ctx = request.num_ctx if request.num_ctx is not None else DEFAULT_NUM_CTX
    options["num_ctx"] = min(num_ctx, MAX_NUM_CTX)

    if request.num_gpu is not None:
        options["num_gpu"] = request.num_gpu
    if request.num_batch is not None:
        options["num_batch"] = request.num_batch

    payload = {
        "model": request.model,
        "messages": messages,
        "stream": request.stream,
        "think": think_enabled,
        "options": options,
    }

    if request.tools is not None:
        payload["tools"] = request.tools
    if request.tool_choice is not None:
        payload["tool_choice"] = request.tool_choice

    return payload


def extract_content_and_reasoning(ollama_message: dict,
                                  effort: str) -> tuple[str, Optional[str]]:
    content = ollama_message.get("content", "") or ""
    thinking = ollama_message.get("thinking", "") or ""

    if not content.strip() and thinking.strip():
        content = thinking
        thinking = ""

    reasoning_content = None
    if effort in ("medium", "high") and thinking.strip():
        reasoning_content = thinking

    return content, reasoning_content


def estimate_token_split(ollama_resp: dict) -> tuple[int, int, int]:
    """Returns (prompt_tokens, answer_tokens, reasoning_tokens)."""
    prompt_tokens = ollama_resp.get("prompt_eval_count", 0) or 0
    total_eval = ollama_resp.get("eval_count", 0) or 0

    msg = ollama_resp.get("message", {})
    thinking_text = msg.get("thinking", "") or ""
    content_text = msg.get("content", "") or ""
    total_len = len(thinking_text) + len(content_text)

    if total_len > 0 and thinking_text:
        reasoning_tokens = int(total_eval * len(thinking_text) / total_len)
        answer_tokens = total_eval - reasoning_tokens
    else:
        reasoning_tokens = 0
        answer_tokens = total_eval

    return prompt_tokens, answer_tokens, reasoning_tokens


# ---------------------------------------------------------------------------
# Tool calls: Ollama → OpenAI формат (Этап 7)
# ---------------------------------------------------------------------------


def convert_ollama_tool_calls_to_openai(
        ollama_tool_calls: list) -> list[dict]:
    """
    Конвертирует tool_calls из формата Ollama в формат OpenAI.

    Ollama формат:
    {
      "id": "call_abc123",
      "function": {
        "index": 0,
        "name": "run_terminal_command",
        "arguments": {"command": "ls -R"}     ← dict
      }
    }

    OpenAI формат:
    {
      "index": 0,
      "id": "call_abc123",
      "type": "function",
      "function": {
        "name": "run_terminal_command",
        "arguments": "{\"command\": \"ls -R\"}"  ← JSON string
      }
    }

    Различия:
    - index перемещается из function на верхний уровень
    - type: "function" добавляется на верхний уровень
    - arguments конвертируется из dict в JSON string
    - Если id отсутствует — генерируем
    """
    openai_calls = []
    for i, tc in enumerate(ollama_tool_calls):
        if not isinstance(tc, dict):
            continue

        func = tc.get("function", {})
        if not isinstance(func, dict):
            continue

        # arguments: dict → JSON string
        args = func.get("arguments", {})
        if isinstance(args, dict):
            args_str = json.dumps(args, ensure_ascii=False)
        elif isinstance(args, str):
            args_str = args
        else:
            args_str = json.dumps(args, ensure_ascii=False)

        # index: из function или порядковый
        index = func.get("index", i)

        # id: из Ollama или генерируем
        call_id = tc.get("id", f"call_{uuid.uuid4().hex[:8]}")

        openai_calls.append({
            "index": index,
            "id": call_id,
            "type": "function",
            "function": {
                "name": func.get("name", ""),
                "arguments": args_str,
            },
        })

    return openai_calls


# ---------------------------------------------------------------------------
# Построение OpenAI-ответов
# ---------------------------------------------------------------------------


def build_openai_response(ollama_resp: dict, effort: str,
                          request_id: str) -> dict:
    """
    Non-stream OpenAI response.
    Этап 7: поддержка tool_calls в message и finish_reason.
    """
    msg = ollama_resp.get("message", {})
    content, reasoning_content = extract_content_and_reasoning(msg, effort)
    prompt_tokens, answer_tokens, reasoning_tokens = estimate_token_split(
        ollama_resp)

    # Определяем наличие tool_calls
    ollama_tool_calls = msg.get("tool_calls")
    has_tool_calls = bool(ollama_tool_calls)

    message_payload: dict = {"role": "assistant", "content": content}
    if reasoning_content is not None:
        message_payload["reasoning_content"] = reasoning_content

    # Этап 7: добавляем tool_calls в message
    if has_tool_calls:
        message_payload["tool_calls"] = convert_ollama_tool_calls_to_openai(
            ollama_tool_calls)
        # OpenAI: content может быть null при tool_calls
        if not content.strip():
            message_payload["content"] = None

    finish_reason = "tool_calls" if has_tool_calls else "stop"

    return {
        "id": request_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": ollama_resp.get("model", ""),
        "system_fingerprint": None,
        "service_tier": None,
        "choices": [{
            "index": 0,
            "message": message_payload,
            "finish_reason": finish_reason,
        }],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": answer_tokens,
            "total_tokens": prompt_tokens + answer_tokens,
            "completion_tokens_details": {
                "reasoning_tokens": reasoning_tokens,
            },
        },
    }


def format_sse_chunk(request_id: str, model: str, delta: dict,
                     finish_reason: Optional[str] = None,
                     usage: Optional[dict] = None) -> str:
    """P1/P5: system_fingerprint и service_tier в каждом чанке."""
    chunk: dict = {
        "id": request_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "system_fingerprint": None,
        "service_tier": None,
        "choices": [{
            "index": 0,
            "delta": delta,
            "finish_reason": finish_reason,
        }],
    }
    if usage is not None:
        chunk["usage"] = usage
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"


async def stream_generator(resp: httpx.Response, effort: str,
                           request_id: str, model: str):
    """
    Генератор SSE-чанков из Ollama streaming response.
    Этап 7: поддержка tool_calls в stream-чанках.

    Ollama отдаёт tool_calls целиком в одном чанке (не потоково).
    Конвертируем в формат OpenAI и пробрасываем через delta.
    finish_reason: "tool_calls" если были tool_calls, иначе "stop".
    """
    yield format_sse_chunk(request_id, model, delta={"role": "assistant"})

    total_thinking_len = 0
    total_content_len = 0
    has_tool_calls = False

    async for line in resp.aiter_lines():
        line = line.strip()
        if not line:
            continue
        try:
            chunk = json.loads(line)
        except json.JSONDecodeError:
            continue

        if chunk.get("done", False):
            prompt_tokens = chunk.get("prompt_eval_count", 0) or 0
            eval_count = chunk.get("eval_count", 0) or 0

            total_len = total_thinking_len + total_content_len
            if total_len > 0 and total_thinking_len > 0:
                reasoning_tokens = int(
                    eval_count * total_thinking_len / total_len)
                answer_tokens = eval_count - reasoning_tokens
            else:
                reasoning_tokens = 0
                answer_tokens = eval_count

            usage = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": answer_tokens,
                "total_tokens": prompt_tokens + answer_tokens,
                "completion_tokens_details": {
                    "reasoning_tokens": reasoning_tokens,
                },
            }
            finish_reason = "tool_calls" if has_tool_calls else "stop"
            yield format_sse_chunk(request_id, model, delta={},
                                   finish_reason=finish_reason, usage=usage)
            yield "data: [DONE]\n\n"
            break

        msg = chunk.get("message", {})

        # Этап 7: обработка tool_calls в stream-чанках
        ollama_tool_calls = msg.get("tool_calls")
        if ollama_tool_calls:
            has_tool_calls = True
            openai_tool_calls = convert_ollama_tool_calls_to_openai(
                ollama_tool_calls)
            yield format_sse_chunk(
                request_id, model,
                delta={"tool_calls": openai_tool_calls})
            logger.info("REQ %s tool_calls detected: %d call(s)",
                        request_id, len(openai_tool_calls))
            continue

        thinking_piece = msg.get("thinking", "") or ""
        content_piece = msg.get("content", "") or ""

        total_thinking_len += len(thinking_piece)
        total_content_len += len(content_piece)

        if thinking_piece and not content_piece:
            if effort in ("medium", "high"):
                yield format_sse_chunk(
                    request_id, model,
                    delta={"reasoning_content": thinking_piece})
            continue

        if content_piece:
            yield format_sse_chunk(
                request_id, model, delta={"content": content_piece})


# ---------------------------------------------------------------------------
# Утилита: парсинг Ollama timestamp (P6)
# ---------------------------------------------------------------------------


def parse_ollama_timestamp(modified_at: str) -> int:
    """
    ISO datetime из Ollama → Unix timestamp.
    Ollama: "2026-03-15T10:30:00.123456789+03:00" (наносекунды).
    Python datetime max 6 знаков дробной части → обрезаем.
    """
    if not modified_at:
        return int(time.time())
    try:
        s = modified_at
        # Обрезаем дробную часть секунд до 6 знаков
        dot_pos = s.find(".")
        if dot_pos != -1:
            # Найти конец дробной части (до + или - или Z)
            end = dot_pos + 1
            while end < len(s) and s[end].isdigit():
                end += 1
            frac = s[dot_pos + 1:end]
            frac = frac[:6].ljust(6, "0")
            s = s[:dot_pos + 1] + frac + s[end:]
        dt = datetime.fromisoformat(s)
        return int(dt.timestamp())
    except (ValueError, TypeError, OverflowError):
        return int(time.time())


# ---------------------------------------------------------------------------
# Маршруты
# ---------------------------------------------------------------------------


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    effort = resolve_effort(request)
    think_enabled = effort != "none"
    request_id = f"ollama-chat-{uuid.uuid4().hex}"
    ollama_payload = build_ollama_payload(request, think_enabled)

    logger.info("REQ %s model=%s stream=%s effort=%s",
                request_id, request.model, request.stream, effort)
    logger.debug("REQ %s options=%s",
                 request_id, ollama_payload.get("options", {}))

    has_openai_penalties = (request.frequency_penalty is not None
                           or request.presence_penalty is not None)
    if request.repeat_penalty is not None and has_openai_penalties:
        logger.warning(
            "REQ %s both repeat_penalty and frequency/presence_penalty set",
            request_id)

    try:
        if request.stream:
            # ------ Этап 6: настоящий стриминг ------
            resp = await ollama_stream_with_retry(
                OLLAMA_CHAT_URL, ollama_payload, request_id)
            return StreamingResponse(
                stream_generator(resp, effort, request_id, request.model),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache",
                         "X-Accel-Buffering": "no"},
                background=BackgroundTask(resp.aclose))
        else:
            # ------ Non-stream: без изменений ------
            resp = await ollama_post_with_retry(
                OLLAMA_CHAT_URL, ollama_payload, request_id)
            ollama_data = resp.json()
            return build_openai_response(ollama_data, effort, request_id)

    except httpx.HTTPStatusError as e:
        error_body = {}
        try:
            error_body = e.response.json() if e.response else {}
        except Exception:
            error_body = {"error": str(e)}
        status_code = e.response.status_code if e.response else 502
        raise classify_ollama_error(status_code, error_body, request_id)

    except GatewayError:
        raise

    except Exception as e:
        logger.exception("REQ %s unexpected error: %s", request_id, e)
        raise GatewayError(
            500, f"Internal gateway error: {type(e).__name__}: {e}",
            "server_error", "internal_error")


@app.get("/v1/models")
async def list_models():
    """P6: парсинг modified_at вместо time.time()."""
    try:
        resp = await client.get(OLLAMA_TAGS_URL)
        resp.raise_for_status()
        data = resp.json()
    except httpx.RequestError as e:
        raise GatewayError(
            502, f"Cannot connect to Ollama: {type(e).__name__}: {e}",
            "server_error", "ollama_unavailable")
    except httpx.HTTPStatusError as e:
        raise GatewayError(
            502, f"Ollama error fetching models: {e}",
            "server_error", "ollama_error")

    openai_models = []
    for m in data.get("models", []):
        name = m.get("name", "")
        created = parse_ollama_timestamp(m.get("modified_at", ""))
        openai_models.append({
            "id": name,
            "object": "model",
            "created": created,
            "owned_by": "ollama",
            "permission": [],
            "root": name,
            "parent": None,
        })

    return {"object": "list", "data": openai_models}


@app.get("/health")
async def health():
    result = {
        "gateway": "ok",
        "version": "0.7.0",
        "ollama": "unknown",
        "models_count": 0,
        "auth_enabled": bool(GATEWAY_API_KEY),
        "timestamp": int(time.time()),
    }
    try:
        resp = await client.get(OLLAMA_TAGS_URL)
        resp.raise_for_status()
        data = resp.json()
        result["ollama"] = "ok"
        result["models_count"] = len(data.get("models", []))
    except Exception as e:
        result["ollama"] = f"error: {type(e).__name__}: {e}"
    return result
```

## Приложение B — Полный config.yaml Continue

Файл: `%USERPROFILE%\.continue\config.yaml` (Windows) или `~/.continue/config.yaml` (Linux/Mac).

```yaml
name: Lab RTX3090
version: 0.0.1
schema: v1

context:
  - provider: code
  - provider: repo-map
  - provider: file
  - provider: currentFile
  - provider: open
  - provider: diff
  - provider: terminal
  - provider: tree
  - provider: problems
  - provider: clipboard
  - provider: os

models:
  - name: embedder
    provider: transformers.js
    model: all-MiniLM-L6-v2
    roles:
      - embed

  - name: autocomplete
    provider: ollama
    model: qwen2.5-coder:7b
    apiBase: http://192.168.0.128:11434
    roles:
      - autocomplete
    requestOptions:
      timeout: 30000
    autocompleteOptions:
      debounceDelay: 500
      maxPromptTokens: 2048
      multilineCompletions: auto
      modelTimeout: 30000

  - name: qwen35-9b
    provider: openai
    model: qwen3.5:9b
    apiBase: http://192.168.0.128:8000/v1
    apiKey: ollama
    capabilities:
      - image_input
    roles:
      - chat
      - edit
      - apply
    defaultCompletionOptions:
      temperature: 0.7
    requestOptions:
      timeout: 600000
      extraBodyProperties:
        num_ctx: 8192
        reasoning_effort: "none"

  - name: qwen3-coder
    provider: openai
    model: qwen3-coder:30b
    apiBase: http://192.168.0.128:8000/v1
    apiKey: ollama
    roles:
      - chat
      - edit
      - apply
    defaultCompletionOptions:
      temperature: 0.3
    requestOptions:
      timeout: 600000
      extraBodyProperties:
        num_ctx: 8192
        reasoning_effort: "none"

  - name: glm-flash
    provider: openai
    model: glm-4.7-flash
    apiBase: http://192.168.0.128:8000/v1
    apiKey: ollama
    roles:
      - chat
      - edit
      - apply
    defaultCompletionOptions:
      temperature: 0.7
    requestOptions:
      timeout: 600000
      extraBodyProperties:
        num_ctx: 8192
        reasoning_effort: "none"

  - name: deepseek-r1
    provider: openai
    model: deepseek-r1:32b
    apiBase: http://192.168.0.128:8000/v1
    apiKey: ollama
    roles:
      - chat
    defaultCompletionOptions:
      temperature: 0.6
    requestOptions:
      timeout: 600000
      extraBodyProperties:
        num_ctx: 8192
        reasoning_effort: "medium"

  - name: qwen35
    provider: openai
    model: qwen3.5:35b
    apiBase: http://192.168.0.128:8000/v1
    apiKey: ollama
    capabilities:
      - image_input
    roles:
      - chat
      - edit
      - apply
    defaultCompletionOptions:
      temperature: 0.7
    requestOptions:
      timeout: 600000
      extraBodyProperties:
        num_ctx: 8192
        reasoning_effort: "none"

  - name: qwen3-vl
    provider: openai
    model: qwen3-vl:8b
    apiBase: http://192.168.0.128:8000/v1
    apiKey: ollama
    capabilities:
      - image_input
    roles:
      - chat
    defaultCompletionOptions:
      temperature: 0.5
    requestOptions:
      timeout: 600000
      extraBodyProperties:
        num_ctx: 8192
        reasoning_effort: "none"

prompts:
  - name: review
    description: Code review with actionable feedback
    prompt: |
      Review the provided code. For each issue found:
      1. State the problem clearly.
      2. Explain why it matters (bug, performance, readability, security).
      3. Show the fix.
      Focus on: bugs, error handling, edge cases, readability, naming.
      Skip praise and generic advice. Only flag real issues.

  - name: refactor
    description: Refactor code for clarity and maintainability
    prompt: |
      Refactor the provided code. Requirements:
      - Improve readability and structure without changing behavior.
      - Extract repeated logic into functions if appropriate.
      - Simplify conditionals and reduce nesting.
      - Improve naming where it helps clarity.
      Show the refactored code, then briefly list what changed and why.

  - name: docstring
    description: Generate documentation for functions and classes
    prompt: |
      Write documentation for the provided code:
      - For Python: Google-style docstrings with Args, Returns, Raises sections.
      - For JavaScript: JSDoc format with @param, @returns, @throws tags.
      - For other languages: use the conventional doc format.
      Include a one-line summary, then details only if the function is non-trivial.
      Do not restate what is obvious from the signature.

  - name: commit
    description: Generate a commit message from current changes
    prompt: |
      Write a git commit message for the provided diff. Follow conventional commits format:
          type(scope): short description
          Optional body with details.
      Types: feat, fix, refactor, docs, style, test, chore, perf.
      Scope: the module or area affected.
      Description: imperative mood, lowercase, no period at the end.
      Output only the commit message, nothing else.

  - name: explain
    description: Explain how the selected code works
    prompt: |
      Explain the provided code step by step:
      1. What does this code do overall (one sentence).
      2. Walk through the logic, explaining each significant block.
      3. Note any non-obvious patterns, tricks, or potential pitfalls.
      Assume the reader is a developer who understands the language but is new to this codebase.

  - name: tests
    description: Generate high-value unit tests for the selected code
    prompt: |
      Write unit tests for the provided code:
      - Focus on behavior, not implementation details.
      - Cover both happy path and important edge cases.
      - Use the existing testing framework if detectable, otherwise common style for the language.
      - Group logically, clear test names, Arrange-Act-Assert structure.
      After tests, briefly list what is covered and what edge cases could be added later.
```

---

## Приложение C — Rule-файлы

### C.1. Глобальный rule: `%USERPROFILE%\.continue\rules\01-general.md`

```markdown
---
name: General Guidelines
alwaysApply: true
---

## Environment
- Server: Ubuntu 22.04, RTX 3090 (24 GB VRAM), 62 GB RAM
- Client: Windows 11, VS Code + Continue.dev
- Language: Respond in Russian by default. Use English for code, comments, and technical terms.

## Style
- Be concise and direct. Skip introductions and pleasantries.
- When suggesting changes, show the complete modified code, not fragments.
- Explain architectural decisions, not just "what to type".
- If uncertain, say so explicitly rather than guessing.
```

### C.2. Глобальный rule: `%USERPROFILE%\.continue\rules\02-coding.md`

```markdown
---
name: Coding Standards
alwaysApply: true
---

## Python
- Python 3.10+. Type hints for function signatures.
- Docstrings: Google style (Args, Returns, Raises).
- Logging via `logging` module, not `print()`.
- Error handling: specific exceptions, not bare `except`.

## General
- UTF-8 everywhere. LF line endings.
- Meaningful variable names. No single-letter names except loop counters.
- Comments explain "why", not "what".
- Functions: single responsibility, < 50 lines preferred.
```

### C.3. Проектный rule (шаблон): `<workspace>\.continue\rules\01-project.md`

```markdown
---
name: Project Architecture
alwaysApply: true
---

## Stack
- Backend: FastAPI + httpx + Pydantic
- LLM: Ollama (local), accessed via gateway.py proxy
- Config: YAML (Continue config), INI (systemd overrides)

## Naming
- Python: snake_case for functions/variables, PascalCase for classes
- Files: lowercase with underscores
- Constants: UPPER_SNAKE_CASE

## Project structure
- gateway.py: single-file FastAPI application
- No ORM, no database — stateless proxy
```

Замените содержимое под свой проект. `alwaysApply: true` — правило добавляется в каждый запрос. Подхватывается после `Developer: Reload Window`.

---

## Приложение D — Тестовые curl-команды

Все команды выполняются с клиентской машины. Замените `192.168.0.128` на IP вашего сервера.

```bash
#!/bin/bash
# test_all.sh — полный набор проверок

SERVER="http://192.168.0.128:8000"
OLLAMA="http://192.168.0.128:11434"

echo "=== 1. Health check ==="
curl -s $SERVER/health | python3 -m json.tool

echo ""
echo "=== 2. Models list ==="
curl -s $SERVER/v1/models | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data['data']:
    print(f\"  {m['id']}\")
print(f\"Total: {len(data['data'])}\")
"

echo ""
echo "=== 3. Non-stream chat ==="
curl -s $SERVER/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.5:9b","messages":[{"role":"user","content":"What is 2+2? One word."}],"stream":false,"temperature":0,"reasoning_effort":"none"}' \
  | python3 -c "
import sys, json
r = json.load(sys.stdin)
print(f\"Content: {r['choices'][0]['message']['content']}\")
print(f\"Tokens: {r['usage']}\")
"

echo ""
echo "=== 4. Stream TTFT ==="
START=$(date +%s%3N)
curl -s $SERVER/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.5:9b","messages":[{"role":"user","content":"Count 1 to 5"}],"stream":true,"reasoning_effort":"none"}' \
  | head -1
END=$(date +%s%3N)
echo "TTFT: $((END - START)) ms"

echo ""
echo "=== 5. 404 model not found ==="
curl -s -w "\nHTTP: %{http_code}\n" $SERVER/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"nonexistent-42","messages":[{"role":"user","content":"test"}]}'

echo ""
echo "=== 6. 422 validation ==="
curl -s -w "\nHTTP: %{http_code}\n" $SERVER/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.5:9b","messages":[{"role":"user","content":"test"}],"temperature":5.0}'

echo ""
echo "=== 7. Tool calling ==="
curl -s $SERVER/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3-coder:30b","messages":[{"role":"user","content":"List files"}],"stream":true,"tools":[{"type":"function","function":{"name":"run_command","description":"Run shell command","parameters":{"type":"object","properties":{"command":{"type":"string"}}}}}],"reasoning_effort":"none"}' \
  2>/dev/null | grep -o '"tool_calls"' | head -1
echo "(expected: tool_calls found)"

echo ""
echo "=== 8. Ollama direct (FIM sanity) ==="
curl -s $OLLAMA/api/tags | python3 -c "
import sys, json
models = json.load(sys.stdin)['models']
print(f\"Ollama models: {len(models)}\")
"
```

---

## Приложение E — Ollama systemd override

Файл: `/etc/systemd/system/ollama.service.d/override.conf`

```ini
[Service]
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
Environment="OLLAMA_MAX_LOADED_MODELS=2"
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="CUDA_VISIBLE_DEVICES=0"
Environment="GGML_CUDA_NO_GRAPHS=1"
```

После изменения:

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

---

## Приложение F — VS Code settings.json (Copilot BYOK)

Добавить в `settings.json` (дополнительно к другим настройкам):

```json
{
  "github.copilot.chat.byok.ollamaEndpoint": "http://192.168.0.128:11434",

  "oaicopilot.baseUrl": "http://192.168.0.128:8000/v1",
  "oaicopilot.models": [
    {
      "id": "qwen3-coder:30b",
      "owned_by": "ollama",
      "context_length": 8192,
      "temperature": 0.3
    },
    {
      "id": "qwen3.5:9b",
      "owned_by": "ollama",
      "context_length": 8192,
      "temperature": 0.7
    },
    {
      "id": "glm-4.7-flash",
      "owned_by": "ollama",
      "context_length": 8192,
      "temperature": 0.7
    }
  ]
}
```

Необходимые расширения VS Code:

| Расширение | ID | Назначение |
|---|---|---|
| GitHub Copilot | `github.copilot` | Базовое расширение Copilot |
| GitHub Copilot Chat | `github.copilot-chat` | Чат-интерфейс Copilot |
| OAI Compatible Provider | `johnny-zhao.oai-compatible-copilot` | OpenAI-совместимый провайдер (Путь C) |

---

## Приложение G — Справочник моделей

### G.1. Полная таблица (13 моделей)

| # | Модель | Размер на диске | Архитектура | Параметры | Контекст (макс.) | Capabilities |
|---|---|---|---|---|---|---|
| 1 | qwen3.5:35b | 23 ГБ | qwen35moe (MoE) | 36B | 262144 | completion, vision, tools*, thinking |
| 2 | qwen3.5:9b | 6.6 ГБ | qwen35 (Dense) | 9.7B | 262144 | completion, vision, tools**, thinking |
| 3 | deepseek-r1:32b | 19 ГБ | deepseek2 | 32B | 131072 | completion, thinking |
| 4 | deepseek-r1:14b | 9.0 ГБ | deepseek2 | 14B | 131072 | completion, thinking |
| 5 | qwen3:30b | 18 ГБ | qwen3 | 30B | 40960 | completion, tools |
| 6 | qwen3:14b | 9.3 ГБ | qwen3 | 14B | 40960 | completion, tools |
| 7 | qwen3-coder:30b | 18 ГБ | qwen3 | 30B | 40960 | completion, tools ✅ |
| 8 | glm-4.7-flash | 19 ГБ | glm4moelite (MoE) | 29.9B (3B актив.) | 202752 | completion, tools ✅, thinking |
| 9 | qwen2.5-coder:7b | 4.7 ГБ | qwen2 | 7B | 32768 | completion, FIM ✅ |
| 10 | qwen2.5-coder:1.5b | 986 МБ | qwen2 | 1.5B | 32768 | completion, FIM ✅ |
| 11 | deepseek-coder-v2:16b | 8.9 ГБ | deepseek2 | 16B | 131072 | completion |
| 12 | qwen3-vl:8b | 6.1 ГБ | qwen3vl | 8B | 32768 | completion, vision ✅ |
| 13 | qwen3-embedding | 4.7 ГБ | qwen3 | — | — | embedding |

\* tools у qwen3.5:35b **сломаны** в Ollama (issues #14493, #14745). Неправильный parser pipeline (Hermes JSON вместо Qwen-Coder XML).

\** tools у qwen3.5:9b работают с оговорками — не всегда надёжно.

### G.2. Квантизация

Все модели используют Q4_K_M квантизацию (кроме deepseek-coder-v2 — Q4_0). Q4_K_M — это 4-bit квантизация с k-quants оптимизацией, баланс между размером и качеством.

### G.3. Рекомендации по памяти

| Пара моделей (одновременно) | Примерный расход VRAM+RAM | Подходит для |
|---|---|---|
| qwen3.5:9b + qwen2.5-coder:7b | ~14 ГБ | Повседневная работа |
| qwen3-coder:30b + qwen2.5-coder:7b | ~25 ГБ | Agent + autocomplete |
| deepseek-r1:32b + qwen2.5-coder:7b | ~27 ГБ | Reasoning + autocomplete |
| qwen3.5:35b + qwen2.5-coder:7b | ~30 ГБ | Experimental + autocomplete |

При 86 ГБ суммарной памяти — любая пара помещается. При меньшем объёме — выбирайте пару с учётом RAM.

---

## Приложение H — Грабли Continue 1.2.17

Полный список подтверждённых проблем и их решений.

### H.1. Конфигурация

| # | Проблема | Симптом | Решение |
|---|---|---|---|
| 1 | `timeout` в **миллисекундах** | Все запросы таймаутятся (`timeout: 600` = 0.6 сек) | `timeout: 600000` (10 мин для chat), `timeout: 30000` (30 сек для autocomplete) |
| 2 | `extraBodyProperties` **внутри** `requestOptions` | 400 от Ollama: `can't find closing '}'` | Перенести внутрь `requestOptions`, не на уровень модели |
| 3 | **YAML anchors** не работают | Ошибка парсинга `<<: *defaults` | Не использовать anchors. Копировать параметры для каждой модели |
| 4 | **Имена моделей со скобками** | `Invalid input` при парсинге | Имена без скобок и спецсимволов: `qwen35`, не `qwen3.5:35b (reasoning)` |
| 5 | **roles: agent** | Ошибка конфигурации | Не существует. Agent mode использует модель с ролями chat+edit |
| 6 | **tabAutocompleteModel** | Autocomplete не работает | Не существует в YAML schema v1. Autocomplete — через `models` с `roles: [autocomplete]` |
| 7 | **debounce** → **debounceDelay** | Игнорируется | Правильное имя: `debounceDelay` |
| 8 | **Дефолтный таймаут autocomplete ~5 сек** | Холодный старт FIM-модели → abort | `requestOptions.timeout: 30000` + `autocompleteOptions.modelTimeout: 30000` |

### H.2. Embeddings и индексация

| # | Проблема | Симптом | Решение |
|---|---|---|---|
| 9 | `transformers.js` требует поле `model` | `Invalid input` при парсинге | Указать `model: all-MiniLM-L6-v2` явно |
| 10 | Секция `context:` сбрасывает дефолты | Пропадают File, Current File и др. | Перечислить все 11 провайдеров явно |

### H.3. Prompts и Rules

| # | Проблема | Симптом | Решение |
|---|---|---|---|
| 11 | Prompts в `.continue/rules/` | Slash-команды не появляются | Prompts — в `prompts:` config.yaml или `.continue/prompts/`, не в `rules/` |
| 12 | Проектные rules не подхватываются | Rule не виден в UI | `Developer: Reload Window` после создания |

### H.4. Модели и Agent

| # | Проблема | Симптом | Решение |
|---|---|---|---|
| 13 | `capabilities: [tool_use]` | Может сбить автодетекцию | Не указывать — Continue автодетектит |
| 14 | qwen3.5:35b в Agent mode | Мусорный текст / зацикливание | Не использовать для Agent. Только chat |
| 15 | Autocomplete-модель не видна в дропдауне | Кажется, что модель не подключилась | Нормально: роль `autocomplete` не отображается в chat-дропдауне |

### H.5. Диагностика

| # | Проблема | Симптом | Решение |
|---|---|---|---|
| 16 | Network tab не показывает запросы | Не видно HTTP-трафика | Запросы идут из extension host, не из webview. Смотреть логи шлюза |
| 17 | Ошибки конфигурации | Молча не работает | Правый нижний угол VS Code (`⚠ Continue`) + DevTools Console фильтр `continuedev` |

---

## Приложение I — Systemd unit файлы

### I.1. Ollama override

Файл: `/etc/systemd/system/ollama.service.d/override.conf`

Содержимое — см. Приложение E.

### I.2. llm-gateway.service

Файл: `/etc/systemd/system/llm-gateway.service`

```ini
[Unit]
Description=LLM Gateway (OpenAI-compatible proxy for Ollama)
After=network.target ollama.service
Requires=ollama.service

[Service]
Type=simple
User=<ВАШ_ПОЛЬЗОВАТЕЛЬ>
WorkingDirectory=/home/<ВАШ_ПОЛЬЗОВАТЕЛЬ>/llm-gateway
ExecStart=/home/<ВАШ_ПОЛЬЗОВАТЕЛЬ>/llm-gateway/venv/bin/uvicorn gateway:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
```

Замените `<ВАШ_ПОЛЬЗОВАТЕЛЬ>` на имя пользователя на сервере (например, `vladimir`).

Для аутентификации добавьте в секцию `[Service]`:
```ini
Environment="LLM_GATEWAY_API_KEY=ваш-секретный-ключ"
```

Активация:
```bash
sudo systemctl daemon-reload
sudo systemctl enable llm-gateway
sudo systemctl start llm-gateway
```
