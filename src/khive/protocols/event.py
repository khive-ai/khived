from abc import abstractmethod
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from ._utils import serialize_model_to_dict
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
        return serialize_model_to_dict(v)

    @abstractmethod
    async def invoke(self, *args, **kwargs):
        pass
