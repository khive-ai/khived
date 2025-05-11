from pydantic import BaseModel
from typing import ClassVar, Any
from abc import abstractmethod
from .event import Event

class ServiceGroupMeta(BaseModel):
    name: str
    actions: set[str]
    instructions: str | None = None
    default_settings: dict[str, str] | None = None

class ServiceGroup:
    
    metadata: ClassVar[ServiceGroupMeta]
    
    @abstractmethod
    async def handle_request(self, request: BaseModel) -> BaseModel:
        pass

class ServiceRequest(BaseModel):
    service_name: str
    action: str
    params: dict[str, Any] | None = None
    
    
class ServiceResponse(BaseModel):
    pass


class ServiceEvent(Event):
    
    def __init__(
        self,
        request: ServiceRequest,
        response: ServiceResponse | None = None,
        status: str = "pending",
        duration: float | None = None,
        error: str | None = None,
        response_obj: Any = None,
    ):
        super().__init__(
            request=request,
            response=response,
            status=status,
            duration=duration,
            error=error,
            response_obj=response_obj,
        )
