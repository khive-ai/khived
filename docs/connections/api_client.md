# API Client

The `AsyncAPIClient` class is a robust async HTTP client for API interactions
with proper resource management. It serves as a key component in Khive's
resource access layer, providing a consistent interface for making HTTP requests
to external APIs.

## Overview

The `AsyncAPIClient` class:

- Manages HTTP session lifecycle
- Handles connection pooling
- Provides proper resource cleanup
- Integrates with resilience patterns
- Offers a comprehensive error handling system

## Class Definition

```python
class AsyncAPIClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 10.0,
        headers: dict[str, str] | None = None,
        auth: httpx.Auth | None = None,
        client: httpx.AsyncClient | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        retry_config: RetryConfig | None = None,
        **client_kwargs,
    ):
        """
        Initialize the async API client.

        Args:
            base_url: The base URL for the API.
            timeout: The timeout for requests in seconds.
            headers: Default headers to include with every request.
            auth: Authentication to use for requests.
            client: An existing httpx.AsyncClient to use instead of creating a new one.
            circuit_breaker: Optional circuit breaker for resilience.
            retry_config: Optional retry configuration for resilience.
            **client_kwargs: Additional keyword arguments to pass to httpx.AsyncClient.
        """
```

## Key Features

### Async Context Manager Support

The `AsyncAPIClient` implements the async context manager protocol (`__aenter__`
and `__aexit__`), allowing it to be used with the `async with` statement for
automatic resource management:

```python
async with AsyncAPIClient(base_url="https://api.example.com") as client:
    response = await client.get("/endpoint")
    # Resources automatically cleaned up when exiting the context
```

### Resource Management

The `AsyncAPIClient` ensures proper resource management through:

- Lazy initialization of the HTTP client
- Thread-safe client access with asyncio locks
- Proper cleanup of resources when exiting the context
- Idempotent `close()` method for explicit cleanup

### Resilience Integration

The `AsyncAPIClient` integrates with Khive's resilience patterns:

- **Circuit Breaker**: Prevents repeated calls to failing services
- **Retry with Backoff**: Handles transient failures with exponential backoff

### Comprehensive Error Handling

The `AsyncAPIClient` provides detailed error handling for HTTP requests:

- `APIConnectionError`: For connection errors
- `APITimeoutError`: For request timeouts
- `RateLimitError`: For rate limit exceeded errors (HTTP 429)
- `AuthenticationError`: For authentication failures (HTTP 401)
- `ResourceNotFoundError`: For resource not found errors (HTTP 404)
- `ServerError`: For server errors (HTTP 5xx)
- `APIClientError`: For other API client errors

## Methods

### HTTP Methods

The `AsyncAPIClient` provides methods for common HTTP operations:

```python
async def get(self, url: str, params: dict[str, Any] | None = None, **kwargs) -> Any:
    """Make a GET request to the API."""

async def post(
    self,
    url: str,
    json: dict[str, Any] | None = None,
    data: dict[str, Any] | bytes | str | None = None,
    **kwargs,
) -> Any:
    """Make a POST request to the API."""

async def put(
    self,
    url: str,
    json: dict[str, Any] | None = None,
    data: dict[str, Any] | bytes | str | None = None,
    **kwargs,
) -> Any:
    """Make a PUT request to the API."""

async def patch(
    self,
    url: str,
    json: dict[str, Any] | None = None,
    data: dict[str, Any] | bytes | str | None = None,
    **kwargs,
) -> Any:
    """Make a PATCH request to the API."""

async def delete(self, url: str, **kwargs) -> Any:
    """Make a DELETE request to the API."""
```

### ResourceClient Protocol Support

The `AsyncAPIClient` implements the `ResourceClient` protocol through the `call`
method:

```python
async def call(self, request: dict[str, Any], **kwargs) -> Any:
    """
    Make a call to the API using the ResourceClient protocol.

    This method is part of the ResourceClient protocol and provides
    a generic way to make API calls.

    Args:
        request: The request parameters.
        **kwargs: Additional keyword arguments for the request.

    Returns:
        The parsed response data.
    """
```

### Resource Management Methods

```python
async def close(self) -> None:
    """
    Close the client session and release resources.

    This method is idempotent and can be called multiple times.
    """

async def __aenter__(self) -> "AsyncAPIClient":
    """
    Enter the async context manager.

    Returns:
        The AsyncAPIClient instance.
    """

async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
    """
    Exit the async context manager and release resources.

    Args:
        exc_type: The exception type, if an exception was raised.
        exc_val: The exception value, if an exception was raised.
        exc_tb: The exception traceback, if an exception was raised.
    """
```

## Integration with Connections Layer

The `AsyncAPIClient` integrates with the Connections Layer in several ways:

