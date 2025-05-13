import json
from collections.abc import Callable
from functools import wraps
from typing import Any

from pydapter import AsyncAdapter

from khive.config import settings
from khive.utils import validate_model_to_dict

from .embedable import Embedable
from .identifiable import Identifiable
from .invokable import Invokable
from .types import Log


class Event(Identifiable, Embedable, Invokable):
    def __init__(
        self,
        event_invoke_function: Callable,
        event_invoke_args: list[Any],
        event_invoke_kwargs: dict[str, Any],
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

    def to_log(self, event_type: str | None = None) -> Log:
        if self.content is None:
            self.create_content()

        event_dict = self.model_dump()
        log_params = {"event_type": event_type or self.__class__.__name__}
        for k, v in event_dict.items():
            if k in Log.model_fields:
                log_params[k] = v
            if k == "execution":
                execution = {k: v for k, v in v.items() if k in Log.model_fields}
                log_params.update(execution)

        return Log(**log_params)


def as_event(
    *,
    request_arg: str | None = None,
    embed_content: bool = settings.KHIVE_AUTO_EMBED_LOG,
    store: bool = settings.KHIVE_AUTO_STORE_EVENT,
    storage_adapter: type[AsyncAdapter] | None = None,
    event_type: str | None = None,
    **storage_kw,
):
    def decorator(func: Callable):
        adapter = storage_adapter
        if store is True and storage_adapter is None:
            if (_a := settings.KHIVE_STORAGE_PROVIDER) is not None:
                if _a == "async_qdrant":
                    from pydapter.extras.async_qdrant_ import AsyncQdrantAdapter

                    adapter = AsyncQdrantAdapter
                if _a == "async_mongodb":
                    from pydapter.extras.async_mongo_ import AsyncMongoAdapter

                    adapter = AsyncMongoAdapter
                if _a == "async_postgres_":
                    from pydapter.extras.async_postgres_ import AsyncPostgresAdapter

                    adapter = AsyncPostgresAdapter
            if adapter is None:
                raise ValueError(
                    f"Storage adapter {_a} is not supported. "
                    "Please provide a valid storage adapter."
                )

        @wraps(func)
        async def wrapper(*args, **kwargs) -> Event:
            args = args[1:] if args and hasattr(args[0], "__class__") else args
            event = Event(func, args, kwargs)

            request_obj = kwargs.get(request_arg) if request_arg else args[0]
            event.request = validate_model_to_dict(request_obj)
            await event.invoke()
            if embed_content:
                event = await event.generate_embedding()

            if store:
                await adapter.to_obj(event.to_log(event_type=event_type), **storage_kw)

            return event

        return wrapper

    return decorator
