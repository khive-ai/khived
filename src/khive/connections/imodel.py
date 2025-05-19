import asyncio
from datetime import datetime
from typing import Any

from pydantic import Field, field_serializer, field_validator
from pydapter.protocols import Temporal
from pydapter.protocols.types import ExecutionStatus

from .api_call import APICalling
from .endpoint import Endpoint
from .rate_limited_executor import RateLimitedExecutor


class iModel(Temporal):

    endpoint: Endpoint
    executor: RateLimitedExecutor
    last_used: datetime | None = None

    @field_serializer("executor")
    def _serialize_executor(self, value: RateLimitedExecutor) -> dict[str, Any]:
        return value.to_dict()

    @field_validator("executor", mode="before")
    def _validate_executor(
        self, value: RateLimitedExecutor | dict
    ) -> RateLimitedExecutor:
        if isinstance(value, dict):
            return RateLimitedExecutor.from_dict(value)
        return value

    @field_serializer("endpoint")
    def _serialize_endpoint(self, value: Endpoint) -> dict[str, Any]:
        return value.config.model_dump()

    @field_validator("endpoint", mode="before")
    def _validate_endpoint(self, value: Endpoint | dict | None) -> Endpoint:
        if isinstance(value, dict):
            return Endpoint(value)
        return value

    def create_api_calling(
        self, request: dict | None = None, cache_control: bool = False, **kwargs
    ) -> APICalling:
        if self.endpoint is None:
            raise ValueError("Endpoint is not set")

        return APICalling(
            endpoint=self.endpoint,
            request=request or {},
            cache_control=cache_control,
            **kwargs,
        )

    def update_last_used(self) -> None:
        self.last_used = datetime.now()

    @field_serializer("last_used")
    def _serialize_last_used(self, value: datetime | None) -> str | None:
        return self._serialize_datetime(value)

    @field_validator("last_used", mode="before")
    def _validate_last_used(self, value: str | None) -> datetime | None:
        return self._validate_datetime(value)

    async def invoke(
        self, api_call: APICalling | list[APICalling]
    ) -> APICalling | list[APICalling]:
        try:
            async with self.executor as exe:
                api_call = [api_call] if not isinstance(api_call, list) else api_call
                for call in api_call:
                    exe.append(call)
                await exe.forward()

                ctr = 0
                while not all(
                    call.execution.status
                    in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED)
                    for call in api_call
                ):
                    if ctr > 1000:
                        break
                    await exe.forward()
                    ctr += 1
                    await asyncio.sleep(0.1)
                return [exe.pop(call.id) for call in api_call]
        except Exception as e:
            raise ValueError(f"Failed to invoke API call: {e}")
        finally:
            self.update_last_used()