### Shared Interfaces

Both `AsyncAPIClient` and `Endpoint` implement the `AsyncResourceManager`
protocol, ensuring consistent resource management:

```python
# AsyncResourceManager protocol
class AsyncResourceManager(Protocol):
    async def __aenter__(self) -> "AsyncResourceManager": ...
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None: ...
```

### ResourceClient Protocol

Both `AsyncAPIClient` and `Endpoint` implement the `ResourceClient` protocol,
providing a consistent interface for making API calls:

```python
# ResourceClient protocol
class ResourceClient(AsyncResourceManager, Protocol):
    async def call(self, request: Any, **kwargs) -> Any: ...
    async def close(self) -> None: ...
```

### Resilience Patterns

Both `AsyncAPIClient` and `Endpoint` integrate with the same resilience
patterns:

```python
# Create a client with resilience patterns
client = AsyncAPIClient(
    base_url="https://api.example.com",
    circuit_breaker=CircuitBreaker(failure_threshold=5, recovery_time=30.0),
    retry_config=RetryConfig(max_retries=3, base_delay=1.0)
)

# Create an endpoint with resilience patterns
endpoint = Endpoint(
    config=config,
    circuit_breaker=CircuitBreaker(failure_threshold=5, recovery_time=30.0),
    retry_config=RetryConfig(max_retries=3, base_delay=1.0)
)
```

### Complementary Roles

The `AsyncAPIClient` and `Endpoint` classes serve complementary roles:

- `AsyncAPIClient`: General-purpose HTTP client for any REST API
- `Endpoint`: Specialized client for specific API providers with additional
  features like SDK support

## Usage Examples

### Basic Usage

```python
from khive.clients import AsyncAPIClient

async def example():
    # Create a client
    async with AsyncAPIClient(base_url="https://api.example.com") as client:
        # Make a GET request
        user = await client.get("/users/123")
        print(f"User: {user['name']}")

        # Make a POST request
        response = await client.post(
            "/users",
            json={"name": "John Doe", "email": "john@example.com"}
        )
        print(f"Created user with ID: {response['id']}")
```

### With Resilience Patterns

```python
from khive.clients import AsyncAPIClient
from khive.clients.resilience import CircuitBreaker, RetryConfig

async def example():
    # Create a client with resilience patterns
    client = AsyncAPIClient(
        base_url="https://api.example.com",
        circuit_breaker=CircuitBreaker(failure_threshold=5, recovery_time=30.0),
        retry_config=RetryConfig(max_retries=3, base_delay=1.0)
    )

    # Use the client with resilience patterns
    async with client:
        try:
            response = await client.get("/users/123")
            print(f"User: {response['name']}")
        except CircuitBreakerOpenError:
            # Handle circuit breaker open
            print("Service is currently unavailable")
        except APITimeoutError:
            # Handle timeout
            print("Request timed out")
        except APIClientError as e:
            # Handle other API errors
            print(f"API error: {e}")
```

### Using the ResourceClient Protocol

```python
from khive.clients import AsyncAPIClient
from khive.clients.protocols import ResourceClient
from typing import Any

async def make_api_call(client: ResourceClient, request: dict[str, Any]) -> Any:
    """
    Make an API call using any ResourceClient implementation.

    Args:
        client: Any implementation of ResourceClient (AsyncAPIClient or Endpoint)
        request: The request parameters

    Returns:
        The API response
    """
    return await client.call(request)

async def example():
    # Create an API client
    api_client = AsyncAPIClient(base_url="https://api.example.com")

    # Use the generic function with the API client
    async with api_client:
        response = await make_api_call(api_client, {
            "method": "GET",
            "url": "/users/123"
        })
        print(f"User: {response['name']}")
```

## Best Practices

1. **Always Use Context Managers**: Prefer the async context manager pattern
   (`async with`) over manual resource management to ensure proper cleanup.

2. **Configure Appropriate Timeouts**: Set appropriate timeouts based on the
   expected response time of the API.

3. **Use Resilience Patterns**: Configure circuit breakers and retry mechanisms
   for better resilience against transient failures.

4. **Handle Specific Exceptions**: Catch and handle specific exception types
   (`APITimeoutError`, `RateLimitError`, etc.) for more precise error handling.

5. **Reuse Client Instances**: Create a single client instance for each API and
   reuse it to benefit from connection pooling.

## Related Documentation

- [Endpoint](endpoint.md): Documentation on the Endpoint class
- [Async Resource Management](../core-concepts/async_resource_management.md):
  Documentation on the standardized async resource cleanup patterns
- [Resilience Patterns](../core-concepts/resilience_patterns.md): Documentation
  on the Circuit Breaker and Retry patterns
