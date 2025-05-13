# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

import logging

from pydantic import Field

from khive.traits.identifiable import Identifiable
from khive.traits.invokable import Invokable

from .endpoint import Endpoint

logger = logging.getLogger(__name__)


class APICalling(Identifiable, Invokable):
    """Represents an API call event, storing payload, headers, and endpoint info.

    This class extends `Event` and provides methods to invoke or stream the
    request asynchronously.
    """

    endpoint: Endpoint = Field(exclude=True)
    cache_control: bool = Field(default=False, exclude=True)
    headers: dict | None = Field(None, exclude=True)

    async def _invoke(self):
        return await self.endpoint.call(
            payload=self.request,
            headers=self.headers,
            cache_control=self.cache_control,
        )
