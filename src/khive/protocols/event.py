from abc import abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .identifiable import Identifiable

__all__ = (
    "Event",
    "EventStatus",
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


class Event(Identifiable):
    """Extends Element with an execution state.

    Attributes:
        execution (Execution): The execution state of this event.
    """

    request: dict | None = None
    response: Any = None
    status: EventStatus = EventStatus.PENDING
    duration: float | None = None
    error: str | None = None
    response_obj: Any = Field(None, exclude=True)

    @field_validator("request", mode="before")
    def _validate_request(cls, v):
        """Serialize a Pydantic model to a dictionary. kwargs are passed to model_dump."""

        if isinstance(v, BaseModel):
            return v.model_dump()
        if v is None:
            return {}
        if isinstance(v, dict):
            return v

        error_msg = "Input value for field <model> should be a `pydantic.BaseModel` object or a `dict`"
        raise ValueError(error_msg)

    @abstractmethod
    async def invoke(self, *args, **kwargs):
        pass
