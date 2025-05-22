---
title: "Technical Design Specification: Reader Ingestion Pipeline with Pydapter"
by: khive-architect
created: 2025-05-22
updated: 2025-05-22
version: 1.0
doc_type: TDS
output_subdir: tds
description: "Technical Design Specification for refactoring the Khive Reader ingestion pipeline to use the pydapter library for data persistence and interactions, addressing Issue #26."
date: 2025-05-22
issue_refs:
  - "#26"
  - "#25"
  - "#24"
  - "#27"
---

# Guidance

**Purpose** Lay out an **implementation-ready** blueprint for a microservice or
feature: data models, APIs, flows, error handling, security, etc.

**When to Use**

- After the Research is done, to guide the Implementer.
- Before Implementation Plan or simultaneously with it.

**Best Practices**

- Keep the design as **complete** as possible so coders can proceed with minimal
  guesswork.
- Emphasize any performance or security corners.
- Use diagrams (Mermaid) for clarity.

---

# Technical Design Specification: Reader Ingestion Pipeline with Pydapter

## 1. Overview

### 1.1 Purpose

This document outlines the technical design for refactoring the Khive Reader
service's document ingestion pipeline. The primary goal is to integrate the
`pydapter` library for all data persistence and interaction tasks, replacing
previous custom solutions for database and potentially object storage
management. This change aims to leverage `pydapter`'s adapter pattern, Pydantic
model integration, and event-driven capabilities to create a more robust,
maintainable, and extensible ingestion system.

### 1.2 Scope

**In Scope:**

- Redesign of data persistence for `Document` and `DocumentChunk` models using
  `pydapter` adapters.
- Re-evaluation and potential redesign of object storage interactions
  (`ObjectStorageClient`) using or integrating with `pydapter`.
- Refactoring of the `DocumentIngestionService` to utilize `pydapter` for its
  core operations.
- Definition of how CRUD operations and vector searches on `DocumentChunk` will
  be performed via `pydapter`.
- Consideration of `pydapter`'s event model (e.g., `@as_event`) for asynchronous
  processing within the ingestion pipeline.
