from abc import abstractmethod
from enum import Enum
from abc import ABC
from pydantic import BaseModel, Field, JsonValue

from .utils import serialize_model_to_dict

__all__ = (
    "Event",
    "InvokationStatus",
)


class InvokationStatus(str, Enum):
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


class Invokation:
    """Represents an invokation of an event."""

    def __init__(
        self,
        request: dict = None,
        response: dict = None,
        status: InvokationStatus = InvokationStatus.PENDING,
        duration: float = None,
        error: str = None,
        error_code: str = None,
        response_obj: BaseModel | dict = None,
    ):
        """Initializes the Invokation class.

        Args:
            request (dict): The request json dict for the invokation.
            response (dict): The response json object for the invokation.
            status (InvokationStatus): The status of the invokation.
            duration (float): The duration of the invokation in seconds.
            error (str): The error message if the invokation failed.
            error_code (str): The error code if the invokation failed. If any.
            response_obj (BaseModel | dict): The response object for the invokation.
        """

        self.request: dict = request
        self.response: JsonValue = response
        self.status: InvokationStatus = status
        self.duration: float | None = duration
        self.error: str | None = error
        self.error_code: str | None = error_code
        self._response_obj: BaseModel | dict = response_obj

    @classmethod
    def create(
        cls,
        request: dict | BaseModel = None,
        response: dict | BaseModel = None,
        response_obj: BaseModel | dict = None,
    ):
        params = {}
        params["request"] = serialize_model_to_dict(request)
        params["response"] = serialize_model_to_dict(response_obj or response)
        if response_obj:
            params["response_obj"] = response_obj

        return cls(**params)

    def to_dict(self):
        """Converts the Invokation object to a dictionary."""
        return {
            "request": self.request,
            "response": self.response,
            "status": self.status.value,
            "duration": self.duration,
            "error": self.error,
            "error_code": self.error_code,
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Populates the Invokation object from a dictionary."""
        self = cls()
        self.request = data.get("request")
        self.response = data.get("response")
        self.status = InvokationStatus(data.get("status"))
        self.duration = data.get("duration")
        self.error = data.get("error")
        self.error_code = data.get("error_code")
        self._response_obj = data.get("response_obj")


class Invokable(ABC):
    """Extends Element with an execution state.

    Attributes:
        execution (Execution): The execution state of this event.
    """

    invokation: Invokation = Field(default_factory=Invokation)

    @abstractmethod
    async def invoke(self, *args, **kwargs):
        pass
