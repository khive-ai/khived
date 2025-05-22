import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
import logging

from khive.reader.monitoring.thresholds import PerformanceThreshold, PerformanceMonitor

# Suppress logging during tests unless specifically testing logging
# logging.disable(logging.CRITICAL)


@pytest.fixture
def mock_check_function():
    return AsyncMock()

@pytest.fixture
def mock_alert_handler():
    return AsyncMock()

@pytest.fixture
def basic_threshold(mock_check_function, mock_alert_handler):
    return PerformanceThreshold(
        name="test_threshold",
        description="A test threshold",
        threshold_value=100.0,
        check_function=mock_check_function,
        alert_handler=mock_alert_handler
    )

# Test UT-T1
@pytest.mark.asyncio
async def test_performance_threshold_check_below_threshold(basic_threshold, mock_check_function):
    """Test PerformanceThreshold.check when value is below threshold."""
    mock_check_function.return_value = 50.0
    
    exceeded = await basic_threshold.check()
    
    assert not exceeded
    assert not basic_threshold.exceeded
    assert basic_threshold.last_value == 50.0
    mock_check_function.assert_called_once()
    basic_threshold.alert_handler.assert_not_called()

# Test UT-T2
@pytest.mark.asyncio
async def test_performance_threshold_check_exceeds_threshold_first_time(basic_threshold, mock_check_function, mock_alert_handler):
    """Test PerformanceThreshold.check when value exceeds threshold for the first time."""
    mock_check_function.return_value = 150.0
    
    exceeded = await basic_threshold.check()
    
    assert exceeded
    assert basic_threshold.exceeded
    assert basic_threshold.last_value == 150.0
    mock_check_function.assert_called_once()
    mock_alert_handler.assert_called_once_with("test_threshold", "A test threshold", 150.0, 100.0)

@pytest.mark.asyncio
async def test_performance_threshold_check_remains_exceeded(basic_threshold, mock_check_function, mock_alert_handler):
    """Test PerformanceThreshold.check when value remains exceeded (alert not called again)."""
    # First exceed
    mock_check_function.return_value = 150.0
    await basic_threshold.check()
    mock_alert_handler.assert_called_once() # Alerted
    mock_alert_handler.reset_mock()
    mock_check_function.reset_mock()

    # Still exceeded
    mock_check_function.return_value = 160.0
    exceeded = await basic_threshold.check()

    assert exceeded
    assert basic_threshold.exceeded
    assert basic_threshold.last_value == 160.0
    mock_check_function.assert_called_once()
    mock_alert_handler.assert_not_called() # Not alerted again

# Test UT-T3
@pytest.mark.asyncio
async def test_performance_threshold_check_recovers_from_exceeded(basic_threshold, mock_check_function, mock_alert_handler, caplog):
    """Test PerformanceThreshold.check when value recovers from an exceeded state."""
    # First exceed
    mock_check_function.return_value = 150.0
    await basic_threshold.check()
    mock_alert_handler.assert_called_once()
    mock_check_function.reset_mock()
    
    # Now recover
    mock_check_function.return_value = 80.0
    with caplog.at_level(logging.INFO):
        exceeded = await basic_threshold.check()
    
    assert not exceeded
    assert not basic_threshold.exceeded
    assert basic_threshold.last_value == 80.0
    mock_check_function.assert_called_once()
    assert "Performance threshold RECOVERED: test_threshold" in caplog.text

# Test UT-T4
@pytest.mark.asyncio
async def test_performance_threshold_check_handles_exception_in_check_function(basic_threshold, mock_check_function, caplog):
    """Test PerformanceThreshold.check handles exceptions in check_function."""
    mock_check_function.side_effect = Exception("Check function error")
    basic_threshold.exceeded = True # Simulate it was previously exceeded
    
    with caplog.at_level(logging.ERROR):
        exceeded_status = await basic_threshold.check()
    
    assert "Error checking threshold test_threshold: Check function error" in caplog.text
    # State should remain as it was before the error
    assert exceeded_status == True 
    assert basic_threshold.exceeded == True 
    mock_check_function.assert_called_once()
    basic_threshold.alert_handler.assert_not_called()


@pytest.fixture
def mock_db_session_factory():
    return AsyncMock()

@pytest.fixture
def mock_task_queue():
    mock_queue = MagicMock()
    mock_queue.qsize.return_value = 5 # For asyncio.Queue like behavior
    # mock_queue.pending_tasks = [1,2,3,4,5] # For custom queue behavior
    return mock_queue

@pytest.fixture
def performance_monitor(mock_db_session_factory, mock_task_queue):
    # Patch the default alert handler during PerformanceMonitor instantiation for simplicity
    with patch.object(PerformanceMonitor, 'default_alert_handler', new_callable=AsyncMock) as mock_default_alert:
        monitor = PerformanceMonitor(mock_db_session_factory, mock_task_queue)
        monitor.default_alert_handler_mock = mock_default_alert # Attach mock for assertions
        return monitor

