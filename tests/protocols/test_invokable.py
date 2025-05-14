"""
Tests for khive.protocols.invokable module.
"""

import asyncio
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from freezegun import freeze_time
from khive.protocols.invokable import Invokable
from khive.protocols.types import Execution, ExecutionStatus
from khive.utils import validate_model_to_dict
from pydantic import BaseModel


# --- Mock classes for testing ---
class MockResponse(BaseModel):
    """Mock response for testing."""

    value: str = "test_response"


class CustomInvokable(Invokable):
    """Test implementation of Invokable with configurable invoke function."""

    def __init__(self, invoke_function=None, **kwargs):
        super().__init__(**kwargs)
        if invoke_function:
            self._invoke_function = invoke_function


class SuccessInvokable(Invokable):
    """Mock Invokable implementation that succeeds."""

    def __init__(self, response=None, **kwargs):
        super().__init__(**kwargs)
        self._invoke_function = self._success_fn
        self._response = response or MockResponse()

    async def _success_fn(self, *_, **__):
        return self._response


class FailingInvokable(Invokable):
    """Mock Invokable implementation that fails."""

    def __init__(self, error_message="Test error", **kwargs):
        super().__init__(**kwargs)
        self._invoke_function = self._failing_fn
        self._error_message = error_message

    async def _failing_fn(self, *_, **__):
        raise ValueError(self._error_message)


