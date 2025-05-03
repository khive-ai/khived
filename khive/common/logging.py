"""
Structured logging configuration for distributed systems.

This module provides a unified logging approach that integrates Python's standard
logging with structlog to enable structured, contextual logging with consistent
JSON output format.

Features:
- Unified configuration for both stdlib and structlog loggers
- Context-aware logging with correlation IDs and tenant tracking
- High-performance JSON serialization with orjson
- Middleware-friendly context management for web applications
"""

from __future__ import annotations

import logging
import sys
import uuid
from typing import Any

import orjson
import structlog

__all__ = ("Logging", "get_logger")


def _to_level(level: int | str) -> int:
    """
    Convert log level string to integer (e.g., "INFO" → 20).

    Uses the built-in mapping from Python 3.11+ (logging.getLevelNamesMapping()),
    which validates both standard and custom level names.

    Args:
        level: Level as string name or integer value

    Returns:
        Integer representation of the log level

    Raises:
        KeyError: If string level is invalid
    """
    if isinstance(level, int):
        return level
    return logging.getLevelNamesMapping()[level.upper()]


def _orjson_dumps(event_dict: dict, *, default: Any) -> str:
    """
    Custom JSON serializer using orjson for performance.

    Handles structlog's expected serializer interface while leveraging
    orjson's significantly faster performance (6-10x vs stdlib json).

    Args:
        event_dict: Dictionary of log event data
        default: Fallback serializer for non-serializable objects

    Returns:
        JSON-encoded string (orjson returns bytes, so we decode to str)
    """
    return orjson.dumps(event_dict, default=default).decode()


class Logging:
    """
    Unified logging configuration and utilities for distributed applications.

    This class provides static methods for configuring and interacting with
    the logging system. It ensures consistent log output format between
    standard library logging and structlog.
    """

    @staticmethod
    def configure_logging(
        service: str,
        level: int | str = "INFO",
        json_format: bool = True,
        utc: bool = True,
    ) -> None:
        """
        Initialize stdlib and structlog with unified JSON output format.

        Args:
            service: Non-empty service identifier bound into each log record
            level: Numeric or symbolic log level (e.g., "INFO" or 20)
            json_format: If False, use colored console text instead of JSON
            utc: Use UTC for ISO timestamps (recommended for distributed systems)

        Raises:
            ValueError: If service parameter is empty
        """
        if not service:
            raise ValueError("`service` must be a non-empty string.")

        lvl = _to_level(level)

        # Processors applied to all log records (stdlib and structlog)
        shared_processors: list[structlog.types.Processor] = [
            structlog.contextvars.merge_contextvars,  # Add context-local state
            structlog.processors.add_log_level,  # Add log level
            structlog.processors.TimeStamper(fmt="iso", utc=utc),  # Add timestamp
        ]

        # Select renderer based on format
        renderer = (
            structlog.processors.JSONRenderer(serializer=_orjson_dumps)
            if json_format
            else structlog.dev.ConsoleRenderer(colors=True)
        )

        # Configure stdlib logging
        formatter = structlog.stdlib.ProcessorFormatter(
            processor=renderer,
            foreign_pre_chain=shared_processors,
        )
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)

        root = logging.getLogger()
        root.handlers.clear()
        root.addHandler(handler)
        root.setLevel(lvl)

        # Configure structlog
        structlog.configure(
            processors=[*shared_processors, renderer],
            wrapper_class=structlog.make_filtering_bound_logger(lvl),
            cache_logger_on_first_use=True,
        )

        # Initialize global context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(service=service)

    @staticmethod
    def get_logger(name: str) -> structlog.stdlib.BoundLogger:  # type: ignore[override]
        """
        Return a structlog logger wrapped for stdlib compatibility.

        Args:
            name: Logger name, typically __name__ of the calling module

        Returns:
            A configured logger instance with context binding capabilities
        """
        return structlog.get_logger(name)

    @staticmethod
    def new_correlation_id() -> str:
        """
        Generate and bind a fresh correlation ID to the current context.

        This creates a new UUID, binds it to the correlation_id context variable,
        and returns the generated ID.

        Returns:
            The newly generated UUID as string
        """
        cid = str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(correlation_id=cid)
        return cid

    @staticmethod
    def set_correlation_id(correlation_id: str | None = None) -> str:
        """
        Bind or replace the correlation ID in the current context.

        Accepts an externally supplied ID to support request propagation,
        falling back to a new UUID when None is provided.

        Args:
            correlation_id: Existing correlation ID to propagate, or None to generate new

        Returns:
            The correlation ID that was set
        """
        cid = correlation_id if correlation_id else str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(correlation_id=cid)
        return cid

    @staticmethod
    def set_tenant_id(tenant: str | None) -> str | None:
        """
        Bind or clear the tenant ID in the current context.

        For multi-tenant applications, this attaches tenant information
        to all subsequent log entries in the current execution context.

        Args:
            tenant: Tenant ID to set, or None to clear

        Returns:
            The tenant ID that was set, or None if cleared
        """
        if tenant is None:
            structlog.contextvars.unbind_contextvars("tenant_id")
        else:
            structlog.contextvars.bind_contextvars(tenant_id=tenant)
        return tenant

    @staticmethod
    def enrich_log_context(**kv: Any) -> dict[str, Any]:
        """
        Add additional fields to the logging context.

        Call inside a request/task to attach arbitrary extra context
        that will appear in all subsequent log entries within the
        current execution context.

        Args:
            **kv: Key-value pairs to add to the context

        Returns:
            The values that were added to the context
        """
        structlog.contextvars.bind_contextvars(**kv)
        return kv

    @staticmethod
    def clear_context() -> None:
        """
        Reset all context variables.

        IMPORTANT: Call at the end of each request/task to prevent
        context leakage between requests. For web frameworks, add this
        to middleware that runs after the response is sent.
        """
        structlog.contextvars.clear_contextvars()


get_logger = Logging.get_logger
