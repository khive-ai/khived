"""
OpenTelemetry tracing utilities for distributed systems.

This module provides a consistent, high-level API for distributed tracing
with OpenTelemetry, including setup, context propagation, and instrumentation
for common libraries. It seamlessly integrates with structured logging.

Features:
- Simple one-line initialization
- Automatic correlation between traces and logs
- Built-in instrumentation for FastAPI, HTTPX, and SQLAlchemy
- Support for trace context propagation across service boundaries
- Decorator for tracing function calls
"""

from __future__ import annotations

import inspect
import os
import threading
from functools import wraps
from typing import Any, Callable, Dict, Optional, ParamSpec, TypeVar, overload

from opentelemetry import propagate, trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import (
    ALWAYS_OFF,
    ALWAYS_ON,
    ParentBased,
    TraceIdRatioBased,
)
from opentelemetry.trace import Span, SpanKind
from structlog import contextvars as log_ctx

# Type variables for function decorators
P = ParamSpec("P")
R = TypeVar("R")

__all__ = (
    "Tracing",
    "get_tracer",
)


class Tracing:
    """
    Simplified OpenTelemetry tracing utilities for distributed systems.

    This class provides static methods for configuring OpenTelemetry tracing,
    propagating trace context across services, and instrumenting common libraries.
    It integrates with structlog for consistent trace context in logs.
    """

    _init_lock = threading.Lock()
    _initialized = False

    @classmethod
    def init_tracer(
        cls,
        service: str,
        ratio: float = 0.1,
        otlp_endpoint: str | None = None,
        always_on: bool = False,
        always_off: bool = False,
        additional_attributes: Dict[str, str] | None = None,
    ) -> None:
        """
        Initialize OpenTelemetry with an OTLP exporter and configurable sampling.

        This method configures the global TracerProvider with appropriate resource
        attributes and sampling strategy. It should be called once at application startup.

        Args:
            service: Service name for identification in trace data
            ratio: Sampling ratio (0.0-1.0) when using trace ID ratio sampling
            otlp_endpoint: OTLP exporter endpoint (defaults to OTEL_EXPORTER_OTLP_ENDPOINT or localhost:4317)
            always_on: If True, sample all traces (overrides ratio)
            always_off: If True, disable tracing completely (overrides always_on and ratio)
            additional_attributes: Additional resource attributes to include in traces

        Raises:
            ValueError: If service name is empty or sampling ratio is outside valid range
        """
        with cls._init_lock:
            if cls._initialized:
                return

            if not service:
                raise ValueError("Service name must not be empty")

            if ratio < 0.0 or ratio > 1.0:
                raise ValueError(
                    f"Sampling ratio must be between 0.0 and 1.0, got {ratio}"
                )

            # Create resource with service info and additional attributes
            resource_attributes = {SERVICE_NAME: service}
            if additional_attributes:
                resource_attributes.update(additional_attributes)

            resource = Resource.create(resource_attributes)

            # Configure sampler based on parameters
            if always_off:
                sampler = ALWAYS_OFF
            elif always_on:
                sampler = ALWAYS_ON
            else:
                sampler = ParentBased(TraceIdRatioBased(ratio))

            # Create and configure the tracer provider
            provider = TracerProvider(
                resource=resource,
                sampler=sampler,
            )

            # Configure exporter
            endpoint = otlp_endpoint or os.getenv(
                "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
            )
            exporter = OTLPSpanExporter(endpoint=endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))

            # Set as global provider
            trace.set_tracer_provider(provider)
            cls._initialized = True

    @staticmethod
    def instrument_fastapi(
        app: Any, *, tracer_provider: Optional[TracerProvider] = None
    ) -> None:
        """
        Instrument a FastAPI application for distributed tracing.

        Args:
            app: FastAPI application instance
            tracer_provider: Optional TracerProvider (uses global provider if None)
        """
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(
            app, tracer_provider=tracer_provider or trace.get_tracer_provider()
        )

    @staticmethod
    def instrument_httpx(
        client: Any, *, tracer_provider: Optional[TracerProvider] = None
    ) -> None:
        """
        Instrument an HTTPX client for distributed tracing.

        Args:
            client: HTTPX client instance
            tracer_provider: Optional TracerProvider (uses global provider if None)
        """
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument_client(
            client, tracer_provider=tracer_provider or trace.get_tracer_provider()
        )

    @staticmethod
    def instrument_sqlalchemy(
        engine: Any, *, tracer_provider: Optional[TracerProvider] = None
    ) -> None:
        """
        Instrument a SQLAlchemy engine for distributed tracing.

        Args:
            engine: SQLAlchemy engine instance
            tracer_provider: Optional TracerProvider (uses global provider if None)
        """
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        SQLAlchemyInstrumentor().instrument(
            engine=engine,
            tracer_provider=tracer_provider or trace.get_tracer_provider(),
        )

    @staticmethod
    def inject_headers(carrier: Dict[str, str]) -> Dict[str, str]:
        """
        Inject current trace context into a carrier dictionary.

        Used for propagating trace context across service boundaries,
        typically by adding headers to outgoing HTTP requests or
        properties to message queue entries.

        Args:
            carrier: Dictionary to inject trace context into (e.g., HTTP headers)

        Returns:
            The carrier with injected trace context
        """
        propagate.inject(carrier)
        Tracing._bind_trace_context_to_logs()
        return carrier

    @staticmethod
    def extract_headers(carrier: Dict[str, str]) -> None:
        """
        Extract trace context from a carrier dictionary.

        Used for continuing traces across service boundaries,
        typically by extracting context from incoming HTTP request
        headers or message queue properties.

        Args:
            carrier: Dictionary containing trace context (e.g., HTTP headers)
        """
        ctx = propagate.extract(carrier)
        trace.set_span_in_context(trace.get_current_span(ctx))
        Tracing._bind_trace_context_to_logs()

    @staticmethod
    def create_span(
        name: str,
        kind: Optional[SpanKind] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """
        Create and start a new span as the current active span.

        Args:
            name: Name of the span
            kind: Optional kind of span (SERVER, CLIENT, etc.)
            attributes: Optional span attributes

        Returns:
            The created span (must be ended by the caller)
        """
        tracer = trace.get_tracer(__name__)
        span = tracer.start_as_current_span(name, kind=kind, attributes=attributes)
        Tracing._bind_trace_context_to_logs()
        return span

    @staticmethod
    def get_current_trace_id() -> Optional[str]:
        """
        Get the current trace ID as a formatted hexadecimal string.

        Returns:
            Trace ID as a hex string or None if no active trace
        """
        span = trace.get_current_span()
        if not span:
            return None

        ctx = span.get_span_context()
        if not ctx.is_valid:
            return None

        return f"{ctx.trace_id:032x}"

    @staticmethod
    def get_current_span_id() -> Optional[str]:
        """
        Get the current span ID as a formatted hexadecimal string.

        Returns:
            Span ID as a hex string or None if no active span
        """
        span = trace.get_current_span()
        if not span:
            return None

        ctx = span.get_span_context()
        if not ctx.is_valid:
            return None

        return f"{ctx.span_id:016x}"

    @staticmethod
    def _bind_trace_context_to_logs() -> None:
        """
        Bind current trace and span IDs to the structured logging context.

        This ensures that log entries include trace context information,
        allowing correlation between logs and traces.
        """
        span = trace.get_current_span()
        if not span:
            return

        ctx = span.get_span_context()
        if not ctx.is_valid:
            return

        log_ctx.bind_contextvars(
            trace_id=f"{ctx.trace_id:032x}",
            span_id=f"{ctx.span_id:016x}",
        )

    @staticmethod
    def get_tracer(name: str) -> trace.Tracer:
        """
        Get a tracer for the specified instrumentation scope.

        Args:
            name: Name of the instrumentation scope (typically module name)

        Returns:
            An OpenTelemetry tracer instance
        """
        return trace.get_tracer(name)

    @overload
    @staticmethod
    def trace_fn(func: Callable[P, R]) -> Callable[P, R]: ...

    @overload
    @staticmethod
    def trace_fn(
        *, span_name: Optional[str] = None, kind: Optional[SpanKind] = None
    ) -> Callable[[Callable[P, R]], Callable[P, R]]: ...

    @staticmethod
    def trace_fn(
        func=None, *, span_name: Optional[str] = None, kind: Optional[SpanKind] = None
    ):
        """
        Decorator to trace a function call.

        Can be used with or without parameters:

        @Tracing.trace_fn
        def my_function():
            ...

        @Tracing.trace_fn(span_name="custom_name", kind=SpanKind.CLIENT)
        def my_function():
            ...

        Args:
            func: Function to decorate
            span_name: Optional custom span name (defaults to function name)
            kind: Optional span kind

        Returns:
            Decorated function
        """

        def decorator(fn: Callable[P, R]) -> Callable[P, R]:
            @wraps(fn)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                name = span_name or f"{fn.__module__}.{fn.__qualname__}"
                with Tracing.get_tracer(fn.__module__).start_as_current_span(
                    name, kind=kind
                ):
                    Tracing._bind_trace_context_to_logs()
                    return fn(*args, **kwargs)

            return wrapper

        # Handle both @trace_fn and @trace_fn() syntax
        if func is None:
            return decorator
        return decorator(func)

    @staticmethod
    def trace_async_fn(
        span_name: Optional[str] = None, kind: Optional[SpanKind] = None
    ):
        """
        Decorator to trace an async function call.

        @Tracing.trace_async_fn(span_name="custom_name")
        async def my_async_function():
            ...

        Args:
            span_name: Optional custom span name (defaults to function name)
            kind: Optional span kind

        Returns:
            Decorated async function
        """

        def decorator(fn):
            if not inspect.iscoroutinefunction(fn):
                raise TypeError(
                    "@trace_async_fn can only be applied to async functions"
                )

            @wraps(fn)
            async def wrapper(*args, **kwargs):
                name = span_name or f"{fn.__module__}.{fn.__qualname__}"
                with Tracing.get_tracer(fn.__module__).start_as_current_span(
                    name, kind=kind
                ):
                    Tracing._bind_trace_context_to_logs()
                    return await fn(*args, **kwargs)

            return wrapper

        return decorator


# Convenience accessor for the get_tracer function
get_tracer = Tracing.get_tracer
