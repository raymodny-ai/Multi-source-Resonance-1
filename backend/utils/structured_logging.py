"""
Structured logging module using structlog.

Provides JSON-formatted log output with contextual information
(request_id, source, timestamp) for better observability.

Usage:
    from backend.utils.structured_logging import get_logger, setup_logging

    # Initialize once at startup
    setup_logging(log_level="INFO", json_output=True)

    # Get a structured logger
    logger = get_logger(__name__)
    logger.info("pipeline_started", source="gexmetrix", request_id="abc-123")
"""

import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

try:
    import structlog
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False


def setup_logging(
    log_level: str = "INFO",
    json_output: bool = True,
    service_name: str = "multi-source-resonance",
) -> None:
    """Configure structured logging for the application.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR).
        json_output: If True, output JSON format; otherwise, colored console.
        service_name: Service name included in every log entry.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    if HAS_STRUCTLOG:
        # Configure structlog processors
        processors: list[Any] = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _add_request_id,
            _add_service_name(service_name),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
        ]

        if json_output:
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer(colors=True))

        structlog.configure(
            processors=processors,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        # Configure root logger handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        if json_output:
            handler.setFormatter(logging.Formatter("%(message)s"))
        else:
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
                )
            )

        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.addHandler(handler)
        root_logger.setLevel(level)

        # Suppress noisy loggers
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("aiosqlite").setLevel(logging.WARNING)

    else:
        # Fallback: standard logging with JSON formatter
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        if json_output:
            handler.setFormatter(JsonFormatter(service_name))
        else:
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
                )
            )

        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.addHandler(handler)
        root_logger.setLevel(level)

    logging.info(
        "Structured logging initialized",
        extra={"level": log_level, "json_output": json_output},
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    If structlog is available, returns a structlog-wrapped logger.
    Otherwise returns a standard Python logger.

    Args:
        name: Logger name (typically __name__).

    Returns:
        Configured logger instance.
    """
    if HAS_STRUCTLOG:
        return structlog.get_logger(name)
    return logging.getLogger(name)


def bind_context(**kwargs: Any) -> None:
    """Bind contextual key-value pairs to all subsequent log entries.

    Useful for adding request_id, source, user_id to all logs
    within a request scope.

    Args:
        **kwargs: Key-value pairs to bind.

    Example:
        bind_context(request_id="abc-123", source="gexmetrix")
    """
    if HAS_STRUCTLOG:
        structlog.contextvars.bind_contextvars(**kwargs)


def unbind_context(*keys: str) -> None:
    """Remove bound context keys.

    Args:
        *keys: Keys to unbind.
    """
    if HAS_STRUCTLOG:
        structlog.contextvars.unbind_contextvars(*keys)


def clear_context() -> None:
    """Clear all bound context variables."""
    if HAS_STRUCTLOG:
        structlog.contextvars.clear_contextvars()


class RequestContext:
    """Context manager for request-scoped logging context.

    Usage:
        async with RequestContext(request_id="abc", source="pipeline"):
            logger.info("processing")  # includes request_id and source
    """

    def __init__(self, **kwargs: Any):
        self._kwargs = kwargs

    def __enter__(self):
        bind_context(**self._kwargs)
        return self

    def __exit__(self, *args):
        unbind_context(*self._kwargs.keys())

    async def __aenter__(self):
        bind_context(**self._kwargs)
        return self

    async def __aexit__(self, *args):
        unbind_context(*self._kwargs.keys())


# ── Internal helpers ─────────────────────────────────────────────────────────


def _add_request_id(
    logger: Any, method_name: str, event_dict: dict
) -> dict:
    """Add request_id to log entry if not present."""
    if "request_id" not in event_dict:
        event_dict["request_id"] = str(uuid.uuid4())[:8]
    return event_dict


def _add_service_name(service_name: str):
    """Return a processor that adds service name to log entries."""

    def processor(
        logger: Any, method_name: str, event_dict: dict
    ) -> dict:
        event_dict["service"] = service_name
        return event_dict

    return processor


class JsonFormatter(logging.Formatter):
    """Fallback JSON formatter when structlog is not available."""

    def __init__(self, service_name: str = "multi-source-resonance"):
        super().__init__()
        self._service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        import json

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self._service_name,
        }

        # Add extra fields
        for key in ["request_id", "source", "event"]:
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False) + "\n"
