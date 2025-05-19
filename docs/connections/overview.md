# Connections Layer

The Connections Layer in Khive provides a robust, flexible system for managing
connections to external API providers. It handles authentication, request
formatting, response parsing, and proper resource management for various API
services.

## Overview

The Connections Layer is designed to:

1. **Abstract API Complexity**: Provide a consistent interface for interacting
   with different API providers
2. **Manage Resources**: Ensure proper initialization and cleanup of connection
   resources
3. **Support Resilience**: Integrate with Khive's resilience patterns for
   reliable API interactions
4. **Enable Configuration**: Allow flexible configuration of endpoints and
   connection parameters

This layer is a critical component in Khive's layered resource control
architecture, sitting between the service layer and the external APIs.

## Key Components

The Connections Layer consists of several key components:

- **[Endpoint](endpoint.md)**: The core class that manages connections to
  external APIs
- **[EndpointConfig](endpoint_config.md)**: Configuration class for endpoints
  with validation
- **[HeaderFactory](header_factory.md)**: Utility for creating appropriate
  authentication headers
- **[match_endpoint](match_endpoint.md)**: Function to select the appropriate
  endpoint implementation

## Architecture

The Connections Layer follows a layered architecture pattern:

```
┌─────────────────┐
│  Service Layer  │
└────────┬────────┘
         │
┌────────▼────────┐
│ Resource Control│
│     Layer       │
└────────┬────────┘
         │
┌────────▼────────┐
│ Connections     │
│     Layer       │
└────────┬────────┘
         │
┌────────▼────────┐
│  External APIs  │
└─────────────────┘
```

## Integration with Other Components

The Connections Layer integrates with other Khive components:

- **Resilience Patterns**: Circuit breaker and retry mechanisms for handling
  transient failures
- **Rate Limiting**: Controls the rate of API requests to prevent overwhelming
  external services
- **Async Resource Management**: Ensures proper resource cleanup through async
  context managers

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

## Provider Support

The Connections Layer supports various API providers:

- OpenAI
- Anthropic
- Perplexity
- Exa
- Groq
- Ollama
- OpenRouter

## Related Documentation

- [Async Resource Management](../core-concepts/async_resource_management.md):
  Documentation on the standardized async resource cleanup patterns
- [Resilience Patterns](../core-concepts/resilience_patterns.md): Documentation
  on the Circuit Breaker and Retry patterns
- [Bounded Async Queue](../core-concepts/async_queue.md): Documentation on the
  queue-based backpressure mechanism
