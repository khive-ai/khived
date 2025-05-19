# EndpointConfig

The `EndpointConfig` class is a Pydantic model that defines the configuration
options for endpoints in Khive's Connections Layer. It provides validation,
serialization, and secure handling of API credentials.

## Overview

The `EndpointConfig` class serves as a configuration container for the
`Endpoint` class, handling:

- API endpoint details and parameters
- Authentication configuration
- Transport type selection
- Request validation
- Secure API key management

## Class Definition

```python
class EndpointConfig(BaseModel):
    name: str
    provider: str
    transport_type: Literal["http", "sdk"] = "http"
    base_url: str | None = None
    endpoint: str
    endpoint_params: list[str] | None = None
    method: str = "POST"
    params: dict[str, str] = Field(default_factory=dict)
    content_type: str = "application/json"
    auth_type: AUTH_TYPES = "bearer"
    default_headers: dict = {}
    request_options: B | None = None
    api_key: str | SecretStr | None = None
    timeout: int = 300
    max_retries: int = 3
    openai_compatible: bool = False
    kwargs: dict = Field(default_factory=dict)
    client_kwargs: dict = Field(default_factory=dict)
    _api_key: str | None = PrivateAttr(None)
```

## Fields

| Field               | Type                       | Default              | Description                                   |
| ------------------- | -------------------------- | -------------------- | --------------------------------------------- |
| `name`              | `str`                      | Required             | Unique name for the endpoint                  |
| `provider`          | `str`                      | Required             | API provider (e.g., "openai", "anthropic")    |
| `transport_type`    | `Literal["http", "sdk"]`   | `"http"`             | Transport mechanism to use                    |
| `base_url`          | `str \| None`              | `None`               | Base URL for the API                          |
| `endpoint`          | `str`                      | Required             | Specific API endpoint path                    |
| `endpoint_params`   | `list[str] \| None`        | `None`               | Parameters for endpoint URL formatting        |
| `method`            | `str`                      | `"POST"`             | HTTP method for the request                   |
| `params`            | `dict[str, str]`           | `{}`                 | URL parameters for endpoint formatting        |
| `content_type`      | `str`                      | `"application/json"` | Content type for the request                  |
| `auth_type`         | `AUTH_TYPES`               | `"bearer"`           | Authentication type ("bearer" or "x-api-key") |
| `default_headers`   | `dict`                     | `{}`                 | Default headers to include with every request |
| `request_options`   | `B \| None`                | `None`               | Pydantic model for request validation         |
| `api_key`           | `str \| SecretStr \| None` | `None`               | API key for authentication                    |
| `timeout`           | `int`                      | `300`                | Request timeout in seconds                    |
| `max_retries`       | `int`                      | `3`                  | Maximum number of retry attempts              |
| `openai_compatible` | `bool`                     | `False`              | Whether the API is OpenAI-compatible          |
| `kwargs`            | `dict`                     | `{}`                 | Additional keyword arguments for the request  |
| `client_kwargs`     | `dict`                     | `{}`                 | Additional keyword arguments for the client   |

## Key Features

### API Key Resolution

The `EndpointConfig` class handles API key resolution from various sources:

1. Direct value (as string or `SecretStr`)
2. Environment variables
3. Khive settings

This is handled by the `_validate_api_key` model validator:

```python
@model_validator(mode="after")
def _validate_api_key(self):
    if self.api_key is None and self.transport_type == "sdk":
        if self.provider == "ollama":
            self.api_key = "ollama_key"
            self._api_key = "ollama_key"
        else:
            raise ValueError(
                "API key is required for SDK transport type except for Ollama provider."
            )

    if self.api_key is not None:
        if isinstance(self.api_key, SecretStr):
            self._api_key = self.api_key.get_secret_value()
        elif isinstance(self.api_key, str):
            from khive.config import settings

            try:
                self._api_key = settings.get_secret(self.api_key)
            except (AttributeError, ValueError):
                self._api_key = os.getenv(self.api_key, self.api_key)

    return self
```

### URL Construction

The `EndpointConfig` class provides a `full_url` property that constructs the
complete URL for the API request, handling parameter substitution:

```python
@property
def full_url(self):
    if not self.endpoint_params:
        return f"{self.base_url}/{self.endpoint}"
    return f"{self.base_url}/{self.endpoint.format(**self.params)}"
```

### Request Validation

The `EndpointConfig` class supports request validation through the
`request_options` field, which can be a Pydantic model or a schema definition:

