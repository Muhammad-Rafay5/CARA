"""
Structured JSON logging configuration for CARA.
Uses structlog for consistent, parseable log output across all modules.
"""

from __future__ import annotations

import logging
import sys

import re

import structlog


# ── Secret Scrubbing Processor ───────────────────────────────────────────────
# Redacts any log event value whose key matches common secret patterns.
_SECRET_KEY_PATTERN = re.compile(
    r"(api[_-]?key|secret|password|token|authorization|credential|auth)",
    re.IGNORECASE,
)
_REDACTED = "[REDACTED]"


def _scrub_secrets(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict,
) -> dict:
    """Remove sensitive values from structured log events before output."""
    for key in list(event_dict.keys()):
        if _SECRET_KEY_PATTERN.search(key):
            event_dict[key] = _REDACTED
    return event_dict


def configure_logging(log_level: str = "INFO") -> None:
    """
    Set up structlog with JSON output (machine-parseable in production,
    pretty-printed in development via ConsoleRenderer).

    Call this ONCE at application startup via the lifespan handler.

    Args:
        log_level: One of DEBUG | INFO | WARNING | ERROR | CRITICAL.
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure stdlib logging to route through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
    )

    # Shared processors applied to every log event
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        _scrub_secrets,  # ← redact API keys, secrets, tokens before output
    ]

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Attach formatter to all handlers
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )

    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.setFormatter(formatter)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Retrieve a named structlog logger.

    Usage:
        logger = get_logger(__name__)
        logger.info("research_started", query=query, request_id=rid)
    """
    return structlog.get_logger(name)
