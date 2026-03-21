import logging
import sys
from typing import Any

import structlog

from app.config import settings


def _add_logger_name(logger: Any, method: str, event_dict: dict) -> dict:
    """Safely add logger name — works with both PrintLogger and stdlib Logger."""
    name = getattr(logger, "name", None)
    if name:
        event_dict["logger"] = name
    return event_dict


def setup_logging() -> None:
    """Configure structlog for structured logging.

    - Development: human-readable colored output with ConsoleRenderer.
    - Production: JSON output suitable for log aggregators (Loki, ELK, etc.).
    """
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        _add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.app_env == "development":
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.debug else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Silence noisy third-party loggers in production
    if settings.app_env != "development":
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
