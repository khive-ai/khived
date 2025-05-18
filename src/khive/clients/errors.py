# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Error classes for the API client.

This module defines the error classes for the API client, including
connection errors, timeout errors, rate limit errors, authentication errors,
resource not found errors, server errors, circuit breaker errors, and queue-related errors.
"""

from typing import Any


class APIClientError(Exception):
    """Base exception for all API client errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
        response_data: dict[str, Any] | None = None,
    ):
        """
        Initialize the API client error.

        Args:
            message: The error message.
            status_code: The HTTP status code, if applicable.
            headers: The response headers, if applicable.
            response_data: The response data, if applicable.
        """
        self.message = message
        self.status_code = status_code
        self.headers = headers or {}
        self.response_data = response_data or {}
        super().__init__(message)


class APIConnectionError(APIClientError):
    """Exception raised when a connection error occurs."""


class APITimeoutError(APIClientError):
    """Exception raised when a request times out."""


class RateLimitError(APIClientError):
    """Exception raised when a rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        status_code: int | None = 429,
        headers: dict[str, str] | None = None,
        response_data: dict[str, Any] | None = None,
        retry_after: float | None = None,
    ):
        """
        Initialize the rate limit error.

        Args:
            message: The error message.
            status_code: The HTTP status code (default: 429).
            headers: The response headers, if applicable.
            response_data: The response data, if applicable.
            retry_after: The time to wait before retrying, in seconds.
        """
        super().__init__(message, status_code, headers, response_data)
        self.retry_after = retry_after


class AuthenticationError(APIClientError):
    """Exception raised when authentication fails."""


class ResourceNotFoundError(APIClientError):
    """Exception raised when a resource is not found."""


class ServerError(APIClientError):
    """Exception raised when a server error occurs."""


class CircuitBreakerOpenError(APIClientError):
    """Exception raised when a circuit breaker is open."""

    def __init__(self, message: str, retry_after: float | None = None):
        """
        Initialize the circuit breaker open error.

        Args:
            message: The error message.
            retry_after: The time to wait before retrying, in seconds.
        """
        super().__init__(message)
        self.retry_after = retry_after


class TestError(APIClientError):
    """Exception raised for testing purposes."""

    def __init__(self, message: str = "Test exception"):
        """
        Initialize the test error.

        Args:
            message: The error message (default: "Test exception").
        """
        super().__init__(message)


class QueueError(APIClientError):
    """Base exception for all queue-related errors."""


class QueueFullError(QueueError):
    """Exception raised when a queue is full and cannot accept more items."""

    def __init__(
        self,
        message: str = "Queue is full",
        queue_size: int | None = None,
        queue_capacity: int | None = None,
    ):
        """
        Initialize the queue full error.

        Args:
            message: The error message.
            queue_size: The current queue size.
            queue_capacity: The maximum queue capacity.
        """
        details = {}
        if queue_size is not None:
            details["queue_size"] = queue_size
        if queue_capacity is not None:
            details["queue_capacity"] = queue_capacity

        super().__init__(message, response_data=details)


class QueueEmptyError(QueueError):
    """Exception raised when trying to get an item from an empty queue."""

    def __init__(self, message: str = "Queue is empty"):
        """
        Initialize the queue empty error.

        Args:
            message: The error message.
        """
        super().__init__(message)


class QueueStateError(QueueError):
    """Exception raised when queue operations are attempted in invalid states."""

    def __init__(self, message: str, current_state: str | None = None):
        """
        Initialize the queue state error.

        Args:
            message: The error message.
            current_state: The current state of the queue.
        """
        details = {}
        if current_state is not None:
            details["current_state"] = current_state

        super().__init__(message, response_data=details)
