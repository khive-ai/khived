from __future__ import annotations

import logging
from abc import abstractmethod
from enum import Enum
from typing import Any

from pydantic import (
    BaseModel,
    Field,
    JsonValue,
    PrivateAttr,
    field_serializer,
    field_validator,
)

from .element import Identifiable

logger = logging.getLogger(__name__)


class EventStatus(str, Enum):
    """Status states for tracking action execution progress.

    Attributes:
        PENDING: Initial state before execution starts.
        PROCESSING: Action is currently being executed.
        COMPLETED: Action completed successfully.
        FAILED: Action failed during execution.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Event(Identifiable):
    """Represents an event in the system."""

    @classmethod
    def from_dict(cls, data: dict):
        raise NotImplementedError("Event cannot be re-constructed from a dictionary.")


class Event(Identifiable):
    request: dict | None = None
    response: Any = None
    status: EventStatus = EventStatus.PENDING
    duration: float | None = None
    error: str | None = None
    error_code: str | None = None
    response_obj: Any = Field(None, exclude=True)


__all__ = (
    "Event",
    "EventStatus",
)


class Event(Identifiable):
    request: dict | None = None
    response: Any = None
    status: EventStatus = EventStatus.PENDING
    duration: float | None = None
    error: str | None = None
    error_code: str | None = None
    response_obj: Any = Field(None, exclude=True)

    @field_validator("request", mode="before")
    def _validate_request(cls, v):
        if isinstance(v, Identifiable):
            return v.to_dict()
        if isinstance(v, BaseModel):
            return v.model_dump()
        if isinstance(v, dict):
            return v
        if v is None:
            return {}

    @field_serializer("status")
    def _serialize_request(self, v: EventStatus):
        return v.value

    @abstractmethod
    async def invoke(self, *args, **kwargs):
        pass


class Log(Identifiable):
    """
    An immutable log entry that wraps a dictionary of content.

    Once created or restored from a dictionary, the log is marked
    as read-only.
    """

    content: dict[str, JsonValue]
    _immutable: bool = PrivateAttr(False)

    def __setattr__(self, name: str, value: Any) -> None:
        """Prevent mutation if log is immutable."""
        if getattr(self, "_immutable", False):
            raise AttributeError("This Log is immutable.")
        super().__setattr__(name, value)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Log:
        """
        Create a Log from a dictionary previously produced by `to_dict`.

        The dictionary must contain keys in `serialized_keys`.
        """
        self = cls.model_validate(data)
        self._immutable = True
        return self

    @classmethod
    def create(cls, content: BaseModel | dict) -> Log:
        """
        Create a new Log from an Element, storing a dict snapshot
        of the element's data.
        """
        if isinstance(content, BaseModel):
            content = content.model_dump()

        if content == {}:
            logger.warning(
                "No content to log, or original data was of invalid type. Making an empty log..."
            )
            return cls(content={"error": "No content to log."})
        if not isinstance(content, dict):
            raise ValueError(
                "The input content for log creation should be of type `Element`, subclass of `pydantic.BaseModel` or a python dict"
            )

        return cls(content=content)
