---
title: Test Implementation for Embedable Protocol
by: khive-implementer
created: 2025-05-14
updated: 2025-05-14
version: 1.0
doc_type: TI
output_subdir: ti
description: Detailed test implementation for the Embedable protocol in khive
date: 2025-05-14
---

# Test Implementation Plan: Embedable Protocol

## 1. Overview

### 1.1 Component Under Test

The Embedable protocol (`khive.protocols.embedable`) provides a standard
interface for objects that can be embedded into vector spaces. This protocol is
fundamental for AI and machine learning applications within khive, enabling
objects to be represented as vectors in embedding spaces for similarity
comparisons, clustering, and other vector operations.

### 1.2 Test Approach

The test approach will primarily focus on unit testing, with comprehensive
coverage of:

- The Embedable base class and its methods
- Field validators
- Helper functions
- Edge cases and error handling

We'll use mocks to isolate tests from external dependencies such as embedding
endpoints.

### 1.3 Key Testing Goals

- Verify the Embedable base class functionality works as expected
- Ensure the embedding validator correctly handles various input types
- Test the embedding generation flow with mocked endpoints
- Verify helper functions correctly parse different embedding response formats
- Achieve >80% test coverage for the module

## 2. Test Environment

### 2.1 Test Framework

```
pytest
pytest-asyncio  # For testing async functions
pytest-mock     # For mocking
pytest-cov      # For coverage reporting
```

### 2.2 Mock Framework

```
unittest.mock
pytest-mock
```

### 2.3 Test Database

Not applicable for this protocol test suite.

## 3. Unit Tests

### 3.1 Test Suite: Embedable Base Class

#### 3.1.1 Test Case: Initialization

**Purpose:** Verify that Embedable initializes correctly with default and custom
values.

**Test Implementation:**

```python
def test_embedable_default_initialization():
    """Test that Embedable initializes with default values."""
    obj = Embedable()
    assert obj.content is None
    assert obj.embedding == []
    assert obj.n_dim == 0


def test_embedable_custom_initialization_content():
    """Test that Embedable accepts custom content."""
    obj = Embedable(content="test content")
    assert obj.content == "test content"
    assert obj.embedding == []
    assert obj.n_dim == 0


def test_embedable_custom_initialization_embedding():
    """Test that Embedable accepts custom embedding."""
    embedding = [0.1, 0.2, 0.3]
    obj = Embedable(embedding=embedding)
    assert obj.content is None
    assert obj.embedding == embedding
    assert obj.n_dim == 3


def test_embedable_custom_initialization_both():
    """Test that Embedable accepts both custom content and embedding."""
    embedding = [0.1, 0.2, 0.3]
    obj = Embedable(content="test content", embedding=embedding)
    assert obj.content == "test content"
    assert obj.embedding == embedding
    assert obj.n_dim == 3
```

#### 3.1.2 Test Case: n_dim Property

**Purpose:** Verify that the n_dim property returns the correct embedding
dimension.

**Test Implementation:**

```python
def test_embedable_n_dim_empty():
    """Test that n_dim returns 0 for empty embedding."""
    obj = Embedable()
    assert obj.n_dim == 0


def test_embedable_n_dim_with_embedding():
    """Test that n_dim returns the correct dimension for non-empty embedding."""
    obj = Embedable(embedding=[0.1, 0.2, 0.3, 0.4])
    assert obj.n_dim == 4
```

#### 3.1.3 Test Case: _parse_embedding Validator

**Purpose:** Verify that the _parse_embedding validator correctly handles
various input types.

**Test Implementation:**

