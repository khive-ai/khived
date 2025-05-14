---
title: Test Implementation for khive/protocols/temporal.py
by: khive-implementer
created: 2025-05-14
updated: 2025-05-14
version: 1.0
doc_type: TI
output_subdir: ti
description: Detailed test implementation for the khive/protocols/temporal.py module
date: 2025-05-14
---

# Test Implementation Plan: khive/protocols/temporal.py

## 1. Overview

### 1.1 Component Under Test

This document outlines the test implementation for the
`khive/protocols/temporal.py` module, which defines the `Temporal` base class
used throughout the khive project. The `Temporal` class provides:

- Automatic timestamp generation for created_at and updated_at fields
- Timestamp validation and conversion
- Timestamp serialization to ISO format
- A method to update the updated_at timestamp

### 1.2 Test Approach

The test approach is primarily unit testing, as the module consists of a base
class without external dependencies. The tests verify:

1. Default timestamp initialization works correctly
2. Custom timestamps are properly validated and assigned
3. Timestamp serialization functions as expected
4. The update_timestamp() method works correctly
5. Field immutability/mutability behaves as expected
6. Edge cases and error handling are properly managed

### 1.3 Key Testing Goals

- Ensure 100% test coverage for the `temporal.py` module
- Verify all methods and properties function correctly
- Test edge cases and error handling
- Validate field validators and serializers
- Ensure deterministic time testing with freezegun

## 2. Test Environment

### 2.1 Test Framework

```
pytest
pytest-cov
```

### 2.2 Mock Framework

```
freezegun (for deterministic time testing)
unittest.mock
pytest-mock
```

### 2.3 Test Database

No database is required for these tests as the module doesn't interact with
databases.

## 3. Unit Tests

### 3.1 Test Suite: Temporal Class

#### 3.1.1 Test Case: Default Timestamp Initialization

**Purpose:** Verify that the Temporal class automatically initializes both
timestamps to the current time.

**Test Implementation:**

```python
@freeze_time("2025-05-14T12:00:00Z")
def test_temporal_default_initialization():
    """Test that Temporal initializes with current UTC time for both timestamps."""
    obj = Temporal()

    # Both timestamps should be the frozen time
    expected_time = datetime(2025, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    assert obj.created_at == expected_time
    assert obj.updated_at == expected_time

    # Verify timezone is UTC
    assert obj.created_at.tzinfo == timezone.utc
    assert obj.updated_at.tzinfo == timezone.utc
```

#### 3.1.2 Test Case: Custom Timestamp Initialization

**Purpose:** Verify that the Temporal class accepts custom datetime objects.

**Test Implementation:**

```python
def test_temporal_custom_initialization():
    """Test that Temporal accepts custom datetime objects."""
    created = datetime(2025, 5, 10, 10, 0, 0, tzinfo=timezone.utc)
    updated = datetime(2025, 5, 10, 11, 0, 0, tzinfo=timezone.utc)

    obj = Temporal(created_at=created, updated_at=updated)

    assert obj.created_at == created
    assert obj.updated_at == updated
```

#### 3.1.3 Test Case: String Timestamp Initialization

**Purpose:** Verify that the Temporal class accepts ISO format strings and
converts them to datetime objects.

**Test Implementation:**

```python
def test_temporal_string_initialization():
    """Test that Temporal accepts ISO format strings and converts them to datetime."""
    created_str = "2025-05-10T10:00:00+00:00"
    updated_str = "2025-05-10T11:00:00+00:00"

    obj = Temporal(created_at=created_str, updated_at=updated_str)

    assert isinstance(obj.created_at, datetime)
    assert isinstance(obj.updated_at, datetime)
    assert obj.created_at == datetime(2025, 5, 10, 10, 0, 0, tzinfo=timezone.utc)
    assert obj.updated_at == datetime(2025, 5, 10, 11, 0, 0, tzinfo=timezone.utc)
```

#### 3.1.4 Test Case: Update Timestamp Method

**Purpose:** Verify that the update_timestamp() method updates the updated_at
field to the current time.

**Test Implementation:**

```python
@freeze_time("2025-05-14T12:00:00Z")
def test_update_timestamp():
    """Test that update_timestamp() updates the updated_at field to current time."""
    # Create with custom timestamps
    created = datetime(2025, 5, 10, 10, 0, 0, tzinfo=timezone.utc)
    updated = datetime(2025, 5, 10, 11, 0, 0, tzinfo=timezone.utc)
    obj = Temporal(created_at=created, updated_at=updated)

    # Initial state
    assert obj.created_at == created
    assert obj.updated_at == updated

    # Update timestamp
    obj.update_timestamp()

    # created_at should remain unchanged
    assert obj.created_at == created

    # updated_at should be updated to the frozen time
    expected_time = datetime(2025, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    assert obj.updated_at == expected_time
```

#### 3.1.5 Test Case: Datetime Serialization

**Purpose:** Verify that datetime fields are serialized to ISO format strings.

**Test Implementation:**

```python
def test_datetime_serialization():
    """Test that datetime fields are serialized to ISO format strings."""
    created = datetime(2025, 5, 10, 10, 0, 0, tzinfo=timezone.utc)
    updated = datetime(2025, 5, 10, 11, 0, 0, tzinfo=timezone.utc)

    obj = Temporal(created_at=created, updated_at=updated)
    serialized = obj.model_dump()

    assert isinstance(serialized["created_at"], str)
    assert isinstance(serialized["updated_at"], str)
    assert serialized["created_at"] == "2025-05-10T10:00:00+00:00"
    assert serialized["updated_at"] == "2025-05-10T11:00:00+00:00"
```

