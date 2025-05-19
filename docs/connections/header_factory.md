# HeaderFactory

The `HeaderFactory` class is a utility in Khive's Connections Layer that creates
appropriate authentication headers for API requests. It provides a standardized
way to handle different authentication types across various API providers.

## Overview

The `HeaderFactory` class is responsible for:

- Creating content type headers
- Generating authentication headers (Bearer token, API key)
- Combining headers for API requests
- Handling secure API key management

## Class Definition

```python
class HeaderFactory:
    @staticmethod
    def get_content_type_header(
        content_type: str = "application/json",
    ) -> dict[str, str]:
        """
        Get a content type header.

        Args:
            content_type: The content type (default: "application/json")

        Returns:
            A dictionary with the Content-Type header
        """
        return {"Content-Type": content_type}

    @staticmethod
    def get_bearer_auth_header(api_key: str) -> dict[str, str]:
        """
        Get a Bearer authentication header.

        Args:
            api_key: The API key to use for authentication

        Returns:
            A dictionary with the Authorization header
        """
        return {"Authorization": f"Bearer {api_key}"}

    @staticmethod
    def get_x_api_key_header(api_key: str) -> dict[str, str]:
        """
        Get an x-api-key authentication header.

        Args:
            api_key: The API key to use for authentication

        Returns:
            A dictionary with the x-api-key header
        """
        return {"x-api-key": api_key}

    @staticmethod
    def get_header(
        auth_type: AUTH_TYPES,
        content_type: str = "application/json",
        api_key: str | SecretStr | None = None,
        default_headers: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """
        Get a complete set of headers for an API request.

        Args:
            auth_type: The authentication type ("bearer" or "x-api-key")
            content_type: The content type (default: "application/json")
            api_key: The API key for authentication
            default_headers: Additional headers to include

        Returns:
            A dictionary with all headers

        Raises:
            ValueError: If the API key is missing or the auth type is unsupported
        """
```

## Authentication Types

The `HeaderFactory` supports the following authentication types, defined by the
`AUTH_TYPES` type:

```python
AUTH_TYPES = Literal["bearer", "x-api-key"]
```

- **Bearer Authentication**: Uses the `Authorization: Bearer <token>` header
  format, commonly used by OAuth 2.0 and many modern APIs
- **API Key Authentication**: Uses the `x-api-key: <key>` header format,
  commonly used by AWS API Gateway and other services

## Methods

### `get_content_type_header`

```python
@staticmethod
def get_content_type_header(
    content_type: str = "application/json",
) -> dict[str, str]:
    return {"Content-Type": content_type}
```

Creates a content type header with the specified content type (default:
"application/json").

### `get_bearer_auth_header`

```python
@staticmethod
def get_bearer_auth_header(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}
```

Creates a Bearer authentication header using the provided API key.

### `get_x_api_key_header`

```python
@staticmethod
def get_x_api_key_header(api_key: str) -> dict[str, str]:
    return {"x-api-key": api_key}
```

Creates an x-api-key authentication header using the provided API key.

### `get_header`

```python
@staticmethod
def get_header(
    auth_type: AUTH_TYPES,
    content_type: str = "application/json",
    api_key: str | SecretStr | None = None,
    default_headers: dict[str, str] | None = None,
) -> dict[str, str]:
```

The main method of the `HeaderFactory` class, which:

1. Validates that an API key is provided
2. Extracts the API key value from `SecretStr` if necessary
3. Creates a content type header
4. Adds the appropriate authentication header based on the auth type
5. Merges in any default headers
6. Returns the complete set of headers

## Usage Examples

### Basic Usage

```python
from khive.connections.header_factory import HeaderFactory

# Create headers with Bearer authentication
headers = HeaderFactory.get_header(
    auth_type="bearer",
    api_key="sk-1234567890abcdef",
    content_type="application/json"
)

# Result:
# {
#     "Content-Type": "application/json",
#     "Authorization": "Bearer sk-1234567890abcdef"
# }
```

### With API Key Authentication

```python
from khive.connections.header_factory import HeaderFactory

# Create headers with API key authentication
headers = HeaderFactory.get_header(
    auth_type="x-api-key",
    api_key="1234567890abcdef",
    content_type="application/json"
)

# Result:
# {
#     "Content-Type": "application/json",
#     "x-api-key": "1234567890abcdef"
# }
```

### With Default Headers

```python
from khive.connections.header_factory import HeaderFactory

# Create headers with additional default headers
headers = HeaderFactory.get_header(
    auth_type="bearer",
    api_key="sk-1234567890abcdef",
    content_type="application/json",
    default_headers={
        "User-Agent": "Khive/1.0",
        "Accept": "application/json"
    }
)

# Result:
# {
#     "Content-Type": "application/json",
#     "Authorization": "Bearer sk-1234567890abcdef",
#     "User-Agent": "Khive/1.0",
#     "Accept": "application/json"
# }
```

### With SecretStr API Key

```python
from pydantic import SecretStr
from khive.connections.header_factory import HeaderFactory

# Create headers with a SecretStr API key
api_key = SecretStr("sk-1234567890abcdef")
headers = HeaderFactory.get_header(
    auth_type="bearer",
    api_key=api_key,
    content_type="application/json"
)

# Result:
# {
#     "Content-Type": "application/json",
#     "Authorization": "Bearer sk-1234567890abcdef"
# }
```

## Integration with Endpoint

The `HeaderFactory` is used by the `Endpoint` class to create headers for API
requests:

```python
def create_payload(
    self,
    request: dict | BaseModel,
    extra_headers: dict | None = None,
    **kwargs,
):
    headers = HeaderFactory.get_header(
        auth_type=self.config.auth_type,
        content_type=self.config.content_type,
        api_key=self.config._api_key,
        default_headers=self.config.default_headers,
    )
    if extra_headers:
        headers.update(extra_headers)

    # ... rest of the method
```

## Best Practices

1. **Use SecretStr for API Keys**: When possible, use `SecretStr` for API keys
   to prevent accidental logging.

2. **Include Appropriate Content Types**: Set the correct content type for the
   API you're interacting with.

3. **Use Default Headers for Common Headers**: Use the `default_headers`
   parameter for headers that should be included in all requests to a particular
   API.

4. **Handle API Key Securely**: Never hardcode API keys in your code; use
   environment variables or secure storage.

## Related Documentation

- [Endpoint](endpoint.md): Documentation on the Endpoint class that uses
  HeaderFactory
- [EndpointConfig](endpoint_config.md): Documentation on the configuration
  options for endpoints
- [Pydantic SecretStr](https://docs.pydantic.dev/latest/api/types/#secretstr):
  Official documentation for Pydantic's SecretStr type
