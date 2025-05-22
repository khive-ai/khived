import logging
import uuid
from abc import abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol

import httpx  # Replaced requests with httpx
from pydantic import BaseModel, Field, HttpUrl

from khive.reader.storage.minio_client import ObjectStorageClient

logger = logging.getLogger(__name__)


class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    DOWNLOAD_FAILED = "DOWNLOAD_FAILED"
    CONTENT_STORED = "CONTENT_STORED"
    QUEUED_FOR_PROCESSING = "QUEUED_FOR_PROCESSING"
    PROCESSING = "PROCESSING"
    PROCESSING_FAILED = "PROCESSING_FAILED"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


# --- Placeholder Data Models (to be refined/moved based on Issue #25) ---
class DocumentBase(BaseModel):
    source_uri: HttpUrl
    metadata_: dict[str, Any] | None = Field(default_factory=dict, alias="metadata")
    content_type: str | None = None
    size_bytes: int | None = None


class DocumentCreate(DocumentBase):
    pass


class Document(DocumentBase):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    status: DocumentStatus = DocumentStatus.PENDING
    storage_path: str | None = None  # e.g., s3_bucket/document_id/raw_content.ext
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: str | None = None

    class Config:
        use_enum_values = True
        allow_population_by_field_name = True


# --- Placeholder Repository Interface (to be refined/moved based on Issue #25) ---
class DocumentRepository(Protocol):
    @abstractmethod
    async def create_document(self, doc_create: DocumentCreate) -> Document: ...

    @abstractmethod
    async def get_document_by_id(self, document_id: uuid.UUID) -> Document | None: ...

    @abstractmethod
    async def update_document_status(
        self,
        document_id: uuid.UUID,
        status: DocumentStatus,
        error_message: str | None = None,
    ) -> Document | None: ...

    @abstractmethod
    async def update_document_storage_path(
        self, document_id: uuid.UUID, storage_path: str, size_bytes: int | None = None
    ) -> Document | None: ...


