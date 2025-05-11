from enum import Enum

from pydantic import BaseModel, field_validator

from khive.protocols.utils import validate_model_to_dict

from .identifiable import Identifiable, Temporal

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


class EventRequest(Identifiable):
    service_name: str
    action: str
    options: dict

    @field_validator("options", mode="before")
    def _serialize_options(cls, v: dict | BaseModel) -> dict:
        return validate_model_to_dict(v)


class Execution(Temporal):
    response: dict | None = None
    error: str | None = None
    status: EventStatus = EventStatus.PENDING
    duration: float | None = None

    @field_validator("response", mode="before")
    def _serialize_response(cls, v: dict | BaseModel) -> dict:
        return validate_model_to_dict(v)


class Event(Identifiable):
    request: EventRequest
    execution: Execution | None = None
