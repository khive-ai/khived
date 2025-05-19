# Endpoint

The `Endpoint` class is a core component of Khive's Connections Layer,
responsible for managing connections to external APIs. It implements the
`AsyncResourceManager` protocol to ensure proper resource initialization and
cleanup.

## Overview

The `Endpoint` class provides a unified interface for interacting with various
API providers, handling:

- Connection lifecycle management
- Request formatting and authentication
- Response parsing
- Integration with resilience patterns
- Support for both HTTP and SDK-based APIs

## Class Definition

```python
class Endpoint:
    def __init__(
        self,
        config: dict | EndpointConfig,
        circuit_breaker: CircuitBreaker | None = None,
        retry_config: RetryConfig | None = None,
        **kwargs,
    ):
        """
        Initialize the endpoint.

        Args:
            config: The endpoint configuration.
            circuit_breaker: Optional circuit breaker for resilience.
            retry_config: Optional retry configuration for resilience.
            **kwargs: Additional keyword arguments to update the configuration.
        """
```

## Key Features

### Async Context Manager Support

The `Endpoint` class implements the async context manager protocol (`__aenter__`
and `__aexit__`), allowing it to be used with the `async with` statement for
automatic resource management:

```python
async with Endpoint(config) as endpoint:
    response = await endpoint.call(request)
    # Resources automatically cleaned up when exiting the context
```

### Transport Type Support

The `Endpoint` class supports different transport types:

- **HTTP**: Uses `aiohttp.ClientSession` for making HTTP requests
- **SDK**: Uses provider-specific SDKs (e.g., OpenAI's Python SDK)

### Resilience Integration

The `Endpoint` class integrates with Khive's resilience patterns:

- **Circuit Breaker**: Prevents repeated calls to failing services
- **Retry with Backoff**: Handles transient failures with exponential backoff

### Caching Support

The `Endpoint` class supports caching of responses using `aiocache`:

```python
# Make a call with caching enabled
response = await endpoint.call(request, cache_control=True)
```

## Methods

### `call`

```python
async def call(
    self, request: dict | BaseModel, cache_control: bool = False, **kwargs
) -> Any:
    """
    Make a call to the endpoint.

    Args:
        request: The request parameters or model.
        cache_control: Whether to use cache control.
        **kwargs: Additional keyword arguments for the request.

    Returns:
        The response from the endpoint.
    """
```

The `call` method is the primary method for interacting with the API. It:

1. Creates a payload from the request
2. Applies resilience patterns if configured
3. Makes the API call using the appropriate transport
4. Returns the parsed response

### `create_payload`

```python
def create_payload(
    self,
    request: dict | BaseModel,
    extra_headers: dict | None = None,
    **kwargs,
) -> tuple[dict, dict]:
    """
    Create a payload for the API call.

    Args:
        request: The request parameters or model.
        extra_headers: Additional headers to include.
        **kwargs: Additional keyword arguments for the request.

    Returns:
        A tuple of (payload, headers).
    """
```

The `create_payload` method prepares the request payload and headers for the API
call, handling:

- Authentication headers
- Content type
- Request validation
- Parameter merging

### `aclose`

```python
async def aclose(self) -> None:
    """
    Gracefully close the client session.

    This method can be called explicitly to close the client without using
    the context manager. It ensures proper resource cleanup for both HTTP
    and SDK clients.
    """
```

The `aclose` method provides a way to explicitly close the client session
without using the context manager.

## Internal Methods

### `_create_client`

```python
def _create_client(self) -> Any:
    """
    Create a client for the endpoint based on the transport type.

    Returns:
        A client instance (either aiohttp.ClientSession or SDK client).
    """
```

The `_create_client` method creates the appropriate client based on the
transport type:

- For HTTP transport, it creates an `aiohttp.ClientSession`
- For SDK transport with OpenAI compatibility, it creates an `AsyncOpenAI`
  client

### `_close_client`

```python
async def _close_client(self) -> None:
    """
    Internal method to close the client and release resources.

    This method handles different client types and ensures proper cleanup
    in all cases, including error scenarios.
    """
```

The `_close_client` method ensures proper resource cleanup for both HTTP and SDK
clients, handling:

- Different client types
- Synchronous and asynchronous close methods
- Error handling during cleanup

### `_call_aiohttp`

```python
async def _call_aiohttp(self, payload: dict, headers: dict, **kwargs) -> Any:
    """
    Make a call using aiohttp.

    Args:
        payload: The request payload.
        headers: The request headers.
        **kwargs: Additional keyword arguments for the request.

    Returns:
        The response from the endpoint.
    """
```

The `_call_aiohttp` method makes an HTTP request using `aiohttp`, handling:

- Request formatting
- Response parsing
- Error handling
- Retry logic with backoff

### `_call_openai`

```python
async def _call_openai(self, payload: dict, headers: dict, **kwargs) -> Any:
    """
    Make a call using the OpenAI SDK.

    Args:
        payload: The request payload.
        headers: The request headers.
        **kwargs: Additional keyword arguments for the request.

    Returns:
        The response from the endpoint.
    """
```

The `_call_openai` method makes a request using the OpenAI SDK, handling:

- Different endpoint types (chat, embeddings, etc.)
- Response format options
- Error handling
- Retry logic with backoff

## Usage Examples

### Basic Usage

```python
from khive.connections import Endpoint, EndpointConfig

# Create an endpoint configuration
config = EndpointConfig(
    name="openai-chat",
    provider="openai",
    transport_type="sdk",
    endpoint="chat/completions",
    api_key="OPENAI_API_KEY",  # Will be resolved from environment
    openai_compatible=True
)

# Use the endpoint with async context manager
async with Endpoint(config) as endpoint:
    response = await endpoint.call({
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "Hello, world!"}]
    })
    print(response.choices[0].message.content)
```

### With Resilience Patterns

```python
from khive.connections import Endpoint, EndpointConfig
from khive.clients.resilience import CircuitBreaker, RetryConfig

# Create resilience components
circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_time=30.0)
retry_config = RetryConfig(max_retries=3, base_delay=1.0)

# Create an endpoint with resilience
endpoint = Endpoint(
    config=config,
    circuit_breaker=circuit_breaker,
    retry_config=retry_config
)

# Use the endpoint with resilience patterns
async with endpoint:
    try:
        response = await endpoint.call(request)
    except CircuitBreakerOpenError:
        # Handle circuit breaker open
        response = get_cached_response()
```

### Manual Resource Management

```python
from khive.connections import Endpoint, EndpointConfig

# Create an endpoint
endpoint = Endpoint(config)

try:
    # Initialize the client
    await endpoint._create_client()

    # Make API calls
    response = await endpoint.call(request)

finally:
    # Ensure resources are cleaned up
    await endpoint.aclose()
```

### With Caching

```python
from khive.connections import Endpoint, EndpointConfig

# Create an endpoint
endpoint = Endpoint(config)

# Make a call with caching enabled
async with endpoint:
    # This response will be cached
    response = await endpoint.call(request, cache_control=True)

    # Subsequent identical calls will use the cached response
    cached_response = await endpoint.call(request, cache_control=True)
```

## Best Practices

1. **Always Use Context Managers**: Prefer the async context manager pattern
   (`async with`) over manual resource management to ensure proper cleanup.

2. **Configure Resilience Patterns**: Use circuit breakers and retry
   configurations to handle transient failures and prevent cascading failures.

3. **Use Appropriate Transport Type**: Choose the appropriate transport type
   (HTTP or SDK) based on the API provider and your needs.

4. **Handle Exceptions**: Catch and handle exceptions appropriately, especially
   `CircuitBreakerOpenError` when using circuit breakers.

5. **Use Request Validation**: Configure request validation through
   `EndpointConfig.request_options` to ensure valid requests.

6. **Enable Caching When Appropriate**: Use the `cache_control` parameter to
   enable caching for appropriate requests.

## Related Documentation

- [EndpointConfig](endpoint_config.md): Documentation on the configuration
  options for endpoints
- [HeaderFactory](header_factory.md): Documentation on the header creation
  utility
- [Async Resource Management](../core-concepts/async_resource_management.md):
  Documentation on the standardized async resource cleanup patterns
- [Resilience Patterns](../core-concepts/resilience_patterns.md): Documentation
  on the Circuit Breaker and Retry patterns