```python
def test_parse_embedding_none():
    """Test that _parse_embedding returns empty list for None."""
    result = Embedable._parse_embedding(None)
    assert result == []


def test_parse_embedding_valid_string():
    """Test that _parse_embedding correctly parses valid JSON string."""
    result = Embedable._parse_embedding('[0.1, 0.2, 0.3]')
    assert result == [0.1, 0.2, 0.3]


def test_parse_embedding_invalid_string():
    """Test that _parse_embedding raises ValueError for invalid JSON string."""
    with pytest.raises(ValueError, match="Invalid embedding string"):
        Embedable._parse_embedding('not a valid json')


def test_parse_embedding_valid_list():
    """Test that _parse_embedding correctly parses valid list."""
    result = Embedable._parse_embedding([0.1, 0.2, 0.3])
    assert result == [0.1, 0.2, 0.3]


def test_parse_embedding_list_with_non_floats():
    """Test that _parse_embedding converts non-float list items to floats."""
    result = Embedable._parse_embedding([1, 2, 3])
    assert result == [1.0, 2.0, 3.0]


def test_parse_embedding_invalid_list():
    """Test that _parse_embedding raises ValueError for list with non-convertible items."""
    with pytest.raises(ValueError, match="Invalid embedding list"):
        Embedable._parse_embedding([0.1, "not a number", 0.3])


def test_parse_embedding_invalid_type():
    """Test that _parse_embedding raises ValueError for invalid types."""
    with pytest.raises(ValueError, match="Invalid embedding type"):
        Embedable._parse_embedding(123)  # type: ignore
```

### 3.2 Test Suite: Embedable Methods

#### 3.2.1 Test Case: create_content Method

**Purpose:** Verify that the create_content method returns the content
attribute.

**Test Implementation:**

```python
def test_create_content():
    """Test that create_content returns the content attribute."""
    obj = Embedable(content="test content")
    assert obj.create_content() == "test content"


def test_create_content_none():
    """Test that create_content returns None when content is None."""
    obj = Embedable()
    assert obj.create_content() is None
```

#### 3.2.2 Test Case: generate_embedding Method

**Purpose:** Verify that the generate_embedding method correctly calls the
endpoint and sets the embedding.

**Setup:**

```python
class MockEndpoint:
    """Mock endpoint for testing."""

    def __init__(self, return_value):
        self.return_value = return_value
        self.called_with = None

    async def call(self, params):
        self.called_with = params
        return self.return_value


class TestEmbedable(Embedable):
    """Test implementation of Embedable with custom embed_endpoint."""

    embed_endpoint = None  # Will be set in tests
```

**Test Implementation:**

```python
@pytest.mark.asyncio
async def test_generate_embedding():
    """Test that generate_embedding calls endpoint and sets embedding."""
    # Arrange
    mock_endpoint = MockEndpoint(return_value=[0.1, 0.2, 0.3])
    TestEmbedable.embed_endpoint = mock_endpoint

    obj = TestEmbedable(content="test content")

    # Act
    result = await obj.generate_embedding()

    # Assert
    assert result is obj  # Returns self
    assert obj.embedding == [0.1, 0.2, 0.3]
    assert mock_endpoint.called_with == {"input": "test content"}


@pytest.mark.asyncio
async def test_generate_embedding_custom_content():
    """Test that generate_embedding uses create_content result."""
    # Arrange
    mock_endpoint = MockEndpoint(return_value=[0.1, 0.2, 0.3])

    class CustomContentEmbedable(Embedable):
        embed_endpoint = mock_endpoint

        def create_content(self):
            return "custom content"

    obj = CustomContentEmbedable(content="original content")

    # Act
    result = await obj.generate_embedding()

    # Assert
    assert result is obj
    assert obj.embedding == [0.1, 0.2, 0.3]
    assert mock_endpoint.called_with == {"input": "custom content"}


@pytest.mark.asyncio
async def test_generate_embedding_default_endpoint(monkeypatch):
    """Test that generate_embedding uses default endpoint when class endpoint is None."""
    # Arrange
    mock_default_endpoint = MockEndpoint(return_value=[0.1, 0.2, 0.3])

    def mock_get_default_embed_endpoint():
        return mock_default_endpoint

    monkeypatch.setattr(
        "khive.protocols.embedable._get_default_embed_endpoint",
        mock_get_default_embed_endpoint
    )

    obj = Embedable(content="test content")

    # Act
    result = await obj.generate_embedding()

    # Assert
    assert result is obj
    assert obj.embedding == [0.1, 0.2, 0.3]
    assert mock_default_endpoint.called_with == {"input": "test content"}
```

