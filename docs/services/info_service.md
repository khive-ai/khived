# InfoService

The InfoService is a core component of Khive that provides access to external
information sources through a unified interface. It enables searching the web
and consulting with AI models through various providers.

## Overview

The InfoService is designed to:

1. **Provide a Unified Interface**: Offer a consistent way to interact with
   different information providers
2. **Handle Provider-Specific Logic**: Abstract away the details of different
   API providers
3. **Ensure Resource Management**: Properly initialize and clean up resources
4. **Support Concurrent Operations**: Handle multiple concurrent requests
   efficiently

## Architecture

The InfoService follows Khive's layered resource control architecture:

```
┌─────────────────┐
│    Client       │
└────────┬────────┘
         │
┌────────▼────────┐
│   InfoService   │
└────────┬────────┘
         │
┌────────▼────────┐
│    Endpoint     │
└────────┬────────┘
         │
┌────────▼────────┐
│ AsyncAPIClient  │
└────────┬────────┘
         │
┌────────▼────────┐
│  External API   │
└─────────────────┘
```

This layered approach provides several benefits:

- Clear separation of concerns
- Improved testability
- Better resource management
- Enhanced resilience

## Implementation

The InfoService is implemented as the `InfoServiceGroup` class, which:

1. Uses lazy-loaded endpoints obtained via `match_endpoint`
2. Handles different types of information requests (search, consult)
3. Manages concurrent operations through an `AsyncExecutor`
4. Ensures proper resource cleanup

### Key Components

- **InfoServiceGroup**: The main service class that handles requests
- **Endpoints**: Provider-specific endpoints (Perplexity, Exa, OpenRouter)
- **AsyncExecutor**: Manages concurrent operations
- **match_endpoint**: Function to obtain the appropriate endpoint for a provider

## Usage

### Basic Usage

```python
from khive.services.info import InfoServiceGroup
from khive.services.info.parts import InfoRequest, InfoAction, InfoSearchParams, SearchProvider

# Create the service
service = InfoServiceGroup()

# Create a search request
request = InfoRequest(
    action=InfoAction.SEARCH,
    params=InfoSearchParams(
        provider=SearchProvider.PERPLEXITY,
        provider_params={"query": "What is Khive?"}
    )
)

# Handle the request
response = await service.handle_request(request)

# Use the response
if response.success:
    print(response.content)
else:
    print(f"Error: {response.error}")

# Clean up resources
await service.close()
```

### Using with Context Manager

```python
from khive.services.info import InfoServiceGroup
from khive.services.info.parts import InfoRequest, InfoAction, InfoConsultParams

async with InfoServiceGroup() as service:
    # Create a consult request
    request = InfoRequest(
        action=InfoAction.CONSULT,
        params=InfoConsultParams(
            question="Compare Python and Rust for systems programming",
            models=["openai/gpt-4", "anthropic/claude-3-opus"]
        )
    )

    # Handle the request
    response = await service.handle_request(request)

    # Use the response
    if response.success:
        for model, result in response.content.items():
            print(f"Response from {model}:")
            print(result)
    else:
        print(f"Error: {response.error}")
```

## Endpoint Integration

The InfoService uses the `match_endpoint` function to obtain the appropriate
endpoint for each provider:

```python
# Lazy initialization of the Perplexity endpoint
if self._perplexity is None:
    self._perplexity = match_endpoint("perplexity", "chat")
```

This approach provides several benefits:

- **Lazy Loading**: Endpoints are only initialized when needed
- **Consistent Interface**: All endpoints follow the same interface
- **Resource Management**: Endpoints handle their own resource lifecycle
- **Resilience**: Endpoints include retry logic and circuit breakers

## Resource Management

The InfoService implements proper resource management through its `close()`
method:

```python
async def close(self) -> None:
    """
    Close the service and release resources.

    This method ensures proper cleanup of all resources.
    """
    # Shutdown the executor
    if hasattr(self, "_executor") and self._executor is not None:
        await self._executor.shutdown()

    # Close any initialized endpoints
    for endpoint_attr in ("_perplexity", "_exa", "_openrouter"):
        endpoint = getattr(self, endpoint_attr, None)
        if endpoint is not None and hasattr(endpoint, "aclose"):
            await endpoint.aclose()
```

This ensures that all resources are properly cleaned up, preventing resource
leaks.

## Supported Providers

The InfoService supports the following providers:

| Provider   | Endpoint Type | Usage                                |
| ---------- | ------------- | ------------------------------------ |
| Perplexity | chat          | Web search with AI-powered responses |
| Exa        | search        | Semantic search across the web       |
| OpenRouter | chat          | Access to multiple AI models         |

## Error Handling

The InfoService implements comprehensive error handling:

1. **Endpoint Initialization Errors**: Handles cases where endpoints cannot be
   initialized
2. **API Call Errors**: Catches and processes exceptions from API calls
3. **Request Validation Errors**: Validates requests before processing
4. **Resource Cleanup Errors**: Ensures resources are cleaned up even in error
   cases

## Related Documentation

- [Connections Overview](../connections/overview.md): Documentation on the
  Connections Layer
- [Endpoint](../connections/endpoint.md): Documentation on the Endpoint class
- [match_endpoint](../connections/match_endpoint.md): Documentation on the
  match_endpoint function
- [Async Resource Management](../core-concepts/async_resource_management.md):
  Documentation on async resource management patterns
