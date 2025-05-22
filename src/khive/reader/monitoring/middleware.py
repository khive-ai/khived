import time
from collections.abc import Callable

from fastapi import Request  # type: ignore

# Assuming prometheus_client is installed and metrics are defined elsewhere
# from khive.reader.monitoring.prometheus import HTTP_REQUESTS, HTTP_LATENCY
# For now, defining them here for standalone context, will need adjustment
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware  # type: ignore
from starlette.responses import Response  # type: ignore
from starlette.routing import Match  # type: ignore

# Define metrics for HTTP endpoints (if not imported)
HTTP_REQUESTS_TOTAL = (
    Counter(  # Renamed to avoid conflict if imported, and align with common naming
        "khive_reader_http_requests_total",
        "Total number of HTTP requests",
        [
            "method",
            "path_template",
            "status_code",
        ],  # Using path_template for better cardinality
    )
)

HTTP_REQUESTS_LATENCY_SECONDS = Histogram(  # Renamed for clarity
    "khive_reader_http_requests_latency_seconds",
    "HTTP request latency in seconds",
    ["method", "path_template"],  # Using path_template
    buckets=[
        0.005,
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.5,
        5.0,
        7.5,
        10.0,
    ],  # Example buckets
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware for recording Prometheus metrics for FastAPI endpoints."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and record metrics."""
        method = request.method

        # Get path template if available (FastAPI specific)
        path_template = request.scope.get("path_template", request.url.path)
        # For Starlette standalone, route might be available
        if "route" in request.scope:
            path_template = request.scope["route"].path

        # Fallback if no template found (e.g. 404s handled by Starlette itself)
        if not path_template:
            path_template = "unknown_path"
            # Try to get it from the router if possible for 404s
            for route in request.app.routes:
                match, child_scope = route.matches(request.scope)
                if match == Match.FULL:
                    path_template = route.path
                    request.scope["path_template"] = (
                        path_template  # Store for future access
                    )
                    break

        start_time = time.time()
        status_code = 500  # Default status code for unhandled exceptions

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as e:
            # status_code remains 500
            raise e  # Re-raise the exception
        finally:
            duration = time.time() - start_time
            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                path_template=path_template,
                status_code=str(
                    status_code
                ),  # Ensure status_code is a string for label
            ).inc()
            HTTP_REQUESTS_LATENCY_SECONDS.labels(
                method=method, path_template=path_template
            ).observe(duration)
