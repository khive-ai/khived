import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import the Typer app from the CLI module
from khive.cli.khive_reader import app as reader_cli_app
from khive.reader.services.ingestion_service import Document as IngestDocumentModel
from khive.reader.services.ingestion_service import DocumentStatus
from typer.testing import CliRunner

runner = CliRunner()

# Mocked environment variables for MinIO
MOCK_MINIO_ENV = {
    "MINIO_ENDPOINT_URL": "http://minio.test:9000",
    "MINIO_ACCESS_KEY": "testkey",
    "MINIO_SECRET_KEY": "testsecret",
    "MINIO_BUCKET_NAME_READER_INGEST": "test-ingest-bucket-cli",
}


@pytest.fixture
def mock_ingestion_service_components():
    # This fixture will patch the dependencies of the _ingest_document_async function
    # or the DocumentIngestionService itself if that's easier to target.

    # Mock ObjectStorageClient
    mock_osc = MagicMock()
    mock_osc.ensure_bucket_exists.return_value = True  # Assume bucket is fine
    mock_osc.upload_object.return_value = True  # Assume upload is fine by default
    mock_osc.bucket_name = MOCK_MINIO_ENV["MINIO_BUCKET_NAME_READER_INGEST"]

    # Mock DocumentRepository (InMemory or other)
    mock_dr = AsyncMock()  # Using AsyncMock as DocumentRepository methods are async

    # Mock DocumentIngestionService itself
    mock_dis_instance = AsyncMock()  # The service's main method is async

    with (
        patch(
            "khive.cli.khive_reader.ObjectStorageClient", return_value=mock_osc
        ) as patched_osc,
        patch(
            "khive.cli.khive_reader.InMemoryDocumentRepository", return_value=mock_dr
        ) as patched_dr,
        patch(
            "khive.cli.khive_reader.DocumentIngestionService"
        ) as patched_dis_constructor,
    ):
        # Configure the constructor to return our mock instance
        patched_dis_constructor.return_value = mock_dis_instance

        yield {
            "ObjectStorageClient": patched_osc,
            "InMemoryDocumentRepository": patched_dr,
            "DocumentIngestionServiceConstructor": patched_dis_constructor,
            "DocumentIngestionServiceInstance": mock_dis_instance,
            "mock_osc_instance": mock_osc,  # for direct assertions on the instance
        }


def test_ingest_command_success_no_metadata(mock_ingestion_service_components):
    source_uri = "http://example.com/doc.pdf"
    doc_id = uuid.uuid4()

    # Configure the mock DocumentIngestionService instance
    mock_service_instance = mock_ingestion_service_components[
        "DocumentIngestionServiceInstance"
    ]
    mock_service_instance.ingest_document_from_url.return_value = IngestDocumentModel(
        id=doc_id,
        source_uri=source_uri,
        status=DocumentStatus.QUEUED_FOR_PROCESSING,
        storage_path=f"{MOCK_MINIO_ENV['MINIO_BUCKET_NAME_READER_INGEST']}/{doc_id}/raw_content.pdf",
        size_bytes=12345,
    )

    with patch.dict(importlib.import_module("os").environ, MOCK_MINIO_ENV):
        result = runner.invoke(reader_cli_app, ["ingest", "--source-uri", source_uri])

    assert result.exit_code == 0
    assert f"ID: {doc_id}" in result.stdout
    assert f"Source URI: {source_uri}" in result.stdout
    assert f"Status: {DocumentStatus.QUEUED_FOR_PROCESSING.value}" in result.stdout

    mock_service_instance.ingest_document_from_url.assert_called_once()
    call_args = mock_service_instance.ingest_document_from_url.call_args[1]  # kwargs
    assert str(call_args["source_uri"]) == source_uri
    assert call_args["metadata_file_content"] is None


