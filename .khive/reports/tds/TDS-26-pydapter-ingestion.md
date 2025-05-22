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
Issue #26 comments and available `pydapter` source code (e.g.,
[`pydapter.async_core.AsyncAdaptable`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/async_core.py#L92),
[`pydapter.protocols.event.@as_event`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/protocols/event.py#L63))
is an asynchronous library featuring an adapter pattern, deep integration with
Pydantic models (via the `AsyncAdaptable` mixin), and an event model driven by
the `@as_event` decorator. This TDS refactors the ingestion architecture to
align with `pydapter`.

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
  models and must be integrated with `pydapter` by inheriting from
  `pydapter.async_core.AsyncAdaptable`.
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
  [`pydapter.extras.async_postgres_.AsyncPostgresAdapter`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/extras/async_postgres_.py#L17))
  for managing `Document` metadata in a relational database.
- **`DocumentChunkAdapter` (Qdrant/VectorDB)**: A `pydapter` adapter
  (specifically
  [`pydapter.extras.async_qdrant_.AsyncQdrantAdapter`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/extras/async_qdrant_.py#L23))
  for storing and searching `DocumentChunk` objects, including their vector
  embeddings.
- **Downstream Processes (Issue #27)**: Text Extraction, Chunking, Embedding
  services/processes that are triggered after initial ingestion and interact
  with `pydapter` adapters to read/write data.

### 2.2 Dependencies

- **`pydapter` library**: Core dependency for data persistence and interaction.
  (see
  [`pydapter.protocols.event`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/protocols/event.py),
  [`pydapter.extras.async_qdrant_`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/extras/async_qdrant_.py),
  [`pydapter.extras.async_postgres_`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/extras/async_postgres_.py)).
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

_Note: `pydapter`'s
[`@as_event` decorator](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/protocols/event.py#L63)
can be used on methods (e.g., a service method that calls an adapter's `to_obj`)
to automatically capture the operation as an `Event` (which can be logged as a
`Log` object) and trigger further actions, potentially by persisting this `Log`
object using another adapter. This facilitates decoupling `DIS` from
`DownstreamProcessing`._

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
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
# Assuming Document, DocumentChunk are defined in khive.reader.models
# and inherit from pydapter.async_core.AsyncAdaptable
from khive.reader.models import Document, DocumentChunk
from pydapter.async_core import AsyncAdapter # Protocol for type hinting
from pydapter.extras.async_postgres_ import AsyncPostgresAdapter
from pydapter.extras.async_qdrant_ import AsyncQdrantAdapter
from pydapter.protocols.event import as_event, Event # For event handling

class DocumentIngestionService:
    def __init__(
        self,
        object_adapter: AsyncAdapter, # Custom DocumentObjectAdapter
        metadata_adapter: AsyncPostgresAdapter,
        chunk_adapter: AsyncQdrantAdapter,
        event_log_adapter: Optional[AsyncAdapter] = None # e.g., another AsyncPostgresAdapter for event logs
    ):
        self.object_adapter = object_adapter
        self.metadata_adapter = metadata_adapter
        self.chunk_adapter = chunk_adapter
        self.event_log_adapter = event_log_adapter

    # This method could be decorated with @as_event if the event creation
    # itself is the primary action we want to log and react to.
    # Alternatively, the underlying adapter calls within it could be wrapped
    # or a service method calling adapter.to_obj could be decorated.
    async def _store_document_metadata(self, doc_model: Document) -> Document:
        # This internal method is a candidate for @as_event if we want to log its execution
        # and potentially trigger downstream processes based on this specific event.
        # For example, if event_log_adapter is configured:
        # @as_event(adapter=self.event_log_adapter.__class__ if self.event_log_adapter else None, adapt=bool(self.event_log_adapter), event_type="DocumentMetadataStored")

        # For AsyncPostgresAdapter, to_obj expects the model instance and table name.
        # The Pydantic model 'Document' should have its __table_name__ or similar defined,
        # or table name passed in kw.
        await self.metadata_adapter.to_obj(
            doc_model,
            table=getattr(doc_model.__class__, '__tablename__', 'documents') # Example: get table from model or default
        )
        return doc_model

    async def ingest_document(self, file_path: str, user_metadata: Optional[Dict[str, Any]] = None) -> Document:
        """
        Orchestrates the ingestion of a new document.
        1. Stores raw document using object_adapter (custom).
        2. Creates Document metadata record using AsyncPostgresAdapter.
           This step, or a wrapper around it, can be an event source using @as_event.
        3. Downstream processing is triggered based on this event.
        """
        # 1. Store raw document (details depend on custom object_adapter)
        # Assuming object_adapter.to_obj returns a dict with 'storage_uri'
        obj_storage_result = await self.object_adapter.to_obj(
            {"file_path": file_path, "type": "raw"}, # Example input for custom adapter
            # ... other params for custom adapter
        )
        raw_doc_storage_uri = obj_storage_result.get("storage_uri") # Conceptual

        # 2. Create Document Pydantic model
        doc = Document(
            source_uri=file_path,
            storage_uri=raw_doc_storage_uri,
            metadata=user_metadata or {},
            status="UPLOADED"
        )

        # 3. Store document metadata & trigger event (implicitly or explicitly)
        # If _store_document_metadata is decorated with @as_event and configured to adapt,
        # it will persist an Event/Log object.
        persisted_doc = await self._store_document_metadata(doc)

        # Downstream processing would be triggered by listeners to the persisted event,
        # or by an explicit message queue if not using @as_event for direct triggering.

        return persisted_doc
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

Adapters will conform to the
[`pydapter.async_core.AsyncAdapter` protocol](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/async_core.py#L21).

**`DocumentMetadataAdapter` (for `Document` model, using
`AsyncPostgresAdapter`):** The `AsyncPostgresAdapter` (which inherits from
`AsyncSQLAdapter`) will be used.

- `to_obj(document_model, table="documents", ...)`: Saves the `Document` model.
- `from_obj(Document, {"table": "documents", "selectors": {"id": "..."}}, ...)`:
  Retrieves `Document`. (Actual method signatures are `to_obj(subj, /, **kw)`
  and `from_obj(subj_cls, obj, /, **kw)`)

- `save(document: Document) -> Document`
- `get_by_id(document_id: str) -> Optional[Document]`
- `update(document: Document) -> Document`
- `delete(document_id: str) -> bool`
- `list_documents(...) -> List[Document]`

**`DocumentChunkAdapter` (for `DocumentChunk` model, using
`AsyncQdrantAdapter`):** The
[`pydapter.extras.async_qdrant_.AsyncQdrantAdapter`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/extras/async_qdrant_.py#L23)
will be used.

- `to_obj(chunks_list, collection="document_chunks", vector_field="embedding", id_field="id", ...)`:
  Saves `DocumentChunk` models. **Note:** The default
  `AsyncQdrantAdapter.to_obj` recreates the collection. This needs to be handled
  by either: a) Ensuring the collection is created once externally before
  ingestion starts. b) Modifying/extending the adapter or using Qdrant client
  directly for upsert without recreate if `pydapter` doesn't offer a flag. c)
  The `to_obj` method in the notebook example does not show
  `recreate_collection`, it directly upserts. The source code of
  `AsyncQdrantAdapter` shows `recreate_collection`. This discrepancy needs to be
  clarified by the implementer. For this TDS, we assume the collection exists or
  is managed to allow additive upserts.
- `from_obj(DocumentChunk, {"collection": "document_chunks", "query_vector": ..., "top_k": ...}, ...)`:
  Searches chunks. (Actual method signatures are `to_obj(subj, /, **kw)` and
  `from_obj(subj_cls, obj, /, **kw)`)

- `save_batch(chunks: List[DocumentChunk]) -> List[DocumentChunk]`
- `get_by_id(chunk_id: str) -> Optional[DocumentChunk]`
- `get_chunks_for_document(document_id: str) -> List[DocumentChunk]`
- `search_chunks(query_embedding: List[float], top_k: int, filter_criteria: Optional[Dict] = None) -> List[DocumentChunk]`
- `delete_chunks_for_document(document_id: str) -> bool`

**`DocumentObjectAdapter` (Local Object Storage / MinIO-Docker):** This might be
a more specialized adapter if `pydapter` doesn't have a generic object storage
one. It could target a local MinIO instance (running in Docker) or potentially
direct filesystem operations. As `pydapter` source does not show a readily
available adapter for this, a **custom `AsyncAdapter` will likely need to be
developed** for this purpose, potentially using `aiofiles` for filesystem
operations or `minio-py` for a local MinIO Docker instance.

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
from
[`pydapter.async_core.AsyncAdaptable`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/async_core.py#L92)
mixin. This allows them to use `adapt_to_async` and `adapt_from_async` methods.

### 4.1 `pydapter`-compatible Pydantic Models

Example (conceptual, actual implementation depends on `pydapter` specifics):

```python
import uuid
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydapter.async_core import AsyncAdaptable # Import the mixin

# Pydantic models will inherit from AsyncAdaptable to use pydapter's features.
# They also need to be compatible with the specific adapters.
# For AsyncPostgresAdapter, field names typically map to column names.
# For AsyncQdrantAdapter, 'id' and 'embedding' (default) fields are used.

class Document(AsyncAdaptable, BaseModel):
    # For AsyncPostgresAdapter, define __tablename__ or pass table name to to_obj/from_obj
    # __tablename__ = "documents" # Example for SQLAlchemy mapping if not using model_adapters directly

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_uri: Optional[str] = None
    storage_uri: Optional[str] = None # URI in local object storage
    extracted_text_uri: Optional[str] = None # URI for extracted text
    mime_type: Optional[str] = None
    # metadata field will map to JSONB in PostgreSQL
    metadata: Dict[str, Any] = Field(default_factory=dict, json_schema_extra={"db_type": "jsonb"})
    status: str = "PENDING"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True # For SQLAlchemy compatibility if models are generated by pydapter.model_adapters
        from_attributes = True # Pydantic v2

class DocumentChunk(AsyncAdaptable, BaseModel):
    # This model is primarily for Qdrant.
    # AsyncQdrantAdapter uses 'id' and 'embedding' fields by default.
    # Other fields become the payload.
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    text: str
    # metadata field will be part of the Qdrant payload
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: List[float] # Must be populated before sending to AsyncQdrantAdapter.to_obj
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        orm_mode = True
        from_attributes = True
```

### 4.2 Domain Models

The Pydantic models above serve as the primary domain models.

### 4.3 Database Schema

Database schemas for PostgreSQL (for `Document` metadata) and Qdrant (for
`DocumentChunk` with vectors) will be implicitly defined by the `pydapter`
adapters and the Pydantic models.

- **PostgreSQL:** `pydapter` includes a migrations system, likely leveraging
  Alembic (see
  [`pydapter.migrations.sql.alembic_adapter.py`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/migrations/sql/alembic_adapter.py)).
  Table schema for `Document` will be defined and managed through this. The
  `pydapter.model_adapters.postgres_model.PostgresModelAdapter` handles
  Pydantic-to-SQLAlchemy model conversion, including types like `JSONB` for
  `Document.metadata`.
- **Qdrant:** Collection (`document_chunks`) creation and configuration (vector
  size, distance metric) must be handled. The `AsyncQdrantAdapter.to_obj`
  method, as seen in source, attempts to `recreate_collection`. This behavior
  needs careful management in a production setup to avoid data loss. It's
  recommended to ensure the collection exists with the correct configuration
  before the ingestion service starts or modify adapter usage to only upsert.

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
   `DocumentMetadataAdapter.to_obj(document_model, table="documents")` to
   persist the `Document` record in PostgreSQL. d. **Event Triggering using
   `pydapter @as_event`**: A service method responsible for calling
   `DocumentMetadataAdapter.to_obj` (or the `to_obj` call itself if the adapter
   method could be decorated, though less likely for generic adapters) can be
   decorated with
   [`@as_event`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/protocols/event.py#L63).
   Example:
   ```python
   # In DocumentIngestionService or a dedicated event-sourcing part
   # @as_event(adapter=self.event_log_adapter_class, adapt=True, event_type="DocumentMetadataStored")
   # async def _persist_doc_and_log_event(self, doc: Document):
   #    await self.metadata_adapter.to_obj(doc, table="documents") # Or use doc.adapt_to_async
   #    return {"document_id": doc.id, "status": "METADATA_STORED"}
   ```
   When `_persist_doc_and_log_event` is called, `pydapter` will: i. Execute the
   function. ii. Create an `Event` object capturing its request and response.
   iii. If `adapt=True` and an `adapter` (e.g., for an SQL event log table) is
   provided to `@as_event`, it will convert the `Event` to a `Log` object (see
   [`pydapter.protocols.event.Event.to_log`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/protocols/event.py#L38))
   and persist it using the specified `event_log_adapter`. This `Log` object
   contains details like `event_type`, `content` (request/response of the
   decorated function), `status`, `duration`, etc.
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
   `DocumentChunkAdapter.to_obj(list_of_chunks, collection="document_chunks", vector_field="embedding", id_field="id")`
   to store all chunks and their embeddings in Qdrant. (Note:
   `AsyncQdrantAdapter.to_obj` takes `Sequence[T]`, so a list of chunks is
   appropriate). f. Uses
   `DocumentMetadataAdapter.to_obj(updated_document_model, table="documents", update_existing=True)`
   (assuming `AsyncSQLAdapter` supports an `update_existing` or similar flag for
   upsert/update, or a separate update method) to set `Document.status` to
   "COMPLETED". If not, a specific update method via `from_obj` with selectors
   and then `to_obj` or a dedicated update method in `AsyncSQLAdapter` would be
   needed.
5. `DocumentIngestionService.ingest_document` returns the initial `Document`
   model (or an ID/status).

**B. Vector Search on Chunks:**

1. A search service receives a query.
2. Query is embedded to get `query_embedding`.
3. Search service uses
   `DocumentChunkAdapter.from_obj(DocumentChunk, {"collection": "document_chunks", "query_vector": query_embedding, "top_k": N})`
   to find relevant chunks from Qdrant.
4. Results are processed and returned.

### 5.2 Error Handling

- **Adapter Errors:** `pydapter` adapters should raise specific exceptions for
  database/storage connection issues, query failures, object not found, etc.
  (see
  [`pydapter.exceptions`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/exceptions.py)).
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
from pydapter.extras.async_postgres_ import AsyncPostgresAdapter
from pydapter.extras.async_qdrant_ import AsyncQdrantAdapter
# from khive.reader.adapters import LocalObjectStorageAdapter # Assumed custom

# postgres_adapter = AsyncPostgresAdapter() # DSN and other params passed to to_obj/from_obj methods or configured globally
# qdrant_adapter = AsyncQdrantAdapter() # URL and other params passed to to_obj/from_obj methods
# local_object_adapter = LocalObjectStorageAdapter(...) # Custom adapter initialization

# # Example of registering adapters with a model (if using AsyncAdaptable mixin)
# Document.register_async_adapter(AsyncPostgresAdapter) # obj_key would be "async_pg"
# DocumentChunk.register_async_adapter(AsyncQdrantAdapter) # obj_key would be "async_qdrant"
# # Then use:
# # await doc_instance.adapt_to_async(obj_key="async_pg", table="documents", dsn=...)
# # await DocumentChunk.adapt_from_async({"collection": "chunks", ...}, obj_key="async_qdrant", url=...)

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
  characteristics of specific adapters need to be understood. (see
  [`pydapter.extras.async_qdrant_.AsyncQdrantAdapter`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/extras/async_qdrant_.py),
  [`pydapter.extras.async_sql_.AsyncSQLAdapter`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/extras/async_sql_.py)).
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
     fully reviewed (e.g., by studying its source code at
     `https://github.com/khive-ai/pydapter`).
  2. **Flexible Adapter Design:** Design custom adapters (if needed) with a
     clear interface, allowing for easier replacement or modification if
     `pydapter`'s native support is different.
  3. **Iterative Refinement:** Be prepared to iterate on this TDS based on
     findings from the PoC.

### 11.2 Risk: Complexity of Custom `pydapter` Adapters

- **Description:** If `pydapter` does not provide out-of-the-box adapters for
  all needed local systems (especially for local MinIO Docker interaction or
  robust filesystem object storage, as these are not explicitly provided by
  `pydapter`), developing robust, async custom adapters can be complex and
  time-consuming.
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
     guidelines and best practices by reviewing its source and examples.
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
   (e.g., custom adapter development guidelines)? The `pydapter` source does not
   show a built-in adapter for this.
2. **`pydapter` Event Model Details:** What are the specific mechanisms and
   guarantees of `pydapter`'s event model (e.g., `@as_event`)? How are events
   published, subscribed to, and what are the delivery semantics (at-least-once,
   at-most-once)? The
   [`@as_event` decorator](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/protocols/event.py#L63)
   allows persisting an event `Log` via another adapter; delivery semantics
   would depend on that secondary adapter and any message bus if used.
3. **`pydapter` Migration Handling:** Does `pydapter` include a database
   migration system (e.g., via
   [`pydapter.migrations.sql.alembic_adapter.py`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/migrations/sql/alembic_adapter.py)
   for SQL databases like PostgreSQL)? Or is schema management expected to be
   handled externally (manual for Qdrant collections is likely)?
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

- `pydapter` Source Code (assumed GitHub location for citation purposes):
  - Core Async:
    [`https://github.com/khive-ai/pydapter/blob/main/src/pydapter/async_core.py`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/async_core.py)
  - Event Protocol:
    [`https://github.com/khive-ai/pydapter/blob/main/src/pydapter/protocols/event.py`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/protocols/event.py)
  - Async Qdrant Adapter:
    [`https://github.com/khive-ai/pydapter/blob/main/src/pydapter/extras/async_qdrant_.py`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/extras/async_qdrant_.py)
  - Async Postgres Adapter:
    [`https://github.com/khive-ai/pydapter/blob/main/src/pydapter/extras/async_postgres_.py`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/extras/async_postgres_.py)
  - Async SQL Adapter:
    [`https://github.com/khive-ai/pydapter/blob/main/src/pydapter/extras/async_sql_.py`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/extras/async_sql_.py)
  - Postgres Model Adapter:
    [`https://github.com/khive-ai/pydapter/blob/main/src/pydapter/model_adapters/postgres_model.py`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/model_adapters/postgres_model.py)
  - Migrations:
    [`https://github.com/khive-ai/pydapter/blob/main/src/pydapter/migrations/`](https://github.com/khive-ai/pydapter/blob/main/src/pydapter/migrations/)
- Khive Issue #26: "Implement `khive reader ingest` command"
- Khive Issue #25: "Design `DocumentRepository`"
- Khive Issue #24: "Define `Document` and `DocumentChunk` Pydantic Models"
- Khive Issue #27: "Implement Text Extraction, Chunking, and Embedding"
- Qdrant Documentation: For vector storage concepts.
- PostgreSQL Documentation: For relational storage concepts.
- MinIO Documentation: For local Docker setup and S3-compatible API usage.
- Python Filesystem Libraries (e.g., `aiofiles`, `pathlib`): If direct
  filesystem object storage is considered.
