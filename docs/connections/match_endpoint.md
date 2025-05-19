# match_endpoint

The `match_endpoint` function is a utility in Khive's Connections Layer that
selects the appropriate endpoint implementation based on the provider and
endpoint type. It provides a convenient way to create pre-configured endpoints
for common API providers.

## Overview

The `match_endpoint` function:

- Analyzes the provider and endpoint parameters
- Selects the appropriate endpoint implementation
- Returns a pre-configured `Endpoint` instance
- Supports various API providers (OpenAI, Anthropic, Perplexity, etc.)
- Serves as a bridge between services and the Connections Layer

### Role in Layered Architecture

The `match_endpoint` function plays a crucial role in Khive's layered resource
control architecture:

```
┌─────────────────┐
│  Service Layer  │
│                 │
│  InfoService    │───┐
└─────────────────┘   │
                      │ match_endpoint("provider", "endpoint")
                      ▼
┌─────────────────┐
│ Connections     │
│     Layer       │
│                 │
│  Endpoint       │
└─────────────────┘
```

By using `match_endpoint`, services can:

- Obtain pre-configured endpoints for specific providers
- Maintain separation of concerns
- Implement lazy loading of resources
- Ensure consistent error handling and resource management

## Function Definition

```python
def match_endpoint(
    provider: str,
    endpoint: str,
) -> Endpoint:
    """
    Match a provider and endpoint to a pre-configured Endpoint instance.

    Args:
        provider: The API provider (e.g., "openai", "anthropic")
        endpoint: The endpoint type (e.g., "chat", "search")

    Returns:
        A pre-configured Endpoint instance, or None if no match is found
    """
```

## Supported Providers and Endpoints

The `match_endpoint` function supports the following provider and endpoint
combinations:

| Provider     | Endpoint             | Implementation              |
| ------------ | -------------------- | --------------------------- |
| `openai`     | `chat`               | `OpenaiChatEndpoint`        |
| `openai`     | `response`           | `OpenaiResponseEndpoint`    |
| `openrouter` | `chat`               | `OpenrouterChatEndpoint`    |
| `ollama`     | `chat`               | `OllamaChatEndpoint`        |
| `exa`        | `search`             | `ExaSearchEndpoint`         |
| `anthropic`  | `messages` or `chat` | `AnthropicMessagesEndpoint` |
| `groq`       | `chat`               | `GroqChatEndpoint`          |
| `perplexity` | `chat`               | `PerplexityChatEndpoint`    |

## Implementation Details

The `match_endpoint` function uses a series of conditional checks to determine
the appropriate endpoint implementation:

```python
def match_endpoint(
    provider: str,
    endpoint: str,
) -> Endpoint:
    if provider == "openai":
        if "chat" in endpoint:
            from .providers.oai_ import OpenaiChatEndpoint
            return OpenaiChatEndpoint()
        if "response" in endpoint:
            from .providers.oai_ import OpenaiResponseEndpoint
            return OpenaiResponseEndpoint()
    if provider == "openrouter" and "chat" in endpoint:
        from .providers.oai_ import OpenrouterChatEndpoint
        return OpenrouterChatEndpoint()
    if provider == "ollama" and "chat" in endpoint:
        from .providers.ollama_ import OllamaChatEndpoint
        return OllamaChatEndpoint()
    if provider == "exa" and "search" in endpoint:
        from .providers.exa_ import ExaSearchEndpoint
        return ExaSearchEndpoint()
    if provider == "anthropic" and ("messages" in endpoint or "chat" in endpoint):
        from .providers.anthropic_ import AnthropicMessagesEndpoint
        return AnthropicMessagesEndpoint()
    if provider == "groq" and "chat" in endpoint:
        from .providers.oai_ import GroqChatEndpoint
        return GroqChatEndpoint()
    if provider == "perplexity" and "chat" in endpoint:
        from .providers.perplexity_ import PerplexityChatEndpoint
        return PerplexityChatEndpoint()

    return None
```

The function uses lazy imports to avoid importing all provider modules when only
one is needed.

## Provider-Specific Endpoints

Each provider-specific endpoint implementation is a subclass of the `Endpoint`
class, pre-configured with appropriate settings for that provider:

### OpenAI Chat Endpoint

```python
class OpenaiChatEndpoint(Endpoint):
    def __init__(self, **kwargs):
        config = EndpointConfig(
            name="openai-chat",
            provider="openai",
            transport_type="sdk",
            endpoint="chat/completions",
            api_key="OPENAI_API_KEY",  # Will be resolved from environment
            openai_compatible=True,
            **kwargs
        )
        super().__init__(config)
```

### Anthropic Messages Endpoint

```python
class AnthropicMessagesEndpoint(Endpoint):
    def __init__(self, **kwargs):
        config = EndpointConfig(
            name="anthropic-messages",
            provider="anthropic",
            transport_type="sdk",
            endpoint="messages",
            api_key="ANTHROPIC_API_KEY",  # Will be resolved from environment
            **kwargs
        )
        super().__init__(config)
```

### Exa Search Endpoint

