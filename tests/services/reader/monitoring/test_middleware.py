import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request, FastAPI # type: ignore
from starlette.responses import Response # type: ignore
from starlette.routing import Route # type: ignore

# The middleware defines its own metrics, so we patch those.
# If it were importing from prometheus.py, we'd patch those.
# from khive.reader.monitoring.middleware import PrometheusMiddleware, HTTP_REQUESTS_TOTAL, HTTP_REQUESTS_LATENCY_SECONDS
# For this test, let's assume the middleware file is self-contained or we mock its internal metrics.

# To properly test middleware, we often need a minimal app.
async def sample_endpoint(request: Request):
    if request.query_params.get("error"):
        raise ValueError("Test error in endpoint")
    return Response("Hello, world", status_code=200)

async def another_endpoint(request: Request):
    return Response("Another route", status_code=201)

# Minimal app for testing middleware context
test_app = FastAPI()
test_app.add_route("/testpath", sample_endpoint)
test_app.add_route("/another/path", another_endpoint)


@pytest.fixture
def mock_http_requests_total():
    # Path to the metric defined *within* middleware.py
    with patch('khive.reader.monitoring.middleware.HTTP_REQUESTS_TOTAL') as mock_counter:
        # The .labels().inc() structure
        mock_counter.labels.return_value = MagicMock()
        yield mock_counter

@pytest.fixture
def mock_http_requests_latency_seconds():
    # Path to the metric defined *within* middleware.py
    with patch('khive.reader.monitoring.middleware.HTTP_REQUESTS_LATENCY_SECONDS') as mock_histogram:
        # The .labels().observe() structure
        mock_histogram.labels.return_value = MagicMock()
        yield mock_histogram

@pytest.fixture
async def client():
    # This client setup is more for integration tests, but useful for invoking middleware
    # For pure unit tests of dispatch, one might mock 'call_next' and 'request' more directly.
    # However, to get route templating, a minimal app context is helpful.
    from httpx import AsyncClient
    # Import middleware here to ensure mocks are active if it's reloaded
    from khive.reader.monitoring.middleware import PrometheusMiddleware
    
    # Add middleware to the test_app
    # Ensure this is a fresh app instance or clear middleware if tests run sequentially modifying app state
    # For simplicity, assuming test_app is clean for each client fixture use.
    if not any(isinstance(mw.middleware, PrometheusMiddleware) for mw in test_app.user_middleware):
         test_app.add_middleware(PrometheusMiddleware)

    async with AsyncClient(app=test_app, base_url="http://test") as ac:
        yield ac


# Test T-U4 (basic middleware tests)
@pytest.mark.asyncio
async def test_prometheus_middleware_success(
    client: "AsyncClient", 
    mock_http_requests_total: MagicMock, 
    mock_http_requests_latency_seconds: MagicMock
):
    """Test PrometheusMiddleware records metrics on a successful request."""
    response = await client.get("/testpath")
    assert response.status_code == 200
    assert response.text == "Hello, world"

    # Check that the metrics were called
    mock_http_requests_total.labels.assert_called_once_with(
        method="GET",
        path_template="/testpath", # FastAPI provides this in scope
        status_code="200"
    )
    mock_http_requests_total.labels.return_value.inc.assert_called_once()

    mock_http_requests_latency_seconds.labels.assert_called_once_with(
        method="GET",
        path_template="/testpath"
    )
    mock_http_requests_latency_seconds.labels.return_value.observe.assert_called_once()
    # Check that duration was positive
    assert mock_http_requests_latency_seconds.labels.return_value.observe.call_args[0][0] >= 0

@pytest.mark.asyncio
async def test_prometheus_middleware_failure(
    client: "AsyncClient", 
    mock_http_requests_total: MagicMock, 
    mock_http_requests_latency_seconds: MagicMock
):
    """Test PrometheusMiddleware records metrics on a request that causes an error in the endpoint."""
    with pytest.raises(ValueError, match="Test error in endpoint"):
        await client.get("/testpath?error=true")

    # Check that the metrics were called for failure
    mock_http_requests_total.labels.assert_called_once_with(
        method="GET",
        path_template="/testpath",
        status_code="500" # Default status for unhandled exceptions
    )
    mock_http_requests_total.labels.return_value.inc.assert_called_once()

    mock_http_requests_latency_seconds.labels.assert_called_once_with(
        method="GET",
        path_template="/testpath"
    )
    mock_http_requests_latency_seconds.labels.return_value.observe.assert_called_once()
    assert mock_http_requests_latency_seconds.labels.return_value.observe.call_args[0][0] >= 0

@pytest.mark.asyncio
async def test_prometheus_middleware_not_found(
    client: "AsyncClient", 
    mock_http_requests_total: MagicMock, 
    mock_http_requests_latency_seconds: MagicMock
):
    """Test PrometheusMiddleware records metrics for a 404 Not Found response."""
    response = await client.get("/nonexistentpath")
    assert response.status_code == 404 # FastAPI handles this

    # Check metrics for 404
    # The path_template for 404s can be tricky. The middleware tries to find it.
    # If FastAPI's default 404 handler is hit, path_template might be less specific.
    # The middleware has a fallback to "unknown_path" or tries to match from app.routes.
    # For this test, we expect it to be caught by the fallback or a generic match.
    
    # Based on middleware logic: it tries to find a match. If not, it might be "unknown_path"
    # or the path itself if no template matching logic in middleware for 404s is perfect.
    # Let's assume it resolves to the path itself or a generic one.
    # The middleware's current logic for path_template on 404s might need refinement
    # for perfect template matching if Starlette/FastAPI doesn't populate it.
    # For now, we'll check it's called.
    
    # Expected path_template might be "/nonexistentpath" or "unknown_path"
    # depending on how Starlette/FastAPI populates scope for 404s
    # and how the middleware's fallback logic works.
    # The middleware tries to find a route match; if none, it uses request.url.path.
    # For a 404, request.scope["route"] might not be set.
    # The middleware has a fallback to "unknown_path" if route.path is not found.
    
    # Let's check the call arguments more flexibly for path_template
    mock_http_requests_total.labels.assert_called_once()
    call_args_total = mock_http_requests_total.labels.call_args[0][0]
    assert call_args_total["method"] == "GET"
    assert call_args_total["status_code"] == "404"
    # path_template could be "/nonexistentpath" or "unknown_path"
    assert call_args_total["path_template"] in ["/nonexistentpath", "unknown_path"]


    mock_http_requests_total.labels.return_value.inc.assert_called_once()

    mock_http_requests_latency_seconds.labels.assert_called_once()
    call_args_latency = mock_http_requests_latency_seconds.labels.call_args[0][0]
    assert call_args_latency["method"] == "GET"
    assert call_args_latency["path_template"] in ["/nonexistentpath", "unknown_path"]
    mock_http_requests_latency_seconds.labels.return_value.observe.assert_called_once()
    assert mock_http_requests_latency_seconds.labels.return_value.observe.call_args[0][0] >= 0