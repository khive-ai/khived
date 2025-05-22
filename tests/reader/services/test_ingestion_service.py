import pytest
import uuid
from unittest.mock import MagicMock, AsyncMock, patch, call
import requests # Added for requests.exceptions.RequestException
from pydantic import HttpUrl

from khive.reader.services.ingestion_service import (
    DocumentIngestionService,
    Document,
    DocumentCreate,
    DocumentStatus,
    DocumentRepository, # Protocol
)
from khive.reader.storage.minio_client import ObjectStorageClient

@pytest.fixture
def mock_document_repo():
    repo = AsyncMock(spec=DocumentRepository)
    repo.create_document = AsyncMock()
    repo.get_document_by_id = AsyncMock()
    repo.update_document_status = AsyncMock()
    repo.update_document_storage_path = AsyncMock()
    return repo

@pytest.fixture
def mock_storage_client():
    client = MagicMock(spec=ObjectStorageClient)
    client.upload_object = MagicMock()
    client.ensure_bucket_exists = MagicMock(return_value=True) # Assume bucket exists for tests
    client.bucket_name = "test-ingest-bucket"
    return client

@pytest.fixture
def ingestion_service(mock_document_repo, mock_storage_client):
    return DocumentIngestionService(mock_document_repo, mock_storage_client)

@pytest.fixture
def sample_document_create():
    return DocumentCreate(source_uri=HttpUrl("http://example.com/test.pdf"))

@pytest.fixture
def sample_document(sample_document_create):
    doc_id = uuid.uuid4()
    return Document(
        id=doc_id,
        **sample_document_create.dict(),
        status=DocumentStatus.PENDING,
        storage_path=None
    )

@pytest.mark.asyncio
async def test_ingest_document_from_url_success(
    ingestion_service: DocumentIngestionService,
    mock_document_repo: AsyncMock,
    mock_storage_client: MagicMock,
    sample_document_create: DocumentCreate,
    sample_document: Document
):
    source_uri = sample_document_create.source_uri
    raw_content = b"pdf content"
    
    # Configure mocks for successful path
    # Simulate a document state that gets updated by the mock repository calls
    # The initial state is based on sample_document but will be modified by side effects
    
    # This mutable dictionary will hold the "current" state of the document in our mock DB
    # It's keyed by document ID.
    mock_db_storage = {}

    # Initial document created by the repo
    initial_created_doc = sample_document.copy(deep=True)
    mock_db_storage[initial_created_doc.id] = initial_created_doc
    mock_document_repo.create_document.return_value = initial_created_doc.copy(deep=True)
    
    async def update_status_side_effect(doc_id, status, error_message=None):
        if doc_id not in mock_db_storage:
            # This case should ideally not happen if create_document was called first
            # For robustness, create a base doc if not found, or raise error
            current_doc_in_db = sample_document.copy(deep=True)
            current_doc_in_db.id = doc_id
            mock_db_storage[doc_id] = current_doc_in_db
        else:
            current_doc_in_db = mock_db_storage[doc_id]
        
        current_doc_in_db.status = status
        current_doc_in_db.error_message = error_message
        # print(f"MOCK_DB: Updated status for {doc_id} to {status}. Current storage_path: {current_doc_in_db.storage_path}")
        return current_doc_in_db.copy(deep=True)

    async def update_storage_path_side_effect(doc_id, storage_path, size_bytes=None):
        if doc_id not in mock_db_storage:
            # As above, handle if doc_id somehow not in mock_db_storage
            current_doc_in_db = sample_document.copy(deep=True)
            current_doc_in_db.id = doc_id
            mock_db_storage[doc_id] = current_doc_in_db
        else:
            current_doc_in_db = mock_db_storage[doc_id]

        current_doc_in_db.storage_path = storage_path
        if size_bytes is not None:
            current_doc_in_db.size_bytes = size_bytes
        # print(f"MOCK_DB: Updated storage_path for {doc_id} to {storage_path}. Current status: {current_doc_in_db.status}")
        return current_doc_in_db.copy(deep=True)

    mock_document_repo.update_document_status.side_effect = update_status_side_effect
    mock_document_repo.update_document_storage_path.side_effect = update_storage_path_side_effect
    
    mock_storage_client.upload_object.return_value = True

    with patch('requests.get') as mock_requests_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = raw_content
        mock_response.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_response

        result_doc = await ingestion_service.ingest_document_from_url(source_uri)

    assert result_doc is not None
    assert result_doc.status == DocumentStatus.QUEUED_FOR_PROCESSING
    assert result_doc.source_uri == source_uri
    assert result_doc.storage_path is not None
    assert str(sample_document.id) in result_doc.storage_path
    assert result_doc.size_bytes == len(raw_content)

    mock_document_repo.create_document.assert_called_once_with(sample_document_create)
    
    # Check status updates
    status_calls = [
        call(sample_document.id, DocumentStatus.DOWNLOADING),
        call(sample_document.id, DocumentStatus.CONTENT_STORED),
        call(sample_document.id, DocumentStatus.QUEUED_FOR_PROCESSING),
    ]
    mock_document_repo.update_document_status.assert_has_calls(status_calls, any_order=False) # Order matters here

    mock_requests_get.assert_called_once_with(str(source_uri), timeout=30)
    
    expected_object_name = f"{sample_document.id}/raw_content.pdf" # Assuming extension from URI
    mock_storage_client.upload_object.assert_called_once_with(
        object_name=expected_object_name,
        data=raw_content,
        content_type="application/octet-stream" # Default fallback
    )
    mock_document_repo.update_document_storage_path.assert_called_once_with(
        sample_document.id, storage_path=f"{mock_storage_client.bucket_name}/{expected_object_name}", size_bytes=len(raw_content)
    )


