---
title: Test Implementation for Invokable Protocol
by: khive-implementer
created: 2025-05-14
updated: 2025-05-14
version: 1.0
doc_type: TI
output_subdir: ti
description: Detailed test implementation plan for the Invokable protocol test suite
date: 2025-05-14
author: @khive-implementer
---

# Test Implementation Plan: Invokable Protocol

## 1. Overview

### 1.1 Component Under Test

The `Invokable` protocol (`khive.protocols.invokable.Invokable`) is a core
protocol in the khive framework that extends the `Temporal` protocol. It
provides functionality for objects that can be invoked with a request, execute
some operation, and track the execution status and results.

Key features to test:

- Initialization with default and custom values
- The `has_invoked` property behavior
- The `_invoke` method with different function types
- The `invoke` method with success, failure, and cancellation scenarios
- Status transitions through the execution lifecycle

### 1.2 Test Approach

We will use a unit testing approach with pytest and pytest-asyncio for testing
the asynchronous behavior of the Invokable protocol. We'll create mock
implementations to simulate different execution scenarios.

### 1.3 Key Testing Goals

- Achieve >80% test coverage for the module
- Verify all execution paths (success, failure, cancellation)
- Test proper status transitions
- Ensure proper error handling
- Validate timestamp updates

## 2. Test Environment

### 2.1 Test Framework

```
pytest
pytest-asyncio
pytest-cov
freezegun (for time-related tests)
```

### 2.2 Mock Framework

```
unittest.mock
pytest-monkeypatch
```

### 2.3 Test Database

Not applicable for this protocol test suite as it doesn't interact with
databases.

## 3. Unit Tests

### 3.1 Test Suite: Invokable Initialization and Properties

#### 3.1.1 Test Case: Default Initialization

**Purpose:** Verify that Invokable initializes with correct default values.

**Test Implementation:**

```python
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
```

#### 3.1.2 Test Case: Custom Initialization

**Purpose:** Verify that Invokable accepts custom values during initialization.

**Test Implementation:**

```python
def test_invokable_custom_initialization():
    """Test that Invokable accepts custom values."""
    request = {"param": "value"}
    execution = Execution(status=ExecutionStatus.PROCESSING)
    response_obj = {"result": "data"}

    obj = Invokable(
        request=request,
        execution=execution,
        response_obj=response_obj
    )

    assert obj.request == request
    assert obj.execution == execution
    assert obj.response_obj == response_obj
```

#### 3.1.3 Test Case: has_invoked Property

**Purpose:** Verify that the has_invoked property returns the correct boolean
value based on execution status.

**Test Implementation:**

```python
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
```

### 3.2 Test Suite: _invoke Method

#### 3.2.1 Test Case: _invoke with None Function

**Purpose:** Verify that _invoke raises ValueError when _invoke_function is
None.

**Test Implementation:**

```python
@pytest.mark.asyncio
async def test_invoke_with_none_function():
    """Test that _invoke raises ValueError when _invoke_function is None."""
    obj = Invokable()

    with pytest.raises(ValueError, match="Event invoke function is not set."):
        await obj._invoke()
```

#### 3.2.2 Test Case: _invoke with Synchronous Function

**Purpose:** Verify that _invoke correctly converts a synchronous function to
asynchronous.

**Test Implementation:**

```python
@pytest.mark.asyncio
async def test_invoke_with_sync_function():
    """Test that _invoke correctly converts a synchronous function to asynchronous."""
    # Define a synchronous function
    def sync_fn(a, b, c=None):
        return f"{a}-{b}-{c}"

    # Create Invokable with the sync function
    obj = Invokable()
    obj._invoke_function = sync_fn
    obj._invoke_args = [1, 2]
    obj._invoke_kwargs = {"c": 3}

    # Call _invoke
    result = await obj._invoke()

    # Verify result
    assert result == "1-2-3"
```

#### 3.2.3 Test Case: _invoke with Asynchronous Function

**Purpose:** Verify that _invoke correctly calls an asynchronous function
directly.

**Test Implementation:**

```python
@pytest.mark.asyncio
async def test_invoke_with_async_function():
    """Test that _invoke correctly calls an asynchronous function directly."""
    # Define an asynchronous function
    async def async_fn(a, b, c=None):
        return f"{a}-{b}-{c}"

    # Create Invokable with the async function
    obj = Invokable()
    obj._invoke_function = async_fn
    obj._invoke_args = [1, 2]
    obj._invoke_kwargs = {"c": 3}

    # Call _invoke
    result = await obj._invoke()

    # Verify result
    assert result == "1-2-3"
```

### 3.3 Test Suite: invoke Method

#### 3.3.1 Test Case: Successful Execution

**Purpose:** Verify that invoke handles successful execution correctly.

**Test Implementation:**

