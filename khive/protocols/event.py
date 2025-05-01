from abc import abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_serializer, field_validator

from .element import Element

__all__ = (
    "EventStatus",
    "Execution",
    "Event",
)


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


class Event(Element):
    """Extends Element with an execution state.

    Attributes:
        execution (Execution): The execution state of this event.
    """

    request: dict | None = None
    status: EventStatus = EventStatus.PENDING
    duration: float | None = None
    response: Any = None
    error: str | None = None
    error_code: str | None = None
    response_obj: Any = Field(None, exclude=True)

    @field_validator("request", mode="before")
    def _validate_request(cls, v):
        if isinstance(v, Element):
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
