import asyncio
import logging
from os import getenv
from typing import Any, Dict, Literal, TypeVar

import aiohttp
import backoff
from aiocache import cached
from aiolimiter import AsyncLimiter
from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
    SecretStr,
    field_serializer,
    field_validator,
    model_validator,
)

from khive.config import settings
from khive.protocols.event import Event, EventStatus
from khive.utils import load_pydantic_model_from_schema

B = TypeVar("B", bound=type[BaseModel])

logger = logging.getLogger(__name__)


__all__ = ("Endpoint", "EndpointConfig", "APICalling", "iModel")


class EndpointConfig(BaseModel):

    name: str
    provider: str
    base_url: str | None = None
    endpoint: str
    endpoint_params: list[str] | None = None
    method: Literal["GET", "POST", "PUT", "DELETE"] = "POST"
    request_options: B
    api_key: str | SecretStr | None = None
    timeout: int = 600
    max_retries: int = 3
    default_headers: dict[str, str] = {"content-type": "application/json"}
    auth_template: dict = {"Authorization": "Bearer $API_KEY"}
    params: dict[str, str] = Field(default_factory=dict)
    openai_compatible: bool = False
    organization: str | None = None
    project: str | None = None
    websocket_base_url: str | None = None
    kwargs: dict[str, str] = Field(default_factory=dict)
    _api_key: str | None = PrivateAttr(None)

    @model_validator(mode="before")
    def _validate_kwargs(cls, data: dict):

        kwargs = data.pop("kwargs", {})
        field_keys = list(cls.model_json_schema().get("properties", {}).keys())
        for k in list(data.keys()):
            if k not in field_keys:
                kwargs[k] = data.pop(k)
        data["kwargs"] = kwargs
        return data

    @model_validator(mode="after")
    def _validate_api_key(self):
        if self.api_key is None and self.openai_compatible:
            raise ValueError("API key is required for OpenAI compatible endpoints")

        # Define the set of known environment variable names
        ENV_VAR_NAMES = {
            "OPENAI_API_KEY",
            "OPENROUTER_API_KEY",
            "EXA_API_KEY",
            "PERPLEXITY_API_KEY",
            "OLLAMA_API_KEY",
        }

        if self.api_key is not None:
            if isinstance(self.api_key, SecretStr):
                self._api_key = self.api_key.get_secret_value()
            elif isinstance(self.api_key, str) and self.api_key in ENV_VAR_NAMES:
                # Use settings singleton to get the secret
                from khive.config import settings

                try:
                    self._api_key = settings.get_secret(self.api_key)
                except (AttributeError, ValueError):
                    # Fall back to environment variable if not in settings
                    self._api_key = getenv(self.api_key, self.api_key)
            else:
                self._api_key = getenv(self.api_key, self.api_key)

        # Try settings helper before failing hard for known env vars
        if (
            self._api_key is None
            and isinstance(self.api_key, str)
            and self.api_key in ENV_VAR_NAMES
        ):
            from khive.config import settings

            try:
                self._api_key = settings.get_secret(self.api_key)
            except (AttributeError, ValueError):
                pass

        # Final check after all attempts to resolve the key
        if self._api_key is None:
            raise ValueError("API key is required but not set for this endpoint")

        return self

    @model_validator(mode="after")
    def _validate_base_url(self):
        if self.base_url is None and self.provider == "openai":
            self.base_url = "https://api.openai.com/v1"
        return self

    @property
    def full_url(self):
        if not self.endpoint_params:
            return f"{self.base_url}/{self.endpoint}"
        return f"{self.base_url}/{self.endpoint.format(**self.params)}"

    @field_validator("request_options", mode="before")
    def _validate_request_options(cls, v):
        if v is None:
            return None
        try:
            if isinstance(v, type) and issubclass(v, BaseModel):
                return v
            if isinstance(v, BaseModel):
                return v.__class__
            if isinstance(v, (dict, str)):
                return load_pydantic_model_from_schema(v)
        except Exception as e:
            raise ValueError(f"Invalid request options: {e}")
        raise ValueError(
            "Invalid request options: must be a Pydantic model or a schema dict"
        )

    @field_serializer("request_options")
    def _serialize_request_options(self, v: B | None):
        if v is None:
            return None
        return v.model_json_schema()

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise ValueError(f"Invalid key: {key}")

    def validate_payload(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate payload data against the request_options model.

        Args:
            data: The payload data to validate

        Returns:
            The validated data

        Raises:
            ValueError: If validation fails
        """
        if not self.request_options:
            return data

        try:
            validated = self.request_options.model_validate(data)
            return validated.model_dump(exclude_none=True)
        except Exception as e:
            raise ValueError(f"Invalid payload: {e}")


class Endpoint:
    """
    subclass should implement
    1) create_payload
    2) _call
    3) _stream, if applicable
    """

    def __init__(self, config: EndpointConfig | dict, **kwargs):
        if isinstance(config, EndpointConfig):
            config.update(**kwargs)
        elif isinstance(config, dict):
            config = EndpointConfig(**config, **kwargs)
        self.config = config
        self.client = None

    async def __aenter__(self):
        """Initialize the client when entering the context manager."""
        if not self.config.openai_compatible:
            self.client = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(self.config.timeout),
            )
        else:
            from openai import AsyncOpenAI

            self.client = AsyncOpenAI(
                api_key=self.config._api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout,
                max_retries=self.config.max_retries,
                organization=self.config.organization,
                project=self.config.project,
                websocket_base_url=self.config.websocket_base_url,
                default_headers=self.config.default_headers,
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close the client when exiting the context manager."""
        if self.client and not self.config.openai_compatible:
            await self.client.close()
        # AsyncOpenAI client doesn't need explicit closing

    async def aclose(self):
        """Gracefully close the client session."""
        if not self.config.openai_compatible and self.client and not self.client.closed:
            await self.client.close()

    @property
    def request_options(self):
        return self.config.request_options

    @request_options.setter
    def request_options(self, value):
        self.config.request_options = EndpointConfig._validate_request_options(value)

    def create_payload(
        self,
        request: dict | BaseModel,
        extra_headers: dict = None,
        **kwargs,
    ) -> tuple[dict, dict]:
        auth_header = self.config.auth_template.copy()
        for k, v in auth_header.items():
            auth_header[k] = v.replace("$API_KEY", self.config._api_key)
            break

        headers = {
            **self.config.default_headers,
            **(extra_headers or {}),
            **auth_header,
        }

        payload = (
            request
            if isinstance(request, dict)
            else request.model_dump(exclude_none=True)
        )

        # Use the validate_payload method to validate the payload
        update_config = {
            k: v
            for k, v in kwargs.items()
            if k in list(self.request_options.model_json_schema()["properties"].keys())
        }
        params = self.config.kwargs.copy()
        params.update(payload)
        params.update(update_config)

        return (params, headers)

    async def call(
        self, request: dict | BaseModel, cache_control: bool = False, **kwargs
    ):
        payload, headers = self.create_payload(request, **kwargs)

        async def _call(payload: dict, headers: dict, **kwargs):
            async with self:  # Use the context manager to handle client lifecycle
                if self.config.openai_compatible:
                    return await self._call_openai(
                        payload=payload, headers=headers, **kwargs
                    )
                return await self._call_aiohttp(
                    payload=payload, headers=headers, **kwargs
                )

        if not cache_control:
            return await _call(payload, headers, **kwargs)

        @cached(**settings.aiocache_config.as_kwargs())
        async def _cached_call(payload: dict, headers: dict, **kwargs):
            return await _call(payload=payload, headers=headers, **kwargs)

        return await _cached_call(payload, headers, **kwargs)

    async def _call_aiohttp(self, payload: dict, headers: dict, **kwargs):
        session = self.client  # ClientSession already initialized

        async def _make_request_with_backoff():
            response = None
            try:
                # Don't use context manager to have more control over response lifecycle
                response = await session.request(
                    method=self.config.method,
                    url=self.config.full_url,
                    headers=headers,
                    json=payload,
                    **kwargs,
                )

                # Check for rate limit or server errors that should be retried
                if response.status == 429 or response.status >= 500:
                    response.raise_for_status()  # This will be caught by backoff
                elif response.status != 200:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"Request failed with status {response.status}",
                        headers=response.headers,
                    )

                result = await response.json()
                return result
            finally:
                # Ensure response is properly released if coroutine is cancelled between retries
                if response is not None and not response.closed:
                    await response.release()

        # Define a giveup function for backoff
        def giveup_on_client_error(e):
            # Don't retry on 4xx errors except 429 (rate limit)
            if isinstance(e, aiohttp.ClientResponseError):
                return 400 <= e.status < 500 and e.status != 429
            return False

        # Use backoff for retries with exponential backoff and jitter
        # Moved inside the method to reference runtime config
        backoff_handler = backoff.on_exception(
            backoff.expo,
            (aiohttp.ClientError, asyncio.TimeoutError),
            max_tries=self.config.max_retries,
            giveup=giveup_on_client_error,
            jitter=backoff.full_jitter,
        )

        # Apply the decorator at runtime
        return await backoff_handler(_make_request_with_backoff)()

    async def _call_openai(self, payload: dict, headers: dict, **kwargs):
        payload = {**payload, **self.config.kwargs, **kwargs}

        if headers:
            payload["extra_headers"] = headers

        async def _make_request_with_backoff():
            if "chat" in self.config.endpoint:
                if "response_format" in payload:
                    return await self.client.beta.chat.completions.parse(**payload)
                payload.pop("response_format", None)
                return await self.client.chat.completions.create(**payload)

            if "responses" in self.config.endpoint:
                if "response_format" in payload:
                    return await self.client.responses.parse(**payload)
                payload.pop("response_format", None)
                return await self.client.responses.create(**payload)

            if "embed" in self.config.endpoint:
                return await self.client.embeddings.create(**payload)

            raise ValueError(f"Invalid endpoint: {self.config.endpoint}")

        # Define a giveup function for backoff
        def giveup_on_client_error(e):
            # Don't retry on 4xx errors except 429 (rate limit)
            if hasattr(e, "status") and isinstance(e.status, int):
                return 400 <= e.status < 500 and e.status != 429
            return False

        # Use backoff for retries with exponential backoff and jitter
        backoff_handler = backoff.on_exception(
            backoff.expo,
            Exception,  # OpenAI client can raise various exceptions
            max_tries=self.config.max_retries,
            giveup=giveup_on_client_error,
            jitter=backoff.full_jitter,
        )

        # Apply the decorator at runtime
        return await backoff_handler(_make_request_with_backoff)()