# Test UT-T5
@pytest.mark.asyncio
async def test_performance_monitor_check_all_thresholds(performance_monitor, caplog):
    """Test PerformanceMonitor.check_all_thresholds aggregates results."""
    # Mock the check methods of individual thresholds within the monitor
    # For simplicity, we'll assume the placeholder check functions in PerformanceMonitor are used
    # and they return fixed values.
    
    # Patch the internal check functions of the monitor instance
    performance_monitor._check_vector_count = AsyncMock(return_value=1000.0) # Below 5M
    performance_monitor._check_search_latency = AsyncMock(return_value=50.0) # Below 100ms
    performance_monitor._check_task_queue_depth = AsyncMock(return_value=1500.0) # Above 1000
    performance_monitor._check_db_connection_utilization = AsyncMock(return_value=0.95) # Above 0.9
    
    with caplog.at_level(logging.INFO):
        results = await performance_monitor.check_all_thresholds()

    assert "Checking all performance thresholds..." in caplog.text
    assert "Finished checking all performance thresholds." in caplog.text

    assert len(results) == 4
    assert not results["vector_count"]["exceeded"]
    assert results["vector_count"]["current_value"] == 1000.0
    
    assert not results["search_latency_p95_ms"]["exceeded"]
    assert results["search_latency_p95_ms"]["current_value"] == 50.0
    
    assert results["task_queue_depth"]["exceeded"]
    assert results["task_queue_depth"]["current_value"] == 1500.0
    
    assert results["db_connection_utilization_percent"]["exceeded"]
    assert results["db_connection_utilization_percent"]["current_value"] == 0.95

    # Check if the monitor's default_alert_handler (mocked) was called for exceeded thresholds
    assert performance_monitor.default_alert_handler_mock.call_count == 2
    
    # Example check for one of the calls
    performance_monitor.default_alert_handler_mock.assert_any_call(
        "task_queue_depth", 
        "Number of pending tasks in the queue", 
        1500.0, 
        1000.0
    )


# Test UT-T6 (Placeholder check functions)
@pytest.mark.asyncio
async def test_performance_monitor_placeholder_check_functions(performance_monitor):
    """Test PerformanceMonitor placeholder check functions return expected values."""
    # These are already mocked in the performance_monitor fixture setup for check_all_thresholds
    # This test can verify their default behavior if not mocked externally
    
    # Re-create a monitor without external mocks on its check methods
    monitor = PerformanceMonitor(AsyncMock(), MagicMock())

    assert await monitor._check_vector_count() == 0.0 # Default placeholder
    assert await monitor._check_search_latency() == 50.0 # Default placeholder
    # _check_task_queue_depth depends on mock_task_queue structure
    assert await monitor._check_db_connection_utilization() == 0.5 # Default placeholder

@pytest.mark.asyncio
async def test_performance_monitor_monitor_periodically(performance_monitor, caplog):
    """Test PerformanceMonitor.monitor_periodically calls check_all_thresholds."""
    with patch.object(performance_monitor, 'check_all_thresholds', new_callable=AsyncMock) as mock_check_all, \
         patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep, \
         caplog.at_level(logging.INFO):
        
        mock_sleep.side_effect = asyncio.CancelledError # Stop loop after first iteration
        
        with pytest.raises(asyncio.CancelledError):
            await performance_monitor.monitor_periodically(interval_seconds=10)
            
        mock_check_all.assert_called_once()
        mock_sleep.assert_called_once_with(10)
        assert "Performance monitor starting periodic checks every 10 seconds." in caplog.text

@pytest.mark.asyncio
async def test_performance_monitor_monitor_periodically_handles_check_error(performance_monitor, caplog):
    """Test monitor_periodically handles errors from check_all_thresholds."""
    with patch.object(performance_monitor, 'check_all_thresholds', new_callable=AsyncMock) as mock_check_all, \
         patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep, \
         caplog.at_level(logging.ERROR):
        
        mock_check_all.side_effect = Exception("Periodic check failed")
        mock_sleep.side_effect = asyncio.CancelledError # Stop loop after first iteration
        
        with pytest.raises(asyncio.CancelledError):
            await performance_monitor.monitor_periodically(interval_seconds=10)
            
        mock_check_all.assert_called_once()
        assert "Error during periodic threshold check: Periodic check failed" in caplog.text
        mock_sleep.assert_called_once_with(10)


@pytest.mark.asyncio
async def test_default_alert_handler_logs_correctly(caplog):
    """Test the default_alert_handler logs the correct message."""
    monitor = PerformanceMonitor(AsyncMock(), MagicMock()) # Need an instance to call the method
    
    with caplog.at_level(logging.WARNING):
        await monitor.default_alert_handler(
            name="high_cpu",
            description="CPU utilization is high",
            value=95.0,
            threshold=90.0
        )
    
    assert "PERFORMANCE THRESHOLD EXCEEDED" in caplog.text
    assert "Threshold Name: high_cpu" in caplog.text
    assert "Current Value:  95.00" in caplog.text
    assert "Threshold:      90.00" in caplog.text
    assert "Exceeded by:    5.6%" in caplog.text # ((95/90)-1)*100
    assert "Recommended Action: Investigate the 'high_cpu' metric." in caplog.text