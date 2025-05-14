"""
Tests for khive.protocols.embedable module.
"""

import pytest
from khive.protocols.embedable import (
    Embedable,
    _get_default_embed_endpoint,
    _parse_embedding_response,
)
from pydantic import BaseModel


# --- Mock classes for testing ---
class MockData(BaseModel):
    """Mock data class with embedding attribute."""

    embedding: list[float]


class MockResponse(BaseModel):
    """Mock response model with data attribute."""

    data: list[MockData]

    model_config = {"arbitrary_types_allowed": True}


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


# --- Tests for Embedable base class ---
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


# --- Tests for n_dim property ---
def test_embedable_n_dim_empty():
    """Test that n_dim returns 0 for empty embedding."""
    obj = Embedable()
    assert obj.n_dim == 0


def test_embedable_n_dim_with_embedding():
    """Test that n_dim returns the correct dimension for non-empty embedding."""
    obj = Embedable(embedding=[0.1, 0.2, 0.3, 0.4])
    assert obj.n_dim == 4


# --- Tests for _parse_embedding validator ---
def test_parse_embedding_none():
    """Test that _parse_embedding returns empty list for None."""
    result = Embedable._parse_embedding(None)
    assert result == []


def test_parse_embedding_valid_string():
    """Test that _parse_embedding correctly parses valid JSON string."""
    result = Embedable._parse_embedding("[0.1, 0.2, 0.3]")
    assert result == [0.1, 0.2, 0.3]


def test_parse_embedding_invalid_string():
    """Test that _parse_embedding raises ValueError for invalid JSON string."""
    with pytest.raises(ValueError, match="Invalid embedding string"):
        Embedable._parse_embedding("not a valid json")


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


# --- Tests for create_content method ---
def test_create_content():
    """Test that create_content returns the content attribute."""
    obj = Embedable(content="test content")
    assert obj.create_content() == "test content"


def test_create_content_none():
    """Test that create_content returns None when content is None."""
    obj = Embedable()
    assert obj.create_content() is None


# --- Tests for generate_embedding method ---
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
        mock_get_default_embed_endpoint,
    )

    obj = Embedable(content="test content")

    # Act
    result = await obj.generate_embedding()

    # Assert
    assert result is obj
    assert obj.embedding == [0.1, 0.2, 0.3]
    assert mock_default_endpoint.called_with == {"input": "test content"}


@pytest.mark.asyncio
async def test_generate_embedding_endpoint_error():
    """Test that generate_embedding handles endpoint errors."""

    # Arrange
    class ErrorEndpoint:
        async def call(self, _):
            raise ValueError("Endpoint error")

    class TestErrorEmbedable(Embedable):
        embed_endpoint = ErrorEndpoint()

    obj = TestErrorEmbedable(content="test content")

    # Act & Assert
    with pytest.raises(ValueError, match="Endpoint error"):
        await obj.generate_embedding()


# --- Tests for _parse_embedding_response function ---
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
    response = {"data": [{"embedding": [0.1, 0.2, 0.3]}]}

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


def test_get_default_embed_endpoint_unsupported(monkeypatch):
    """Test _get_default_embed_endpoint with unsupported provider."""

    # Arrange
    class MockSettings:
        KHIVE_EMBEDDING_PROVIDER = "unsupported"
        KHIVE_EMBEDDING_MODEL = "model"

    monkeypatch.setattr("khive.protocols.embedable.settings", MockSettings())

    # Act & Assert
    with pytest.raises(ValueError, match="Unsupported embedding provider"):
        _get_default_embed_endpoint()


# --- Tests for error handling ---
def test_embedable_invalid_initialization():
    """Test that Embedable initialization with invalid embedding raises error."""
    with pytest.raises(ValueError):
        Embedable(embedding="not a valid embedding")
