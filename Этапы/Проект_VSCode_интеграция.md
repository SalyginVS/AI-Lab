# Проект: VS Code ↔ LLM Gateway — Интеграция и сценарии использования

**Дата:** 2026-03-16
**Шлюз:** gateway.py v0.6.0 на http://192.168.0.128:8000
**Задача:** подключить VS Code к локальному LLM-серверу и задействовать все возможности шлюза

---

## 1. Обзор доступных инструментов интеграции

### 1A. Continue.dev (рекомендуемый, основной)

Open-source AI-ассистент (расширение VS Code). Поддерживает OpenAI-совместимые эндпоинты «из коробки» через provider: openai + apiBase. Конфигурируется через `~/.continue/config.yaml` (новый формат, заменил config.json).

Возможности: chat в боковой панели, inline edit (выделить код → «исправь/объясни/рефактори»), autocomplete (tab-completion при наборе кода), Agent mode (многошаговые задачи), context providers (файлы, diff, терминал, codebase).

Совместимость с gateway.py v0.6.0: полная. Continue использует POST /v1/chat/completions (stream и non-stream), GET /v1/models. Поддерживает Bearer auth через apiKey. Настоящий стриминг (Этап 6) критичен — без него UX в чате неприемлемый (ожидание минуты до ответа).

### 1B. VS Code Copilot Chat — BYOK / OpenAI Compatible

С версии VS Code 1.99+ (март 2025) Copilot Chat поддерживает BYOK (Bring Your Own Key) — можно подключить Ollama и другие провайдеры. С версии 1.104+ (VS Code Insiders, октябрь 2025) добавлен провайдер «OpenAI Compatible» — произвольный OpenAI-совместимый эндпоинт через `github.copilot.chat.customOAIModels`.

Статус на март 2026: OpenAI Compatible доступен в VS Code Insiders. В стабильном VS Code может уже быть (зависит от версии). Доступен только для индивидуальных Copilot-планов (Free, Pro, Pro+), НЕ для Business/Enterprise. Требует GitHub Copilot extension.

Альтернатива: расширение «OAI Compatible Provider for Copilot» (JohnnyZ93/oai-compatible-copilot) — подключает любой OpenAI-совместимый endpoint в Copilot Chat, включая vision и thinking-модели.

### 1C. AI Toolkit for VS Code (Microsoft)

Официальное расширение Microsoft. Поддерживает Ollama и Custom OpenAI-compatible endpoints. Может использовать модели в Playground и Agent Builder. Менее гибкий для повседневной работы с кодом, чем Continue, но полезен для экспериментов с моделями.

### 1D. Другие расширения

CodeGPT, Local-AI-Assistant, chatllm-vscode — менее зрелые, но совместимы с OpenAI API. Не рекомендую как основные.

---

## 2. Сценарии использования

### Сценарий A — Chat (чат с моделью в боковой панели)

Пользователь задаёт вопросы по коду, архитектуре, просит объяснения. Модель видит контекст (выделенный код, открытые файлы, diff).

Требования к шлюзу: POST /v1/chat/completions (stream=true), GET /v1/models. Настоящий стриминг (Этап 6) — ответ появляется посимвольно.

Рекомендуемые модели: qwen3.5:35b (reasoning, глубокий анализ), qwen3:30b или qwen3:14b (быстрые ответы).

Конфигурация reasoning: effort=medium для сложных вопросов (Continue может передавать через extraBodyProperties).

### Сценарий B — Inline Edit (редактирование кода по запросу)

Пользователь выделяет код, даёт инструкцию («рефактори», «добавь обработку ошибок», «напиши тесты»). Модель генерирует изменённый код.

Требования: POST /v1/chat/completions (non-stream или stream). Модель должна хорошо следовать инструкциям.

Рекомендуемые модели: qwen3-coder:30b (оптимизирована под код), qwen3.5:35b (reasoning для сложного рефакторинга).

### Сценарий C — Tab Autocomplete (автодополнение при наборе)

При наборе кода в редакторе VS Code подсказывает продолжение (серым текстом, нажатие Tab для принятия). Требует быстрого ответа (<1 сек) и небольшой модели.

Требования: POST /v1/chat/completions (stream=false, max_tokens=50-200, temperature=0.0-0.3). Очень чувствительно к латентности — для 35B модели с cold start это будет медленно.

Рекомендуемые модели: qwen3:14b (быстрая, ~1-2 сек), deepseek-coder-v2:16b (код-ориентированная). НЕ рекомендуется qwen3.5:35b для autocomplete — слишком медленная для real-time.

Ограничение: Ollama с OLLAMA_NUM_PARALLEL=1 обрабатывает один запрос за раз. Если идёт chat-запрос — autocomplete будет ждать в очереди. Это inherent limitation одной GPU.

### Сценарий D — Agent Mode (многошаговые задачи)

Continue Agent mode: модель может читать файлы, запускать терминальные команды, вносить изменения в несколько файлов. Требует tool_use capability.

Требования: POST /v1/chat/completions с tools/tool_choice (Этап 5). Модель должна поддерживать function calling.

Рекомендуемые модели: qwen3.5:35b (reasoning + tools), qwen3-coder:30b (если поддерживает function calling).

