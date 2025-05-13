import json
from functools import wraps
from typing import Any, Callable

from pydapter import AsyncAdapter

from khive.utils import validate_model_to_dict

from .embedable import Embedable
from .identifiable import Identifiable
from .invokable import Invokable
from .types import Log


class Event(Identifiable, Embedable, Invokable):

    def __init__(
        self,
        event_invoke_function: Callable,
        *event_invoke_args: list[Any],
        **event_invoke_kwargs: dict[str, Any],
    ):
        super().__init__()
        self._invoke_function = event_invoke_function
        self._invoke_args = event_invoke_args or []
        self._invoke_kwargs = event_invoke_kwargs or {}

    def create_content(self):
        if self.content is not None:
            return self.content

        event = {"request": self.request, "response": self.execution.response}
        self.content = json.dumps(event, default=str, ensure_ascii=False)
        return self.content

    def to_log(self):
        if self.content is None:
            self.create_content()

        event_dict = self.model_dump()
        log_params = {}
        for k, v in event_dict.items():
            if k in Log.model_fields:
                log_params[k] = v
            if k == "execution":
                for k2, v2 in v.items():
                    if k2 in Log.model_fields:
                        log_params[k2] = v2

        return Log(**log_params)


def as_event(
    *,
    request_arg: str | None = None,
    embed_content: bool = False,
    store: bool = False,
    store_as_log: bool = False,
    storage_adapter: type[AsyncAdapter] | None = None,
    **storage_kw,
):

    def decorator(func: Callable):

        @wraps(func)
        async def wrapper(*args, **kwargs) -> Event:
            if store is True and storage_adapter is None:
                raise ValueError("Storage adapter is not provided.")

            args = args[1:] if args and hasattr(args[0], "__class__") else args
            event = Event(func, *args, **kwargs)

            request_obj = kwargs.get(request_arg) if request_arg else args[0]
            event.request = validate_model_to_dict(request_obj)
            await event.invoke()
            if embed_content:
                event = await event.generate_embedding()

            if store:
                if store_as_log:
                    log = event.to_log()
                    await storage_adapter.to_obj(log, **storage_kw)
                else:
                    await storage_adapter.to_obj(event, **storage_kw)

            return event

        return wrapper

    return decorator