```python
class ExaSearchEndpoint(Endpoint):
    def __init__(self, **kwargs):
        config = EndpointConfig(
            name="exa-search",
            provider="exa",
            transport_type="sdk",
            endpoint="search",
            api_key="EXA_API_KEY",  # Will be resolved from environment
            **kwargs
        )
        super().__init__(config)
```

## Usage Examples

### Basic Usage

```python
from khive.connections import match_endpoint

# Get a pre-configured OpenAI chat endpoint
endpoint = match_endpoint("openai", "chat")

# Use the endpoint
async with endpoint:
    response = await endpoint.call({
        "model": "gpt-4",
        "messages": [{"role": "user", "content": "Hello, world!"}]
    })
    print(response.choices[0].message.content)
```

### Service Integration

```python
from khive.connections import match_endpoint

class MyService:
    def __init__(self):
        # Initialize with None - lazy loading
        self._openai_endpoint = None

    async def generate_text(self, prompt):
        # Lazy initialization of the endpoint
        if self._openai_endpoint is None:
            self._openai_endpoint = match_endpoint("openai", "chat")

        if self._openai_endpoint is None:
            return {"error": "Failed to initialize OpenAI endpoint"}

        try:
            # Use the endpoint
            response = await self._openai_endpoint.call({
                "model": "gpt-4",
                "messages": [{"role": "user", "content": prompt}]
            })
            return {"text": response.choices[0].message.content}
        except Exception as e:
            return {"error": f"API call failed: {str(e)}"}

    async def close(self):
        # Clean up resources
        if self._openai_endpoint is not None:
            await self._openai_endpoint.aclose()
```

This pattern is used in Khive's InfoService to interact with multiple providers
through a unified interface.

````
### With Custom Configuration

```python
from khive.connections import match_endpoint

# Get a pre-configured Anthropic endpoint with custom settings
endpoint = match_endpoint("anthropic", "messages")

# Update the configuration
endpoint.config.update(
    timeout=120,
    max_retries=5
)

# Use the endpoint
async with endpoint:
    response = await endpoint.call({
        "model": "claude-3-opus-20240229",
        "messages": [{"role": "user", "content": "Hello, world!"}]
    })
    print(response.content[0].text)
````

### With Resilience Patterns

```python
from khive.connections import match_endpoint
from khive.clients.resilience import CircuitBreaker, RetryConfig

# Get a pre-configured endpoint
endpoint = match_endpoint("openai", "chat")

# Add resilience patterns
endpoint.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_time=30.0)
endpoint.retry_config = RetryConfig(max_retries=3, base_delay=1.0)

# Use the endpoint with resilience patterns
async with endpoint:
    try:
        response = await endpoint.call({
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello, world!"}]
        })
        print(response.choices[0].message.content)
    except CircuitBreakerOpenError:
        # Handle circuit breaker open
        print("Service is currently unavailable")
```

### Handling No Match

```python
from khive.connections import match_endpoint, Endpoint, EndpointConfig

# Try to get a pre-configured endpoint
endpoint = match_endpoint("custom-provider", "custom-endpoint")

# If no match is found, create a custom endpoint
if endpoint is None:
    endpoint = Endpoint(
        EndpointConfig(
            name="custom-endpoint",
            provider="custom-provider",
            base_url="https://api.custom-provider.com",
            endpoint="v1/custom-endpoint",
            api_key="CUSTOM_API_KEY"
        )
    )

# Use the endpoint
async with endpoint:
    response = await endpoint.call(request)
```

## Extending with Custom Providers

To extend the `match_endpoint` function with support for custom providers, you
can create a wrapper function:

```python
from khive.connections import match_endpoint as base_match_endpoint, Endpoint
from my_custom_provider import MyCustomEndpoint

def extended_match_endpoint(provider: str, endpoint: str) -> Endpoint:
    # Try the base implementation first
    result = base_match_endpoint(provider, endpoint)
    if result is not None:
        return result

    # Add custom provider support
    if provider == "my-custom-provider" and "api" in endpoint:
        return MyCustomEndpoint()

    # Return None if no match is found
    return None
```

## Best Practices

1. **Use Pre-configured Endpoints**: When working with common API providers, use
   `match_endpoint` to get pre-configured endpoints.

2. **Customize as Needed**: Update the configuration of pre-configured endpoints
   to suit your specific needs.

3. **Handle No Match**: Always check if `match_endpoint` returns `None` and
   provide a fallback if needed.

4. **Add Resilience Patterns**: Add circuit breakers and retry configurations to
   pre-configured endpoints for better resilience.

5. **Implement Lazy Loading**: Initialize endpoints only when they are first
   used to improve startup performance and resource usage.

6. **Ensure Proper Cleanup**: Always close endpoints when they are no longer
   needed, preferably using async context managers or explicit `aclose()` calls.

## Related Documentation

- [Endpoint](endpoint.md): Documentation on the Endpoint class
- [EndpointConfig](endpoint_config.md): Documentation on the configuration
  options for endpoints
- [InfoService](../services/info_service.md): Documentation on a service that
  uses `match_endpoint` to interact with multiple providers
- [Connections Overview](overview.md): Documentation on the Connections Layer
  architecture
- [Provider-Specific Documentation](https://platform.openai.com/docs/api-reference):
  Links to official API documentation for supported providers