def test_ingest_command_success_with_metadata(
    mock_ingestion_service_components, tmp_path: Path
):
    source_uri = "http://example.com/doc2.txt"
    doc_id = uuid.uuid4()
    metadata_content = {"author": "Test User", "version": "1.0"}
    metadata_file = tmp_path / "metadata.json"
    metadata_file.write_text(json.dumps(metadata_content))

    mock_service_instance = mock_ingestion_service_components[
        "DocumentIngestionServiceInstance"
    ]
    mock_service_instance.ingest_document_from_url.return_value = IngestDocumentModel(
        id=doc_id,
        source_uri=source_uri,
        status=DocumentStatus.QUEUED_FOR_PROCESSING,
        metadata_=metadata_content,  # Note the alias 'metadata' in Pydantic model
    )

    with patch.dict(importlib.import_module("os").environ, MOCK_MINIO_ENV):
        result = runner.invoke(
            reader_cli_app,
            [
                "ingest",
                "--source-uri",
                source_uri,
                "--metadata-file",
                str(metadata_file),
            ],
        )

    assert result.exit_code == 0
    assert f"ID: {doc_id}" in result.stdout

    mock_service_instance.ingest_document_from_url.assert_called_once()
    call_args = mock_service_instance.ingest_document_from_url.call_args[1]
    assert str(call_args["source_uri"]) == source_uri
    assert call_args["metadata_file_content"] == metadata_content


def test_ingest_command_success_json_output(mock_ingestion_service_components):
    source_uri = "http://example.com/doc.jsonout"
    doc_id = uuid.uuid4()
    expected_doc = IngestDocumentModel(
        id=doc_id,
        source_uri=source_uri,
        status=DocumentStatus.QUEUED_FOR_PROCESSING,
        storage_path="s3_path.bin",
        size_bytes=100,
    )

    mock_service_instance = mock_ingestion_service_components[
        "DocumentIngestionServiceInstance"
    ]
    mock_service_instance.ingest_document_from_url.return_value = expected_doc

    with patch.dict(importlib.import_module("os").environ, MOCK_MINIO_ENV):
        result = runner.invoke(
            reader_cli_app, ["ingest", "--source-uri", source_uri, "--json-output"]
        )

    assert result.exit_code == 0
    output_json = json.loads(result.stdout)
    assert output_json["id"] == str(doc_id)
    assert output_json["source_uri"] == source_uri
    assert output_json["status"] == DocumentStatus.QUEUED_FOR_PROCESSING.value


def test_ingest_command_invalid_uri(mock_ingestion_service_components):
    with patch.dict(importlib.import_module("os").environ, MOCK_MINIO_ENV):
        result = runner.invoke(reader_cli_app, ["ingest", "--source-uri", "not_a_uri"])

    assert result.exit_code == 1
    assert (
        "Invalid source URI" in result.stdout
    )  # Typer prints to stdout for errors by default with secho
    mock_ingestion_service_components[
        "DocumentIngestionServiceInstance"
    ].ingest_document_from_url.assert_not_called()


def test_ingest_command_metadata_file_not_found(mock_ingestion_service_components):
    source_uri = "http://example.com/doc.nf"
    with patch.dict(importlib.import_module("os").environ, MOCK_MINIO_ENV):
        result = runner.invoke(
            reader_cli_app,
            [
                "ingest",
                "--source-uri",
                source_uri,
                "--metadata-file",
                "non_existent.json",
            ],
        )

    assert result.exit_code == 1
    assert "Metadata file not found" in result.stdout


def test_ingest_command_malformed_metadata_json(
    mock_ingestion_service_components, tmp_path: Path
):
    source_uri = "http://example.com/doc.badjson"
    metadata_file = tmp_path / "bad_metadata.json"
    metadata_file.write_text("{'author': 'Test User', 'version': ")  # Malformed

    with patch.dict(importlib.import_module("os").environ, MOCK_MINIO_ENV):
        result = runner.invoke(
            reader_cli_app,
            [
                "ingest",
                "--source-uri",
                source_uri,
                "--metadata-file",
                str(metadata_file),
            ],
        )

    assert result.exit_code == 1
    assert "Error decoding JSON" in result.stdout


def test_ingest_command_ingestion_service_fails(mock_ingestion_service_components):
    source_uri = "http://example.com/doc.fail"
    mock_service_instance = mock_ingestion_service_components[
        "DocumentIngestionServiceInstance"
    ]
    mock_service_instance.ingest_document_from_url.return_value = (
        None  # Simulate failure
    )

    with patch.dict(importlib.import_module("os").environ, MOCK_MINIO_ENV):
        result = runner.invoke(reader_cli_app, ["ingest", "--source-uri", source_uri])

    assert result.exit_code == 1
    assert f"Document ingestion failed for URI: {source_uri}" in result.stdout


