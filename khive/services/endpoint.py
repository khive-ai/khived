import asyncio
import logging
from os import getenv
from typing import Literal, TypeVar

import aiohttp
from aiocache import cached
from aiolimiter import AsyncLimiter
from anyio import CapacityLimiter
from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
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
    api_key: str | None = None
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
        if self.api_key is not None:
            self._api_key = getenv(self.api_key, self.api_key)
        return self

    @property
    def full_url(self):
        if not self.endpoint_params:
            return self.base_url + self.endpoint
        return self.base_url + self.endpoint.format(**self.params)

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
            if self.config.openai_compatible:
                return await self._call_openai(
                    payload=payload, headers=headers, **kwargs
                )
            return await self._call_aiohttp(payload=payload, headers=headers, **kwargs)

        if not cache_control:
            return await _call(payload, headers, **kwargs)

        @cached(**settings.CACHED_CONFIG)
        async def _cached_call(payload: dict, headers: dict, **kwargs):
            return await _call(payload=payload, headers=headers, **kwargs)

        return await _cached_call(payload, headers, **kwargs)

    async def _call_aiohttp(self, payload: dict, headers: dict, **kwargs):
        async with self.client as session:
            for i in range(self.config.max_retries):
                try:
                    async with session.request(
                        method=self.config.method,
                        url=self.config.full_url,
                        headers=headers,
                        json=payload,
                        **kwargs,
                    ) as response:
                        if response.status != 200:
                            raise ValueError(
                                f"Request failed with status {response.status}"
                            )
                        return await response.json()
                except asyncio.CancelledError:
                    logger.warning("Request cancelled")
                    raise
                except aiohttp.ClientError as e:
                    logger.error(f"Request failed: {e}")
                    raise
                except Exception as e:
                    logger.error(f"Request failed: {e}")
                    if i < self.config.max_retries - 1:
                        await asyncio.sleep(2**i)
                    else:
                        raise

    async def _call_openai(self, payload: dict, headers: dict, **kwargs):
        payload = {**payload, **self.config.kwargs, **kwargs}

        if headers:
            payload["extra_headers"] = headers

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
        self.request_limit = request_limit
        self.concurrency_limit = concurrency_limit
        self.limit_interval = limit_interval

        self.rate = AsyncLimiter(request_limit, limit_interval)
        self.slots = CapacityLimiter(concurrency_limit)

    @property
    def name(self):
        return self.endpoint.config.name

    def create_api_calling(
        self, headers: dict = None, cache_control: bool = False, **kwargs
    ):
        kwargs.update(self.endpoint.config.kwargs)
        if self.endpoint.request_options:
            kwargs = self.endpoint.request_options.model_validate(kwargs)

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
                    msg=f"API call to {self.endpoint.config.base_url + self.endpoint.config.endpoint} failed: {e1}"
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