```python
@field_validator("request_options", mode="before")
def _validate_request_options(cls, v):
    # Create a simple empty model if None is provided
    if v is None:
        return None

    try:
        if isinstance(v, type) and issubclass(v, BaseModel):
            return v
        if isinstance(v, BaseModel):
            return v.__class__
        if isinstance(v, dict | str):
            from khive._libs.schema import SchemaUtil

            return SchemaUtil.load_pydantic_model_from_schema(v)
    except Exception as e:
        raise ValueError("Invalid request options") from e
    raise ValueError(
        "Invalid request options: must be a Pydantic model or a schema dict"
    )
```

### Dynamic Configuration Updates

The `EndpointConfig` class provides an `update` method to dynamically update
configuration values:

```python
def update(self, **kwargs):
    """Update the config with new values."""
    for key, value in kwargs.items():
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            # Add to kwargs dict if not a direct attribute
            self.kwargs[key] = value
```

### Payload Validation

The `EndpointConfig` class provides a `validate_payload` method to validate
request payloads against the `request_options` model:

```python
def validate_payload(self, data: dict[str, Any]) -> dict[str, Any]:
    """Validate payload data against the request_options model.

    Args:
        data: The payload data to validate

    Returns:
        The validated data
    """
    if not self.request_options:
        return data

    try:
        validated = self.request_options.model_validate(data)
        return validated.model_dump(exclude_none=True)
    except Exception as e:
        raise ValueError("Invalid payload") from e
```

## Usage Examples

### Basic Configuration

```python
from khive.connections import EndpointConfig

# Create a basic configuration for an HTTP endpoint
config = EndpointConfig(
    name="example-api",
    provider="example",
    base_url="https://api.example.com",
    endpoint="v1/data",
    api_key="EXAMPLE_API_KEY"  # Will be resolved from environment
)
```

### OpenAI-Compatible Configuration

```python
from khive.connections import EndpointConfig

# Create a configuration for OpenAI API
config = EndpointConfig(
    name="openai-chat",
    provider="openai",
    transport_type="sdk",
    endpoint="chat/completions",
    api_key="OPENAI_API_KEY",  # Will be resolved from environment
    openai_compatible=True,
    timeout=60,
    max_retries=2
)
```

### With Request Validation

```python
from pydantic import BaseModel, Field
from khive.connections import EndpointConfig

# Define a request model
class ChatRequest(BaseModel):
    model: str
    messages: list[dict]
    temperature: float = Field(default=0.7, ge=0, le=2.0)
    max_tokens: int = Field(default=1000, gt=0)

# Create a configuration with request validation
config = EndpointConfig(
    name="openai-chat",
    provider="openai",
    transport_type="sdk",
    endpoint="chat/completions",
    api_key="OPENAI_API_KEY",
    openai_compatible=True,
    request_options=ChatRequest
)
```

### With Endpoint Parameters

```python
from khive.connections import EndpointConfig

# Create a configuration with endpoint parameters
config = EndpointConfig(
    name="user-api",
    provider="example",
    base_url="https://api.example.com",
    endpoint="users/{user_id}/profile",
    endpoint_params=["user_id"],
    params={"user_id": "123"},
    api_key="EXAMPLE_API_KEY"
)

# The full_url property will return "https://api.example.com/users/123/profile"
```

### Dynamic Configuration Update

```python
from khive.connections import EndpointConfig

# Create a basic configuration
config = EndpointConfig(
    name="example-api",
    provider="example",
    base_url="https://api.example.com",
    endpoint="v1/data",
    api_key="EXAMPLE_API_KEY"
)

# Update the configuration
config.update(
    timeout=120,
    max_retries=5,
    custom_param="value"  # Will be added to kwargs
)
```

## Best Practices

1. **Use Environment Variables for API Keys**: Store API keys in environment
   variables and reference them by name in the configuration.

2. **Define Request Models**: Use Pydantic models for `request_options` to
   validate requests before sending them to the API.

3. **Set Appropriate Timeouts**: Configure appropriate timeouts based on the
   expected response time of the API.

4. **Use Descriptive Names**: Choose descriptive names for endpoints to make
   them easily identifiable.

5. **Configure Appropriate Retry Counts**: Set `max_retries` based on the
   reliability of the API and the importance of the request.

## Related Documentation

- [Endpoint](endpoint.md): Documentation on the Endpoint class that uses
  EndpointConfig
- [HeaderFactory](header_factory.md): Documentation on the header creation
  utility
- [Pydantic Documentation](https://docs.pydantic.dev/): Official documentation
  for Pydantic, which is used for model validation