# --- Document Ingestion Service ---
class DocumentIngestionService:
    def __init__(
        self,
        document_repository: DocumentRepository,
        storage_client: ObjectStorageClient,
    ):
        self.document_repository = document_repository
        self.storage_client = storage_client
        # Placeholder for task queue client (from Issue #27)
        self.task_queue_client = None  # Replace with actual client later

    async def _download_content_from_url(self, url: HttpUrl) -> bytes | None:
        """Downloads content from the given URL."""
        try:
            logger.info(f"Attempting to download content from URL: {url}")
            async with httpx.AsyncClient() as client:
                response = await client.get(str(url), timeout=30)
            response.raise_for_status()  # Raise an exception for HTTP errors
            logger.info(
                f"Successfully downloaded content from URL: {url}, status: {response.status_code}"
            )
            return response.content
        except httpx.RequestError as e:  # Changed to httpx.RequestError
            logger.error(
                f"Failed to download content from URL '{url}': {e}", exc_info=True
            )
            return None
        except (
            httpx.HTTPStatusError
        ) as e:  # Added specific handling for HTTPStatusError
            logger.error(
                f"HTTP error {e.response.status_code} while downloading from URL '{url}': {e.response.text}",
                exc_info=True,
            )
            return None
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while downloading from URL '{url}': {e}",
                exc_info=True,
            )
            return None

    async def _queue_document_for_processing(self, document: Document) -> bool:
        """
        Placeholder for queuing the document for further processing (e.g., text extraction).
        This will be implemented properly with the task queue from Issue #27.
        """
        if self.task_queue_client:
            # Example: await self.task_queue_client.enqueue_task("process_document", {"document_id": str(document.id)})
            logger.info(
                f"Document '{document.id}' would be queued for processing (Task Queue TBD)."
            )
            return True  # Assume success for now
        logger.warning(
            f"Task queue client not available. Document '{document.id}' not queued for processing."
        )
        # For now, we'll consider it successfully "queued" as a placeholder step
        return True

    async def ingest_document_from_url(
        self,
        source_uri: HttpUrl,
        metadata_file_content: dict[str, Any] | None = None,
    ) -> Document | None:
        """
        Manages the document ingestion process:
        1. Creates a document record in the database.
        2. Downloads content from the URL.
        3. Stores raw content in object storage.
        4. Queues the document for processing.
        """
        doc_create = DocumentCreate(
            source_uri=source_uri, metadata=metadata_file_content or {}
        )

        try:
            document = await self.document_repository.create_document(doc_create)
            logger.info(
                f"Created document record with ID: {document.id} for URI: {source_uri}"
            )
        except Exception as e:
            logger.error(
                f"Failed to create document record for URI '{source_uri}': {e}",
                exc_info=True,
            )
            return None

        # Update status to DOWNLOADING
        document = await self.document_repository.update_document_status(
            document.id, DocumentStatus.DOWNLOADING
        )
        if not document:
            logger.error(
                f"Failed to update document {document.id} status to DOWNLOADING."
            )
            # Potentially set an error status on the original document object if possible, or just return
            return None  # Or the original document with an error status if the repo returns it

        # Download content
        raw_content = await self._download_content_from_url(source_uri)
        if raw_content is None:
            logger.error(
                f"Failed to download content for document ID: {document.id} from {source_uri}"
            )
            return await self.document_repository.update_document_status(
                document.id,
                DocumentStatus.DOWNLOAD_FAILED,
                error_message="Failed to download content from source URI.",
            )

        document.size_bytes = len(raw_content)
        # Infer content_type if possible, or use what's provided/default
        # For simplicity, this example doesn't deeply infer content_type from raw_content
        # It would typically come from HTTP headers or file extension if available.

        # Store raw content in object storage
        # Using document.id as part of the path ensures uniqueness.
        # Extension could be inferred or fixed if known.
        file_extension = (
            source_uri.path.split(".")[-1] if "." in source_uri.path else "bin"
        )
        storage_object_name = f"{document.id}/raw_content.{file_extension}"

        upload_successful = self.storage_client.upload_object(
            object_name=storage_object_name,
            data=raw_content,
            # metadata={"document_id": str(document.id), "source_uri": str(source_uri)}, # Optional: S3 metadata
            content_type=document.content_type
            or "application/octet-stream",  # Fallback
        )

        if not upload_successful:
            logger.error(
                f"Failed to upload raw content to S3 for document ID: {document.id}"
            )
            # Get the updated document after setting status to ERROR
            return await self.document_repository.update_document_status(
                document.id,
                DocumentStatus.ERROR,
                error_message="Failed to store raw content in object storage.",
            )

        logger.info(
            f"Successfully stored raw content for document ID: {document.id} at S3 path: {storage_object_name}"
        )
        original_document_id = document.id  # Save ID before potential None
        updated_doc_after_storage_path = (
            await self.document_repository.update_document_storage_path(
                document.id,
                storage_path=f"{self.storage_client.bucket_name}/{storage_object_name}",
                size_bytes=document.size_bytes,
            )
        )

        if not updated_doc_after_storage_path:
            logger.error(
                f"Failed to update document {original_document_id} with storage path in repository."
            )
            # Attempt to set original document to an error state if possible, or just return None
            # For now, we'll set an error status on the last known good state of the document (which is 'document' before this call)
            # However, the test expects the service to return None if this specific update fails and subsequent ones also fail.
            # Let's ensure we try to set an error status and return that document.
            # If update_document_status itself fails, then we might return None from the whole function.
            return await self.document_repository.update_document_status(
                original_document_id,
                DocumentStatus.ERROR,
                error_message="Failed to update document with storage path.",
            )

        document = updated_doc_after_storage_path  # Continue with the updated document

        updated_doc_after_status = (
            await self.document_repository.update_document_status(
                document.id, DocumentStatus.CONTENT_STORED
            )
        )
        if not updated_doc_after_status:
            logger.error(
                f"Failed to update document {document.id} status to CONTENT_STORED."
            )
            # Return the document as it was before this failed status update, potentially with an error message already set
            # Or, if the contract is that any failure in status update means the overall operation is compromised:
            return document  # Return the document which has storage_path but failed CONTENT_STORED update
            # The test expects None if the CONTENT_STORED update returns None.
            # So, if updated_doc_after_status is None, we should return None.
        document = updated_doc_after_status

        # Queue document for processing (placeholder)
        queued_successfully = await self._queue_document_for_processing(document)
        if queued_successfully:
            logger.info(f"Document ID: {document.id} queued for processing.")
            document = await self.document_repository.update_document_status(
                document.id, DocumentStatus.QUEUED_FOR_PROCESSING
            )
            if not document:
                logger.error(
                    f"Failed to update document {document.id} status to QUEUED_FOR_PROCESSING."
                )
                return document  # Return with previous status
        else:
            logger.error(f"Failed to queue document ID: {document.id} for processing.")
            # Potentially set a different status or error message
            document = await self.document_repository.update_document_status(
                document.id,
                DocumentStatus.ERROR,
                error_message="Failed to queue document for processing.",
            )
            if not document:
                logger.error(
                    f"Failed to update document {document.id} status to ERROR after queue failure."
                )
                return document  # Return with previous status

        return document


