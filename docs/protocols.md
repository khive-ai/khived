# Khive Protocols Guide

This guide provides a comprehensive overview of the protocol system in Khive,
explaining how to understand, implement, and test protocol-based classes.

## Understanding Protocols in Khive

Protocols in Khive are abstract interfaces that define consistent patterns for
object behavior. They establish a contract that implementing classes must
follow, ensuring interoperability and consistency across the system.

### Protocol Hierarchy and Relationships

Khive protocols are organized in a hierarchical structure, with each level
building on the capabilities of the previous ones:

````
                  ┌─────────────┐
                  │   types.py  │
                  └──────┬──────┘
                         │
                  ┌──────▼──────┐
                  │identifiable.py
                  └──────┬──────┘
                         │
                  ┌──────▼──────┐
                  │ temporal.py │
                  └──────┬──────┘
                         │
          ┌──────────────┼──────────────┐
          │              │              │
┌─────────▼────────┐    ┌▼─────────┐    ┌▼────────┐
│  embedable.py    │    │invokable.py    │service.py│
└─────────┬────────┘    └┬─────────┘    └──────────┘
          │              │
          └──────────────┼──────────────┐
                         │              │
                    ┌────▼─────┐   ┌────▼─────┐
                    │ event.py │   │  Other   │
                    └──────────┘   │Extensions│
                                   |                                    └──────────┘
                                   ```

                                   #### Resource Management Layer

                                   - **protocols.py**: Defines protocols for async resource management
                                     - `AsyncResourceManager`: Protocol for components that manage async resources with context managers
                                     - `ResourceClient`: Protocol for resource clients that interact with external APIs
                                     - `Executor`: Protocol for executors that manage concurrent operations
                                     - Features: Standardized resource initialization and cleanup, proper async context management
                                     - See [Async Resource Management](core-concepts/async_resource_management.md) for details

                                   #### Foundation Layer

- **types.py**: Defines basic types and enums used throughout the system
  - `Embedding`: Type alias for a list of floats representing vector embeddings
  - `ExecutionStatus`: Enum for tracking execution states (PENDING, PROCESSING,
    COMPLETED, FAILED)
  - `Execution`: Model for tracking execution state, including duration,
    response, and errors
  - `Log`: Model for storing event logs with metadata

#### Core Layer

- **identifiable.py**: Provides unique identification capabilities
  - `Identifiable`: Base class that adds a UUID to objects
  - Features: UUID generation, validation, serialization

- **temporal.py**: Adds timestamp tracking capabilities
  - `Temporal`: Base class that adds creation and update timestamps
  - Features: Timestamp management, update tracking

#### Capability Layer

- **embedable.py**: Enables vector embedding generation
  - `Embedable`: Base class for objects that can generate embeddings
  - Features: Content creation, embedding generation, dimension tracking

- **invokable.py**: Supports function invocation and execution tracking
  - `Invokable`: Base class for objects that can be invoked
  - Features: Execution state tracking, error handling, response processing

- **service.py**: Defines service interface for request handling
  - `Service`: Abstract base class for service implementations
  - Features: Standardized request handling interface

#### Integration Layer

- **event.py**: Combines multiple capabilities for comprehensive event tracking
  - `Event`: Class that integrates Identifiable, Embedable, and Invokable
  - `as_event`: Decorator for tracking function calls as events
  - Features: Event creation, storage, embedding generation

### Key Protocol Characteristics

Each protocol in Khive follows these principles:

1. **Pydantic-Based**: Uses Pydantic for data validation and serialization
2. **Self-Contained**: Each protocol has a single, focused responsibility
3. **Composable**: Protocols can be combined through inheritance or composition
4. **Well-Tested**: All protocols have comprehensive test coverage
5. **Well-Documented**: All protocols have clear documentation

## Implementing Protocol-Based Classes

When implementing classes that follow Khive protocols, you should adhere to
these guidelines:

### 1. Choose the Right Protocol(s)

Select the appropriate protocol(s) based on the functionality you need:

```python
# For a simple identifiable object
from khive.protocols.identifiable import Identifiable

class MyIdentifiableObject(Identifiable):
    name: str
    description: str = None

# For an object with timestamps
from khive.protocols.temporal import Temporal

class MyTemporalObject(Temporal):
    name: str
    description: str = None

# For a complex object with multiple capabilities
from khive.protocols.event import Event

class MyCustomEvent(Event):
    # Custom implementation...
````

### 2. Implement Required Methods

Each protocol may require implementing specific methods:

```python
from khive.protocols.embedable import Embedable

class MyEmbedable(Embedable):
    name: str
    description: str = None

    def create_content(self):
        """Override to provide custom content creation logic."""
        return f"{self.name}: {self.description}"
```

### 3. Use Protocol Decorators

Some protocols provide decorators to simplify implementation:

