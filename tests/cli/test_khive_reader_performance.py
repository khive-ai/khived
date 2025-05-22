import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

# Assuming PerformanceMonitor and other necessary components are accessible
# For CLI tests, we often mock at a higher level, e.g., the check_performance function itself,
# or the PerformanceMonitor's check_all_thresholds method.

# Path to the functions/classes in the CLI module
CLI_MODULE_PATH = "khive.cli.khive_reader"

# Test UT-C1 (check_performance successfully retrieves and formats data)
@pytest.mark.asyncio
async def test_check_performance_success():
    """Test the check_performance async function for successful data retrieval."""
    
    mock_threshold_data = {
        "vector_count": {"exceeded": False, "current_value": 1000, "threshold_value": 5000000, "last_checked_timestamp": time.time()},
        "task_queue_depth": {"exceeded": True, "current_value": 1500, "threshold_value": 1000, "last_checked_timestamp": time.time()}
    }
    
    # Mock the PerformanceMonitor instance and its check_all_thresholds method
    mock_monitor_instance = AsyncMock()
    mock_monitor_instance.check_all_thresholds.return_value = mock_threshold_data
    
    with patch(f"{CLI_MODULE_PATH}.PerformanceMonitor", return_value=mock_monitor_instance) as mock_perf_monitor_class, \
         patch(f"{CLI_MODULE_PATH}.get_db_session", new_callable=AsyncMock) as mock_get_db, \
         patch(f"{CLI_MODULE_PATH}.task_queue", MagicMock()): # Mock task_queue if it's directly used by check_performance

        from khive.cli.khive_reader import check_performance # Import here to use patched versions
        
        result = await check_performance()
        
        assert result["status"] == "success"
        assert result["exceeded"] is True
        assert len(result["thresholds"]) == 2
        assert result["thresholds"]["vector_count"]["current_value"] == 1000
        assert result["thresholds"]["task_queue_depth"]["exceeded"] is True
        
        mock_perf_monitor_class.assert_called_once() # With get_db_session and task_queue
        mock_monitor_instance.check_all_thresholds.assert_called_once()

# Test UT-C2 (check_performance handles errors from PerformanceMonitor)
@pytest.mark.asyncio
async def test_check_performance_error_handling():
    """Test check_performance handles errors from PerformanceMonitor."""
    
    mock_monitor_instance = AsyncMock()
    mock_monitor_instance.check_all_thresholds.side_effect = Exception("Monitor failed")
    
    with patch(f"{CLI_MODULE_PATH}.PerformanceMonitor", return_value=mock_monitor_instance), \
         patch(f"{CLI_MODULE_PATH}.get_db_session", new_callable=AsyncMock), \
         patch(f"{CLI_MODULE_PATH}.task_queue", MagicMock()):
        
        from khive.cli.khive_reader import check_performance
        result = await check_performance()
        
        assert result["status"] == "error"
        assert "Error checking performance: Monitor failed" in result["message"]

# Tests for the CLI command itself (using subprocess or by directly calling main with mocked args)
# For simplicity, we'll test by calling main with mocked args and capturing stdout/stderr.

@patch(f"{CLI_MODULE_PATH}.asyncio.run") # Mock asyncio.run to control what check_performance returns
@patch("builtins.print") # Mock print to capture output
@patch(f"{CLI_MODULE_PATH}.sys.exit") # Mock sys.exit to prevent test termination
def test_cli_performance_command_success_no_exceed(mock_sys_exit, mock_print, mock_asyncio_run):
    """Test the 'performance' CLI command with successful, non-exceeded thresholds."""
    
    mock_asyncio_run.return_value = {
        "status": "success",
        "thresholds": {
            "vector_count": {"exceeded": False, "current_value": 1000.0, "threshold_value": 5000000.0},
            "search_latency": {"exceeded": False, "current_value": 50.0, "threshold_value": 100.0}
        },
        "exceeded": False
    }
    
    with patch(f"{CLI_MODULE_PATH}.argparse.ArgumentParser") as mock_arg_parser:
        # Simulate argparse behavior
        mock_args_instance = MagicMock()
        mock_args_instance.action_command = "performance"
        mock_args_instance.json = False
        mock_arg_parser.return_value.parse_args.return_value = mock_args_instance
        
        from khive.cli.khive_reader import main
        main()

    # Check print calls for formatted output
    output = "\n".join([call.args[0] for call in mock_print.call_args_list if call.args])
    assert "Performance Threshold Check Results:" in output
    assert "vector_count\033[0m: 1000.00 / 5000000.00 [OK]" in output # Check for ANSI reset too
    assert "search_latency\033[0m: 50.00 / 100.00 [OK]" in output
    assert "All thresholds within acceptable limits." in output
    mock_sys_exit.assert_called_once_with(0)


