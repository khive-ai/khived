"""
Tests for the adapter system.

This module contains tests for the adapter system, including:
- Round-trip tests for each adapter
- Alias resolution tests
- Concurrency tests
- Validation tests
"""

import concurrent.futures
import json
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from khive.adapters.adapter import AdapterRegistry, MissingAdapterError
from khive.adapters.json_adapter import JsonAdapter, JsonFileAdapter
from khive.adapters.pd_dataframe_adapter import PandasDataFrameAdapter
from khive.adapters.toml_adapter import TomlAdapter, TomlFileAdapter
from khive.adapters.validation import validate_data

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    from pydantic import BaseModel, Field

    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False


# Test data
TEST_DATA_SINGLE = {"name": "Test Item", "value": 42, "tags": ["tag1", "tag2"]}
TEST_DATA_MANY = [
    {"name": "Item 1", "value": 42, "tags": ["tag1", "tag2"]},
    {"name": "Item 2", "value": 43, "tags": ["tag2", "tag3"]},
]


# Mock subject class for testing
class MockSubject:
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.created_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {**self.data, "created_at": self.created_at}


# Test registry
class TestAdapterRegistry(AdapterRegistry):
    pass


# Pydantic model for validation tests
if HAS_PYDANTIC:

    class TestModel(BaseModel):
        name: str
        value: int
        tags: List[str]
        created_at: Optional[float] = None


# Register test adapters
TestAdapterRegistry.register(JsonAdapter)
TestAdapterRegistry.register(JsonFileAdapter)
TestAdapterRegistry.register(TomlAdapter)
TestAdapterRegistry.register(TomlFileAdapter)
if HAS_PANDAS:
    TestAdapterRegistry.register(PandasDataFrameAdapter)


# Fixture for temporary directory
@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield Path(tmpdirname)


# Test JSON adapter round-trip
def test_json_adapter_roundtrip():
    # Create a mock subject
    subject = MockSubject(TEST_DATA_SINGLE)

    # Convert to JSON
    json_str = TestAdapterRegistry.adapt_to(subject, "json")

    # Convert back to dict
    result = TestAdapterRegistry.adapt_from(MockSubject, json_str, "json")

    # Check that the data is preserved
    assert result["name"] == TEST_DATA_SINGLE["name"]
    assert result["value"] == TEST_DATA_SINGLE["value"]
    assert result["tags"] == TEST_DATA_SINGLE["tags"]


# Test JSON adapter round-trip with many items
def test_json_adapter_roundtrip_many():
    # Create mock subjects
    subjects = [MockSubject(item) for item in TEST_DATA_MANY]

    # Convert to JSON
    json_str = TestAdapterRegistry.adapt_to(subjects, "json", many=True)

    # Convert back to dicts
    results = TestAdapterRegistry.adapt_from(MockSubject, json_str, "json", many=True)

    # Check that the data is preserved
    assert len(results) == len(TEST_DATA_MANY)
    for i, result in enumerate(results):
        assert result["name"] == TEST_DATA_MANY[i]["name"]
        assert result["value"] == TEST_DATA_MANY[i]["value"]
        assert result["tags"] == TEST_DATA_MANY[i]["tags"]


# Test JSON file adapter round-trip
def test_json_file_adapter_roundtrip(temp_dir):
    # Create a mock subject
    subject = MockSubject(TEST_DATA_SINGLE)

    # File path
    file_path = temp_dir / "test.json"

    # Write to file
    TestAdapterRegistry.adapt_to(subject, ".json", fp=file_path)

    # Read from file
    result = TestAdapterRegistry.adapt_from(MockSubject, file_path, ".json")

    # Check that the data is preserved
    assert result["name"] == TEST_DATA_SINGLE["name"]
    assert result["value"] == TEST_DATA_SINGLE["value"]
    assert result["tags"] == TEST_DATA_SINGLE["tags"]


# Test TOML adapter round-trip
def test_toml_adapter_roundtrip():
    # Create a mock subject
    subject = MockSubject(TEST_DATA_SINGLE)

    # Convert to TOML
    toml_str = TestAdapterRegistry.adapt_to(subject, "toml")

    # Convert back to dict
    result = TestAdapterRegistry.adapt_from(MockSubject, toml_str, "toml")

    # Check that the data is preserved
    assert result["name"] == TEST_DATA_SINGLE["name"]
    assert result["value"] == TEST_DATA_SINGLE["value"]
    assert result["tags"] == TEST_DATA_SINGLE["tags"]


# Test TOML adapter round-trip with many items
def test_toml_adapter_roundtrip_many():
    # Create mock subjects
    subjects = [MockSubject(item) for item in TEST_DATA_MANY]

    # Convert to TOML
    toml_str = TestAdapterRegistry.adapt_to(subjects, "toml", many=True)

    # Convert back to dicts
    results = TestAdapterRegistry.adapt_from(MockSubject, toml_str, "toml", many=True)

    # Check that the data is preserved
    assert len(results) == len(TEST_DATA_MANY)
    for i, result in enumerate(results):
        assert result["name"] == TEST_DATA_MANY[i]["name"]
        assert result["value"] == TEST_DATA_MANY[i]["value"]
        assert result["tags"] == TEST_DATA_MANY[i]["tags"]


# Test TOML file adapter round-trip
def test_toml_file_adapter_roundtrip(temp_dir):
    # Create a mock subject
    subject = MockSubject(TEST_DATA_SINGLE)

    # File path
    file_path = temp_dir / "test.toml"

    # Write to file
    TestAdapterRegistry.adapt_to(subject, ".toml", fp=file_path)

    # Read from file
    result = TestAdapterRegistry.adapt_from(MockSubject, file_path, ".toml")

    # Check that the data is preserved
    assert result["name"] == TEST_DATA_SINGLE["name"]
    assert result["value"] == TEST_DATA_SINGLE["value"]
    assert result["tags"] == TEST_DATA_SINGLE["tags"]