- Outline of impacts on downstream processes like text extraction, chunking, and
  embedding (Issue #27).

**Out of Scope:**

- Detailed implementation of `pydapter` adapters if custom ones are needed (this
  TDS will specify the need and high-level design).
- Full implementation details of downstream processing services (text
  extraction, embedding), though their interaction points will be considered.
- UI/CLI command implementation details for `khive reader ingest`, beyond how it
  triggers the `DocumentIngestionService`.

### 1.3 Background

The Khive Reader service requires an efficient pipeline to ingest various
document types, store them, process them into manageable chunks, and make them
available for embedding and search. Previous design discussions (Issue #26,
Issue #25) outlined components like `ObjectStorageClient` and
`DocumentRepository`.

A new critical requirement mandates the use of the `pydapter` library for data
persistence and interactions. `Pydapter` (as understood from provided context in
Issue #26 comments - `(pplx:placeholder-pydapter-doc)`) is an asynchronous
library featuring an adapter pattern, deep integration with Pydantic models
(e.g., `AsyncAdaptable`), and potentially an event model (e.g., `@as_event`).
This TDS refactors the ingestion architecture to align with `pydapter`.

Relevant Issues:

- Issue #26: "Implement `khive reader ingest` command" - Core ingestion logic.
- Issue #25: "Design `DocumentRepository`" - Now superseded/refactored by
  `pydapter`.
- Issue #24: "Define `Document` and `DocumentChunk` Pydantic Models" - These
  models will be made `pydapter`-compatible.
- Issue #27: "Implement Text Extraction, Chunking, and Embedding" - Downstream
  consumers of ingested data.

### 1.4 Design Goals

- **Pydapter-centric Architecture:** Fully leverage `pydapter` for data
  persistence and interactions.
- **Modularity:** Design components (services, adapters) with clear
  responsibilities.
- **Asynchronous Operations:** Ensure the pipeline is fully asynchronous,
  utilizing `pydapter`'s async capabilities.
- **Extensibility:** Allow for easy addition of new document types or `pydapter`
  adapters in the future.
- **Maintainability:** Simplify data access logic by using `pydapter`'s
  abstractions.
- **Testability:** Design components that are easily testable, especially
  interactions with `pydapter` adapters.

### 1.5 Key Constraints

- **Mandatory `pydapter` Usage:** All data persistence and related interactions
  must use `pydapter`.
- **Pydantic Models:** `Document` and `DocumentChunk` (Issue #24) are Pydantic
  models and must be integrated with `pydapter` (e.g., via `AsyncAdaptable`).
- **Asynchronous Nature:** The entire ingestion pipeline must be asynchronous.
- **Compatibility:** The solution must be compatible with chosen database (e.g.,
  PostgreSQL for metadata, Qdrant for vectors) and local object storage (e.g.,
  MinIO running in Docker, or local filesystem via pydapter if suitable).

## 2. Architecture

### 2.1 Component Diagram

The architecture will revolve around the `DocumentIngestionService`, which
orchestrates the ingestion process using various `pydapter` adapters.

```mermaid
graph TD
    subgraph Khive CLI / API
        A[khive reader ingest]
    end

    subgraph Document Ingestion Pipeline
        A --> DIS[DocumentIngestionService];

        subgraph Pydapter Adapters
            DIS --> DOA[DocumentObjectAdapter Local/MinIO-Docker];
            DIS --> DMA[DocumentMetadataAdapter Postgres];
            DIS --> DCA[DocumentChunkAdapter Qdrant/VectorDB];
        end

        subgraph External Systems
            DOA --> LocalOS[(Local Object Storage e.g., MinIO via Docker)];
            DMA --> PG[(PostgreSQL Database)];
            DCA --> QD[(Qdrant/Vector Database)];
        end

        DIS --> TEP[TextExtractionProcess Issue #27];
        TEP --> CHP[ChunkingProcess Issue #27];
        CHP --> EMP[EmbeddingProcess Issue #27];
        EMP --> DCA; # Persist embeddings via chunk adapter
    end

    %% Styling
    classDef service fill:#D6EAF8,stroke:#AED6F1,stroke-width:2px;
    classDef adapter fill:#D1F2EB,stroke:#A3E4D7,stroke-width:2px;
    classDef process fill:#FCF3CF,stroke:#F7DC6F,stroke-width:2px;
    classDef external fill:#FADBD8,stroke:#F1948A,stroke-width:2px;

    class DIS,TEP,CHP,EMP service;
    class DOA,DMA,DCA adapter;
    class LocalOS,PG,QD external;
    class A process;
```

**Key Components:**

- **`DocumentIngestionService`**: Orchestrates the ingestion flow. Uses
  `pydapter` adapters.
- **`DocumentObjectAdapter` (Local/MinIO-Docker)**: A `pydapter` adapter
  (potentially custom if not available out-of-the-box) responsible for
  interacting with local object storage (e.g., a MinIO instance running in
  Docker, or direct filesystem access if `pydapter` supports this robustly for
  binary objects). Handles upload/download of raw documents and extracted text.
- **`DocumentMetadataAdapter` (Postgres)**: A `pydapter` adapter (e.g.,
  `AsyncPostgresAdapter`) for managing `Document` metadata in a relational
  database.
- **`DocumentChunkAdapter` (Qdrant/VectorDB)**: A `pydapter` adapter (e.g.,
  `AsyncQdrantAdapter` or a generic vector DB adapter) for storing and searching
  `DocumentChunk` objects, including their vector embeddings.
- **Downstream Processes (Issue #27)**: Text Extraction, Chunking, Embedding
  services/processes that are triggered after initial ingestion and interact
  with `pydapter` adapters to read/write data.

### 2.2 Dependencies

- **`pydapter` library**: Core dependency for data persistence and interaction.
  `(pplx:placeholder-pydapter-doc)`
- **Pydantic**: For data modeling.
- **Database Drivers**: e.g., `asyncpg` for PostgreSQL, Qdrant client library.
- **MinIO Client Library / Filesystem Libraries**: e.g., `minio-py` (if
  interacting with a local MinIO Docker instance via a custom adapter) or
  relevant Python filesystem libraries (if `pydapter` supports direct filesystem
  object storage).
- **Khive Core Libraries**: For shared utilities, configuration.

### 2.3 Data Flow (High-Level Ingestion)

```mermaid
sequenceDiagram
    participant CLI as khive reader ingest
    participant DIS as DocumentIngestionService
    participant DOA as DocumentObjectAdapter (Local/MinIO-Docker)
    participant DMA as DocumentMetadataAdapter (Postgres)
    participant Proc as DownstreamProcessing (Text Extract, Chunk, Embed - Issue #27)
    participant DCA as DocumentChunkAdapter (Qdrant)

    CLI->>+DIS: ingest_document(file_path, metadata)
    DIS->>+DOA: store_raw_document(file_path)
    DOA-->>-DIS: raw_doc_storage_ref (e.g., local MinIO URI or file path)
    DIS->>+DMA: create_document_record(raw_doc_storage_ref, metadata)
    DMA-->>-DIS: document_id
    Note over DIS: Document record created. Raw file stored.
    DIS-)+Proc: trigger_processing(document_id, raw_doc_storage_ref)
    Note over Proc: Proc reads raw doc via DOA, extracts text, stores it via DOA.
    Note over Proc: Proc chunks text, generates embeddings.
    Proc->>+DCA: store_chunks_with_embeddings(document_id, chunks_data)
    DCA-->>-Proc: stored_chunk_ids
    Proc--)-DIS: processing_complete(document_id, status)
    DIS->>+DMA: update_document_status(document_id, status)
    DMA-->>-DIS: updated_document_record
```

_Note: `pydapter`'s `@as_event` or similar event mechanisms could be used to
decouple `DIS` from `DownstreamProcessing` steps, making them event-driven._

## 3. Interface Definitions

### 3.1 API Endpoints

The primary entry point is the `khive reader ingest` CLI command. This TDS
focuses on the service layer triggered by this command. The CLI command itself
is defined in `src/khive/commands/reader.py` and
`src/khive/cli/khive_reader.py`.

### 3.2 Internal Interfaces (`DocumentIngestionService`)

The `DocumentIngestionService` will expose methods like:

```python
from pydantic import BaseModel
from typing import Dict, Any, Optional
from khive.reader.models import Document, DocumentChunk # Assuming these are defined as per Issue #24

class DocumentIngestionService:
    def __init__(
        self,
        object_adapter: pydapter.BaseAsyncAdapter, # e.g., DocumentObjectAdapter
        metadata_adapter: pydapter.BaseAsyncAdapter, # e.g., DocumentMetadataAdapter for Document model
        chunk_adapter: pydapter.BaseAsyncAdapter # e.g., DocumentChunkAdapter for DocumentChunk model
    ):
        self.object_adapter = object_adapter
        self.metadata_adapter = metadata_adapter
        self.chunk_adapter = chunk_adapter

    async def ingest_document(self, file_path: str, user_metadata: Optional[Dict[str, Any]] = None) -> Document:
        """
        Orchestrates the ingestion of a new document.
        1. Stores raw document using object_adapter.
        2. Creates Document metadata record using metadata_adapter.
        3. Potentially triggers downstream processing (e.g., via pydapter @as_event or direct call).
        """
        pass

    # Potentially methods to handle updates/status from downstream processes
    # async def update_document_processing_status(self, document_id: str, status: str, details: Dict) -> Document:
    #    pass

    # Methods for downstream processes to interact (could also be direct adapter usage)
    # async def store_extracted_text(self, document_id: str, text_content: str) -> str: # returns storage_ref
    #    pass
    # async def store_document_chunks(self, document_id: str, chunks: List[DocumentChunk]) -> List[str]: # returns chunk_ids
    #    pass
```

### 3.3 Pydapter Adapter Interfaces (Conceptual)

Adapters will conform to `pydapter.BaseAsyncAdapter` (or similar `pydapter`
protocol).

**`DocumentMetadataAdapter` (for `Document` model):**

- `save(document: Document) -> Document`
- `get_by_id(document_id: str) -> Optional[Document]`
- `update(document: Document) -> Document`
- `delete(document_id: str) -> bool`
- `list_documents(...) -> List[Document]`

**`DocumentChunkAdapter` (for `DocumentChunk` model):**

- `save_batch(chunks: List[DocumentChunk]) -> List[DocumentChunk]`
- `get_by_id(chunk_id: str) -> Optional[DocumentChunk]`
- `get_chunks_for_document(document_id: str) -> List[DocumentChunk]`
- `search_chunks(query_embedding: List[float], top_k: int, filter_criteria: Optional[Dict] = None) -> List[DocumentChunk]`
- `delete_chunks_for_document(document_id: str) -> bool`

**`DocumentObjectAdapter` (Local Object Storage / MinIO-Docker):** This might be
a more specialized adapter if `pydapter` doesn't have a generic object storage
one. It could target a local MinIO instance (running in Docker) or potentially
direct filesystem operations if `pydapter` offers such an adapter suitable for
binary objects.

- `upload_file(file_path: str, destination_key: str, content_type: Optional[str] = None) -> str`
  (returns URI/key)
- `upload_content(content: bytes, destination_key: str, content_type: Optional[str] = None) -> str`
- `download_file(source_key: str, destination_path: str)`
- `download_content(source_key: str) -> bytes`
- `delete_object(key: str) -> bool`
- `get_object_uri(key: str) -> str`

## 4. Data Models

Data models (`Document`, `DocumentChunk`) are defined as Pydantic models (Issue
#24). They will need to be made compatible with `pydapter`, likely by inheriting
from a `pydapter.AsyncAdaptable` base class or using a similar mechanism
provided by `pydapter`. `(pplx:placeholder-pydapter-doc)`

### 4.1 `pydapter`-compatible Pydantic Models

Example (conceptual, actual implementation depends on `pydapter` specifics):

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
# Assuming pydapter provides a base or a way to register models
# from pydapter import AsyncAdaptable # Conceptual

# class BasePydapterModel(AsyncAdaptable, BaseModel): # Conceptual
class BasePydapterModel(BaseModel): # Placeholder if AsyncAdaptable is a decorator or registration
    class Config:
        orm_mode = True # If pydapter uses ORM-like features

class Document(BasePydapterModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())) # Or generated by pydapter adapter
    source_uri: Optional[str] = None # URI of the original document (e.g., local path, web URL)
    storage_uri: Optional[str] = None # URI in local object storage (e.g., path within local MinIO or filesystem path)
    extracted_text_uri: Optional[str] = None # URI in local object storage for extracted text
    mime_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict) # User-provided and system-generated metadata
    status: str = "PENDING" # e.g., PENDING, PROCESSING, COMPLETED, FAILED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    # pydapter specific fields/methods might be added by inheritance or decorators

class DocumentChunk(BasePydapterModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())) # Or generated by pydapter adapter
    document_id: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict) # Chunk-specific metadata, e.g., page number
    embedding: Optional[List[float]] = None # Vector embedding
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    # pydapter specific fields/methods
```

### 4.2 Domain Models

The Pydantic models above serve as the primary domain models.

### 4.3 Database Schema

Database schemas for PostgreSQL (for `Document` metadata) and Qdrant (for
`DocumentChunk` with vectors) will be implicitly defined by the `pydapter`
adapters and the Pydantic models. `Pydapter` might include a migration system or
expect schema to be managed externally/initially.
`(pplx:placeholder-pydapter-doc)`

- **PostgreSQL (`Document` table):** Columns corresponding to `Document` model
  fields.
- **Qdrant (`DocumentChunk` collection):** Fields corresponding to
  `DocumentChunk` model fields, with a vector field for `embedding`.

## 5. Behavior

### 5.1 Core Workflows

**A. Document Ingestion (Happy Path):**

1. `khive reader ingest <file_path> --metadata '{"key": "value"}'` is executed.
2. CLI invokes `DocumentIngestionService.ingest_document(file_path, metadata)`.
3. `DocumentIngestionService`: a. Uses `DocumentObjectAdapter` to upload the raw
   file from `file_path` to local object storage (e.g., MinIO via Docker). Gets
   back `storage_uri`. b. Constructs a `Document` Pydantic model instance with
   `source_uri`, `storage_uri`, `mime_type`, user `metadata`, and initial
   `status` (e.g., "UPLOADED"). c. Uses
   `DocumentMetadataAdapter.save(document_model)` to persist the `Document`
   record in PostgreSQL. Gets back the persisted `Document` model (possibly with
   a generated ID). d. **Event Triggering (Option 1: `pydapter @as_event`):** If
   `DocumentMetadataAdapter.save` is decorated with `@as_event` (or similar
   `pydapter` mechanism), saving the `Document` automatically publishes an event
   (e.g., `DocumentCreatedEvent`) with document details. e. **Event Triggering
   (Option 2: Explicit Event/Queue):** `DocumentIngestionService` explicitly
   publishes an event or places a message on an internal queue for downstream
   processing.
4. Downstream Processing (Issue #27 - Text Extraction, Chunking, Embedding): a.
   A listener/worker picks up the `DocumentCreatedEvent` (or queue message). b.
   **Text Extraction:** i. Uses `DocumentObjectAdapter` to download the raw
   document content from `storage_uri`. ii. Extracts text. iii. Uses
   `DocumentObjectAdapter` to upload extracted text to local object storage.
   Gets `extracted_text_uri`. iv. Uses `DocumentMetadataAdapter.update()` to
   save `extracted_text_uri` and update `Document.status` (e.g.,
   "TEXT_EXTRACTED"). c. **Chunking:** i. Uses `DocumentObjectAdapter` to
   download extracted text. ii. Chunks the text into `DocumentChunk` Pydantic
   models, linking them to `document_id`. d. **Embedding:** i. Generates vector
   embeddings for each `DocumentChunk.text`. ii. Updates `DocumentChunk` models
   with their embeddings. e. Uses
   `DocumentChunkAdapter.save_batch(list_of_chunks)` to store all chunks and
   their embeddings in Qdrant. f. Uses `DocumentMetadataAdapter.update()` to set
   `Document.status` to "COMPLETED".
5. `DocumentIngestionService.ingest_document` returns the initial `Document`
   model (or an ID/status).

**B. Vector Search on Chunks:**

1. A search service receives a query.
2. Query is embedded to get `query_embedding`.
3. Search service uses
   `DocumentChunkAdapter.search_chunks(query_embedding, top_k=N, ...)` to find
   relevant chunks from Qdrant.
4. Results are processed and returned.

### 5.2 Error Handling

- **Adapter Errors:** `pydapter` adapters should raise specific exceptions for
  database/storage connection issues, query failures, object not found, etc.
  `(pplx:placeholder-pydapter-doc)`
- **`DocumentIngestionService`**: Will catch exceptions from adapters and
  internal logic.
  - Transient errors (e.g., network issues) might be handled with retries
    (possibly managed by `pydapter` or a resilience library).
  - Persistent errors will result in the `Document.status` being set to "FAILED"
    with error details stored in `Document.metadata`.
- **Downstream Processing Errors:** Errors in text extraction, chunking, or
  embedding should update the `Document.status` to "FAILED" and log details.
- **Validation Errors:** Pydantic models will provide data validation.
  `pydapter` should handle or propagate these.

### 5.3 Security Considerations

- **Credentials Management:** Database, object storage, and `pydapter` (if it
  has its own auth) credentials must be securely managed (e.g., via environment
  variables, secrets manager). `pydapter` adapters will be configured with these
  credentials.
- **Data in Transit:** Ensure TLS is used for connections to PostgreSQL and
  Qdrant. For local MinIO (Docker), configure TLS if accessing over a network
  interface; for direct filesystem access, this is less relevant but ensure
  proper file permissions.
- **Data at Rest:** Encryption for data at rest in object storage and databases
  should be configured at the storage/DB level if required.
- **Input Sanitization:** While Pydantic handles type validation, be mindful of
  any string inputs that might be used in constructing queries if `pydapter`
  allows raw query components (though typically it abstracts this).

## 6. External Interactions

### 6.1 Dependencies on Other Services

- **PostgreSQL Database:** For storing `Document` metadata. Accessed via
  `DocumentMetadataAdapter`.
- **Qdrant/Vector Database:** For storing `DocumentChunk` objects and their
  embeddings. Accessed via `DocumentChunkAdapter`.
- **Local Object Storage (e.g., MinIO via Docker or direct filesystem access
  managed by pydapter):** For storing raw documents and extracted text. Accessed
  via `DocumentObjectAdapter`.

### 6.2 External API Integrations

This section primarily refers to the `pydapter` adapters themselves as the
"clients" to these external systems.

```python
# Conceptual pydapter adapter initialization (depends on pydapter's API)
# from pydapter.adapters.postgres import AsyncPostgresAdapter # Conceptual
# from pydapter.adapters.qdrant import AsyncQdrantAdapter # Conceptual
# from khive.reader.adapters import LocalObjectAdapter # Custom or pydapter-provided

# postgres_adapter = AsyncPostgresAdapter(dsn="postgresql+asyncpg://user:pass@host/db", model=Document)
# qdrant_adapter = AsyncQdrantAdapter(host="localhost", port=6333, collection_name="document_chunks", model=DocumentChunk)
# local_object_adapter = LocalObjectAdapter(storage_type="minio_docker", endpoint_url="http://localhost:9000", access_key="minio", secret_key="minio123", bucket_name="khive-documents")
# OR
# local_object_adapter = LocalObjectAdapter(storage_type="filesystem", base_path="/var/khive_data/objects")

# document_ingestion_service = DocumentIngestionService(
#     object_adapter=local_object_adapter,
#     metadata_adapter=postgres_adapter,
#     chunk_adapter=qdrant_adapter
# )
```

## 7. Performance Considerations

### 7.1 Expected Load

- The system should handle ingestion of hundreds to thousands of documents per
  day initially.
- Document sizes can vary from KBs to tens of MBs.
- Vector search queries will depend on application usage.

### 7.2 Scalability Approach

- **Asynchronous Processing:** The use of `async` operations and `pydapter`'s
  async capabilities is fundamental.
- **Stateless Services:** `DocumentIngestionService` and downstream processing
  components should be designed as stateless as possible to allow horizontal
  scaling.
- **Database/Storage Scaling:** PostgreSQL and Qdrant (running locally, perhaps
  in Docker) have their own scaling considerations for a local setup (resource
  allocation to Docker). Local MinIO (Docker) also scales based on allocated
  resources. Direct filesystem storage scales with disk space.
- **`pydapter` Performance:** Assumed to be efficient. Performance
  characteristics of specific adapters need to be understood.
  `(pplx:placeholder-pydapter-doc)`
- **Batch Operations:** Utilize batch operations provided by `pydapter` adapters
  (e.g., `save_batch` for chunks) where possible.

### 7.3 Optimizations

- Efficient serialization/deserialization of Pydantic models.
- Connection pooling for database adapters (likely handled by `pydapter`).
- Optimized vector indexing in Qdrant.

### 7.4 Caching Strategy

- Caching is not a primary concern for the ingestion pipeline itself but might
  be relevant for frequently accessed document metadata or search results at a
  higher application layer.

## 8. Observability

### 8.1 Logging

- Structured logging (e.g., JSON format) throughout the
  `DocumentIngestionService` and `pydapter` adapters.
- Log key events: document received, storage operations, database operations,
  processing steps (start, end, errors), status changes.
- Include correlation IDs (e.g., `document_id`) in logs.

### 8.2 Metrics

- **Ingestion Rate:** Number of documents ingested per unit of time.
- **Processing Time:** Average time taken for each stage (upload, metadata save,
  text extraction, chunking, embedding).
- **Error Rates:** Number and type of errors encountered in adapters and
  services.
- **Queue Lengths (if applicable):** If `pydapter` events or explicit queues are
  used.
- **Adapter Performance:** Latency of `pydapter` adapter operations.

### 8.3 Tracing

- Distributed tracing (e.g., OpenTelemetry) can be integrated to trace requests
  across the `DocumentIngestionService` and its interactions with `pydapter`
  adapters and downstream processes.

## 9. Testing Strategy

### 9.1 Unit Testing

- Test business logic within `DocumentIngestionService` by mocking `pydapter`
  adapters.
- Test individual `pydapter` adapter logic if custom adapters are developed
  (e.g., `DocumentObjectAdapter`).
- Test Pydantic model validation and transformations.

### 9.2 Integration Testing

- Test `DocumentIngestionService` with real (or test-containerized) instances of
  PostgreSQL, Qdrant, and local object storage (e.g., Dockerized MinIO), using
  actual `pydapter` adapters.
- Verify the end-to-end ingestion flow: file upload -> metadata persistence ->
  chunk persistence -> vector search.
- Test `pydapter` event handling if used.

### 9.3 Performance Testing

- Load test the ingestion pipeline to measure throughput and identify
  bottlenecks.
- Test vector search performance under load.

## 10. Deployment and Configuration

### 10.1 Deployment Requirements

- Python runtime environment.
- Access to PostgreSQL, Qdrant (likely running in Docker locally).
- Local object storage solution (e.g., Dockerized MinIO instance or a configured
  filesystem path accessible by the application).
- Configuration for `pydapter` adapters.

### 10.2 Configuration Parameters

```json
{
  "PYDAPTER_POSTGRES_DSN": "postgresql+asyncpg://user:pass@localhost:5432/khive_reader_db",
  "PYDAPTER_QDRANT_HOST": "localhost",
  "PYDAPTER_QDRANT_PORT": 6333,
  "PYDAPTER_QDRANT_COLLECTION_DOCUMENTS": "khive_documents",
  "PYDAPTER_QDRANT_COLLECTION_CHUNKS": "khive_document_chunks",
  "LOCAL_OBJECT_STORAGE_TYPE": "minio_docker", // or "filesystem"
  "MINIO_DOCKER_ENDPOINT": "http://localhost:9000", // if type is "minio_docker"
  "MINIO_DOCKER_ACCESS_KEY": "minioadmin", // if type is "minio_docker"
  "MINIO_DOCKER_SECRET_KEY": "minioadmin", // if type is "minio_docker"
  "MINIO_DOCKER_BUCKET_NAME": "khive-documents", // if type is "minio_docker"
  "FILESYSTEM_STORAGE_BASE_PATH": "/var/khive_data/objects", // if type is "filesystem"
  "LOG_LEVEL": "INFO"
  // Other pydapter specific configurations
}
```

These will be managed via Khive's standard configuration system (e.g., Pydantic
settings, .env files).

## 11. Risks & Mitigations

### 11.1 Risk: `pydapter` Feature Gaps or Misinterpretation

- **Description:** The design relies on assumed capabilities of `pydapter`
  (e.g., specific adapter availability for local MinIO/filesystem, event model
  details, migration handling) based on limited information. Actual features
  might differ or require more custom development.
- **Mitigation:**
  1. **Early Spike/PoC:** The Implementer should conduct an early
     proof-of-concept with `pydapter` and the target databases/storage to
     validate core assumptions as soon as the actual `pydapter` documentation is
     fully reviewed. `(pplx:placeholder-pydapter-doc)`
  2. **Flexible Adapter Design:** Design custom adapters (if needed) with a
     clear interface, allowing for easier replacement or modification if
     `pydapter`'s native support is different.
  3. **Iterative Refinement:** Be prepared to iterate on this TDS based on
     findings from the PoC.

### 11.2 Risk: Complexity of Custom `pydapter` Adapters

- **Description:** If `pydapter` does not provide out-of-the-box adapters for
  all needed local systems (especially for local MinIO Docker interaction or
  robust filesystem object storage, or specific Qdrant features), developing
  robust, async custom adapters can be complex and time-consuming.
- **Mitigation:**
  1. **Prioritize Native Adapters:** Thoroughly investigate if `pydapter` or its
     ecosystem offers existing solutions before committing to custom
     development.
  2. **Simplified Custom Adapter Scope:** If custom adapters are necessary,
     start with the minimal required functionality and iterate.
  3. **Leverage Existing Libraries:** Build custom adapters on top of
     well-tested underlying client libraries (e.g., `minio-py` for local MinIO,
     Python's `aiofiles` for filesystem).

### 11.3 Risk: Performance Overheads of `pydapter`

- **Description:** While `pydapter` is assumed to be performant, any abstraction
  layer can introduce overhead. Specific adapter implementations or general
  `pydapter` mechanics might impact ingestion speed or query latency.
- **Mitigation:**
  1. **Performance Testing:** Conduct thorough performance testing early in the
     implementation phase, focusing on critical paths like batch chunk saving
     and vector search.
  2. **Consult `pydapter` Documentation:** Review `pydapter` performance
     guidelines and best practices. `(pplx:placeholder-pydapter-doc)`
  3. **Direct Client Fallback (Contingency):** In extreme cases, for highly
     performance-critical operations where `pydapter` overhead is prohibitive,
     consider if a direct client library usage for that specific operation is
     feasible as a last resort, while still using `pydapter` for other
     operations. This should be avoided if possible to maintain consistency.

## 12. Open Questions

1. **`pydapter` Local Object Storage Adapter:** Does `pydapter` provide a
   generic adapter suitable for local object storage (like a Dockerized MinIO
   instance via its S3-compatible API, or direct filesystem object management)?
   If not, what is the recommended pattern for integrating such local storage
   (e.g., custom adapter development guidelines)?
   `(pplx:placeholder-pydapter-doc)`
2. **`pydapter` Event Model Details:** What are the specific mechanisms and
   guarantees of `pydapter`'s event model (e.g., `@as_event`)? How are events
   published, subscribed to, and what are the delivery semantics (at-least-once,
   at-most-once)? `(pplx:placeholder-pydapter-doc)`
3. **`pydapter` Migration Handling:** Does `pydapter` include a database
   migration system, or is schema management expected to be handled externally
   (e.g., Alembic for PostgreSQL, manual for Qdrant collections)?
   `(pplx:placeholder-pydapter-doc)`
4. **`pydapter` Transaction/Unit of Work:** How does `pydapter` handle
   transactions or units of work across multiple adapter operations, if at all?
   This is important for ensuring consistency, e.g., when saving a `Document`
   and then triggering an event.

## 13. Appendices

### Appendix A: Alternative Designs

- **No `pydapter` (Original Design):** The original approach involved custom
  repositories and clients (Issue #25, #26). This was superseded by the
  requirement to use `pydapter`.
- **Partial `pydapter` Adoption:** Using `pydapter` only for database
  interactions and keeping a separate `ObjectStorageClient`. This was considered
  less aligned with the goal of a unified `pydapter`-centric approach.

### Appendix B: Research References

- `pydapter` Documentation: `(pplx:placeholder-pydapter-doc)` - To be filled in
  by the implementer/researcher with actual links/references.
- Khive Issue #26: "Implement `khive reader ingest` command"
- Khive Issue #25: "Design `DocumentRepository`"
- Khive Issue #24: "Define `Document` and `DocumentChunk` Pydantic Models"
- Khive Issue #27: "Implement Text Extraction, Chunking, and Embedding"
- Qdrant Documentation: For vector storage concepts.
- PostgreSQL Documentation: For relational storage concepts.
- MinIO Documentation: For local Docker setup and S3-compatible API usage.
- Python Filesystem Libraries (e.g., `aiofiles`, `pathlib`): If direct
  filesystem object storage is considered.