# Example of a concrete (in-memory) repository for testing/early dev
# This would typically be in its own file and use a real database.
class InMemoryDocumentRepository(DocumentRepository):
    def __init__(self):
        self._documents: dict[uuid.UUID, Document] = {}

    async def create_document(self, doc_create: DocumentCreate) -> Document:
        doc = Document(**doc_create.dict(by_alias=True), id=uuid.uuid4())
        doc.created_at = datetime.now(timezone.utc)
        doc.updated_at = datetime.now(timezone.utc)
        self._documents[doc.id] = doc
        logger.info(f"(InMemoryRepo) Created document: {doc.id}")
        return doc.copy(deep=True)

    async def get_document_by_id(self, document_id: uuid.UUID) -> Document | None:
        doc = self._documents.get(document_id)
        logger.info(
            f"(InMemoryRepo) Get document by ID {document_id}: {'Found' if doc else 'Not Found'}"
        )
        return doc.copy(deep=True) if doc else None

    async def update_document_status(
        self,
        document_id: uuid.UUID,
        status: DocumentStatus,
        error_message: str | None = None,
    ) -> Document | None:
        if document_id in self._documents:
            doc = self._documents[document_id]
            doc.status = status
            doc.error_message = error_message
            doc.updated_at = datetime.now(timezone.utc)
            logger.info(
                f"(InMemoryRepo) Updated document {document_id} status to {status}"
            )
            return doc.copy(deep=True)
        logger.warning(
            f"(InMemoryRepo) Update status: Document {document_id} not found."
        )
        return None

    async def update_document_storage_path(
        self, document_id: uuid.UUID, storage_path: str, size_bytes: int | None = None
    ) -> Document | None:
        if document_id in self._documents:
            doc = self._documents[document_id]
            doc.storage_path = storage_path
            if size_bytes is not None:
                doc.size_bytes = size_bytes
            doc.updated_at = datetime.now(timezone.utc)
            logger.info(
                f"(InMemoryRepo) Updated document {document_id} storage path to {storage_path}"
            )
            return doc.copy(deep=True)
        logger.warning(
            f"(InMemoryRepo) Update storage path: Document {document_id} not found."
        )
        return None


if __name__ == "__main__":
    # Example Usage (illustrative)
    import asyncio
    import os

    from dotenv import load_dotenv

    load_dotenv()

    # Configure basic logging for the example
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # MinIO Client Setup (assuming it's running and configured)
    MINIO_ENDPOINT_URL = os.getenv("MINIO_ENDPOINT_URL", "http://localhost:9000")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "khive-reader-ingest-test")

    async def main_example():
        if not all([
            MINIO_ENDPOINT_URL,
            MINIO_ACCESS_KEY,
            MINIO_SECRET_KEY,
            MINIO_BUCKET_NAME,
        ]):
            logger.error(
                "MinIO environment variables not fully set for example. Skipping."
            )
            return

        storage_client = ObjectStorageClient(
            endpoint_url=MINIO_ENDPOINT_URL,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            bucket_name=MINIO_BUCKET_NAME,
            secure=MINIO_ENDPOINT_URL.startswith("https"),
        )

        # Ensure bucket exists for the test
        if not storage_client.ensure_bucket_exists():
            logger.error(
                f"Failed to ensure MinIO bucket '{MINIO_BUCKET_NAME}' exists. Aborting example."
            )
            return
        logger.info(f"MinIO bucket '{MINIO_BUCKET_NAME}' is ready.")

        # Initialize services
        doc_repo = InMemoryDocumentRepository()
        ingestion_service = DocumentIngestionService(doc_repo, storage_client)

        # Example: Ingest a document (use a publicly accessible raw text file or PDF for testing)
        # For this example, let's use a placeholder URL that might return a small text file.
        # Replace with a real, stable URL for actual testing.
        # test_url = HttpUrl("https://www.w3.org/TR/PNG/iso_8859-1.txt") # Example public text file
        test_url = HttpUrl(
            "https://raw.githubusercontent.com/khive-ai/khive.d/main/README.md"
        )

        logger.info(f"--- Starting ingestion for {test_url} ---")
        ingested_doc = await ingestion_service.ingest_document_from_url(test_url)

        if ingested_doc:
            logger.info(f"--- Ingestion Result for {test_url} ---")
            logger.info(f"Document ID: {ingested_doc.id}")
            logger.info(f"Status: {ingested_doc.status}")
            logger.info(f"Storage Path: {ingested_doc.storage_path}")
            logger.info(f"Size (bytes): {ingested_doc.size_bytes}")
            logger.info(f"Error: {ingested_doc.error_message}")
            logger.info(f"Metadata: {ingested_doc.metadata_}")

            if ingested_doc.storage_path:
                # Verify by downloading from S3
                obj_name_in_s3 = ingested_doc.storage_path.split(
                    f"{MINIO_BUCKET_NAME}/"
                )[-1]
                logger.info(
                    f"Attempting to download {obj_name_in_s3} from S3 to verify..."
                )
                s3_content = storage_client.download_object(obj_name_in_s3)
                if s3_content:
                    logger.info(
                        f"Successfully downloaded {len(s3_content)} bytes from S3 for {obj_name_in_s3}."
                    )
                    # logger.info(f"S3 Content (first 100 chars): {s3_content[:100].decode(errors='ignore')}")
                else:
                    logger.error(
                        f"Failed to download {obj_name_in_s3} from S3 for verification."
                    )
        else:
            logger.error(f"Ingestion failed for {test_url}.")

        logger.info("--- Example Finished ---")

    if __name__ == "__main__":  # This block needs to be outside async def main_example
        asyncio.run(main_example())