@pytest.mark.asyncio
async def test_ingest_document_from_url_repo_create_fails(
    ingestion_service: DocumentIngestionService,
    mock_document_repo: AsyncMock,
    sample_document_create: DocumentCreate
):
    mock_document_repo.create_document.side_effect = Exception("DB error")
    
    result_doc = await ingestion_service.ingest_document_from_url(sample_document_create.source_uri)
    
    assert result_doc is None
    mock_document_repo.update_document_status.assert_not_called()


@pytest.mark.asyncio
async def test_ingest_document_from_url_download_fails(
    ingestion_service: DocumentIngestionService,
    mock_document_repo: AsyncMock,
    sample_document_create: DocumentCreate,
    sample_document: Document
):
    mock_document_repo.create_document.return_value = sample_document
    
    # Mock status updates to return the document with the new status
    async def update_status_side_effect(doc_id, status, error_message=None):
        updated_doc = sample_document.copy(deep=True)
        updated_doc.id = doc_id
        updated_doc.status = status
        updated_doc.error_message = error_message
        return updated_doc
    mock_document_repo.update_document_status.side_effect = update_status_side_effect

    with patch('requests.get') as mock_requests_get:
        mock_requests_get.side_effect = requests.exceptions.RequestException("Network error")
        
        result_doc = await ingestion_service.ingest_document_from_url(sample_document_create.source_uri)

    assert result_doc is not None
    assert result_doc.status == DocumentStatus.DOWNLOAD_FAILED
    assert result_doc.error_message == "Failed to download content from source URI."
    
    status_calls = [
        call(sample_document.id, DocumentStatus.DOWNLOADING),
        call(sample_document.id, DocumentStatus.DOWNLOAD_FAILED, error_message="Failed to download content from source URI."),
    ]
    mock_document_repo.update_document_status.assert_has_calls(status_calls, any_order=False)


