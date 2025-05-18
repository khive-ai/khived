# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Khive API Client module.

This module provides robust async API clients with resource management,
rate limiting, concurrency control, and resilience patterns.
"""

from .api_client import AsyncAPIClient
from .errors import (
    APIClientError,
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    CircuitBreakerOpenError,
    RateLimitError,
    ResourceNotFoundError,
    ServerError,
)
from .executor import AsyncExecutor, RateLimitedExecutor
from .protocols import Executor, Queue, RateLimiter, ResourceClient
from .rate_limiter import TokenBucketRateLimiter
from .resilience import CircuitBreaker, retry_with_backoff

__all__ = [
    "AsyncAPIClient",
    "ResourceClient",
    "Executor",
    "RateLimiter",
    "Queue",
    "APIClientError",
    "APIConnectionError",
    "APITimeoutError",
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
