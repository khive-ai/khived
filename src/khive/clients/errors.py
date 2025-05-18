# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Error classes for the API client.

This module defines the error classes for the API client, including
connection errors, timeout errors, rate limit errors, authentication errors,
resource not found errors, server errors, and circuit breaker errors.
"""

from typing import Optional, Dict, Any


class APIClientError(Exception):
    """Base exception for all API client errors."""

    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        response_data: Optional[Dict[str, Any]] = None
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


class ConnectionError(APIClientError):
    """Exception raised when a connection error occurs."""
    pass


class TimeoutError(APIClientError):
    """Exception raised when a request times out."""
    pass


class RateLimitError(APIClientError):
    """Exception raised when a rate limit is exceeded."""

    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = 429,
        headers: Optional[Dict[str, str]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        retry_after: Optional[float] = None
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
    pass


class ResourceNotFoundError(APIClientError):
    """Exception raised when a resource is not found."""
    pass


class ServerError(APIClientError):
    """Exception raised when a server error occurs."""
    pass


class CircuitBreakerOpenError(APIClientError):
    """Exception raised when a circuit breaker is open."""

    def __init__(
        self, 
        message: str, 
        retry_after: Optional[float] = None
    ):
        """
        Initialize the circuit breaker open error.

        Args:
            message: The error message.
            retry_after: The time to wait before retrying, in seconds.
        """
        super().__init__(message)
        self.retry_after = retry_after