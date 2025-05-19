# InfoService

The InfoService provides a unified interface for accessing external information
sources, including web search and AI model consultation.

## Overview

The InfoService is designed to:

- Provide search capabilities through providers like Perplexity and Exa
- Enable consultation with multiple AI models through OpenRouter
- Handle request routing, validation, and error handling
- Ensure proper resource management

## Architecture

The InfoService follows Khive's layered resource control architecture:

```
Client -> InfoService -> Endpoint -> AsyncAPIClient -> External API
```

This architecture provides clear separation of concerns and improved resource
management.

## Key Components

- **InfoServiceGroup**: Main service class that handles requests
- **Endpoints**: Provider-specific endpoints obtained via `match_endpoint`
- **AsyncExecutor**: Manages concurrent operations

## Implementation Details

The InfoService uses lazy-loaded endpoints that are initialized only when
needed:

```python
# Lazy initialization of the Perplexity endpoint
if self._perplexity is None:
    self._perplexity = match_endpoint("perplexity", "chat")
```

This approach ensures efficient resource usage and proper separation between the
service layer and the connections layer.

## Usage

See the [InfoService documentation](../../../docs/services/info_service.md) for
detailed usage examples.