class iModel:

    def __init__(
        self,
        endpoint: Endpoint | EndpointConfig | dict,
        name: str | None = None,
        request_limit: int | None = 100,
        concurrency_limit: int | None = 20,
        limit_interval: int | None = 60,
        **kwargs,
    ):
        if isinstance(endpoint, Endpoint):
            self.endpoint = endpoint
            self.endpoint.config.update(**kwargs)
        elif isinstance(endpoint, (EndpointConfig, dict)):
            self.endpoint = Endpoint(endpoint, **kwargs)

        if name:
            self.endpoint.config.name = name

        # Set default limits based on provider if not specified
        if self.endpoint.config.provider == "openai":
            self.request_limit = request_limit or 3500
            self.limit_interval = limit_interval or 60
        elif self.endpoint.config.provider == "perplexity":
            self.request_limit = request_limit or 50
            self.limit_interval = limit_interval or 60
        else:
            self.request_limit = request_limit
            self.limit_interval = limit_interval

        self.concurrency_limit = concurrency_limit

        self.rate = AsyncLimiter(self.request_limit, self.limit_interval)
        # Use asyncio.Semaphore instead of anyio.CapacityLimiter
        self.slots = asyncio.Semaphore(self.concurrency_limit)

    @property
    def name(self):
        return self.endpoint.config.name

    def create_api_calling(
        self, headers: dict = None, cache_control: bool = False, **kwargs
    ):
        kwargs.update(self.endpoint.config.kwargs)
        if self.endpoint.request_options:
            # Use the validate_payload method
            kwargs = self.endpoint.config.validate_payload(kwargs)

        return APICalling(
            request=kwargs,
            endpoint=self.endpoint,
            headers=headers,
            cache_control=cache_control,
        )

    async def invoke(self, **kwargs):
        async with self.slots:
            async with self.rate:
                api_calling = self.create_api_calling(**kwargs)
                await api_calling.invoke()
                return api_calling

    def to_dict(self):
        return {
            "endpoint": self.endpoint.config.model_dump(),
            "request_limit": self.request_limit,
            "concurrency_limit": self.concurrency_limit,
            "limit_interval": self.limit_interval,
        }

    @classmethod
    def from_dict(cls, data: dict):
        endpoint = data.pop("endpoint")
        endpoint = EndpointConfig(**endpoint)
        return cls(endpoint=endpoint, **data)


