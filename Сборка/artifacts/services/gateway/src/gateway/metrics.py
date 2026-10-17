"""
/metrics — In-memory metrics endpoint для LLM Gateway (Этап 10B).

MetricsCollector аккумулирует счётчики из structured log events.
GET /metrics возвращает JSON-снимок текущих значений.

Архитектурные решения:
  - Монотонные счётчики (monotonic counters): только растут, никогда не
    сбрасываются (кроме рестарта процесса). Потребитель метрик вычисляет
    rates через разницу между двумя замерами — стандартный подход
    Prometheus/StatsD.
  - Thread safety: threading.Lock вокруг обновления. В asyncio single-thread
    это формально избыточно, но стоит наносекунды и гарантирует корректность
    при будущем переходе на workers > 1.
  - Интеграция: chat.py и embeddings.py вызывают collector.record(log_data)
    рядом с каждым structured log event. log_data — тот же dict, что идёт
    в logger.info(extra=...).

Формат ответа: JSON (решение ADR — Prometheus text format отложен до этапа 15).
"""

import threading
import time
from typing import Any

from fastapi import APIRouter

from . import VERSION

router = APIRouter()


class MetricsCollector:
    """
    In-memory metrics store.

    Один экземпляр (singleton) на процесс gateway. Счётчики живут
    в памяти — при рестарте обнуляются. Это ожидаемое поведение:
    персистентная история — в structured logs (journalctl).
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._started_at = time.time()

        # --- Global counters ---
        self._total_requests: int = 0
        self._total_errors: int = 0

        # --- Per-endpoint counters ---
        # key: endpoint path, e.g. "/v1/chat/completions"
        self._endpoints: dict[str, dict[str, int]] = {}

        # --- Per-model counters ---
        # key: model name, e.g. "qwen3-coder:30b"
        self._models: dict[str, dict[str, int]] = {}

    # ------------------------------------------------------------------
    # Запись метрики
    # ------------------------------------------------------------------

    def record(self, log_data: dict[str, Any]) -> None:
        """
        Обновить счётчики из structured log event dict.

        Вызывается из chat.py и embeddings.py с тем же dict,
        который передаётся в logger.info(extra=...).

        Извлекаемые поля:
          endpoint, model, status_code, prompt_tokens,
          completion_tokens (только chat), latency_ms.
        """
        endpoint = log_data.get("endpoint", "unknown")
        model = log_data.get("model", "unknown")
        status_code = log_data.get("status_code", 0)
        prompt_tokens = log_data.get("prompt_tokens", 0) or 0
        completion_tokens = log_data.get("completion_tokens", 0) or 0
        latency_ms = log_data.get("latency_ms", 0) or 0
        is_error = status_code >= 400

        with self._lock:
            # Global
            self._total_requests += 1
            if is_error:
                self._total_errors += 1

            # Endpoint
            ep = self._endpoints.setdefault(endpoint, {
                "requests": 0,
                "errors": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "latency_ms_sum": 0,
                "latency_ms_count": 0,
            })
            ep["requests"] += 1
            if is_error:
                ep["errors"] += 1
            ep["total_prompt_tokens"] += prompt_tokens
            ep["total_completion_tokens"] += completion_tokens
            ep["latency_ms_sum"] += latency_ms
            ep["latency_ms_count"] += 1

            # Model
            md = self._models.setdefault(model, {
                "requests": 0,
                "total_tokens": 0,
                "errors": 0,
            })
            md["requests"] += 1
            md["total_tokens"] += prompt_tokens + completion_tokens
            if is_error:
                md["errors"] += 1

    # ------------------------------------------------------------------
    # Снимок метрик
    # ------------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        """
        Текущее состояние всех счётчиков.

        Возвращает dict, готовый к JSON-сериализации через FastAPI.
        Все значения — копии (snapshot), не ссылки на внутренние структуры.
        """
        with self._lock:
            return {
                "gateway_version": VERSION,
                "uptime_seconds": int(time.time() - self._started_at),
                "started_at": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime(self._started_at)
                ),
                "totals": {
                    "requests": self._total_requests,
                    "errors": self._total_errors,
                },
                "endpoints": {
                    ep: dict(counters)
                    for ep, counters in self._endpoints.items()
                },
                "models": {
                    m: dict(counters)
                    for m, counters in self._models.items()
                },
            }


# ------------------------------------------------------------------
# Singleton — один экземпляр на процесс
# ------------------------------------------------------------------

collector = MetricsCollector()


# ------------------------------------------------------------------
# Маршрут
# ------------------------------------------------------------------


@router.get("/metrics")
async def get_metrics():
    """
    GET /metrics — JSON-снимок in-memory счётчиков.

    Не требует аутентификации (освобождён в auth_middleware, как /health).
    Счётчики обнуляются при рестарте gateway — это ожидаемое поведение.
    """
    return collector.snapshot()
