"""
Tests for khive.protocols.identifiable module.
"""

import uuid
import pytest
from pydantic import ValidationError

from khive.protocols.identifiable import Identifiable


# --- Tests for Identifiable class ---
def test_identifiable_default_id():
    """Test that Identifiable generates a default UUID."""
    obj = Identifiable()
    assert isinstance(obj.id, uuid.UUID)
    assert obj.id is not None


def test_identifiable_custom_id():
    """Test that Identifiable accepts a custom UUID."""
    custom_id = uuid.uuid4()
    obj = Identifiable(id=custom_id)
    assert obj.id == custom_id


def test_identifiable_string_id():
    """Test that Identifiable accepts a string UUID and converts it."""
    id_str = "123e4567-e89b-12d3-a456-426614174000"
    obj = Identifiable(id=id_str)
    assert isinstance(obj.id, uuid.UUID)
    assert str(obj.id) == id_str


def test_identifiable_id_serialization():
    """Test that the id field is serialized to a string."""
    obj = Identifiable()
    serialized = obj.model_dump()
    assert isinstance(serialized["id"], str)
    assert uuid.UUID(serialized["id"]) == obj.id


def test_identifiable_id_validation_invalid_string():
    """Test that invalid UUID strings are rejected."""
    with pytest.raises(ValidationError):
        Identifiable(id="not-a-uuid")


def test_identifiable_id_validation_invalid_type():
    """Test that invalid UUID types are rejected."""
    with pytest.raises(ValidationError):
        Identifiable(id=123)  # type: ignore


def test_identifiable_id_immutability():
    """Test that the id field is immutable (frozen)."""
    obj = Identifiable()
    original_id = obj.id
    
    # Attempting to change the id should raise an error
    with pytest.raises(Exception):
        obj.id = uuid.uuid4()  # type: ignore
    
    # Verify the id hasn't changed
    assert obj.id == original_id


def test_identifiable_model_config():
    """Test the model configuration settings."""
    # Test extra="forbid"
    with pytest.raises(ValidationError):
        Identifiable(extra_field="value")  # type: ignore
    
    # Test that valid initialization works
    obj = Identifiable()
    assert obj is not None


def test_identifiable_json_serialization():
    """Test JSON serialization of Identifiable objects."""
    obj = Identifiable()
    json_str = obj.model_dump_json()
    assert isinstance(json_str, str)
    assert f'"id":"{obj.id}"' in json_str


def test_identifiable_dict_serialization():
    """Test dict serialization of Identifiable objects."""
    obj = Identifiable()
    dict_obj = obj.model_dump()
    assert isinstance(dict_obj, dict)
    assert "id" in dict_obj
    assert dict_obj["id"] == str(obj.id)