```python
@pytest.mark.asyncio
async def test_invoke_successful_execution():
    """Test that invoke handles successful execution correctly."""
    # Create a mock response
    mock_response = {"result": "success"}

    # Create a mock async function
    async def mock_fn():
        return mock_response

    # Create Invokable with the mock function
    obj = Invokable()
    obj._invoke_function = mock_fn

    # Call invoke
    await obj.invoke()

    # Verify execution state
    assert obj.execution.status == ExecutionStatus.COMPLETED
    assert obj.execution.error is None
    assert obj.execution.response == mock_response
    assert obj.response_obj == mock_response
    assert isinstance(obj.execution.duration, float)
    assert obj.execution.duration > 0
```

#### 3.3.2 Test Case: Failed Execution

**Purpose:** Verify that invoke handles failed execution correctly.

**Test Implementation:**

```python
@pytest.mark.asyncio
async def test_invoke_failed_execution():
    """Test that invoke handles failed execution correctly."""
    # Create a mock function that raises an exception
    async def mock_fn():
        raise ValueError("Test error")

    # Create Invokable with the mock function
    obj = Invokable()
    obj._invoke_function = mock_fn

    # Call invoke
    await obj.invoke()

    # Verify execution state
    assert obj.execution.status == ExecutionStatus.FAILED
    assert "Test error" in obj.execution.error
    assert obj.execution.response is None
    assert obj.response_obj is None
    assert isinstance(obj.execution.duration, float)
    assert obj.execution.duration > 0
```

#### 3.3.3 Test Case: Cancelled Execution

**Purpose:** Verify that invoke handles cancellation correctly.

**Test Implementation:**

```python
@pytest.mark.asyncio
async def test_invoke_cancelled_execution():
    """Test that invoke handles cancellation correctly."""
    # Create a mock function that raises CancelledError
    async def mock_fn():
        raise asyncio.CancelledError()

    # Create Invokable with the mock function
    obj = Invokable()
    obj._invoke_function = mock_fn

    # Call invoke and expect CancelledError to be re-raised
    with pytest.raises(asyncio.CancelledError):
        await obj.invoke()

    # Execution state should not be updated since the finally block won't complete
    assert obj.execution.status == ExecutionStatus.PENDING
```

#### 3.3.4 Test Case: Timestamp Update

**Purpose:** Verify that invoke updates the timestamp.

**Test Implementation:**

```python
@pytest.mark.asyncio
async def test_invoke_updates_timestamp():
    """Test that invoke updates the timestamp."""
    # Create a mock function
    async def mock_fn():
        return "success"

    # Create Invokable with the mock function
    obj = Invokable()
    obj._invoke_function = mock_fn

    # Store the initial timestamp
    initial_timestamp = obj.updated_at

    # Freeze time and advance it
    with freeze_time(initial_timestamp + timedelta(seconds=10)):
        # Call invoke
        await obj.invoke()

        # Verify timestamp is updated
        assert obj.updated_at > initial_timestamp
```

## 4. Mock Implementation Details

### 4.1 Mock Classes

```python
class MockResponse:
    """Mock response object for testing."""
    def __init__(self, value="test_response"):
        self.value = value

class TestInvokable(Invokable):
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

    async def _success_fn(self, *args, **kwargs):
        return self._response

class FailingInvokable(Invokable):
    """Mock Invokable implementation that fails."""

    def __init__(self, error_message="Test error", **kwargs):
        super().__init__(**kwargs)
        self._invoke_function = self._failing_fn
        self._error_message = error_message

    async def _failing_fn(self, *args, **kwargs):
        raise ValueError(self._error_message)

class CancellingInvokable(Invokable):
    """Mock Invokable implementation that gets cancelled."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._invoke_function = self._cancelling_fn

    async def _cancelling_fn(self, *args, **kwargs):
        raise asyncio.CancelledError()
```

### 4.2 Mock Event Loop Time

```python
@pytest.fixture
def mock_event_loop_time(monkeypatch):
    """Mock the event loop time method to return predictable values."""
    time_values = [1.0, 2.0]  # Start time and end time
    mock_time = MagicMock(side_effect=time_values)

    # Create a mock event loop
    mock_loop = MagicMock()
    mock_loop.time = mock_time

    # Mock the get_event_loop function
    monkeypatch.setattr(asyncio, "get_event_loop", lambda: mock_loop)

    return mock_loop
```

## 5. Test Coverage Targets

- **Line Coverage Target:** >80%
- **Branch Coverage Target:** >80%
- **Critical Methods:**
  - `_invoke`: 100% coverage
  - `invoke`: 100% coverage including all execution paths

## 6. Helper Functions

```python
def create_invokable_with_function(func, *args, **kwargs):
    """Helper to create an Invokable with a specific function and arguments."""
    obj = Invokable()
    obj._invoke_function = func
    obj._invoke_args = list(args)
    obj._invoke_kwargs = kwargs
    return obj

async def assert_execution_completed(invokable):
    """Helper to assert that execution completed successfully."""
    assert invokable.execution.status == ExecutionStatus.COMPLETED
    assert invokable.execution.error is None
    assert invokable.execution.response is not None
    assert invokable.response_obj is not None
    assert isinstance(invokable.execution.duration, float)
    assert invokable.execution.duration > 0

async def assert_execution_failed(invokable, error_substring=None):
    """Helper to assert that execution failed with expected error."""
    assert invokable.execution.status == ExecutionStatus.FAILED
    assert invokable.execution.error is not None
    if error_substring:
        assert error_substring in invokable.execution.error
    assert invokable.execution.response is None
    assert isinstance(invokable.execution.duration, float)
    assert invokable.execution.duration > 0
```

