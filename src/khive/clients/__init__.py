# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Khive API Client module.

This module provides robust async API clients with resource management,
rate limiting, concurrency control, and resilience patterns.
"""

from .api_client import AsyncAPIClient
from .protocols import ResourceClient, Executor, RateLimiter, Queue
from .errors import (
    APIClientError,
    ConnectionError,
    TimeoutError,
    RateLimitError,
    AuthenticationError,
    ResourceNotFoundError,
    ServerError,
    CircuitBreakerOpenError,
)
from .rate_limiter import TokenBucketRateLimiter
from .executor import AsyncExecutor, RateLimitedExecutor
from .resilience import CircuitBreaker, retry_with_backoff

__all__ = [
    "AsyncAPIClient",
    "ResourceClient",
    "Executor",
    "RateLimiter",
    "Queue",
    "APIClientError",
    "ConnectionError",
    "TimeoutError",
    "RateLimitError",
    "AuthenticationError",
    "ResourceNotFoundError",
    "ServerError",
    "CircuitBreakerOpenError",
    "TokenBucketRateLimiter",
    "AsyncExecutor",
    "RateLimitedExecutor",
    "CircuitBreaker",
    "retry_with_backoff",
]