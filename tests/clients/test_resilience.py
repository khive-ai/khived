# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for resilience patterns.

This module contains tests for the circuit breaker and retry patterns
implemented in the resilience module.
"""

from unittest.mock import AsyncMock, patch

import pytest

from khive.clients.errors import CircuitBreakerOpenError
from khive.clients.resilience import (
    CircuitBreaker,
    CircuitState,
    RetryConfig,
    circuit_breaker,
    retry_with_backoff,
    with_retry,
)


class TestCircuitBreaker:
    """Tests for the CircuitBreaker class."""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test that CircuitBreaker initializes with correct default values."""
        cb = CircuitBreaker(failure_threshold=5, recovery_time=30.0)

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_threshold == 5
        assert cb.recovery_time == 30.0
        assert cb.failure_count == 0
        assert cb._metrics["success_count"] == 0
        assert cb._metrics["failure_count"] == 0
        assert cb._metrics["rejected_count"] == 0
        assert len(cb._metrics["state_changes"]) == 0

    @pytest.mark.asyncio
    async def test_state_transition_to_open(self):
        """Test that CircuitBreaker transitions from CLOSED to OPEN after reaching failure threshold."""
        # Arrange
        cb = CircuitBreaker(failure_threshold=2)
        failing_function = AsyncMock(side_effect=ValueError("Test error"))

        # Act & Assert
        # First failure - circuit stays closed
        with pytest.raises(ValueError):
            await cb.execute(failing_function)
        assert cb.state == CircuitState.CLOSED

        # Second failure - circuit opens
        with pytest.raises(ValueError):
            await cb.execute(failing_function)
        assert cb.state == CircuitState.OPEN

        # Call when circuit is open - raises CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            await cb.execute(failing_function)

    @pytest.mark.asyncio
    async def test_state_transition_to_half_open(self):
        """Test that CircuitBreaker transitions from OPEN to HALF_OPEN after recovery time."""
        # Arrange
        cb = CircuitBreaker(failure_threshold=1, recovery_time=60.0)
        failing_function = AsyncMock(side_effect=ValueError("Test error"))

        with patch("time.time") as mock_time:
            # Set initial time
            mock_time.return_value = 100.0

            # Act & Assert
            # First failure - circuit opens
            with pytest.raises(ValueError):
                await cb.execute(failing_function)
            assert cb.state == CircuitState.OPEN

            # Time hasn't passed - circuit stays open
            with pytest.raises(CircuitBreakerOpenError):
                await cb.execute(failing_function)

            # Time passes - circuit transitions to half-open
            mock_time.return_value = 161.0  # 61 seconds later

            # Next call should be allowed (in half-open state)
            with pytest.raises(ValueError):
                await cb.execute(failing_function)
            assert cb.state == CircuitState.OPEN  # Failed in half-open, back to open

    @pytest.mark.asyncio
    async def test_state_transition_to_closed(self):
        """Test that CircuitBreaker transitions from HALF_OPEN to CLOSED after successful execution."""
        # Arrange
        cb = CircuitBreaker(failure_threshold=1, recovery_time=60.0)

        # Create a function that fails once then succeeds
        call_count = 0

        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First call fails")
            return "success"

        with patch("time.time") as mock_time:
            # Set initial time
            mock_time.return_value = 100.0

            # Act & Assert
            # First call - circuit opens
            with pytest.raises(ValueError):
                await cb.execute(test_function)
            assert cb.state == CircuitState.OPEN

            # Time passes - circuit transitions to half-open
            mock_time.return_value = 161.0  # 61 seconds later

            # Next call succeeds - circuit closes
            result = await cb.execute(test_function)
            assert result == "success"
            assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_excluded_exceptions(self):
        """Test that excluded exceptions don't count toward failure threshold."""
        # Arrange
        cb = CircuitBreaker(failure_threshold=2, excluded_exceptions=(ValueError,))

        # Create a function that raises excluded exception
        async def test_function():
            raise ValueError("Excluded exception")

        # Act & Assert
        # Multiple excluded exceptions don't open circuit
        for _ in range(5):
            with pytest.raises(ValueError):
                await cb.execute(test_function)

        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_metrics_tracking(self):
        """Test that CircuitBreaker correctly tracks metrics."""
        # Arrange
        cb = CircuitBreaker(failure_threshold=2)

        # Create functions for success and failure
        async def success_function():
            return "success"

        async def failure_function():
            raise RuntimeError("Failure")

        # Act
        # Two successful calls
        await cb.execute(success_function)
        await cb.execute(success_function)

        # Two failed calls - opens circuit
        with pytest.raises(RuntimeError):
            await cb.execute(failure_function)
        with pytest.raises(RuntimeError):
            await cb.execute(failure_function)

        # Rejected call
        with pytest.raises(CircuitBreakerOpenError):
            await cb.execute(success_function)

        # Assert
        metrics = cb.metrics
        assert metrics["success_count"] == 2
        assert metrics["failure_count"] == 2
        assert metrics["rejected_count"] == 1
        assert len(metrics["state_changes"]) == 1
        assert metrics["state_changes"][0]["from"] == CircuitState.CLOSED
        assert metrics["state_changes"][0]["to"] == CircuitState.OPEN