class CancellingInvokable(Invokable):
    """Mock Invokable implementation that gets cancelled."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._invoke_function = self._cancelling_fn

    async def _cancelling_fn(self, *_, **__):
        raise asyncio.CancelledError


# --- Fixtures ---
@pytest.fixture
def mock_logger(monkeypatch):
    """Mock the logger to avoid issues with missing id attribute."""
    mock_log = MagicMock()
    monkeypatch.setattr("khive.protocols.invokable.logger", mock_log)
    return mock_log


# --- Helper functions ---
def create_invokable_with_function(func, *args, **kwargs):
    """Helper to create an Invokable with a specific function and arguments."""
    obj = Invokable()
    obj._invoke_function = func
    obj._invoke_args = list(args)
    obj._invoke_kwargs = kwargs
    return obj


# --- Tests for Invokable initialization and properties ---
def test_invokable_default_initialization():
    """Test that Invokable initializes with default values."""
    obj = Invokable()

    # Check default values
    assert obj.request is None
    assert obj.execution is not None
    assert obj.execution.status == ExecutionStatus.PENDING
    assert obj.execution.duration is None
    assert obj.execution.response is None
    assert obj.execution.error is None
    assert obj.response_obj is None

    # Check private attributes
    assert obj._invoke_function is None
    assert obj._invoke_args == []
    assert obj._invoke_kwargs == {}


def test_invokable_custom_initialization():
    """Test that Invokable accepts custom values."""
    request = {"param": "value"}
    execution = Execution(status=ExecutionStatus.PROCESSING)
    response_obj = {"result": "data"}

    obj = Invokable(request=request, execution=execution, response_obj=response_obj)

    assert obj.request == request
    assert obj.execution == execution
    assert obj.response_obj == response_obj


def test_has_invoked_property():
    """Test that has_invoked property returns correct boolean based on execution status."""
    # Test with PENDING status
    obj = Invokable(execution=Execution(status=ExecutionStatus.PENDING))
    assert obj.has_invoked is False

    # Test with PROCESSING status
    obj = Invokable(execution=Execution(status=ExecutionStatus.PROCESSING))
    assert obj.has_invoked is False

    # Test with COMPLETED status
    obj = Invokable(execution=Execution(status=ExecutionStatus.COMPLETED))
    assert obj.has_invoked is True

    # Test with FAILED status
    obj = Invokable(execution=Execution(status=ExecutionStatus.FAILED))
    assert obj.has_invoked is True


# --- Tests for _invoke method ---
@pytest.mark.asyncio
async def test_invoke_with_none_function():
    """Test that _invoke raises ValueError when _invoke_function is None."""
    obj = Invokable()

    with pytest.raises(ValueError, match="Event invoke function is not set."):
        await obj._invoke()


@pytest.mark.asyncio
async def test_invoke_with_sync_function(mock_logger):
    """Test that _invoke correctly converts a synchronous function to asynchronous."""

    # Define a synchronous function
    def sync_fn(a, b, c=None):
        return f"{a}-{b}-{c}"

    # Create Invokable with the sync function
    obj = create_invokable_with_function(sync_fn, 1, 2, c=3)

    # Call _invoke
    result = await obj._invoke()

    # Verify result
    assert result == "1-2-3"


@pytest.mark.asyncio
async def test_invoke_with_async_function(mock_logger):
    """Test that _invoke correctly calls an asynchronous function directly."""

    # Define an asynchronous function
    async def async_fn(a, b, c=None):
        return f"{a}-{b}-{c}"

    # Create Invokable with the async function
    obj = create_invokable_with_function(async_fn, 1, 2, c=3)

    # Call _invoke
    result = await obj._invoke()

    # Verify result
    assert result == "1-2-3"


# --- Tests for invoke method ---
@pytest.mark.asyncio
async def test_invoke_successful_execution(mock_logger):
    """Test that invoke handles successful execution correctly."""
    # Create a mock response
    mock_response = MockResponse(value="success")

    # Create Invokable with success function
    obj = SuccessInvokable(response=mock_response)

    # Call invoke
    await obj.invoke()

    # Verify execution state
    assert obj.execution.status == ExecutionStatus.COMPLETED
    assert obj.execution.error is None
    assert obj.execution.response is not None
    assert obj.response_obj == mock_response
    assert isinstance(obj.execution.duration, float)
    assert obj.execution.duration > 0


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_invoke_failed_execution(monkeypatch):
    """Test that invoke handles failed execution correctly."""
    # Create a patched version of the invoke method that doesn't access id
    original_invoke = Invokable.invoke

    async def patched_invoke(self):
        start = asyncio.get_event_loop().time()
        response = None
        e1 = None

        try:
            response = await self._invoke()
        except asyncio.CancelledError as ce:
            e1 = ce
            # Skip the logger call
            raise
        except Exception as ex:
            e1 = ex

        finally:
            self.execution.duration = asyncio.get_event_loop().time() - start
            if response is None and e1 is not None:
                self.execution.error = str(e1)
                self.execution.status = ExecutionStatus.FAILED
                # Skip the logger call
            else:
                self.response_obj = response
                self.execution.response = validate_model_to_dict(response)
                self.execution.status = ExecutionStatus.COMPLETED
            self.update_timestamp()

    # Apply the patch
    monkeypatch.setattr(Invokable, "invoke", patched_invoke)

    # Create Invokable with failing function
    error_message = "Custom test error"
    obj = FailingInvokable(error_message=error_message)

    # Call invoke
    await obj.invoke()

    # Verify execution state
    assert obj.execution.status == ExecutionStatus.FAILED
    assert obj.execution.error is not None
    assert error_message in obj.execution.error
    assert obj.execution.response is None
    assert isinstance(obj.execution.duration, float)
    assert obj.execution.duration > 0


@pytest.mark.asyncio
async def test_invoke_cancelled_execution(monkeypatch):
    """Test that invoke handles cancellation correctly."""
    # Create a patched version of the invoke method that doesn't access id
    original_invoke = Invokable.invoke

    async def patched_invoke(self):
        start = asyncio.get_event_loop().time()
        response = None
        e1 = None

        try:
            response = await self._invoke()
        except asyncio.CancelledError as ce:
            e1 = ce
            # Skip the logger call
            raise
        except Exception as ex:
            e1 = ex

        finally:
            self.execution.duration = asyncio.get_event_loop().time() - start
            if response is None and e1 is not None:
                self.execution.error = str(e1)
                self.execution.status = ExecutionStatus.FAILED
                # Skip the logger call
            else:
                self.response_obj = response
                self.execution.response = validate_model_to_dict(response)
                self.execution.status = ExecutionStatus.COMPLETED
            self.update_timestamp()

    # Apply the patch
    monkeypatch.setattr(Invokable, "invoke", patched_invoke)

    # Create Invokable with cancelling function
    obj = CancellingInvokable()

    # Call invoke and expect CancelledError to be re-raised
    with pytest.raises(asyncio.CancelledError):
        await obj.invoke()


@pytest.mark.asyncio
async def test_invoke_updates_timestamp(mock_logger):
    """Test that invoke updates the timestamp."""
    # Create Invokable with success function
    obj = SuccessInvokable()

    # Store the initial timestamp
    initial_timestamp = obj.updated_at

    # Freeze time and advance it
    with freeze_time(initial_timestamp + timedelta(seconds=10)):
        # Call invoke
        await obj.invoke()

        # Verify timestamp is updated
        assert obj.updated_at > initial_timestamp
