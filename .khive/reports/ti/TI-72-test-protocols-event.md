---
title: Test Implementation for Event Protocol
by: khive-implementer
created: 2025-05-14
updated: 2025-05-14
version: 1.0
doc_type: TI
output_subdir: ti
description: Detailed test implementation plan for the Event protocol in khive
date: 2025-05-14
---

# Test Implementation Plan: Event Protocol

## 1. Overview

### 1.1 Component Under Test

The Event protocol (`khive.protocols.event`) is a core component that integrates
multiple protocols (Identifiable, Embedable, and Invokable) to create a unified
event tracking and processing system. It provides:

- An `Event` class that inherits from Identifiable, Embedable, and Invokable
- Methods for content creation and log generation
- An `as_event` decorator for wrapping functions to automatically create and
  process events

### 1.2 Test Approach

We will use a combination of:

- Unit tests for individual methods and components
- Integration tests for the decorator and its interaction with other systems
- Mock objects to isolate testing from external dependencies
- Async testing with pytest-asyncio for asynchronous behavior

### 1.3 Key Testing Goals

- Verify correct initialization and inheritance from parent protocols
- Test content creation and log generation with various parameters
- Test the decorator with different configurations
- Verify embedding and storage adapter integration
- Test error handling and edge cases
- Achieve >80% test coverage

## 2. Test Environment

### 2.1 Test Framework

```
pytest
pytest-asyncio
pytest-cov
freezegun
```

### 2.2 Mock Framework

```
unittest.mock
```

### 2.3 Test Database

No actual database will be used. Instead, we will create mock adapters that
simulate the behavior of storage adapters.

## 3. Unit Tests

### 3.1 Test Suite: Event Initialization and Inheritance

#### 3.1.1 Test Case: Event Initialization

**Purpose:** Verify that Event initializes correctly with required parameters
**Setup:**

```python
@pytest.fixture
def event_function():
    return lambda x: x

@pytest.fixture
def event_args():
    return [1, 2, 3]

@pytest.fixture
def event_kwargs():
    return {"key": "value"}
```

**Test Implementation:**

```python
def test_event_initialization(event_function, event_args, event_kwargs):
    """Test that Event initializes with the required parameters."""
    # Act
    event = Event(event_function, event_args, event_kwargs)

    # Assert
    assert event._invoke_function == event_function
    assert event._invoke_args == event_args
    assert event._invoke_kwargs == event_kwargs
```

#### 3.1.2 Test Case: Event Protocol Inheritance

**Purpose:** Verify that Event inherits from all required protocols **Test
Implementation:**

```python
def test_event_inheritance(event_function, event_args, event_kwargs):
    """Test that Event inherits from Identifiable, Embedable, and Invokable."""
    # Act
    event = Event(event_function, event_args, event_kwargs)

    # Assert
    assert isinstance(event, Identifiable)
    assert isinstance(event, Embedable)
    assert isinstance(event, Invokable)
```

#### 3.1.3 Test Case: Event Default Values

**Purpose:** Verify that Event sets default values correctly **Test
Implementation:**

```python
def test_event_default_values(event_function):
    """Test that Event sets default values correctly."""
    # Act
    event = Event(event_function, None, None)

    # Assert
    assert event._invoke_args == []
    assert event._invoke_kwargs == {}
```

### 3.2 Test Suite: Event Methods

#### 3.2.1 Test Case: create_content with Existing Content

**Purpose:** Verify that create_content returns existing content if available
**Test Implementation:**

```python
def test_create_content_existing(event_function, event_args, event_kwargs):
    """Test that create_content returns existing content."""
    # Arrange
    event = Event(event_function, event_args, event_kwargs)
    event.content = "existing content"

    # Act
    result = event.create_content()

    # Assert
    assert result == "existing content"
```

#### 3.2.2 Test Case: create_content with No Existing Content

**Purpose:** Verify that create_content creates JSON content from request and
response **Test Implementation:**

```python
def test_create_content_new(event_function, event_args, event_kwargs):
    """Test that create_content creates new content from request and response."""
    # Arrange
    event = Event(event_function, event_args, event_kwargs)
    event.request = {"input": "test"}
    event.execution.response = {"output": "result"}

    # Act
    result = event.create_content()

    # Assert
    assert "request" in result
    assert "response" in result
    assert event.content == result
    # Verify it's valid JSON
    parsed = json.loads(result)
    assert parsed["request"] == {"input": "test"}
    assert parsed["response"] == {"output": "result"}
```

