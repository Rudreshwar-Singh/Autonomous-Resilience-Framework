"""
Structured Logging Module
=========================
Configures Python's stdlib logging to output structured JSON log lines.

WHY STDLIB OVER LOGURU:
    1. FastAPI and Uvicorn natively integrate with stdlib logging. Using
       loguru would require intercepting Uvicorn's internal logger — adding
       fragile monkey-patching to the boot sequence.
    2. Stdlib logging is zero-dependency and guaranteed stable across
       Python versions.
    3. Structured JSON output is what matters for downstream consumers
       (Kafka, Prometheus, Grafana Loki). The formatter, not the library,
       determines pipeline compatibility.

WHY JSON FORMAT:
    Every log line is a self-contained JSON object with consistent fields
    (timestamp, level, service, message). This means:
    - Kafka consumers can deserialize logs without regex parsing.
    - Prometheus/Grafana can filter and aggregate by any field.
    - Interviewers can see you understand observability pipelines.

FUTURE EXTENSIBILITY:
    - Phase 5: Add a KafkaHandler that publishes log records to a Kafka topic.
    - Phase 6: Attach correlation_id / trace_id fields for distributed tracing.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class StructuredJSONFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON objects.

    Each log line contains a consistent schema that downstream systems
    (Kafka consumers, log aggregators) can reliably parse without regex.

    Output Example:
        {"timestamp": "2026-07-02T00:00:00.000Z", "level": "INFO",
         "service": "arf", "logger": "backend.app.main",
         "message": "Application startup complete"}
    """

    # Short service identifier for log filtering in multi-service setups.
    SERVICE_NAME: str = "arf"

    def format(self, record: logging.LogRecord) -> str:
        """
        Serialize a LogRecord into a structured JSON string.

        Args:
            record: The stdlib LogRecord containing the log event data.

        Returns:
            A single-line JSON string with standardized fields.
        """
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "service": self.SERVICE_NAME,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Attach exception traceback if present (e.g., from logger.exception())
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Attach any extra fields passed via logger.info("msg", extra={...})
        # This enables future phases to inject correlation_id, trace_id, etc.
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_entry["extra"] = record.extra_data

        return json.dumps(log_entry, default=str)


def setup_logging(log_level: str = "DEBUG", log_format: str = "json") -> None:
    """
    Configure the root logger for the entire application.

    This function should be called exactly once during application startup
    (inside the FastAPI lifespan context manager). It configures:
    - The root logger's level and handler.
    - Uvicorn's internal loggers to use the same format for consistency.

    Args:
        log_level: Minimum severity to emit. One of DEBUG, INFO, WARNING,
                   ERROR, CRITICAL. Controlled via settings.LOG_LEVEL.
        log_format: Output format — 'json' for structured pipeline output,
                    'text' for human-readable local development.

    WHY WE CONFIGURE UVICORN LOGGERS:
        Uvicorn creates its own loggers ('uvicorn', 'uvicorn.error',
        'uvicorn.access'). Without explicit reconfiguration, they output
        plain-text lines while our app outputs JSON — creating inconsistent
        log streams. By replacing their handlers, every log line from every
        component follows the same structured format.
    """
    # ── Select formatter based on configuration ───────────────────────
    if log_format == "json":
        formatter: logging.Formatter = StructuredJSONFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # ── Configure the stream handler (stdout) ─────────────────────────
    # Writing to stdout (not stderr) ensures Docker and container
    # orchestrators can capture log output via standard log drivers.
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)

    # ── Apply to root logger ──────────────────────────────────────────
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.DEBUG))
    root_logger.handlers.clear()  # Remove any default handlers
    root_logger.addHandler(handler)

    # ── Unify Uvicorn's loggers with our format ───────────────────────
    for uvicorn_logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(uvicorn_logger_name)
        uv_logger.handlers.clear()
        uv_logger.addHandler(handler)
        uv_logger.propagate = False  # Prevent duplicate lines from root logger