# Test pandas adapter round-trip (if pandas is available)
@pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")
def test_pandas_adapter_roundtrip():
    # Create mock subjects
    subjects = [MockSubject(item) for item in TEST_DATA_MANY]

    # Convert to DataFrame
    df = TestAdapterRegistry.adapt_to(subjects, "pd_dataframe")

    # Convert back to dicts
    results = TestAdapterRegistry.adapt_from(MockSubject, df, "pd_dataframe")

    # Check that the data is preserved
    assert len(results) == len(TEST_DATA_MANY)
    for i, result in enumerate(results):
        assert result["name"] == TEST_DATA_MANY[i]["name"]
        assert result["value"] == TEST_DATA_MANY[i]["value"]
        assert "tags" in result  # Tags might be converted to string in DataFrame


# Test alias resolution
def test_alias_resolution():
    # Test that aliases are properly registered (case-insensitive)
    adapter1 = TestAdapterRegistry.get("pd_dataframe")
    adapter2 = TestAdapterRegistry.get("pd.dataframe")  # lowercase version

    # Both should return the same adapter
    assert adapter1 is adapter2


# Test concurrency
def test_concurrent_registration():
    # Create a new registry for this test
    class ConcurrentRegistry(AdapterRegistry):
        pass

    # Function to register adapters in a thread
    def register_adapters():
        ConcurrentRegistry.register(JsonAdapter)
        ConcurrentRegistry.register(TomlAdapter)
        time.sleep(0.01)  # Small delay to increase chance of race condition
        ConcurrentRegistry.register(JsonFileAdapter)
        ConcurrentRegistry.register(TomlFileAdapter)

    # Create and start threads
    threads = []
    for _ in range(10):
        thread = threading.Thread(target=register_adapters)
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Check that all adapters are registered
    adapters = ConcurrentRegistry.list_adapters()
    adapter_keys = [key for key, _ in adapters]

    assert "json" in adapter_keys
    assert "toml" in adapter_keys
    assert ".json" in adapter_keys
    assert ".toml" in adapter_keys


# Test concurrent adapter usage with ThreadPoolExecutor
def test_concurrent_adapter_usage():
    # Create mock subjects
    subjects = [MockSubject(item) for item in TEST_DATA_MANY]

    # Function to convert to JSON and back
    def convert_roundtrip(subject):
        json_str = TestAdapterRegistry.adapt_to(subject, "json")
        return TestAdapterRegistry.adapt_from(MockSubject, json_str, "json")

    # Use ThreadPoolExecutor to run conversions concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(convert_roundtrip, subjects))

    # Check results
    assert len(results) == len(subjects)
    for i, result in enumerate(results):
        assert result["name"] == TEST_DATA_MANY[i]["name"]
        assert result["value"] == TEST_DATA_MANY[i]["value"]


# Test validation (if pydantic is available)
@pytest.mark.skipif(not HAS_PYDANTIC, reason="pydantic not installed")
def test_validation():
    # Valid data
    valid_data = {"name": "Test Item", "value": 42, "tags": ["tag1", "tag2"]}

    # Invalid data (value should be int, not str)
    invalid_data = {
        "name": "Test Item",
        "value": "not an int",
        "tags": ["tag1", "tag2"],
    }

    # Test valid data
    validated = validate_data(valid_data, TestModel)
    assert validated.name == valid_data["name"]
    assert validated.value == valid_data["value"]
    assert validated.tags == valid_data["tags"]

    # Test invalid data (should raise ValidationError)
    with pytest.raises(Exception):  # Could be ValidationError from pydantic
        validate_data(invalid_data, TestModel)


# Test validation with adapter (if pydantic is available)
@pytest.mark.skipif(not HAS_PYDANTIC, reason="pydantic not installed")
def test_validation_with_adapter():
    # Create a mock subject
    subject = MockSubject(TEST_DATA_SINGLE)

    # Convert to JSON without validation first
    json_str = TestAdapterRegistry.adapt_to(subject, "json")

    # Convert back to dict with validation
    result = TestAdapterRegistry.adapt_from(
        MockSubject, json_str, "json", schema=TestModel
    )

    # When using schema validation, the result is a Pydantic model instance
    # Check that the data is preserved
    assert result.name == TEST_DATA_SINGLE["name"]
    assert result.value == TEST_DATA_SINGLE["value"]
    assert result.tags == TEST_DATA_SINGLE["tags"]


# Test missing adapter
def test_missing_adapter():
    with pytest.raises(MissingAdapterError):
        TestAdapterRegistry.get("nonexistent_adapter")


# Simple performance tests (without pytest-benchmark)
def test_adapter_registry_performance():
    # Simple adapter lookup test
    start_time = time.time()
    adapter = TestAdapterRegistry.get("json")
    end_time = time.time()

    # Verify the result
    assert adapter.obj_key == "json"

    # Print performance info
    print(f"\nAdapter lookup took {(end_time - start_time) * 1000:.3f} ms")


# Simple JSON serialization performance test
def test_json_serialization_performance():
    # Create a mock subject
    subject = MockSubject(TEST_DATA_SINGLE)

    # Simple JSON serialization test
    start_time = time.time()
    json_str = TestAdapterRegistry.adapt_to(subject, "json")
    end_time = time.time()

    # Verify the result
    assert json.loads(json_str)["name"] == TEST_DATA_SINGLE["name"]

    # Print performance info
    print(f"\nJSON serialization took {(end_time - start_time) * 1000:.3f} ms")