### 3.3 Test Suite: Helper Functions

#### 3.3.1 Test Case: _parse_embedding_response Function

**Purpose:** Verify that _parse_embedding_response correctly extracts embeddings
from various response formats.

**Setup:**

```python
class MockData:
    """Mock data class with embedding attribute."""

    def __init__(self, embedding):
        self.embedding = embedding


class MockResponse(BaseModel):
    """Mock response model with data attribute."""

    data: list[MockData]
```

**Test Implementation:**

```python
def test_parse_embedding_response_basemodel():
    """Test _parse_embedding_response with BaseModel input."""
    # Arrange
    mock_data = MockData(embedding=[0.1, 0.2, 0.3])
    mock_response = MockResponse(data=[mock_data])

    # Act
    result = _parse_embedding_response(mock_response)

    # Assert
    assert result == [0.1, 0.2, 0.3]


def test_parse_embedding_response_list_of_floats():
    """Test _parse_embedding_response with list of floats."""
    # Arrange
    embedding = [0.1, 0.2, 0.3]

    # Act
    result = _parse_embedding_response(embedding)

    # Assert
    assert result == embedding


def test_parse_embedding_response_list_with_dict():
    """Test _parse_embedding_response with list containing a dict."""
    # Arrange
    embedding = [{"embedding": [0.1, 0.2, 0.3]}]

    # Act
    result = _parse_embedding_response(embedding)

    # Assert
    assert result == [0.1, 0.2, 0.3]


def test_parse_embedding_response_dict_data_format():
    """Test _parse_embedding_response with dict in data format."""
    # Arrange
    response = {
        "data": [
            {"embedding": [0.1, 0.2, 0.3]}
        ]
    }

    # Act
    result = _parse_embedding_response(response)

    # Assert
    assert result == [0.1, 0.2, 0.3]


def test_parse_embedding_response_dict_embedding_format():
    """Test _parse_embedding_response with dict in embedding format."""
    # Arrange
    response = {"embedding": [0.1, 0.2, 0.3]}

    # Act
    result = _parse_embedding_response(response)

    # Assert
    assert result == [0.1, 0.2, 0.3]


def test_parse_embedding_response_passthrough():
    """Test _parse_embedding_response passes through unrecognized formats."""
    # Arrange
    response = "not a recognized format"

    # Act
    result = _parse_embedding_response(response)

    # Assert
    assert result == response
```

#### 3.3.2 Test Case: _get_default_embed_endpoint Function

**Purpose:** Verify that _get_default_embed_endpoint returns the correct
endpoint based on settings.

**Test Implementation:**

```python
def test_get_default_embed_endpoint_openai(monkeypatch):
    """Test _get_default_embed_endpoint with openai provider."""
    # Arrange
    class MockSettings:
        DEFAULT_EMBEDDING_PROVIDER = "openai"
        DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"

    class MockOpenaiEmbedEndpoint:
        def __init__(self, model):
            self.model = model

    monkeypatch.setattr("khive.protocols.embedable.settings", MockSettings())
    monkeypatch.setattr(
        "khive.protocols.embedable.OpenaiEmbedEndpoint",
        MockOpenaiEmbedEndpoint
    )

    # Act
    result = _get_default_embed_endpoint()

    # Assert
    assert isinstance(result, MockOpenaiEmbedEndpoint)
    assert result.model == "text-embedding-3-small"


def test_get_default_embed_endpoint_unsupported(monkeypatch):
    """Test _get_default_embed_endpoint with unsupported provider."""
    # Arrange
    class MockSettings:
        DEFAULT_EMBEDDING_PROVIDER = "unsupported"
        DEFAULT_EMBEDDING_MODEL = "model"

    monkeypatch.setattr("khive.protocols.embedable.settings", MockSettings())

    # Act & Assert
    with pytest.raises(ValueError, match="Unsupported embedding provider"):
        _get_default_embed_endpoint()
```