class APICalling(Event):
    """Represents an API call event, storing payload, headers, and endpoint info.

    This class extends `Event` and provides methods to invoke or stream the
    request asynchronously.
    """

    endpoint: Endpoint = Field(exclude=True)
    cache_control: bool = Field(default=False, exclude=True)
    headers: dict | None = Field(None, exclude=True)

    async def invoke(self) -> None:
        """Invokes the API call, updating the execution state with results.

        Raises:
            Exception: If any error occurs, the status is set to FAILED and
                the error is logged.
        """
        start = asyncio.get_event_loop().time()
        response = None
        e1 = None

        try:
            # Use the endpoint as a context manager
            response = await self.endpoint.call(
                payload=self.request,
                headers=self.headers,
                cache_control=self.cache_control,
            )

        except asyncio.CancelledError as ce:
            e1 = ce
            logger.warning("invoke() canceled by external request.")
            raise
        except Exception as ex:
            e1 = ex

        finally:
            self.duration = asyncio.get_event_loop().time() - start
            if not response and e1:
                self.error = str(e1)
                self.status = EventStatus.FAILED
                logger.error(
                    msg=f"API call to {self.endpoint.config.full_url} failed: {e1}"
                )
            else:
                self.response_obj = response
                self.response = (
                    response.model_dump()
                    if isinstance(response, BaseModel)
                    else response
                )
                self.status = EventStatus.COMPLETED

    def __str__(self) -> str:
        return (
            f"APICalling(id={self.id}, status={self.status}, duration="
            f"{self.duration}, response={self.response}"
            f", error={self.error})"
        )

    __repr__ = __str__
