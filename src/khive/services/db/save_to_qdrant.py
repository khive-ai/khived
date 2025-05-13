import asyncio
import json
from functools import wraps

import orjson as json
from pydapter import AsyncAdapter

from khive.utils import is_coroutine_function

from ...memories.memory import Memory


def save_to_memory(
    *,
    memory_model: type[Memory] = Memory,
    adapter: type[AsyncAdapter] = None,
    request_arg: str | None = None,
    **kw,
):

    if adapter is None:
        from pydapter.extras.async_qdrant_ import AsyncQdrantAdapter

        adapter = AsyncQdrantAdapter

    if adapter.obj_key not in (memory_model._async_registry or {}):
        memory_model.register_async_adapter(adapter)

    """a decorator"""

    def decorator(func):
        is_async = is_coroutine_function(func)

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # -------------------------------------------------- run original
            if is_async:
                response = await func(*args, **kwargs)
            else:  # keep loop non-blocking
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None, lambda: func(*args, **kwargs)
                )

            # ------------------------------------------------ build event
            if request_arg and request_arg in kwargs:
                request_obj = kwargs[request_arg]
            else:
                # skip `self` if present
                request_obj = (
                    args[1]
                    if args and hasattr(args[0], "__class__")
                    else (args[0] if args else None)
                )

            event = {
                "request": request_obj,
                "response": (
                    response.model_dump()
                    if hasattr(response, "model_dump")
                    else response
                ),
            }
            content = json.dumps(event, default=str, ensure_ascii=False)

            # -------------------------------------------- embed & persist
            memory: Memory = await memory_model(content=content).generate_embedding()
            await memory.adapt_to_async(obj_key=adapter.obj_key, **kw)

            return response

        return wrapper

    return decorator
