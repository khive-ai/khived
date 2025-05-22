import pytest
import json
from click.testing import CliRunner # Though not used directly with argparse, kept for context if CLI structure changes
from unittest.mock import MagicMock, patch
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4


# Attempt to import the main CLI group/app and specific services to be mocked.
# Adjust paths based on actual project structure.
try:
    from khive.cli.khive_reader import main as khive_reader_main_entry # Assuming main() can be used or find the Click group
    # If khive_reader_main_entry is the argparse main(), we need the Click command group directly.
    # Let's assume khive_reader.py defines a Click command group, e.g., `reader_cli_group`
    # For now, we'll try to patch where DocumentSearchService is instantiated.
    # This requires knowing the module path used in khive_reader.py for DocumentSearchService.
    # Based on previous diff, it's 'khive.cli.khive_reader.DocumentSearchService'
except ImportError:
    khive_reader_main_entry = None # Fallback
    print("Warning: Could not import khive_reader_main_entry for CLI tests.")

# Placeholder for DocumentSearchService if direct import for patching is tricky
# This is just for type hinting in tests if needed, actual mocking targets the string path.
class DocumentSearchServicePlaceholder:
    def search(self, query: str, document_id: Optional[UUID] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        raise NotImplementedError


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()

@pytest.fixture
def mock_search_service() -> MagicMock:
    service_mock = MagicMock(spec=DocumentSearchServicePlaceholder) # Use placeholder or actual if available
    service_mock.search.return_value = [
        {"chunk_id": str(uuid4()), "document_id": str(uuid4()), "text": "Mocked search result 1", "score": 0.99}
    ]
    return service_mock

# To test argparse, we'll need to simulate command line arguments and call the main() function.
# We'll also need to capture stdout/stderr.
# The `CliRunner` is more for Click applications.
# We will patch `sys.argv` and call the `main()` from `khive.cli.khive_reader`.

@patch('khive.cli.khive_reader.DocumentSearchService')
@patch('khive.cli.khive_reader.EmbeddingGenerator') # Also patch dependencies instantiated in CLI
@patch('khive.cli.khive_reader.DocumentChunkRepository') # Also patch dependencies
def test_cli_search_basic(
    MockDocumentChunkRepository: MagicMock,
    MockEmbeddingGenerator: MagicMock,
    MockDocumentSearchService: MagicMock,
    mock_search_service: MagicMock, # This is the configured instance from fixture
    capsys: pytest.CaptureFixture
):
    """Test basic `khive reader search --query ...` call."""
    # Configure the mock instance that DocumentSearchService will become
    MockDocumentSearchService.return_value = mock_search_service
    
    test_query = "basic cli test"
    mock_search_service.search.return_value = [
        {"chunk_id": "ch_1", "document_id": "doc_1", "text": "CLI result text 1", "score": 0.9876}
    ]

    # Simulate command line arguments
    with patch('sys.argv', ['khive_reader.py', 'search', '--query', test_query]):
        with pytest.raises(SystemExit) as e: # main() calls sys.exit()
            khive_reader_main_entry()
    
    assert e.value.code == 0 # Should exit successfully
    
    mock_search_service.search.assert_called_once_with(
        query=test_query, document_id=None, top_k=5
    )
    
    captured = capsys.readouterr()
    assert "Search results for query" in captured.out
    assert "CLI result text 1" in captured.out
    assert "0.9876" in captured.out # Check score formatting

@patch('khive.cli.khive_reader.DocumentSearchService')
@patch('khive.cli.khive_reader.EmbeddingGenerator')
@patch('khive.cli.khive_reader.DocumentChunkRepository')
def test_cli_search_json_output(
    MockDocumentChunkRepository: MagicMock,
    MockEmbeddingGenerator: MagicMock,
    MockDocumentSearchService: MagicMock,
    mock_search_service: MagicMock,
    capsys: pytest.CaptureFixture
):
    MockDocumentSearchService.return_value = mock_search_service
    test_query = "json output test"
    expected_results = [
        {"chunk_id": "ch_json", "document_id": "doc_json", "text": "JSON output content", "score": 0.777}
    ]
    mock_search_service.search.return_value = expected_results

    with patch('sys.argv', ['khive_reader.py', 'search', '--query', test_query, '--json-output']):
        with pytest.raises(SystemExit) as e:
            khive_reader_main_entry()
            
    assert e.value.code == 0
    mock_search_service.search.assert_called_once_with(
        query=test_query, document_id=None, top_k=5
    )
    captured = capsys.readouterr()
    assert json.loads(captured.out) == expected_results

@patch('khive.cli.khive_reader.DocumentSearchService')
@patch('khive.cli.khive_reader.EmbeddingGenerator')
@patch('khive.cli.khive_reader.DocumentChunkRepository')
def test_cli_search_with_filters(
    MockDocumentChunkRepository: MagicMock,
    MockEmbeddingGenerator: MagicMock,
    MockDocumentSearchService: MagicMock,
    mock_search_service: MagicMock,
    capsys: pytest.CaptureFixture
):
    MockDocumentSearchService.return_value = mock_search_service
    test_query = "filters test"
    doc_id_str = str(uuid4())
    top_k_val = 3
    
    mock_search_service.search.return_value = [] # Return value not critical for call assertion

    with patch('sys.argv', [
        'khive_reader.py', 'search',
        '--query', test_query,
        '--document-id', doc_id_str,
        '--top-k', str(top_k_val)
    ]):
        with pytest.raises(SystemExit) as e:
            khive_reader_main_entry()
            
    assert e.value.code == 0
    mock_search_service.search.assert_called_once_with(
        query=test_query, document_id=UUID(doc_id_str), top_k=top_k_val
    )

@patch('khive.cli.khive_reader.DocumentSearchService') # To prevent it from actually running
def test_cli_search_missing_query(MockDocumentSearchService: MagicMock, capsys: pytest.CaptureFixture):
    """Test CLI exits with error if --query is missing."""
    with patch('sys.argv', ['khive_reader.py', 'search']): # No --query
        with pytest.raises(SystemExit) as e:
            khive_reader_main_entry()
            
    assert e.value.code != 0 # argparse usually exits with 2 for usage errors
    captured = capsys.readouterr()
    # argparse error messages go to stderr
    assert "required: --query" in captured.err or "the following arguments are required: --query" in captured.err

@patch('khive.cli.khive_reader.DocumentSearchService')
@patch('khive.cli.khive_reader.EmbeddingGenerator')
@patch('khive.cli.khive_reader.DocumentChunkRepository')
def test_cli_search_service_not_implemented_error(
    MockDocumentChunkRepository: MagicMock,
    MockEmbeddingGenerator: MagicMock,
    MockDocumentSearchService: MagicMock,
    mock_search_service: MagicMock,
    capsys: pytest.CaptureFixture
):
    MockDocumentSearchService.return_value = mock_search_service
    mock_search_service.search.side_effect = NotImplementedError("Service not ready")

    with patch('sys.argv', ['khive_reader.py', 'search', '--query', 'test']):
        with pytest.raises(SystemExit) as e:
            khive_reader_main_entry()
    
    assert e.value.code == 1
    captured = capsys.readouterr()
    assert "Search service or its dependencies are not fully implemented" in captured.err

@patch('khive.cli.khive_reader.DocumentSearchService')
@patch('khive.cli.khive_reader.EmbeddingGenerator')
@patch('khive.cli.khive_reader.DocumentChunkRepository')
def test_cli_search_invalid_document_id_format(
    MockDocumentChunkRepository: MagicMock,
    MockEmbeddingGenerator: MagicMock,
    MockDocumentSearchService: MagicMock,
    capsys: pytest.CaptureFixture
):
    # No need to configure mock_search_service as it shouldn't be called
    with patch('sys.argv', ['khive_reader.py', 'search', '--query', 'test', '--document-id', 'not-a-uuid']):
        with pytest.raises(SystemExit) as e:
            khive_reader_main_entry()
            
    assert e.value.code == 1
    captured = capsys.readouterr()
    assert "Invalid Document ID format" in captured.err

@patch('khive.cli.khive_reader.DocumentSearchService')
@patch('khive.cli.khive_reader.EmbeddingGenerator')
@patch('khive.cli.khive_reader.DocumentChunkRepository')
def test_cli_search_invalid_top_k_format(
    MockDocumentChunkRepository: MagicMock,
    MockEmbeddingGenerator: MagicMock,
    MockDocumentSearchService: MagicMock,
    capsys: pytest.CaptureFixture
):
    with patch('sys.argv', ['khive_reader.py', 'search', '--query', 'test', '--top-k', 'zero']): # argparse handles type error
        with pytest.raises(SystemExit) as e:
            khive_reader_main_entry()
    assert e.value.code != 0 # argparse error
    captured = capsys.readouterr()
    assert "invalid int value: 'zero'" in captured.err # argparse error message

    with patch('sys.argv', ['khive_reader.py', 'search', '--query', 'test', '--top-k', '0']): # Value error handled by our code
        with pytest.raises(SystemExit) as e:
            khive_reader_main_entry()
    assert e.value.code == 1
    captured = capsys.readouterr()
    assert "Top K must be a positive integer" in captured.err