#### 3.2.3 Test Case: to_log with Default Parameters

**Purpose:** Verify that to_log creates a Log object with default parameters
**Test Implementation:**

```python
def test_to_log_default(event_function, event_args, event_kwargs):
    """Test that to_log creates a Log with default parameters."""
    # Arrange
    event = Event(event_function, event_args, event_kwargs)
    event.request = {"input": "test"}
    event.execution.response = {"output": "result"}
    event.create_content()

    # Act
    log = event.to_log()

    # Assert
    assert log.event_type == "Event"  # Default is class name
    assert log.content == event.content
    assert log.id == event.id
    assert "sha256" not in log.model_dump()
```

#### 3.2.4 Test Case: to_log with Custom Event Type

**Purpose:** Verify that to_log uses custom event_type when provided **Test
Implementation:**

```python
def test_to_log_custom_event_type(event_function, event_args, event_kwargs):
    """Test that to_log uses custom event_type when provided."""
    # Arrange
    event = Event(event_function, event_args, event_kwargs)
    event.request = {"input": "test"}
    event.execution.response = {"output": "result"}
    event.create_content()

    # Act
    log = event.to_log(event_type="CustomEvent")

    # Assert
    assert log.event_type == "CustomEvent"
```

#### 3.2.5 Test Case: to_log with hash_content=True

**Purpose:** Verify that to_log adds SHA256 hash when requested **Test
Implementation:**

```python
def test_to_log_hash_content(event_function, event_args, event_kwargs):
    """Test that to_log adds SHA256 hash when hash_content=True."""
    # Arrange
    event = Event(event_function, event_args, event_kwargs)
    event.request = {"input": "test"}
    event.execution.response = {"output": "result"}
    event.create_content()

    # Act
    log = event.to_log(hash_content=True)

    # Assert
    assert "sha256" in log.model_dump()
    assert log.sha256 is not None
```

### 3.3 Test Suite: as_event Decorator

#### 3.3.1 Test Case: Basic Decorator Functionality

**Purpose:** Verify that as_event decorator creates and returns an Event
**Setup:**

```python
class MockAdapter:
    """Mock adapter for testing."""

    def __init__(self):
        self.stored_events = []

    @classmethod
    async def to_obj(cls, obj, **kwargs):
        cls.stored_events.append(obj)
        return obj

@pytest.fixture
def mock_adapter():
    adapter = MockAdapter()
    adapter.stored_events = []
    return adapter
```

**Test Implementation:**

```python
@pytest.mark.asyncio
async def test_as_event_basic(mock_adapter):
    """Test that as_event decorator creates and returns an Event."""
    # Arrange
    @as_event(adapt=True, adapter=mock_adapter)
    async def test_function(request):
        return {"result": "success"}

    # Act
    event = await test_function({"input": "test"})

    # Assert
    assert isinstance(event, Event)
    assert event.request == {"input": "test"}
    assert event.execution.status == ExecutionStatus.COMPLETED
    assert event.execution.response == {"result": "success"}
```

#### 3.3.2 Test Case: Decorator with Custom request_arg

**Purpose:** Verify that as_event extracts request from specified argument
**Test Implementation:**

```python
@pytest.mark.asyncio
async def test_as_event_custom_request_arg(mock_adapter):
    """Test that as_event uses custom request_arg to extract request."""
    # Arrange
    @as_event(request_arg="custom_req", adapt=True, adapter=mock_adapter)
    async def test_function(other_arg, custom_req):
        return {"result": custom_req["value"]}

    # Act
    event = await test_function("ignored", {"value": "from_custom"})

    # Assert
    assert event.request == {"value": "from_custom"}
    assert event.execution.response == {"result": "from_custom"}
```

#### 3.3.3 Test Case: Decorator with embed_content=True

**Purpose:** Verify that as_event generates embeddings when requested **Setup:**

```python
@pytest.fixture
def mock_embed_function():
    async def embed_fn(content):
        return [0.1, 0.2, 0.3]
    return embed_fn
```

**Test Implementation:**