@patch(f"{CLI_MODULE_PATH}.asyncio.run")
@patch("builtins.print")
@patch(f"{CLI_MODULE_PATH}.sys.exit")
def test_cli_performance_command_success_exceeded(mock_sys_exit, mock_print, mock_asyncio_run):
    """Test the 'performance' CLI command with an exceeded threshold."""
    mock_asyncio_run.return_value = {
        "status": "success",
        "thresholds": {
            "task_queue_depth": {"exceeded": True, "current_value": 1500.0, "threshold_value": 1000.0}
        },
        "exceeded": True
    }
    
    with patch(f"{CLI_MODULE_PATH}.argparse.ArgumentParser") as mock_arg_parser:
        mock_args_instance = MagicMock()
        mock_args_instance.action_command = "performance"
        mock_args_instance.json = False
        mock_arg_parser.return_value.parse_args.return_value = mock_args_instance
        
        from khive.cli.khive_reader import main
        main()

    output = "\n".join([call.args[0] for call in mock_print.call_args_list if call.args])
    assert "task_queue_depth\033[0m: 1500.00 / 1000.00 [EXCEEDED]" in output
    assert "Some thresholds exceeded. Consider architecture changes." in output
    mock_sys_exit.assert_called_once_with(0)


@patch(f"{CLI_MODULE_PATH}.asyncio.run")
@patch("builtins.print")
@patch(f"{CLI_MODULE_PATH}.sys.exit")
def test_cli_performance_command_json_output(mock_sys_exit, mock_print, mock_asyncio_run):
    """Test the 'performance' CLI command with JSON output."""
    expected_result_dict = {
        "status": "success",
        "thresholds": {"vector_count": {"exceeded": False, "current_value": 100.0, "threshold_value": 200.0}},
        "exceeded": False
    }
    mock_asyncio_run.return_value = expected_result_dict
    
    with patch(f"{CLI_MODULE_PATH}.argparse.ArgumentParser") as mock_arg_parser:
        mock_args_instance = MagicMock()
        mock_args_instance.action_command = "performance"
        mock_args_instance.json = True
        mock_arg_parser.return_value.parse_args.return_value = mock_args_instance
        
        from khive.cli.khive_reader import main
        main()

    # Check that print was called with the JSON dump of the result
    printed_json = json.loads(mock_print.call_args[0][0])
    assert printed_json == expected_result_dict
    mock_sys_exit.assert_called_once_with(0)

@patch(f"{CLI_MODULE_PATH}.asyncio.run")
@patch(f"{CLI_MODULE_PATH}.sys.stderr.write") # Capture stderr
@patch(f"{CLI_MODULE_PATH}.sys.exit")
def test_cli_performance_command_error_status(mock_sys_exit, mock_stderr_write, mock_asyncio_run):
    """Test the 'performance' CLI command when check_performance returns an error status."""
    mock_asyncio_run.return_value = {
        "status": "error",
        "message": "A wild error appeared!"
    }
    
    with patch(f"{CLI_MODULE_PATH}.argparse.ArgumentParser") as mock_arg_parser:
        mock_args_instance = MagicMock()
        mock_args_instance.action_command = "performance"
        mock_args_instance.json = False # Test non-JSON error output
        mock_arg_parser.return_value.parse_args.return_value = mock_args_instance
        
        from khive.cli.khive_reader import main
        main()

    # Check that the error message was printed to stderr
    stderr_output = "".join([call.args[0] for call in mock_stderr_write.call_args_list])
    assert "❌ A wild error appeared!" in stderr_output
    mock_sys_exit.assert_called_once_with(1)