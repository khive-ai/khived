import asyncio
from datetime import datetime
from typing import Any

from pydantic import field_serializer, field_validator
from pydapter.protocols import Temporal
from pydapter.protocols.types import ExecutionStatus

from .api_call import APICalling
from .endpoint import Endpoint
from .rate_limited_executor import RateLimitedExecutor


class iModel(Temporal):
    endpoint: Endpoint
    executor: RateLimitedExecutor
    last_used: datetime | None = None

    def __init__(
        self,
        provider: str,
        endpoint: Endpoint | dict | str,
        queue_capacity: int = 100,
        capacity_refresh_time: float = 1,
        interval: float | None = None,
        limit_requests: int = None,
        limit_tokens: int = None,
        concurrency_limit: int | None = None,
        counter: int = None,
    ):
        if isinstance(endpoint, str):
            from .match_endpoint import match_endpoint

            endpoint = match_endpoint(provider, endpoint)
        if isinstance(endpoint, dict):
            endpoint = Endpoint(endpoint)
        executor = RateLimitedExecutor(
            queue_capacity=queue_capacity,
            capacity_refresh_time=capacity_refresh_time,
            interval=interval,
            limit_requests=limit_requests,
            limit_tokens=limit_tokens,
            concurrency_limit=concurrency_limit,
            counter=counter,
        )
        super().__init__(endpoint=endpoint, executor=executor)

    @field_serializer("executor")
    def _serialize_executor(self, value: RateLimitedExecutor) -> dict[str, Any]:
        return value.to_dict()

    @field_validator("executor", mode="before")
    def _validate_executor(
        cls, value: RateLimitedExecutor | dict
    ) -> RateLimitedExecutor:
        if isinstance(value, dict):
            return RateLimitedExecutor.from_dict(value)
        return value

    @field_serializer("endpoint")
    def _serialize_endpoint(self, value: Endpoint) -> dict[str, Any]:
        return value.config.model_dump()

    @field_validator("endpoint", mode="before")
    def _validate_endpoint(cls, value: Endpoint | dict | None) -> Endpoint:
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
    def _validate_last_used(cls, value: str | None) -> datetime | None:
        return cls._validate_datetime(value)

    async def invoke(self, api_call: APICalling | list[APICalling]) -> list[APICalling]:
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