def test_ingest_command_ingestion_service_raises_exception(
    mock_ingestion_service_components,
):
    source_uri = "http://example.com/doc.exception"
    mock_service_instance = mock_ingestion_service_components[
        "DocumentIngestionServiceInstance"
    ]
    mock_service_instance.ingest_document_from_url.side_effect = Exception(
        "Internal service error"
    )

    with patch.dict(importlib.import_module("os").environ, MOCK_MINIO_ENV):
        result = runner.invoke(reader_cli_app, ["ingest", "--source-uri", source_uri])

    assert result.exit_code == 1
    assert (
        "An error occurred during ingestion: Exception: Internal service error"
        in result.stdout
    )


def test_ingest_command_minio_config_missing(mock_ingestion_service_components):
    # Test without setting one of the MinIO env vars
    incomplete_env = MOCK_MINIO_ENV.copy()
    del incomplete_env["MINIO_ACCESS_KEY"]

    with patch.dict(importlib.import_module("os").environ, incomplete_env, clear=True):
        # clear=True ensures only our dict is used for os.environ within this context
        result = runner.invoke(
            reader_cli_app,
            ["ingest", "--source-uri", "http://example.com/doc.miniofail"],
        )

    assert result.exit_code == 1
    assert "MinIO client configuration not fully set" in result.stdout


# Need to import 'importlib' for the patch.dict to work correctly on os.environ
import importlib

from khive.services.reader.parts import (
    DocumentInfo,
    PartialChunk,
    ReaderListDirResponseContent,
    ReaderOpenResponseContent,
    ReaderReadResponseContent,
    ReaderResponse,
)


# Basic tests for 'open', 'read', 'list' to ensure they are still callable
@pytest.mark.asyncio  # Added
@patch("khive.cli.khive_reader.ReaderServiceGroup")
async def test_open_command_callable(MockReaderServiceGroup):
    mock_service_instance = MockReaderServiceGroup.return_value
    # Ensure handle_request is an AsyncMock if ReaderServiceGroup.handle_request is async
    mock_service_instance.handle_request = AsyncMock(
        return_value=ReaderResponse(
            success=True,
            content=ReaderOpenResponseContent(
                doc_info=DocumentInfo(doc_id="doc123", length=100, num_tokens=10)
            ),
        )
    )

    result = runner.invoke(reader_cli_app, ["open", "--path-or-url", "README.md"])
    assert result.exit_code == 0  # Typer runner handles async commands
    assert '"doc_id": "doc123"' in result.stdout
    # mock_service_instance.handle_request.assert_awaited_once() # Check it was awaited


@pytest.mark.asyncio  # Added
@patch("khive.cli.khive_reader.ReaderServiceGroup")
async def test_read_command_callable(MockReaderServiceGroup):
    mock_service_instance = MockReaderServiceGroup.return_value
    mock_service_instance.handle_request = AsyncMock(
        return_value=ReaderResponse(
            success=True,
            content=ReaderReadResponseContent(
                chunk=PartialChunk(start_offset=0, end_offset=11, content="sample text")
            ),
        )
    )

    # Mock the documents attribute on the instance for the read command's cache check
    mock_service_instance.documents = {"doc123": ("/tmp/file", 100)}

    # No need to patch CACHE if service.documents is correctly populated by 'open' or mocked for 'read'
    # with patch('khive.cli.khive_reader.CACHE', {"doc123": {"path": "/tmp/file", "length": 100}}):
    result = runner.invoke(reader_cli_app, ["read", "--doc-id", "doc123"])
    assert result.exit_code == 0
    assert (
        '"text_slice": "sample text"' in result.stdout
    )  # Assuming model_dump uses text_slice for PartialChunk.content
    # mock_service_instance.handle_request.assert_awaited_once()


@pytest.mark.asyncio  # Added
@patch("khive.cli.khive_reader.ReaderServiceGroup")
async def test_list_command_callable(MockReaderServiceGroup):
    mock_service_instance = MockReaderServiceGroup.return_value
    mock_service_instance.handle_request = AsyncMock(
        return_value=ReaderResponse(
            success=True,
            content=ReaderListDirResponseContent(  # This was ReaderOpenResponseContent before, fixed
                files=["file1.md", "file2.txt"],  # Example files
                doc_info=DocumentInfo(
                    doc_id="dir_doc", length=50, num_tokens=5
                ),  # list_dir also creates a doc
            ),
        )
    )
    # Mock the documents attribute for the list command's cache update logic
    mock_service_instance.documents = {}

    result = runner.invoke(reader_cli_app, ["list", "--directory", "."])
    assert result.exit_code == 0
    assert '"doc_id": "dir_doc"' in result.stdout
    # mock_service_instance.handle_request.assert_awaited_once()