```python
@pytest.mark.asyncio
async def test_as_event_with_embedding(mock_adapter, mock_embed_function):
    """Test that as_event generates embeddings when embed_content=True."""
    # Arrange
    @as_event(
        embed_content=True,
        embed_function=mock_embed_function,
        adapt=True,
        adapter=mock_adapter
    )
    async def test_function(request):
        return {"result": "success"}

    # Act
    event = await test_function({"input": "test"})

    # Assert
    assert event.embedding == [0.1, 0.2, 0.3]
    assert event.n_dim == 3
```

#### 3.3.4 Test Case: Decorator with Storage Adapter

**Purpose:** Verify that as_event stores events via adapter **Test
Implementation:**

```python
@pytest.mark.asyncio
async def test_as_event_with_storage(mock_adapter):
    """Test that as_event stores events via adapter when adapt=True."""
    # Arrange
    @as_event(adapt=True, adapter=mock_adapter)
    async def test_function(request):
        return {"result": "success"}

    # Act
    event = await test_function({"input": "test"})

    # Assert
    assert len(mock_adapter.stored_events) == 1
    stored_log = mock_adapter.stored_events[0]
    assert stored_log.id == event.id
    assert stored_log.content == event.content
```

#### 3.3.5 Test Case: Decorator with Class Method

**Purpose:** Verify that as_event works with class methods **Test
Implementation:**

```python
@pytest.mark.asyncio
async def test_as_event_with_class_method(mock_adapter):
    """Test that as_event works with class methods."""
    # Arrange
    class TestClass:
        @as_event(adapt=True, adapter=mock_adapter)
        async def test_method(self, request):
            return {"result": "class_method"}

    # Act
    instance = TestClass()
    event = await instance.test_method({"input": "test"})

    # Assert
    assert isinstance(event, Event)
    assert event.request == {"input": "test"}
    assert event.execution.response == {"result": "class_method"}
```

### 3.4 Test Suite: Error Handling

#### 3.4.1 Test Case: Invalid Storage Provider

**Purpose:** Verify that as_event raises ValueError for invalid storage provider
**Test Implementation:**

```python
def test_as_event_invalid_storage_provider(monkeypatch):
    """Test that as_event raises ValueError for invalid storage provider."""
    # Arrange
    class MockSettings:
        KHIVE_AUTO_STORE_EVENT = True
        KHIVE_AUTO_EMBED_LOG = False
        KHIVE_STORAGE_PROVIDER = "invalid_provider"

    monkeypatch.setattr("khive.protocols.event.settings", MockSettings())

    # Act & Assert
    with pytest.raises(ValueError, match="Storage adapter invalid_provider is not supported"):
        @as_event()
        async def test_function(request):
            return {"result": "success"}
```

#### 3.4.2 Test Case: Function Raises Exception

**Purpose:** Verify that as_event handles exceptions from wrapped function
**Test Implementation:**

```python
@pytest.mark.asyncio
async def test_as_event_function_exception(mock_adapter):
    """Test that as_event handles exceptions from wrapped function."""
    # Arrange
    @as_event(adapt=True, adapter=mock_adapter)
    async def test_function(request):
        raise ValueError("Test error")

    # Act
    event = await test_function({"input": "test"})

    # Assert
    assert event.execution.status == ExecutionStatus.FAILED
    assert "Test error" in event.execution.error
```

#### 3.4.3 Test Case: Function Gets Cancelled

**Purpose:** Verify that as_event propagates CancelledError **Test
Implementation:**

```python
@pytest.mark.asyncio
async def test_as_event_cancellation(mock_adapter):
    """Test that as_event propagates CancelledError."""
    # Arrange
    @as_event(adapt=True, adapter=mock_adapter)
    async def test_function(request):
        raise asyncio.CancelledError()

    # Act & Assert
    with pytest.raises(asyncio.CancelledError):
        await test_function({"input": "test"})
```

## 4. Integration Tests

### 4.1 Test Suite: Event Lifecycle

#### 4.1.1 Test Case: Complete Event Lifecycle

**Purpose:** Verify the complete lifecycle of an event with the decorator **Test
Implementation:**

