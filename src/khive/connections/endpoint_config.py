# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

import os
from typing import Any, Literal, TypeVar

from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
    SecretStr,
    field_serializer,
    field_validator,
    model_validator,
)

from .header_factory import AUTH_TYPES

B = TypeVar("B", bound=type[BaseModel])


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

    @property
    def full_url(self):
        if not self.endpoint_params:
            return f"{self.base_url}/{self.endpoint}"
        return f"{self.base_url}/{self.endpoint.format(**self.params)}"

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

    @field_serializer("request_options")
    def _serialize_request_options(self, v: B | None):
        if v is None:
            return None
        return v.model_json_schema()

    def update(self, **kwargs):
        """Update the config with new values."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                # Add to kwargs dict if not a direct attribute
                self.kwargs[key] = value

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
