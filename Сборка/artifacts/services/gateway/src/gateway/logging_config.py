"""
Конфигурация логирования LLM Gateway — Structured JSON.

Этап 10A-2: Все логи gateway пишутся как single-line JSON → systemd journal.

Архитектура (Схема C по результатам ревью):
  - uvicorn.access ОТКЛЮЧЕН (заменён gateway domain events)
  - uvicorn.error → JSON (startup/shutdown)
  - gateway → JSON (все бизнес-события)
  - Один event per request: llm_completion / llm_embedding
  - Исключения: массив строк внутри JSON (не multiline)

Потребление:
  journalctl -u llm-gateway --output=cat | jq '.'
  journalctl -u llm-gateway --output=cat | jq 'select(.event=="llm_completion")'
"""

import json
import logging
import logging.config
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Определяем стандартные атрибуты LogRecord для фильтрации extras
# ---------------------------------------------------------------------------

_dummy_record = logging.LogRecord("", 0, "", 0, "", (), None)
_RESERVED_ATTRS = set(_dummy_record.__dict__.keys()) | {
    "message",        # добавляется getMessage()
    "taskName",       # Python 3.12+
    "color_message",  # uvicorn иногда добавляет
}
del _dummy_record


# ---------------------------------------------------------------------------
# JSON Formatter
# ---------------------------------------------------------------------------


class JsonFormatter(logging.Formatter):
    """
    Single-line JSON formatter для systemd journal.

    Стандартные поля: timestamp, level, logger, message.
    Extra-поля (переданные через extra={...}): автоматически
    включаются в JSON-объект.
    Исключения: массив строк в поле "exception".
    """

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()

        entry: dict = {
            "timestamp": (
                datetime.fromtimestamp(record.created, tz=timezone.utc)
                .strftime("%Y-%m-%dT%H:%M:%S.")
                + f"{int(record.msecs):03d}Z"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
        }

        # Extra-поля из logger.info("msg", extra={...})
        for key, value in record.__dict__.items():
            if key not in _RESERVED_ATTRS and key not in entry:
                entry[key] = value

        # Исключения — массив строк, не multiline text
        if record.exc_info and record.exc_info[0] is not None:
            entry["exception"] = (
                self.formatException(record.exc_info).splitlines()
            )

        return json.dumps(entry, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Конфигурация логирования (dictConfig формат)
# ---------------------------------------------------------------------------

LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "gateway.logging_config.JsonFormatter",
        },
    },
    "handlers": {
        "json_console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
            "formatter": "json",
        },
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["json_console"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.error": {
            "handlers": ["json_console"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.access": {
            # Подавлен — заменён gateway domain events (Схема C)
            "handlers": ["json_console"],
            "level": "WARNING",
            "propagate": False,
        },
        "gateway": {
            "handlers": ["json_console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


# ---------------------------------------------------------------------------
# Logger-singleton для всех модулей gateway
# ---------------------------------------------------------------------------

logger = logging.getLogger("gateway")
