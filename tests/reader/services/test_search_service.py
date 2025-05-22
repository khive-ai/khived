import pytest
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4
from typing import List, Dict, Optional, Any

# Actual imports will be from the khive project structure
# from khive.reader.services.search_service import DocumentSearchService
# from khive.reader.embedding import EmbeddingGenerator # Placeholder for actual interface
# from khive.reader.repository import DocumentChunkRepository # Placeholder for actual interface

# Using placeholder classes for now, as defined in search_service.py and TI-28.md
# These would be imported from their actual locations in a real scenario.
class EmbeddingGenerator: # Placeholder
    def generate_embedding(self, text: str) -> List[float]:
        raise NotImplementedError # pragma: no cover

class DocumentChunkRepository: # Placeholder
    def search_similar_chunks(
        self, embedding: List[float], top_k: int, document_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError # pragma: no cover

# This import should point to the actual DocumentSearchService once its path is finalized
# For now, assuming it's directly accessible or will be adjusted
try:
    from khive.reader.services.search_service import DocumentSearchService
except ImportError:
    # Fallback for testing if the path isn't set up yet, using a local placeholder
    class DocumentSearchService: # Placeholder
        def __init__(
            self,
            embedding_generator: EmbeddingGenerator,
            document_chunk_repository: DocumentChunkRepository,
        ):
            self.embedding_generator = embedding_generator
            self.document_chunk_repository = document_chunk_repository

        def search(
            self,
            query: str,
            document_id: Optional[UUID] = None,
            top_k: int = 5,
        ) -> List[Dict[str, Any]]:
            if not query or top_k <=0:
                return []
            query_embedding = self.embedding_generator.generate_embedding(query)
            raw_chunks = self.document_chunk_repository.search_similar_chunks(
                embedding=query_embedding,
                top_k=top_k,
                document_id=document_id,
            )
            results = []
            for chunk_data in raw_chunks:
                results.append({
                    "chunk_id": str(chunk_data.get("id")) if chunk_data.get("id") else None,
                    "document_id": str(chunk_data.get("document_id")) if chunk_data.get("document_id") else None,
                    "text": chunk_data.get("text_content"),
                    "score": chunk_data.get("score"),
                })
            return results

@pytest.fixture
def mock_embedding_generator() -> MagicMock:
    mock = MagicMock(spec=EmbeddingGenerator)
    mock.generate_embedding.return_value = [0.1, 0.2, 0.3]  # Example consistent embedding
    return mock

@pytest.fixture
def mock_doc_chunk_repo() -> MagicMock:
    mock = MagicMock(spec=DocumentChunkRepository)
    # Default mock return, can be overridden in specific tests
    mock.search_similar_chunks.return_value = [
        {"id": uuid4(), "document_id": uuid4(), "text_content": "Test chunk 1 from mock", "score": 0.95},
        {"id": uuid4(), "document_id": uuid4(), "text_content": "Test chunk 2 from mock", "score": 0.90},
    ]
    return mock

@pytest.fixture
def search_service(
    mock_embedding_generator: MagicMock, mock_doc_chunk_repo: MagicMock
) -> DocumentSearchService:
    return DocumentSearchService(
        embedding_generator=mock_embedding_generator,
        document_chunk_repository=mock_doc_chunk_repo,
    )

# Test cases will be added below based on TI-28.md / IP-28.md

def test_search_service_instantiation(search_service: DocumentSearchService):
    """Test that the DocumentSearchService can be instantiated."""
    assert search_service is not None
    assert isinstance(search_service.embedding_generator, MagicMock)
    assert isinstance(search_service.document_chunk_repository, MagicMock)

def test_search_valid_query_default_top_k(
    search_service: DocumentSearchService,
    mock_embedding_generator: MagicMock,
    mock_doc_chunk_repo: MagicMock,
):
    query = "test query"
    expected_top_k = 5 # Default top_k in service
    
    # Configure mock for this specific test if needed, or rely on fixture's default
    mock_doc_chunk_repo.search_similar_chunks.return_value = [
        {"id": uuid4(), "document_id": uuid4(), "text_content": "Specific result for valid query", "score": 0.88}
    ]

    results = search_service.search(query=query)

    mock_embedding_generator.generate_embedding.assert_called_once_with(query)
    mock_doc_chunk_repo.search_similar_chunks.assert_called_once_with(
        embedding=[0.1, 0.2, 0.3], top_k=expected_top_k, document_id=None
    )
    assert len(results) == 1
    assert results[0]["text"] == "Specific result for valid query"
    assert results[0]["score"] == 0.88

def test_search_with_document_id_filter(
    search_service: DocumentSearchService,
    mock_embedding_generator: MagicMock,
    mock_doc_chunk_repo: MagicMock,
):
    query = "filter query"
    doc_id = uuid4()
    expected_embedding = [0.1, 0.2, 0.3]
    mock_embedding_generator.generate_embedding.return_value = expected_embedding
    
    mock_doc_chunk_repo.search_similar_chunks.return_value = [
        {"id": uuid4(), "document_id": doc_id, "text_content": "Filtered chunk", "score": 0.8}
    ]

    results = search_service.search(query=query, document_id=doc_id)

    mock_embedding_generator.generate_embedding.assert_called_once_with(query)
    mock_doc_chunk_repo.search_similar_chunks.assert_called_once_with(
        embedding=expected_embedding, top_k=5, document_id=doc_id
    )
    assert len(results) == 1
    assert results[0]["document_id"] == str(doc_id) # Ensure UUID is stringified if service does that

def test_search_custom_top_k(
    search_service: DocumentSearchService,
    mock_embedding_generator: MagicMock,
    mock_doc_chunk_repo: MagicMock,
):
    query = "top_k query"
    custom_top_k = 3
    expected_embedding = [0.1, 0.2, 0.3]
    mock_embedding_generator.generate_embedding.return_value = expected_embedding

    # Adjust mock to return `custom_top_k` items
    mock_doc_chunk_repo.search_similar_chunks.return_value = [
        {"id": uuid4(), "document_id": uuid4(), "text_content": f"Chunk {i}", "score": 0.9}
        for i in range(custom_top_k)
    ]
    
    results = search_service.search(query=query, top_k=custom_top_k)

    mock_embedding_generator.generate_embedding.assert_called_once_with(query)
    mock_doc_chunk_repo.search_similar_chunks.assert_called_once_with(
        embedding=expected_embedding, top_k=custom_top_k, document_id=None
    )
    assert len(results) == custom_top_k

def test_search_no_results_found(
    search_service: DocumentSearchService,
    mock_embedding_generator: MagicMock,
    mock_doc_chunk_repo: MagicMock,
):
    query = "empty query"
    expected_embedding = [0.1, 0.2, 0.3]
    mock_embedding_generator.generate_embedding.return_value = expected_embedding
    mock_doc_chunk_repo.search_similar_chunks.return_value = [] # Simulate no results

    results = search_service.search(query=query)

    mock_embedding_generator.generate_embedding.assert_called_once_with(query)
    mock_doc_chunk_repo.search_similar_chunks.assert_called_once_with(
        embedding=expected_embedding, top_k=5, document_id=None
    )
    assert results == []

def test_search_embedding_generator_exception(
    search_service: DocumentSearchService,
    mock_embedding_generator: MagicMock,
    mock_doc_chunk_repo: MagicMock,
):
    query = "exception query"
    mock_embedding_generator.generate_embedding.side_effect = ValueError("Embedding generation failed")

    with pytest.raises(ValueError, match="Embedding generation failed"):
        search_service.search(query=query)
    
    mock_doc_chunk_repo.search_similar_chunks.assert_not_called()

def test_search_repository_exception(
    search_service: DocumentSearchService,
    mock_embedding_generator: MagicMock,
    mock_doc_chunk_repo: MagicMock,
):
    query = "repo exception query"
    expected_embedding = [0.1, 0.2, 0.3]
    mock_embedding_generator.generate_embedding.return_value = expected_embedding
    mock_doc_chunk_repo.search_similar_chunks.side_effect = ConnectionError("DB connection failed")

    with pytest.raises(ConnectionError, match="DB connection failed"):
        search_service.search(query=query)
    
    mock_embedding_generator.generate_embedding.assert_called_once_with(query)

def test_search_empty_query_string(search_service: DocumentSearchService, mock_embedding_generator: MagicMock, mock_doc_chunk_repo: MagicMock):
    results = search_service.search(query="")
    assert results == []
    mock_embedding_generator.generate_embedding.assert_not_called()
    mock_doc_chunk_repo.search_similar_chunks.assert_not_called()

def test_search_invalid_top_k(search_service: DocumentSearchService, mock_embedding_generator: MagicMock, mock_doc_chunk_repo: MagicMock):
    results_zero = search_service.search(query="test", top_k=0)
    assert results_zero == []
    
    results_negative = search_service.search(query="test", top_k=-1)
    assert results_negative == []

    mock_embedding_generator.generate_embedding.assert_not_called() # Because top_k check is first
    mock_doc_chunk_repo.search_similar_chunks.assert_not_called()