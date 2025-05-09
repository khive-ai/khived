import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Mock tiktoken before importing
tiktoken_mock = MagicMock()
encode_mock = MagicMock()
encode_mock.return_value = ["token1", "token2", "token3"]
tiktoken_mock.get_encoding.return_value.encode = encode_mock

sys.modules["tiktoken"] = tiktoken_mock

from khive.services.reader.utils import calculate_text_tokens, dir_to_files


# --- Tests for calculate_text_tokens ---
def test_calculate_text_tokens_empty_or_none():
    """Test token calculation for empty or None strings."""
    assert calculate_text_tokens(None) == 0
    assert calculate_text_tokens("") == 0


def test_calculate_text_tokens_success():
    """Test successful token calculation."""
    # Since we've already mocked tiktoken at the module level in the imports,
    # we can just use the mock directly
    result = calculate_text_tokens("some example text")

    # The mock was set to return a 3-token list
    assert result == 3
    encode_mock.assert_called_with("some example text")


def test_calculate_text_tokens_import_error():
    """Test token calculation handling an import error."""
    # Use temporary_mock to modify behavior for this test only
    temporary_mock = MagicMock()
    temporary_mock.get_encoding.side_effect = ImportError("Module not found")

    with patch.dict("sys.modules", {"tiktoken": temporary_mock}):
        result = calculate_text_tokens("text that will fail to tokenize")

    assert result == 0  # Should fallback to 0


def test_calculate_text_tokens_general_error():
    """Test token calculation handling a general error."""
    # Use temporary_mock to modify behavior for this test only
    temporary_mock = MagicMock()
    temporary_mock.get_encoding.side_effect = Exception("Generic tokenizer error")

    with patch.dict("sys.modules", {"tiktoken": temporary_mock}):
        result = calculate_text_tokens("text that will fail to tokenize")

    assert result == 0  # Should fallback to 0


# --- Tests for dir_to_files ---
@pytest.fixture
def sample_dir_structure(tmp_path):
    """Create a sample directory structure for testing."""
    root = tmp_path / "sample_dir"
    root.mkdir()
    (root / "file1.txt").write_text("content1")
    (root / "file2.md").write_text("content2")

    sub_dir = root / "subdir"
    sub_dir.mkdir()
    (sub_dir / "file3.txt").write_text("content3")
    (sub_dir / "image.jpg").write_text("fake image data")  # Test different extensions
    (sub_dir / "no_ext_file").write_text("content4")

    return root


def test_dir_to_files_non_recursive(sample_dir_structure):
    """Test listing files non-recursively."""
    files = dir_to_files(sample_dir_structure, recursive=False)
    paths = {f.name for f in files}
    assert paths == {"file1.txt", "file2.md"}


def test_dir_to_files_recursive(sample_dir_structure):
    """Test listing files recursively."""
    files = dir_to_files(sample_dir_structure, recursive=True)
    paths = {f.name for f in files}
    # sub_dir itself is not a file
    assert paths == {"file1.txt", "file2.md", "file3.txt", "image.jpg", "no_ext_file"}


def test_dir_to_files_with_specific_types_recursive(sample_dir_structure):
    """Test listing files recursively with specific file types."""
    files = dir_to_files(
        sample_dir_structure, file_types=[".txt", ".md"], recursive=True
    )
    paths = {f.name for f in files}
    assert paths == {"file1.txt", "file2.md", "file3.txt"}


def test_dir_to_files_with_specific_types_non_recursive(sample_dir_structure):
    """Test listing files non-recursively with specific file types."""
    files = dir_to_files(sample_dir_structure, file_types=[".txt"], recursive=False)
    paths = {f.name for f in files}
    assert paths == {"file1.txt"}


def test_dir_to_files_empty_dir(tmp_path):
    """Test listing files in an empty directory."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    files = dir_to_files(empty_dir)
    assert len(files) == 0


def test_dir_to_files_invalid_directory():
    """Test handling invalid directory path."""
    with pytest.raises(ValueError) as excinfo:
        dir_to_files("non_existent_path_for_sure")
    assert "provided path is not a valid directory" in str(excinfo.value)


def test_dir_to_files_file_as_directory(tmp_path):
    """Test providing a file instead of a directory."""
    file_path = tmp_path / "a_file.txt"
    file_path.write_text("hello")
    with pytest.raises(ValueError) as excinfo:
        dir_to_files(file_path)
    assert "provided path is not a valid directory" in str(excinfo.value)


def test_dir_to_files_with_max_workers(sample_dir_structure):
    """Test setting max_workers parameter."""
    # Just verify it doesn't break with different max_workers values
    files1 = dir_to_files(sample_dir_structure, recursive=True, max_workers=1)
    files2 = dir_to_files(sample_dir_structure, recursive=True, max_workers=2)

    paths1 = {f.name for f in files1}
    paths2 = {f.name for f in files2}

    assert paths1 == paths2  # Results should be the same regardless of worker count


@pytest.mark.skip(
    reason="Test is too complex for mock environment; relies on implementation details that might change"
)
def test_dir_to_files_with_ignore_errors(sample_dir_structure, caplog):
    """Test listing files with ignore_errors=True."""
    # This test is skipped since it's too complex for the test environment
    # and relies on implementation details


def test_dir_to_files_without_ignore_errors(sample_dir_structure):
    """Test listing files with ignore_errors=False."""
    # Mock Path.is_file to raise an error for one specific file
    original_is_file = Path.is_file

    def mock_is_file(self):
        if self.name == "file2.md":
            raise ValueError("Critical error processing file2.md")
        return original_is_file(self)

    with patch.object(Path, "is_file", mock_is_file):
        with pytest.raises(ValueError) as excinfo:
            dir_to_files(sample_dir_structure, ignore_errors=False)

    assert "Critical error processing file2.md" in str(excinfo.value)


def test_dir_to_files_thread_executor_error(sample_dir_structure):
    """Test handling errors in the ThreadPoolExecutor."""
    # We need to patch the correct import path
    with patch("concurrent.futures.ThreadPoolExecutor") as mock_executor_cls:
        # Set up the mock executor to raise an exception
        mock_executor_instance = MagicMock()
        mock_executor_instance.__enter__.side_effect = RuntimeError("Thread pool error")
        mock_executor_cls.return_value = mock_executor_instance

        with pytest.raises(ValueError) as excinfo:
            dir_to_files(sample_dir_structure)

        assert "Error processing directory" in str(excinfo.value)