@pytest.mark.asyncio
async def test_ingest_document_from_url_s3_upload_fails(
    ingestion_service: DocumentIngestionService,
    mock_document_repo: AsyncMock,
    mock_storage_client: MagicMock,
    sample_document_create: DocumentCreate,
    sample_document: Document
):
    raw_content = b"pdf content"
    mock_document_repo.create_document.return_value = sample_document
    
    async def update_status_side_effect(doc_id, status, error_message=None):
        updated_doc = sample_document.copy(deep=True)
        updated_doc.id = doc_id
        updated_doc.status = status
        updated_doc.error_message = error_message
        return updated_doc
    mock_document_repo.update_document_status.side_effect = update_status_side_effect
    
    mock_storage_client.upload_object.return_value = False # Simulate S3 upload failure

    with patch('requests.get') as mock_requests_get:
        mock_response = MagicMock()
        mock_response.content = raw_content
        mock_response.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_response

        result_doc = await ingestion_service.ingest_document_from_url(sample_document_create.source_uri)

    assert result_doc is not None
    assert result_doc.status == DocumentStatus.ERROR
    assert result_doc.error_message == "Failed to store raw content in object storage."
    
    status_calls = [
        call(sample_document.id, DocumentStatus.DOWNLOADING),
        call(sample_document.id, DocumentStatus.ERROR, error_message="Failed to store raw content in object storage."),
    ]
    # We don't check for CONTENT_STORED because upload failed before that
    mock_document_repo.update_document_status.assert_has_calls(status_calls, any_order=False)
    mock_storage_client.upload_object.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_document_from_url_update_storage_path_fails(
    ingestion_service: DocumentIngestionService,
    mock_document_repo: AsyncMock,
    mock_storage_client: MagicMock,
    sample_document_create: DocumentCreate,
    sample_document: Document
):
    raw_content = b"pdf content"
    mock_document_repo.create_document.return_value = sample_document
    
    # Mock status updates
    # For this test, we care that update_document_storage_path returns None
    # and then the subsequent status update to CONTENT_STORED also fails or returns None.
    
    # Mock behavior:
    # 1. create_document: returns sample_document
    # 2. update_document_status (DOWNLOADING): returns sample_document (or copy with status)
    # 3. update_document_storage_path: returns None (simulates failure)
    # 4. update_document_status (ERROR): returns sample_document (or copy with status ERROR)
    
    doc_after_downloading = sample_document.copy(deep=True)
    doc_after_downloading.status = DocumentStatus.DOWNLOADING

    doc_after_error = sample_document.copy(deep=True) # Start from original for simplicity of error state
    doc_after_error.status = DocumentStatus.ERROR
    doc_after_error.error_message = "Failed to update document with storage path."

    mock_document_repo.update_document_status.side_effect = [
        doc_after_downloading, # For the DOWNLOADING call
        doc_after_error        # For the ERROR call after storage_path fails
    ]
    mock_document_repo.update_document_storage_path.return_value = None # Simulate storage path update failure
    mock_storage_client.upload_object.return_value = True # Upload itself is fine


    with patch('requests.get') as mock_requests_get:
        mock_response = MagicMock()
        mock_response.content = raw_content
        mock_response.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_response

        result_doc = await ingestion_service.ingest_document_from_url(sample_document_create.source_uri)

    # The service should return the document with ERROR status
    assert result_doc is not None
    assert result_doc.status == DocumentStatus.ERROR
    assert result_doc.error_message == "Failed to update document with storage path."
    
    # Check that create_document was called
    mock_document_repo.create_document.assert_called_once()
    
    # Check that update_document_status was called for DOWNLOADING
    mock_document_repo.update_document_status.assert_any_call(sample_document.id, DocumentStatus.DOWNLOADING)
    
    # Check that update_document_storage_path was called
    mock_document_repo.update_document_storage_path.assert_called_once()
    
    # Check that update_document_status was called for ERROR
    mock_document_repo.update_document_status.assert_any_call(
        sample_document.id, DocumentStatus.ERROR, error_message="Failed to update document with storage path."
    )


@pytest.mark.asyncio
async def test_ingest_document_from_url_queueing_fails_placeholder(
    ingestion_service: DocumentIngestionService,
    mock_document_repo: AsyncMock,
    mock_storage_client: MagicMock,
    sample_document_create: DocumentCreate,
    sample_document: Document
):
    # This test is somewhat trivial now as _queue_document_for_processing is a placeholder
    # but sets up for when it's a real call.
    raw_content = b"pdf content"
    mock_document_repo.create_document.return_value = sample_document
    
    # Make all repo updates successful until the last one
    async def update_status_side_effect(doc_id, status, error_message=None):
        updated_doc = sample_document.copy(deep=True)
        updated_doc.id = doc_id
        updated_doc.status = status
        updated_doc.error_message = error_message
        if status == DocumentStatus.QUEUED_FOR_PROCESSING and error_message: # Simulate failure for this specific status
             updated_doc.status = DocumentStatus.ERROR # The service sets it to ERROR
        return updated_doc

    async def update_storage_path_side_effect(doc_id, storage_path, size_bytes=None):
        updated_doc = sample_document.copy(deep=True)
        updated_doc.id = doc_id
        updated_doc.storage_path = storage_path
        if size_bytes: updated_doc.size_bytes = size_bytes
        return updated_doc

    mock_document_repo.update_document_status.side_effect = update_status_side_effect
    mock_document_repo.update_document_storage_path.side_effect = update_storage_path_side_effect
    mock_storage_client.upload_object.return_value = True

    with patch('requests.get') as mock_requests_get, \
         patch.object(ingestion_service, '_queue_document_for_processing', new_callable=AsyncMock) as mock_queue_call:
        
        mock_response = MagicMock()
        mock_response.content = raw_content
        mock_response.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_response
        
        mock_queue_call.return_value = False # Simulate queueing failure

        result_doc = await ingestion_service.ingest_document_from_url(sample_document_create.source_uri)

    assert result_doc is not None
    assert result_doc.status == DocumentStatus.ERROR # Service sets to ERROR on queue fail
    assert result_doc.error_message == "Failed to queue document for processing."
    mock_queue_call.assert_called_once()

    status_calls = [
        call(sample_document.id, DocumentStatus.DOWNLOADING),
        call(sample_document.id, DocumentStatus.CONTENT_STORED),
        call(sample_document.id, DocumentStatus.ERROR, error_message="Failed to queue document for processing."),
    ]
    mock_document_repo.update_document_status.assert_has_calls(status_calls, any_order=False)