## 7. Complete Test File Structure

```python
"""
Tests for khive.protocols.invokable module.
"""

import asyncio
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from freezegun import freeze_time
from pydantic import BaseModel

from khive.protocols.invokable import Invokable
from khive.protocols.types import Execution, ExecutionStatus


# --- Mock classes for testing ---
class MockResponse(BaseModel):
    """Mock response for testing."""
    value: str = "test_response"


class TestInvokable(Invokable):
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

    async def _success_fn(self, *args, **kwargs):
        return self._response


class FailingInvokable(Invokable):
    """Mock Invokable implementation that fails."""

    def __init__(self, error_message="Test error", **kwargs):
        super().__init__(**kwargs)
        self._invoke_function = self._failing_fn
        self._error_message = error_message

    async def _failing_fn(self, *args, **kwargs):
        raise ValueError(self._error_message)


class CancellingInvokable(Invokable):
    """Mock Invokable implementation that gets cancelled."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._invoke_function = self._cancelling_fn

    async def _cancelling_fn(self, *args, **kwargs):
        raise asyncio.CancelledError()


# --- Fixtures ---
@pytest.fixture
def mock_event_loop_time(monkeypatch):
    """Mock the event loop time method to return predictable values."""
    time_values = [1.0, 2.0]  # Start time and end time
    mock_time = MagicMock(side_effect=time_values)

    # Create a mock event loop
    mock_loop = MagicMock()
    mock_loop.time = mock_time

    # Mock the get_event_loop function
    monkeypatch.setattr(asyncio, "get_event_loop", lambda: mock_loop)

    return mock_loop


# --- Helper functions ---
def create_invokable_with_function(func, *args, **kwargs):
    """Helper to create an Invokable with a specific function and arguments."""
    obj = Invokable()
    obj._invoke_function = func
    obj._invoke_args = list(args)
    obj._invoke_kwargs = kwargs
    return obj


async def assert_execution_completed(invokable):
    """Helper to assert that execution completed successfully."""
    assert invokable.execution.status == ExecutionStatus.COMPLETED
    assert invokable.execution.error is None
    assert invokable.execution.response is not None
    assert invokable.response_obj is not None
    assert isinstance(invokable.execution.duration, float)
    assert invokable.execution.duration > 0


async def assert_execution_failed(invokable, error_substring=None):
    """Helper to assert that execution failed with expected error."""
    assert invokable.execution.status == ExecutionStatus.FAILED
    assert invokable.execution.error is not None
    if error_substring:
        assert error_substring in invokable.execution.error
    assert invokable.execution.response is None
    assert isinstance(invokable.execution.duration, float)
    assert invokable.execution.duration > 0


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

    obj = Invokable(
        request=request,
        execution=execution,
        response_obj=response_obj
    )

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
async def test_invoke_with_sync_function():
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
async def test_invoke_with_async_function():
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
async def test_invoke_successful_execution(mock_event_loop_time):
    """Test that invoke handles successful execution correctly."""
    # Create a mock response
    mock_response = MockResponse(value="success")

    # Create Invokable with success function
    obj = SuccessInvokable(response=mock_response)

    # Call invoke
    await obj.invoke()

    # Verify execution state
    await assert_execution_completed(obj)
    assert obj.response_obj == mock_response
    assert obj.execution.duration == 1.0  # 2.0 - 1.0 from mock_event_loop_time


@pytest.mark.asyncio
async def test_invoke_failed_execution(mock_event_loop_time):
    """Test that invoke handles failed execution correctly."""
    # Create Invokable with failing function
    error_message = "Custom test error"
    obj = FailingInvokable(error_message=error_message)

    # Call invoke
    await obj.invoke()

    # Verify execution state
    await assert_execution_failed(obj, error_message)
    assert obj.execution.duration == 1.0  # 2.0 - 1.0 from mock_event_loop_time


@pytest.mark.asyncio
async def test_invoke_cancelled_execution():
    """Test that invoke handles cancellation correctly."""
    # Create Invokable with cancelling function
    obj = CancellingInvokable()

    # Call invoke and expect CancelledError to be re-raised
    with pytest.raises(asyncio.CancelledError):
        await obj.invoke()

    # Execution state should not be updated since the finally block won't complete
    assert obj.execution.status == ExecutionStatus.PENDING


@pytest.mark.asyncio
async def test_invoke_updates_timestamp():
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
```

## 8. Notes and Caveats

### 8.1 Known Limitations

- Testing cancellation scenarios can be tricky as they involve asyncio internals
- The mock event loop time approach simplifies duration testing but doesn't test
  actual timing behavior

### 8.2 Future Improvements

- Consider adding more complex scenarios with nested invocations
- Add tests for concurrent invocations if needed in the future
