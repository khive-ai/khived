import asyncio
import logging

from pydantic import BaseModel, Field

from khive.protocols.event import Event, EventStatus

from .endpoint import Endpoint

logger = logging.getLogger(__name__)


class APICalling(Event):
    """Represents an API call event, storing payload, headers, and endpoint info.

    This class extends `Event` and provides methods to invoke or stream the
    request asynchronously.
    """

    endpoint: Endpoint = Field(exclude=True)
    cache_control: bool = Field(default=False, exclude=True)
    headers: dict | None = Field(None, exclude=True)

    async def invoke(self) -> None:
        """Invokes the API call, updating the execution state with results.

        Raises:
            Exception: If any error occurs, the status is set to FAILED and
                the error is logged.
        """
        start = asyncio.get_event_loop().time()
        response = None
        e1 = None

        try:
            # Use the endpoint as a context manager
            response = await self.endpoint.call(
                payload=self.request,
                headers=self.headers,
                cache_control=self.cache_control,
            )

        except asyncio.CancelledError as ce:
            e1 = ce
            logger.warning("invoke() canceled by external request.")
            raise
        except Exception as ex:
            e1 = ex

        finally:
            self.duration = asyncio.get_event_loop().time() - start
            if not response and e1:
                self.error = str(e1)
                self.status = EventStatus.FAILED
                logger.error(
                    msg=f"API call to {self.endpoint.config.full_url} failed: {e1}"
                )
            else:
                self.response_obj = response
                self.response = (
                    response.model_dump()
                    if isinstance(response, BaseModel)
                    else response
                )
                self.status = EventStatus.COMPLETED

    def __str__(self) -> str:
        return (
            f"APICalling(id={self.id}, status={self.status}, duration="
            f"{self.duration}, response={self.response}"
            f", error={self.error})"
        )

    __repr__ = __str__
