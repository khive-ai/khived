# Protocol Testing in Khive

This directory contains comprehensive test suites for all protocol interfaces
defined in the `khive.protocols` module. These tests ensure that each protocol
behaves as expected and maintains compatibility with the rest of the system.

## Testing Approach

The testing approach for protocols follows a layered structure that mirrors the
protocol hierarchy itself:

1. **Foundation Tests**: Tests for basic types and enums (`test_types.py`)
2. **Core Protocol Tests**: Tests for the fundamental protocols
   (`test_identifiable.py`, `test_temporal.py`)
3. **Capability Protocol Tests**: Tests for protocols that add specific
   capabilities (`test_embedable.py`, `test_invokable.py`, `test_service.py`)
4. **Integration Protocol Tests**: Tests for protocols that combine multiple
   capabilities (`test_event.py`)

Each test suite builds on the previous ones, ensuring that protocols work both
individually and in combination.

## Test Structure

Each protocol test file follows a consistent structure:

1. **Mock Classes**: Implementations of the protocol for testing purposes
2. **Fixtures**: Reusable test components
3. **Helper Functions**: Utility functions to simplify test cases
4. **Initialization Tests**: Tests for object creation and default values
5. **Method Tests**: Tests for each method in the protocol
6. **Integration Tests**: Tests for how the protocol interacts with other
   components
7. **Error Handling Tests**: Tests for proper error handling

## Protocol Test Coverage

| Protocol          | Test File              | Coverage Focus                                                              |
| ----------------- | ---------------------- | --------------------------------------------------------------------------- |
| `types.py`        | `test_types.py`        | Basic types, enums, and models (Embedding, ExecutionStatus, Execution, Log) |
| `identifiable.py` | `test_identifiable.py` | UUID generation, validation, serialization, and immutability                |
| `temporal.py`     | `test_temporal.py`     | Timestamp handling, updates, and serialization                              |
| `embedable.py`    | `test_embedable.py`    | Embedding generation, content creation, and response parsing                |
| `invokable.py`    | `test_invokable.py`    | Invocation lifecycle, execution status tracking, and error handling         |
| `service.py`      | `test_service.py`      | Service interface, request handling, and protocol enforcement               |
| `event.py`        | `test_event.py`        | Event creation, decoration, storage, and embedding generation               |

## Best Practices for Testing Protocol Implementations

When implementing tests for new protocol implementations, follow these best
practices:

1. **Test Protocol Compliance**: Ensure that implementations correctly follow
   the protocol interface
2. **Test Default Behavior**: Verify that default values and behaviors match
   expectations
3. **Test Custom Behavior**: Verify that custom implementations extend the
   protocol correctly
4. **Test Error Handling**: Ensure that implementations handle errors gracefully
5. **Test Serialization**: Verify that objects can be properly serialized and
   deserialized
6. **Test Integration**: Verify that the protocol works with other components
7. **Use Mocks Judiciously**: Use mocks to isolate the protocol being tested
8. **Test Edge Cases**: Include tests for boundary conditions and unusual inputs

## Running the Tests

To run the protocol tests:

```bash
# Run all protocol tests
uv run pytest tests/protocols/

# Run tests for a specific protocol
uv run pytest tests/protocols/test_identifiable.py

# Run tests with coverage
uv run pytest tests/protocols/ --cov=khive.protocols

# Generate a coverage report
uv run pytest tests/protocols/ --cov=khive.protocols --cov-report=html
```

## Coverage Requirements

All protocol implementations should maintain high test coverage (>80%). This
ensures that protocols remain stable and reliable as the codebase evolves.

Current coverage metrics:

- Line coverage: >90%
- Branch coverage: >85%
- Function coverage: 100%

## Adding New Protocol Tests

When adding tests for a new protocol:

1. Create a new test file following the naming convention
   `test_<protocol_name>.py`
2. Include tests for all methods and properties in the protocol
3. Test both normal operation and error conditions
4. Ensure that the protocol integrates correctly with existing protocols
5. Maintain high test coverage (>80%)
6. Document any special testing considerations in the test file

By following these guidelines, we ensure that all protocols in the khive system
are thoroughly tested and maintain high quality standards.
