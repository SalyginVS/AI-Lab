#!/usr/bin/env python3
"""
LLM Gateway — entrypoint.

Запуск:
  cd ~/llm-gateway && source venv/bin/activate
  python run.py

Или напрямую через uvicorn:
  uvicorn gateway.app:app --host 0.0.0.0 --port 8000

Примечание: при запуске через uvicorn напрямую JSON logging
НЕ активируется (используется default uvicorn config).
Для JSON logging запускать через python run.py.
"""

import uvicorn

from gateway.logging_config import LOGGING_CONFIG

if __name__ == "__main__":
    uvicorn.run(
        "gateway.app:app",
        host="0.0.0.0",
        port=8000,
        log_config=LOGGING_CONFIG,
        access_log=False,  # Схема C: stock access log отключен
    )
