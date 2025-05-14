"""
Tests for khive.protocols.temporal module.
"""

from datetime import datetime, timezone

import pytest
from freezegun import freeze_time
from khive.protocols.temporal import Temporal
from pydantic import ValidationError


# --- Tests for Temporal class ---
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


def test_temporal_custom_initialization():
    """Test that Temporal accepts custom datetime objects."""
    created = datetime(2025, 5, 10, 10, 0, 0, tzinfo=timezone.utc)
    updated = datetime(2025, 5, 10, 11, 0, 0, tzinfo=timezone.utc)

    obj = Temporal(created_at=created, updated_at=updated)

    assert obj.created_at == created
    assert obj.updated_at == updated


def test_temporal_string_initialization():
    """Test that Temporal accepts ISO format strings and converts them to datetime."""
    created_str = "2025-05-10T10:00:00+00:00"
    updated_str = "2025-05-10T11:00:00+00:00"

    obj = Temporal(created_at=created_str, updated_at=updated_str)

    assert isinstance(obj.created_at, datetime)
    assert isinstance(obj.updated_at, datetime)
    assert obj.created_at == datetime(2025, 5, 10, 10, 0, 0, tzinfo=timezone.utc)
    assert obj.updated_at == datetime(2025, 5, 10, 11, 0, 0, tzinfo=timezone.utc)


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


def test_datetime_validation_invalid_string():
    """Test that invalid datetime strings are rejected."""
    with pytest.raises(ValidationError):
        Temporal(created_at="not-a-datetime")

    with pytest.raises(ValidationError):
        Temporal(updated_at="not-a-datetime")


def test_datetime_validation_invalid_type():
    """Test that invalid datetime types are rejected."""
    with pytest.raises(ValidationError):
        Temporal(created_at=123)  # type: ignore

    with pytest.raises(ValidationError):
        Temporal(updated_at=123)  # type: ignore


def test_created_at_immutability():
    """Test that the created_at field is immutable (frozen)."""
    obj = Temporal()
    original_created_at = obj.created_at

    # Attempting to change created_at should raise an error
    with pytest.raises(ValidationError):
        obj.created_at = datetime.now(timezone.utc)  # type: ignore

    # Verify created_at hasn't changed
    assert obj.created_at == original_created_at


def test_updated_at_mutability():
    """Test that the updated_at field is mutable."""
    obj = Temporal()

    # Should be able to change updated_at directly
    new_time = datetime(2025, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
    obj.updated_at = new_time

    assert obj.updated_at == new_time


def test_temporal_json_serialization():
    """Test JSON serialization of Temporal objects."""
    created = datetime(2025, 5, 10, 10, 0, 0, tzinfo=timezone.utc)
    updated = datetime(2025, 5, 10, 11, 0, 0, tzinfo=timezone.utc)

    obj = Temporal(created_at=created, updated_at=updated)
    json_str = obj.model_dump_json()

    assert isinstance(json_str, str)
    assert '"created_at":"2025-05-10T10:00:00+00:00"' in json_str
    assert '"updated_at":"2025-05-10T11:00:00+00:00"' in json_str


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
