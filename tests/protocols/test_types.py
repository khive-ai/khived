"""
Tests for khive.protocols.types module.
"""

import pytest
from pydantic import BaseModel, ValidationError

from khive.protocols.types import (
    Embedding,
    ExecutionStatus,
    Execution,
    Log,
    Metadata,
)


# --- Tests for Embedding type ---
def test_embedding_type():
    """Test that Embedding is a list of floats."""
    # Valid embeddings
    valid_embedding: Embedding = [0.1, 0.2, 0.3]
    assert isinstance(valid_embedding, list)
    assert all(isinstance(x, float) for x in valid_embedding)

    # Empty embedding is valid
    empty_embedding: Embedding = []
    assert isinstance(empty_embedding, list)


# --- Tests for Metadata type ---
def test_metadata_type():
    """Test that Metadata is a dict."""
    # Valid metadata
    valid_metadata: Metadata = {"key1": "value1", "key2": 123}
    assert isinstance(valid_metadata, dict)

    # Empty metadata is valid
    empty_metadata: Metadata = {}
    assert isinstance(empty_metadata, dict)


# --- Tests for ExecutionStatus enum ---
def test_execution_status_enum():
    """Test the ExecutionStatus enum values."""
    assert ExecutionStatus.PENDING.value == "pending"
    assert ExecutionStatus.PROCESSING.value == "processing"
    assert ExecutionStatus.COMPLETED.value == "completed"
    assert ExecutionStatus.FAILED.value == "failed"

    # Test enum conversion from string
    assert ExecutionStatus("pending") == ExecutionStatus.PENDING
    assert ExecutionStatus("processing") == ExecutionStatus.PROCESSING
    assert ExecutionStatus("completed") == ExecutionStatus.COMPLETED
    assert ExecutionStatus("failed") == ExecutionStatus.FAILED

    # Test invalid enum value
    with pytest.raises(ValueError):
        ExecutionStatus("invalid_status")


# --- Tests for Execution class ---
def test_execution_default_values():
    """Test the default values for Execution."""
    execution = Execution()
    assert execution.duration is None
    assert execution.response is None
    assert execution.status == ExecutionStatus.PENDING
    assert execution.error is None


def test_execution_with_values():
    """Test creating an Execution with specific values."""
    execution = Execution(
        duration=1.5,
        response={"result": "success"},
        status=ExecutionStatus.COMPLETED,
        error=None,
    )
    assert execution.duration == 1.5
    assert execution.response == {"result": "success"}
    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.error is None


def test_execution_with_pydantic_model_response():
    """Test that a Pydantic model can be used as a response and is converted to dict."""
    class SampleResponse(BaseModel):
        field1: str
        field2: int

    sample_response = SampleResponse(field1="test", field2=123)
    
    execution = Execution(response=sample_response)
    
    # The response should be converted to a dict
    assert isinstance(execution.response, dict)
    assert execution.response == {"field1": "test", "field2": 123}


def test_execution_status_serialization():
    """Test that ExecutionStatus is serialized to its string value."""
    execution = Execution(status=ExecutionStatus.COMPLETED)
    
    # Convert to dict to test serialization
    serialized = execution.model_dump()
    assert serialized["status"] == "completed"


def test_execution_invalid_status():
    """Test that an invalid status raises a validation error."""
    with pytest.raises(ValidationError):
        Execution(status="invalid_status")


# --- Tests for Log class ---
def test_log_required_fields():
    """Test that Log requires certain fields."""
    # Missing required fields should raise ValidationError
    with pytest.raises(ValidationError):
        Log()  # Missing id, created_at, updated_at, event_type, status


def test_log_with_valid_values():
    """Test creating a Log with valid values."""
    log = Log(
        id="log123",
        created_at="2025-05-14T12:00:00Z",
        updated_at="2025-05-14T12:01:00Z",
        event_type="test_event",
        content="Test content",
        embedding=[0.1, 0.2, 0.3],
        duration=1.5,
        status="completed",
        error=None,
        sha256="abc123",
    )
    
    assert log.id == "log123"
    assert log.created_at == "2025-05-14T12:00:00Z"
    assert log.updated_at == "2025-05-14T12:01:00Z"
    assert log.event_type == "test_event"
    assert log.content == "Test content"
    assert log.embedding == [0.1, 0.2, 0.3]
    assert log.duration == 1.5
    assert log.status == "completed"
    assert log.error is None
    assert log.sha256 == "abc123"


def test_log_default_values():
    """Test the default values for Log's optional fields."""
    log = Log(
        id="log123",
        created_at="2025-05-14T12:00:00Z",
        updated_at="2025-05-14T12:01:00Z",
        event_type="test_event",
        status="completed",
    )
    
    assert log.content is None
    assert log.embedding == []
    assert log.duration is None
    assert log.error is None
    assert log.sha256 is None


def test_log_with_empty_embedding():
    """Test that Log accepts an empty embedding."""
    log = Log(
        id="log123",
        created_at="2025-05-14T12:00:00Z",
        updated_at="2025-05-14T12:01:00Z",
        event_type="test_event",
        status="completed",
        embedding=[],
    )
    
    assert log.embedding == []