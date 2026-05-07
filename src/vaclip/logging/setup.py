"""Structured logging configuration for VAClip.

Configures structlog for professional structured logging output.
All VAClip modules should use get_logger() from this module.

Agent Notes:
- Never use print() or bare logging.getLogger() in VAClip code
- Always use logger = get_logger(__name__) at module level
- Use bound loggers for request/run context: logger.bind(run_id=...)
- Verbose mode enables DEBUG level and dev-friendly rendering
- Production mode uses JSON renderer for log aggregation compatibility
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def configure_logging(verbose: bool = False) -> None:
    """Configure structlog and stdlib logging for VAClip.

    Call this once at application startup (in CLI main callback).
    Subsequent calls are safe but redundant.

    Args:
        verbose: If True, set DEBUG level and use console renderer.
                 If False, use INFO level and JSON renderer.
    """
    log_level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=log_level,
    )

    renderer = (
        structlog.dev.ConsoleRenderer(colors=True)
        if verbose
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str, **initial_values: Any) -> structlog.BoundLogger:
    """Get a bound structlog logger for the given module name.

    Usage:
        logger = get_logger(__name__)
        logger.info("processing started", run_id=run_id, source=source)
        logger.warning("low confidence score", score=score)
        logger.error("ingest failed", exc_info=True)

    Args:
        name: Module name (use __name__).
        **initial_values: Key-value pairs to bind to all log events.

    Returns:
        A structlog BoundLogger instance.
    """
    return structlog.get_logger(name).bind(**initial_values)