Статус: tools passthrough реализован в gateway.py (Этап 5). Работоспособность зависит от того, поддерживает ли конкретная модель в Ollama function calling — нужно тестировать.

### Сценарий E — Мультимодальный (Vision)

Пользователь отправляет скриншот UI/диаграмму и просит описать, сгенерировать код по макету.

Требования: POST /v1/chat/completions с content: [{type: "image_url", ...}] (Этап 5). Модель qwen3-vl:8b.

Ограничение: qwen3-vl:8b — маленькая модель (8B), качество будет ограниченным. Для серьёзной vision-работы нужны более крупные мультимодальные модели.

### Сценарий F — Embeddings и Codebase Search (RAG)

Continue поддерживает codebase context provider — индексирует файлы проекта и ищет релевантный код для контекста. Для этого нужен embeddings-эндпоинт.

Требования: POST /v1/embeddings (отсутствует в gateway.py). Модель qwen3-embedding.

Статус: НЕ реализовано в текущем шлюзе. Требует нового эндпоинта. Можно обойти — Continue может использовать Ollama напрямую для embeddings (provider: ollama, apiBase: http://192.168.0.128:11434).

---

## 3. Архитектура подключения

```
VS Code (клиентская машина)
  ├── Continue.dev extension
  │     ├── Chat/Edit/Agent → gateway.py :8000 /v1/chat/completions
  │     ├── Model list     → gateway.py :8000 /v1/models
  │     ├── Autocomplete   → gateway.py :8000 /v1/chat/completions
  │     └── Embeddings     → Ollama :11434 /api/embed (напрямую)
  │
  └── [Опционально] Copilot Chat + OpenAI Compatible
        └── Chat           → gateway.py :8000 /v1/chat/completions
```

Ключевое: основной инструмент — Continue.dev. Copilot Chat с OpenAI Compatible — дополнительная опция для тех, кто привык к Copilot UI.

---

## 4. План реализации

### Этап 7A — Continue.dev: Chat + Edit (базовый)

Установка Continue, создание config.yaml с подключением к gateway.py. Настройка нескольких моделей с разными ролями. Проверка: chat в боковой панели, inline edit, /v1/models показывает модели.

Тесты:
1. Chat: задать вопрос по коду — получить streaming-ответ
2. Edit: выделить функцию → «добавь docstring» → получить изменённый код
3. Переключение моделей: qwen3:14b ↔ qwen3.5:35b
4. Reasoning: проверить что effort передаётся через extraBodyProperties

### Этап 7B — Continue.dev: Autocomplete (tab-completion)

Настройка быстрой модели для autocomplete. Оптимизация параметров (debounce, maxPromptTokens, temperature). Проверка латентности.

Тесты:
1. Набрать начало функции — получить предложение автодополнения
2. Замер латентности (должна быть <2 сек для qwen3:14b)
3. Проверка что autocomplete не блокирует chat (или наоборот — с NUM_PARALLEL=1 это будет)

### Этап 7C — Continue.dev: Agent + Context Providers

Настройка context providers (file, code, diff, terminal). Тест agent mode с tool_use (если модель поддерживает). Настройка кастомных промптов (rules, prompts в config.yaml).

### Этап 7D — Copilot Chat: OpenAI Compatible (опционально)

Настройка VS Code Copilot BYOK с OpenAI Compatible provider. Проверка работоспособности через github.copilot.chat.customOAIModels или расширение oai-compatible-copilot.

### Этап 7E — Embeddings для codebase search (если нужно)

Добавление /v1/embeddings в gateway.py. Или прямое подключение Continue к Ollama для embeddings.

---

## 5. Ограничения и риски

| Ограничение | Влияние | Митигация |
|---|---|---|
| OLLAMA_NUM_PARALLEL=1 | Autocomplete и chat конкурируют за GPU | Использовать быструю модель (14b) для autocomplete, либо отключить autocomplete при активном chat |
| Холодный старт модели (~8-30 сек) | Первый запрос после переключения модели медленный | Работать с одной моделью, не переключаться часто |
| 24 ГБ VRAM | Только одна большая модель (30-35B) в памяти | OLLAMA_MAX_LOADED_MODELS=1 уже настроено |
| Autocomplete латентность | 35B модель слишком медленная для tab-completion | Использовать 14B или 16B для autocomplete |
| Function calling | Не все модели в Ollama поддерживают tools | Тестировать конкретные модели; qwen3.5:35b и qwen3-coder:30b наиболее вероятно поддерживают |

---

## 6. Рекомендуемая модельная раскладка

| Роль | Модель | Почему |
|---|---|---|
| Chat (общий) | qwen3:14b | Быстрая, хороша для простых вопросов |
| Chat (сложный) | qwen3.5:35b | Reasoning, глубокий анализ, но медленнее |
| Edit / Refactor | qwen3-coder:30b | Оптимизирована под код |
| Autocomplete | qwen3:14b | Баланс скорости и качества |
| Agent (tools) | qwen3.5:35b | Reasoning + function calling |
| Vision | qwen3-vl:8b | Единственная vision-модель |
| Embeddings | qwen3-embedding | Единственная embedding-модель |

---

## 7. Начинаем с Этапа 7A

Предлагаю начать с базовой настройки Continue.dev — это даст рабочий Chat + Edit за один шаг. Артефакт: config.yaml для Continue, инструкция по установке и проверке.