```python
from khive.protocols.event import as_event

@as_event(embed_content=True, adapt=True)
async def my_function(request):
    """This function will be tracked as an event."""
    return {"result": f"Processed {request['input']}"}
```

### 4. Follow Protocol Patterns

Maintain consistency with existing protocols:

```python
from pydantic import Field
from khive.protocols.temporal import Temporal

class MyCustomObject(Temporal):
    name: str = Field(..., description="The name of the object")
    description: str = Field(None, description="Optional description")

    def process(self):
        """Process the object and update its timestamp."""
        # Do processing...
        self.update_timestamp()  # Update timestamp after changes
        return "Processed"
```

## Common Patterns and Best Practices

### Pattern 1: Combining Multiple Protocols

```python
from khive.protocols.identifiable import Identifiable
from khive.protocols.temporal import Temporal

class TrackedObject(Identifiable, Temporal):
    """An object with both ID and timestamp tracking."""
    name: str
```

### Pattern 2: Extending Protocol Behavior

```python
from khive.protocols.embedable import Embedable

class EnhancedEmbedable(Embedable):
    """Enhanced embedable with additional capabilities."""

    async def generate_embedding(self) -> "EnhancedEmbedable":
        """Override to add pre/post processing."""
        # Pre-processing
        self.content = self.content.lower()

        # Call parent implementation
        await super().generate_embedding()

        # Post-processing
        self.embedding = [x * 0.5 for x in self.embedding]
        return self
```

### Pattern 3: Using the Event Decorator

```python
from khive.protocols.event import as_event

# Basic usage
@as_event()
async def simple_function(request):
    return {"result": "success"}

# Advanced usage
@as_event(
    embed_content=True,  # Generate embeddings
    adapt=True,          # Store in database
    event_type="CustomEvent",  # Custom event type
    request_arg="data"   # Custom request argument name
)
async def advanced_function(context, data):
    return {"processed": data}
```

### Pattern 4: Service Implementation

```python
from khive.protocols.service import Service

class MyService(Service):
    """Custom service implementation."""

    async def handle_request(self, request, ctx=None):
        """Process the request with optional context."""
        ctx = ctx or {}
        user_id = ctx.get("user_id")

        # Process request
        result = {"status": "success", "data": request}

        if user_id:
            result["user_id"] = user_id

        return result
```

## Testing Protocol Implementations

Proper testing is essential for protocol implementations. Follow these
guidelines:

### 1. Test Protocol Compliance

Ensure your implementation correctly follows the protocol interface:

```python
def test_my_embedable_is_embedable():
    """Test that MyEmbedable follows the Embedable protocol."""
    obj = MyEmbedable(name="Test", description="Description")
    assert isinstance(obj, Embedable)
    assert hasattr(obj, "embedding")
    assert hasattr(obj, "generate_embedding")
```

### 2. Test Custom Behavior

Verify that your custom implementation works correctly:

```python
@pytest.mark.asyncio
async def test_my_embedable_create_content():
    """Test custom content creation logic."""
    obj = MyEmbedable(name="Test", description="Description")
    content = obj.create_content()
    assert content == "Test: Description"

    # Test with missing description
    obj2 = MyEmbedable(name="Test")
    content2 = obj2.create_content()
    assert content2 == "Test: None"
```

### 3. Test Integration

Verify that your implementation works with other components:

```python
@pytest.mark.asyncio
async def test_my_embedable_with_event():
    """Test that MyEmbedable works with Event."""
    @as_event(embed_content=True)
    async def test_function(request):
        return MyEmbedable(name=request["name"])

    event = await test_function({"name": "Test"})
    assert isinstance(event.response_obj, MyEmbedable)
    assert event.response_obj.name == "Test"
```

### 4. Test Edge Cases

Include tests for boundary conditions and unusual inputs:

```python
@pytest.mark.asyncio
async def test_my_embedable_with_empty_values():
    """Test behavior with empty values."""
    obj = MyEmbedable(name="")
    content = obj.create_content()
    assert content == ": None"

    # Test embedding generation with empty content
    await obj.generate_embedding()
    assert isinstance(obj.embedding, list)
```

### 5. Maintain High Coverage

Ensure your tests cover all aspects of your implementation:

```bash
# Run tests with coverage
uv run pytest tests/my_module/ --cov=my_module --cov-report=term

# Aim for >80% coverage
```

## Conclusion

Khive's protocol system provides a flexible and powerful foundation for building
consistent, interoperable components. By understanding the protocol hierarchy,
following implementation best practices, and thoroughly testing your code, you
can create robust protocol-based classes that integrate seamlessly with the rest
of the system.

For more detailed information about specific protocols, refer to the API
documentation and the protocol source code in the `khive.protocols` module.

## Related Documentation

- [Async Resource Management](core-concepts/async_resource_management.md):
  Detailed documentation on the AsyncResourceManager protocol and its
  implementations