## 4. Integration Tests

Not applicable for this protocol test suite as we're focusing on unit testing
the protocol itself.

## 5. API Tests

Not applicable for this protocol test suite.

## 6. Error Handling Tests

### 6.1 Test Suite: Embedable Error Handling

```python
@pytest.mark.asyncio
async def test_generate_embedding_endpoint_error():
    """Test that generate_embedding handles endpoint errors."""
    # Arrange
    class ErrorEndpoint:
        async def call(self, params):
            raise ValueError("Endpoint error")

    class TestEmbedable(Embedable):
        embed_endpoint = ErrorEndpoint()

    obj = TestEmbedable(content="test content")

    # Act & Assert
    with pytest.raises(ValueError, match="Endpoint error"):
        await obj.generate_embedding()


def test_embedable_invalid_initialization():
    """Test that Embedable initialization with invalid embedding raises error."""
    with pytest.raises(ValueError):
        Embedable(embedding="not a valid embedding")
```

## 7. Performance Tests

Not applicable for this protocol test suite.

## 8. Mock Implementation Details

```python
class MockEndpoint:
    """Mock endpoint for testing."""

    def __init__(self, return_value):
        self.return_value = return_value
        self.called_with = None

    async def call(self, params):
        self.called_with = params
        return self.return_value


class MockData:
    """Mock data class with embedding attribute."""

    def __init__(self, embedding):
        self.embedding = embedding


class MockResponse(BaseModel):
    """Mock response model with data attribute."""

    data: list[MockData]


class MockSettings:
    """Mock settings for testing."""

    DEFAULT_EMBEDDING_PROVIDER = "openai"
    DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
```

## 9. Test Data

```python
# Sample embeddings of different dimensions
sample_embeddings = {
    "empty": [],
    "small": [0.1, 0.2, 0.3],
    "medium": [0.1, 0.2, 0.3, 0.4, 0.5],
    "large": [0.1 * i for i in range(1, 101)]  # 100-dimensional
}

# Sample response formats
sample_responses = {
    "openai_format": {
        "data": [
            {"embedding": [0.1, 0.2, 0.3]}
        ]
    },
    "direct_embedding": [0.1, 0.2, 0.3],
    "embedding_dict": {"embedding": [0.1, 0.2, 0.3]},
    "list_with_dict": [{"embedding": [0.1, 0.2, 0.3]}]
}
```

## 10. Helper Functions

```python
def create_mock_response(embedding_data):
    """Create a mock response with the given embedding data."""
    mock_data = MockData(embedding=embedding_data)
    return MockResponse(data=[mock_data])


def assert_embeddings_equal(embedding1, embedding2):
    """Assert that two embeddings are equal, with floating point tolerance."""
    assert len(embedding1) == len(embedding2)
    for a, b in zip(embedding1, embedding2):
        assert pytest.approx(a) == b
```

## 11. Test Coverage Targets

- **Line Coverage Target:** 90%
- **Branch Coverage Target:** 85%
- **Critical Functions:**
  - `_parse_embedding` validator: 100% coverage
  - `generate_embedding` method: 100% coverage
  - `_parse_embedding_response` function: 100% coverage

## 12. Continuous Integration

The tests will be run as part of the project's CI pipeline, which is already set
up to run pytest with coverage reporting.

## 13. Notes and Caveats

### 13.1 Known Limitations

- The tests mock the embedding endpoints rather than testing against actual
  embedding providers.
- Some edge cases in embedding response parsing might not be covered if they're
  not encountered in practice.

### 13.2 Future Improvements

- Add property-based testing for more thorough validation of embedding parsing.
- Consider adding integration tests with actual embedding providers in a
  separate test suite.
- Expand test coverage to include more complex subclasses of Embedable.
