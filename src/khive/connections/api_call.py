# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
APICalling event class for representing API calls.

This module provides the APICalling class, which is an Event subclass
that represents an API call to be executed.
"""

from pydantic import PrivateAttr
from pydapter.protocols.event import Event

from khive.connections.endpoint import Endpoint


class APICalling(Event):
    """
    Event representing an API call to be executed.

    This class extends the Event base class to represent an API call
    that can be queued and executed by an Executor. It encapsulates
    the endpoint, request parameters, and token requirements.

    Attributes:
        requires_tokens: Whether this API call requires tokens for rate limiting.
        _required_tokens: The number of tokens required for this API call.
    """

    requires_tokens: bool = False
    _required_tokens: int | None = PrivateAttr(None)

    def __init__(
        self,
        endpoint: Endpoint,
        request: dict,
        cache_control: bool = False,
        requires_tokens: bool = False,
        **kwargs,
    ):
        """
        Initialize the API call event.

        Args:
            endpoint: The endpoint to call.
            request: The request parameters.
            cache_control: Whether to use cache control.
            requires_tokens: Whether this API call requires tokens for rate limiting.
            **kwargs: Additional keyword arguments for the endpoint call.
        """
        invoke_function = endpoint.call
        invoke_kwargs = {"request": request, "cache_control": cache_control, **kwargs}

        super().__init__(
            event_invoke_function=invoke_function,
            event_invoke_args=None,
            event_invoke_kwargs=invoke_kwargs,
            event_type="api_calling",
        )
        self.requires_tokens = requires_tokens

    @property
    def required_tokens(self) -> int:
        """
        Get the number of tokens required for this API call.

        Returns:
            The number of tokens required, or None if not set.
        """
        return self._required_tokens

    @required_tokens.setter
    def required_tokens(self, value: int) -> None:
        """
        Set the number of tokens required for this API call.

        Args:
            value: The number of tokens required.
        """
        self._required_tokens = value
