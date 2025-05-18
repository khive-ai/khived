# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the resilience patterns.
"""

import asyncio
import time
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from khive.clients.resilience import CircuitBreaker, CircuitState, retry_with_backoff
from khive.clients.errors import CircuitBreakerOpenError


@pytest.mark.asyncio
async def test_circuit_breaker_init():
    """Test that CircuitBreaker initializes correctly."""
    # Arrange & Act
    breaker = CircuitBreaker(failure_threshold=5, recovery_time=30.0)
    
    # Assert
    assert breaker.failure_threshold == 5
    assert breaker.recovery_time == 30.0
    assert breaker.failure_count == 0
    assert breaker.state == CircuitState.CLOSED
    assert breaker.last_failure_time == 0


@pytest.mark.asyncio
async def test_circuit_breaker_execute_success():
    """Test that execute method works correctly with successful function."""
    # Arrange
    breaker = CircuitBreaker(failure_threshold=5, recovery_time=30.0)
    mock_func = AsyncMock(return_value="result")
    
    # Act
    result = await breaker.execute(mock_func, "arg1", "arg2", kwarg1="value1")
    
    # Assert
    mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")
    assert result == "result"
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0


@pytest.mark.asyncio
async def test_circuit_breaker_execute_failure():
    """Test that execute method handles failures correctly."""
    # Arrange
    breaker = CircuitBreaker(failure_threshold=5, recovery_time=30.0)
    mock_func = AsyncMock(side_effect=ValueError("Test error"))
    
    # Act & Assert
    with pytest.raises(ValueError) as excinfo:
        await breaker.execute(mock_func)
    
    # Assert
    assert "Test error" in str(excinfo.value)
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 1
    assert breaker.last_failure_time > 0


@pytest.mark.asyncio
async def test_circuit_breaker_open_after_threshold():
    """Test that circuit opens after threshold failures."""
    # Arrange
    breaker = CircuitBreaker(failure_threshold=3, recovery_time=30.0)
    mock_func = AsyncMock(side_effect=ValueError("Test error"))
    
    # Act & Assert
    for i in range(3):
        with pytest.raises(ValueError):
            await breaker.execute(mock_func)
    
    # Assert
    assert breaker.state == CircuitState.OPEN
    assert breaker.failure_count == 3


@pytest.mark.asyncio
async def test_circuit_breaker_rejects_when_open():
    """Test that circuit rejects requests when open."""
    # Arrange
    breaker = CircuitBreaker(failure_threshold=3, recovery_time=30.0)
    breaker.state = CircuitState.OPEN
    breaker.last_failure_time = time.time()  # Set to current time
    mock_func = AsyncMock(return_value="result")
    
    # Act & Assert
    with pytest.raises(CircuitBreakerOpenError) as excinfo:
        await breaker.execute(mock_func)
    
    # Assert
    assert "Circuit breaker is open" in str(excinfo.value)
    mock_func.assert_not_called()


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_after_recovery_time():
    """Test that circuit transitions to half-open after recovery time."""
    # Arrange
    breaker = CircuitBreaker(failure_threshold=3, recovery_time=30.0)
    breaker.state = CircuitState.OPEN
    breaker.last_failure_time = time.time() - 31.0  # Set to 31 seconds ago
    mock_func = AsyncMock(return_value="result")
    
    # Act
    result = await breaker.execute(mock_func)
    
    # Assert
    assert result == "result"
    assert breaker.state == CircuitState.CLOSED  # Should transition to closed after success
    assert breaker.failure_count == 0


@pytest.mark.asyncio
async def test_circuit_breaker_remains_open_after_failure_in_half_open():
    """Test that circuit remains open after failure in half-open state."""
    # Arrange
    breaker = CircuitBreaker(failure_threshold=3, recovery_time=30.0)
    breaker.state = CircuitState.HALF_OPEN
    mock_func = AsyncMock(side_effect=ValueError("Test error"))
    
    # Act & Assert
    with pytest.raises(ValueError):
        await breaker.execute(mock_func)
    
    # Assert
    assert breaker.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_retry_with_backoff_success_first_try():
    """Test that retry_with_backoff succeeds on first try."""
    # Arrange
    mock_func = AsyncMock(return_value="result")
    
    # Act
    result = await retry_with_backoff(
        mock_func, "arg1", "arg2", 
        kwarg1="value1",
        max_retries=3
    )
    
    # Assert
    mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")
    assert result == "result"


@pytest.mark.asyncio
async def test_retry_with_backoff_success_after_retries():
    """Test that retry_with_backoff succeeds after retries."""
    # Arrange
    mock_func = AsyncMock(side_effect=[
        ValueError("Error 1"),
        ValueError("Error 2"),
        "result"
    ])
    
    # Mock asyncio.sleep to avoid actual delays
    mock_sleep = AsyncMock()
    
    # Act
    with patch('asyncio.sleep', mock_sleep):
        result = await retry_with_backoff(
            mock_func, "arg1", "arg2", 
            kwarg1="value1",
            max_retries=3,
            base_delay=1.0,
            jitter=False  # Disable jitter for predictable testing
        )
    
    # Assert
    assert mock_func.call_count == 3
    assert result == "result"
    assert mock_sleep.call_count == 2
    # First retry should wait base_delay (1.0)
    # Second retry should wait base_delay * backoff_factor (1.0 * 2.0 = 2.0)
    mock_sleep.assert_any_call(1.0)
    mock_sleep.assert_any_call(2.0)


@pytest.mark.asyncio
async def test_retry_with_backoff_max_retries_exceeded():
    """Test that retry_with_backoff raises exception after max retries."""
    # Arrange
    mock_func = AsyncMock(side_effect=ValueError("Test error"))
    
    # Mock asyncio.sleep to avoid actual delays
    mock_sleep = AsyncMock()
    
    # Act & Assert
    with patch('asyncio.sleep', mock_sleep):
        with pytest.raises(ValueError) as excinfo:
            await retry_with_backoff(
                mock_func, "arg1", "arg2", 
                kwarg1="value1",
                max_retries=3,
                base_delay=1.0,
                jitter=False  # Disable jitter for predictable testing
            )
    
    # Assert
    assert "Test error" in str(excinfo.value)
    assert mock_func.call_count == 4  # Initial call + 3 retries
    assert mock_sleep.call_count == 3


@pytest.mark.asyncio
async def test_retry_with_backoff_excluded_exceptions():
    """Test that retry_with_backoff doesn't retry excluded exceptions."""
    # Arrange
    mock_func = AsyncMock(side_effect=TypeError("Type error"))
    
    # Mock asyncio.sleep to avoid actual delays
    mock_sleep = AsyncMock()
    
    # Act & Assert
    with patch('asyncio.sleep', mock_sleep):
        with pytest.raises(TypeError) as excinfo:
            await retry_with_backoff(
                mock_func, "arg1", "arg2", 
                kwarg1="value1",
                retry_exceptions=(ValueError, RuntimeError),
                exclude_exceptions=(TypeError,),
                max_retries=3
            )
    
    # Assert
    assert "Type error" in str(excinfo.value)
    assert mock_func.call_count == 1  # Should not retry
    assert mock_sleep.call_count == 0


@pytest.mark.asyncio
async def test_retry_with_backoff_jitter():
    """Test that retry_with_backoff applies jitter correctly."""
    # Arrange
    mock_func = AsyncMock(side_effect=[
        ValueError("Error 1"),
        ValueError("Error 2"),
        "result"
    ])
    
    # Mock random.uniform to return predictable values
    with patch('random.uniform', return_value=1.0):
        # Mock asyncio.sleep to avoid actual delays
        mock_sleep = AsyncMock()
        
        # Act
        with patch('asyncio.sleep', mock_sleep):
            result = await retry_with_backoff(
                mock_func, "arg1", "arg2", 
                kwarg1="value1",
                max_retries=3,
                base_delay=1.0,
                jitter=True
            )
    
    # Assert
    assert mock_func.call_count == 3
    assert result == "result"
    assert mock_sleep.call_count == 2
    # With jitter=1.0, first retry should wait base_delay * 1.0 (1.0)
    # Second retry should wait base_delay * backoff_factor * 1.0 (1.0 * 2.0 * 1.0 = 2.0)
    mock_sleep.assert_any_call(1.0)
    mock_sleep.assert_any_call(2.0)