class TestRetryWithBackoff:
    """Tests for the retry_with_backoff function."""

    @pytest.mark.asyncio
    async def test_success_after_failures(self):
        """Test that retry_with_backoff retries failed operations and eventually succeeds."""
        # Arrange
        call_count = 0

        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError(f"Error on attempt {call_count}")
            return "success"

        # Act
        result = await retry_with_backoff(
            test_function,
            retry_exceptions=(ConnectionError,),
            max_retries=3,
            base_delay=0.01,
        )

        # Assert
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that retry_with_backoff raises the last exception after max retries."""
        # Arrange
        call_count = 0

        async def test_function():
            nonlocal call_count
            call_count += 1
            raise ConnectionError(f"Error on attempt {call_count}")

        # Act & Assert
        with pytest.raises(ConnectionError) as exc_info:
            await retry_with_backoff(
                test_function,
                retry_exceptions=(ConnectionError,),
                max_retries=3,
                base_delay=0.01,
            )

        assert "Error on attempt 4" in str(exc_info.value)
        assert call_count == 4  # Initial attempt + 3 retries

    @pytest.mark.asyncio
    async def test_excluded_exceptions(self):
        """Test that excluded exceptions are not retried."""
        # Arrange
        call_count = 0

        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Excluded exception")
            return "success"

        # Act & Assert
        with pytest.raises(ValueError):
            await retry_with_backoff(
                test_function,
                retry_exceptions=(ConnectionError,),
                exclude_exceptions=(ValueError,),
                max_retries=3,
                base_delay=0.01,
            )

        assert call_count == 1  # No retries for excluded exception

    @pytest.mark.asyncio
    async def test_backoff_timing(self):
        """Test that retry_with_backoff applies correct exponential backoff."""
        # Arrange
        call_count = 0

        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise ConnectionError(f"Error on attempt {call_count}")
            return "success"

        # Act
        with patch("asyncio.sleep") as mock_sleep:
            mock_sleep.return_value = None
            await retry_with_backoff(
                test_function,
                retry_exceptions=(ConnectionError,),
                max_retries=3,
                base_delay=1.0,
                backoff_factor=2.0,
                jitter=False,
            )

        # Assert
        assert call_count == 4
        assert mock_sleep.call_count == 3

        # Check sleep durations follow exponential pattern
        assert mock_sleep.call_args_list[0][0][0] == 1.0  # First retry: base_delay
        assert (
            mock_sleep.call_args_list[1][0][0] == 2.0
        )  # Second retry: base_delay * backoff_factor
        assert (
            mock_sleep.call_args_list[2][0][0] == 4.0
        )  # Third retry: base_delay * backoff_factor^2

    @pytest.mark.asyncio
    async def test_jitter(self):
        """Test that retry_with_backoff applies jitter to backoff times."""
        # Arrange
        call_count = 0

        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise ConnectionError(f"Error on attempt {call_count}")
            return "success"

        # Act
        with (
            patch("asyncio.sleep") as mock_sleep,
            patch("random.uniform", return_value=1.1) as mock_random,
        ):
            mock_sleep.return_value = None
            await retry_with_backoff(
                test_function,
                retry_exceptions=(ConnectionError,),
                max_retries=3,
                base_delay=1.0,
                backoff_factor=2.0,
                jitter=True,
            )

        # Assert
        assert call_count == 4
        assert mock_sleep.call_count == 3

        # Check sleep durations include jitter
        assert mock_sleep.call_args_list[0][0][0] == 1.1  # First retry with jitter
        assert mock_sleep.call_args_list[1][0][0] == 2.2  # Second retry with jitter
        assert mock_sleep.call_args_list[2][0][0] == 4.4  # Third retry with jitter

    @pytest.mark.asyncio
    async def test_retry_config(self):
        """Test that RetryConfig correctly configures retry behavior."""
        # Arrange
        call_count = 0

        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError(f"Error on attempt {call_count}")
            return "success"

        config = RetryConfig(
            max_retries=3, base_delay=0.01, retry_exceptions=(ConnectionError,)
        )

        # Act
        result = await retry_with_backoff(test_function, **config.as_kwargs())

        # Assert
        assert result == "success"
        assert call_count == 3


class TestDecorators:
    """Tests for the decorator functions."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_decorator(self):
        """Test that circuit_breaker decorator applies circuit breaker pattern."""
        # Arrange
        call_count = 0

        @circuit_breaker(failure_threshold=2)
        async def test_function():
            nonlocal call_count
            call_count += 1
            raise ValueError(f"Error on attempt {call_count}")

        # Act & Assert
        # First failure
        with pytest.raises(ValueError):
            await test_function()

        # Second failure - opens circuit
        with pytest.raises(ValueError):
            await test_function()

        # Circuit is open - rejects request
        with pytest.raises(CircuitBreakerOpenError):
            await test_function()

    @pytest.mark.asyncio
    async def test_with_retry_decorator(self):
        """Test that with_retry decorator applies retry pattern."""
        # Arrange
        call_count = 0

        @with_retry(max_retries=2, base_delay=0.01, retry_exceptions=(ValueError,))
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError(f"Error on attempt {call_count}")
            return "success"

        # Act
        result = await test_function()

        # Assert
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_combined_decorators(self):
        """Test that circuit_breaker and with_retry decorators can be combined."""
        # Arrange
        call_count = 0
        failure_count = 0

        @circuit_breaker(failure_threshold=1)  # Changed from 2 to 1
        @with_retry(max_retries=1, base_delay=0.01, retry_exceptions=(ValueError,))
        async def test_function():
            nonlocal call_count, failure_count
            call_count += 1

            # First two calls: retry once then succeed
            if call_count <= 4:
                if call_count % 2 == 1:  # First attempt of each call
                    raise ValueError(f"Error on attempt {call_count}")
                return f"success {call_count // 2}"

            # Third call: always fail to open circuit
            failure_count += 1
            raise RuntimeError(f"Fatal error {failure_count}")

        # Act & Assert
        # First call with retry
        result1 = await test_function()
        assert result1 == "success 1"

        # Second call with retry
        result2 = await test_function()
        assert result2 == "success 2"

        # Third call fails and opens circuit after retry
        with pytest.raises(RuntimeError):
            await test_function()

        # Circuit is open - rejects request
        with pytest.raises(CircuitBreakerOpenError):
            await test_function()