```python
@pytest.mark.asyncio
async def test_event_complete_lifecycle(mock_adapter, mock_embed_function):
    """Test the complete lifecycle of an event with the decorator."""
    # Arrange
    @as_event(
        embed_content=True,
        embed_function=mock_embed_function,
        adapt=True,
        adapter=mock_adapter,
        event_type="TestLifecycle"
    )
    async def test_function(request):
        return {"processed": True, "input": request["value"]}

    # Act
    event = await test_function({"value": "test_input"})

    # Assert - Event properties
    assert isinstance(event, Event)
    assert isinstance(event.id, uuid.UUID)
    assert event.request == {"value": "test_input"}
    assert event.execution.status == ExecutionStatus.COMPLETED
    assert event.execution.response == {"processed": True, "input": "test_input"}
    assert event.embedding == [0.1, 0.2, 0.3]

    # Assert - Storage
    assert len(mock_adapter.stored_events) == 1
    stored_log = mock_adapter.stored_events[0]
    assert stored_log.event_type == "TestLifecycle"
    assert stored_log.id == event.id
    assert stored_log.content == event.content
```

#### 4.1.2 Test Case: Default Storage Provider Selection

**Purpose:** Verify that as_event selects the correct storage provider based on
settings **Test Implementation:**

```python
@pytest.mark.asyncio
async def test_event_default_storage_provider(monkeypatch):
    """Test that as_event selects the correct storage provider based on settings."""
    # Arrange
    class MockSettings:
        KHIVE_AUTO_STORE_EVENT = True
        KHIVE_AUTO_EMBED_LOG = False
        KHIVE_STORAGE_PROVIDER = "async_qdrant"

    class MockQdrantAdapter:
        stored_events = []

        @classmethod
        async def to_obj(cls, obj, **kwargs):
            cls.stored_events.append(obj)
            return obj

    monkeypatch.setattr("khive.protocols.event.settings", MockSettings())
    monkeypatch.setattr(
        "pydapter.extras.async_qdrant_.AsyncQdrantAdapter",
        MockQdrantAdapter
    )

    # Act
    @as_event()
    async def test_function(request):
        return {"result": "success"}

    event = await test_function({"input": "test"})

    # Assert
    assert len(MockQdrantAdapter.stored_events) == 1
    stored_log = MockQdrantAdapter.stored_events[0]
    assert stored_log.id == event.id
```

## 5. Mock Implementation Details

```python
class MockRequest(BaseModel):
    """Mock request for testing."""
    input: str

    def model_dump(self):
        return {"input": self.input}

class MockAdapter:
    """Mock adapter for testing."""

    stored_events = []

    @classmethod
    async def to_obj(cls, obj, **kwargs):
        cls.stored_events.append(obj)
        return obj

async def mock_embed_function(content):
    """Mock embedding function that returns a fixed embedding."""
    return [0.1, 0.2, 0.3]
```

## 6. Test Data

```python
test_requests = [
    {"input": "test1"},
    {"input": "test2", "metadata": {"source": "user"}}
]

test_responses = [
    {"result": "success", "value": 42},
    {"error": "not found", "code": 404}
]
```

## 7. Helper Functions

```python
def create_test_event(func=None, args=None, kwargs=None):
    """Create a test Event instance with optional parameters."""
    if func is None:
        func = lambda x: x
    return Event(func, args or [], kwargs or {})

async def invoke_test_event(event, request=None, response=None):
    """Set up and invoke a test event with the given request and response."""
    if request is not None:
        event.request = request

    if response is not None:
        # Mock the _invoke method to return the specified response
        original_invoke = event._invoke
        event._invoke = lambda: response

    await event.invoke()

    if response is not None:
        # Restore original _invoke
        event._invoke = original_invoke

    return event
```

## 8. Test Coverage Targets

- **Line Coverage Target:** 85%
- **Branch Coverage Target:** 80%
- **Critical Areas:**
  - as_event decorator: 90% coverage
  - Storage adapter integration: 90% coverage
  - Error handling: 90% coverage

## 9. Continuous Integration

```yaml
name: Test Event Protocol
on: [push, pull_request]
jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.10"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install uv
          uv sync
      - name: Run tests
        run: |
          uv run pytest tests/protocols/test_event.py -v --cov=src/khive/protocols/event.py
```

## 10. Notes and Caveats

### 10.1 Known Limitations

- The tests mock the storage adapters rather than using actual databases
- Some complex interactions between protocols may require additional testing
- The tests assume that the parent protocol tests (Identifiable, Embedable,
  Invokable) are already passing

### 10.2 Future Improvements

- Add more comprehensive tests for different storage providers
- Add performance tests for event processing
- Consider adding property-based testing for more thorough validation