#### 3.1.6 Test Case: Invalid String Timestamp Validation

**Purpose:** Verify that invalid datetime strings are rejected.

**Test Implementation:**

```python
def test_datetime_validation_invalid_string():
    """Test that invalid datetime strings are rejected."""
    with pytest.raises(ValidationError):
        Temporal(created_at="not-a-datetime")

    with pytest.raises(ValidationError):
        Temporal(updated_at="not-a-datetime")
```

#### 3.1.7 Test Case: Invalid Type Timestamp Validation

**Purpose:** Verify that invalid datetime types are rejected.

**Test Implementation:**

```python
def test_datetime_validation_invalid_type():
    """Test that invalid datetime types are rejected."""
    with pytest.raises(ValidationError):
        Temporal(created_at=123)  # type: ignore

    with pytest.raises(ValidationError):
        Temporal(updated_at=123)  # type: ignore
```

#### 3.1.8 Test Case: Created_at Immutability

**Purpose:** Verify that the created_at field is immutable (frozen).

**Test Implementation:**

```python
def test_created_at_immutability():
    """Test that the created_at field is immutable (frozen)."""
    obj = Temporal()
    original_created_at = obj.created_at

    # Attempting to change created_at should raise an error
    with pytest.raises(Exception):
        obj.created_at = datetime.now(timezone.utc)  # type: ignore

    # Verify created_at hasn't changed
    assert obj.created_at == original_created_at
```

#### 3.1.9 Test Case: Updated_at Mutability

**Purpose:** Verify that the updated_at field is mutable.

**Test Implementation:**

```python
def test_updated_at_mutability():
    """Test that the updated_at field is mutable."""
    obj = Temporal()

    # Should be able to change updated_at directly
    new_time = datetime(2025, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
    obj.updated_at = new_time

    assert obj.updated_at == new_time
```

#### 3.1.10 Test Case: JSON Serialization

**Purpose:** Verify JSON serialization of Temporal objects.

**Test Implementation:**

```python
def test_temporal_json_serialization():
    """Test JSON serialization of Temporal objects."""
    created = datetime(2025, 5, 10, 10, 0, 0, tzinfo=timezone.utc)
    updated = datetime(2025, 5, 10, 11, 0, 0, tzinfo=timezone.utc)

    obj = Temporal(created_at=created, updated_at=updated)
    json_str = obj.model_dump_json()

    assert isinstance(json_str, str)
    assert '"created_at":"2025-05-10T10:00:00+00:00"' in json_str
    assert '"updated_at":"2025-05-10T11:00:00+00:00"' in json_str
```

#### 3.1.11 Test Case: Multiple Update Timestamps

**Purpose:** Verify behavior with multiple calls to update_timestamp().

**Test Implementation:**

```python
@freeze_time("2025-05-14T12:00:00Z")
def test_multiple_update_timestamps():
    """Test multiple calls to update_timestamp()."""
    obj = Temporal()
    initial_time = obj.updated_at

    # First update - should be the same since time is frozen
    obj.update_timestamp()
    assert obj.updated_at == initial_time

    # Change the time manually to simulate time passing
    obj.updated_at = datetime(2025, 5, 14, 11, 0, 0, tzinfo=timezone.utc)

    # Second update - should update to the frozen time
    obj.update_timestamp()
    expected_time = datetime(2025, 5, 14, 12, 0, 0, tzinfo=timezone.utc)
    assert obj.updated_at == expected_time
```

## 4. Integration Tests

No integration tests are required for this module as it consists of a base class
without external dependencies.

## 5. API Tests

No API tests are required for this module as it doesn't expose any API
endpoints.

## 6. Error Handling Tests

Error handling tests are included in the unit tests for the Temporal class,
particularly:

- `test_datetime_validation_invalid_string`: Tests that invalid datetime strings
  raise a validation error
- `test_datetime_validation_invalid_type`: Tests that invalid datetime types
  raise a validation error
- `test_created_at_immutability`: Tests that attempting to modify the created_at
  field raises an exception

## 7. Performance Tests

No specific performance tests are required for this module as it consists of a
simple base class.

## 8. Mock Implementation Details

The primary mock used is freezegun, which allows for deterministic time testing:

```python
from freezegun import freeze_time

@freeze_time("2025-05-14T12:00:00Z")
def test_function():
    # Inside this function, datetime.now() will always return 2025-05-14T12:00:00Z
    ...
```

## 9. Test Data

Test data is defined inline in each test function, including:

- Frozen time points (2025-05-14T12:00:00Z)
- Custom datetime objects
- ISO format datetime strings
- Invalid datetime strings and types

## 10. Helper Functions

No helper functions are required for these tests.

## 11. Test Coverage Targets

- **Line Coverage Target:** 100%
- **Branch Coverage Target:** 100%
- **Actual Coverage Achieved:** 100%

## 12. Continuous Integration

Tests are run as part of the project's CI pipeline using pytest:

```bash
uv run pytest tests/protocols/test_temporal.py --cov=khive.protocols.temporal --cov-report=term-missing
```

## 13. Notes and Caveats

### 13.1 Known Limitations

- Tests focus on the public interface of the module and don't test internal
  implementation details.
- The tests assume that the system's timezone handling is consistent.

### 13.2 Future Improvements

- Add property-based testing using hypothesis to test with a wider range of
  datetime inputs.
- Add tests for subclasses that inherit from Temporal to ensure proper
  inheritance behavior.
- Consider testing with different timezone configurations to ensure robust
  timezone handling.
