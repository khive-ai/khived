# Khive Reader Microservice: Architecture

This document provides an in-depth look at the architecture of the Khive Reader
Microservice, explaining its components, data flow, and design decisions.

## Overview

The Reader Microservice is designed as a modular, service-oriented component
that provides document processing capabilities to the Khive ecosystem. It
follows a request-response pattern with clearly defined data models and a
service-oriented architecture.

## Core Components

![Reader Microservice Architecture](../assets/reader_architecture.png)

### 1. CLI Interface (`khive_reader.py`)

The CLI interface provides command-line access to the Reader Microservice
functionality. It:

- Parses command-line arguments
- Constructs appropriate request objects
- Invokes the service layer
- Formats and outputs responses as JSON
- Manages a persistent cache for document references

### 2. Service Layer (`ReaderServiceGroup`)

The service layer implements the core business logic of the Reader Microservice.
It:

- Processes incoming requests
- Delegates to the appropriate handler based on the action type
- Manages document conversion and storage
- Handles error conditions
- Returns structured responses

### 3. Data Models (`parts.py`)

The data models define the structure of requests and responses using Pydantic.
Key models include:

- `ReaderRequest`: Encapsulates an action and its parameters
- `ReaderResponse`: Contains success status, error messages, and content
- Action-specific parameter models (e.g., `ReaderOpenParams`,
  `ReaderReadParams`)
- Action-specific response content models (e.g., `ReaderOpenResponseContent`)

### 4. Utility Functions (`utils.py`)

Utility functions provide supporting capabilities:

- `dir_to_files`: Lists files in a directory with filtering options
- `calculate_text_tokens`: Estimates token counts for text using tiktoken

## Data Flow

### Document Opening Flow

1. User invokes `khive reader open --path_or_url <path>`
2. CLI constructs a `ReaderRequest` with action `OPEN` and `ReaderOpenParams`
3. Request is passed to `ReaderServiceGroup.handle_request()`
4. Service delegates to `_open_doc()` method
5. Document is processed using `docling.DocumentConverter`
6. Extracted text is saved to a temporary file
7. Document metadata is stored in the service's index
8. Response with `doc_id` and metadata is returned

### Document Reading Flow

1. User invokes
   `khive reader read --doc_id <id> --start_offset <start> --end_offset <end>`
2. CLI constructs a `ReaderRequest` with action `READ` and `ReaderReadParams`
3. Request is passed to `ReaderServiceGroup.handle_request()`
4. Service delegates to `_read_doc()` method
5. Document is located in the index
6. Specified text slice is read from the temporary file
7. Response with the text chunk is returned

### Directory Listing Flow

1. User invokes `khive reader list_dir --directory <dir> [options]`
2. CLI constructs a `ReaderRequest` with action `LIST_DIR` and
   `ReaderListDirParams`
3. Request is passed to `ReaderServiceGroup.handle_request()`
4. Service delegates to `_list_dir()` method
5. Directory is scanned using `dir_to_files()` utility
6. File listing is saved as a document
7. Response with `doc_id` and metadata is returned

## Caching Mechanism

The Reader Microservice implements a two-level caching strategy:

### In-Memory Cache

The `ReaderServiceGroup` maintains an in-memory index of opened documents:

- Maps `doc_id` to file path and document length
- Persists only for the lifetime of the service instance

### Persistent Cache

The CLI maintains a persistent cache in `~/.khive_reader_cache.json`:

- Maps `doc_id` to file path, length, and token count
- Persists across multiple CLI invocations
- Allows reading documents opened in previous sessions

## Error Handling

The Reader Microservice implements comprehensive error handling:

1. **Input Validation**: Pydantic models validate all request parameters
2. **Service-Level Errors**: Handled and returned as structured responses
3. **CLI-Level Errors**: Reported to stderr with appropriate exit codes

## Dependencies

The Reader Microservice relies on several key dependencies:

- **docling**: Document conversion library that handles various file formats
- **tiktoken**: Token counting library for estimating token usage
- **aiofiles**: Asynchronous file I/O operations
- **Pydantic**: Data validation and settings management

## Design Decisions

### Why Separate CLI and Service Layers?

The separation of CLI and service layers allows:

- Clean separation of concerns
- Potential for future API endpoints
- Easier testing of business logic
- Flexibility in deployment options

### Why Use Temporary Files?

Storing extracted text in temporary files rather than in memory:

- Enables handling of very large documents
- Reduces memory pressure
- Allows for persistent access across sessions
- Provides a clean recovery mechanism

### Why Include Token Counting?

Token counting is included to:

- Help users estimate LLM token usage
- Provide insights into document complexity
- Support efficient chunking strategies

## Future Enhancements

Potential future enhancements to the Reader Microservice include:

1. **Semantic Chunking**: Divide documents into semantic chunks rather than
   character offsets
2. **Metadata Extraction**: Extract and expose document metadata (title, author,
   date, etc.)
3. **Content Summarization**: Provide automatic summarization of document
   content
4. **Streaming Support**: Stream large documents to reduce memory usage
5. **Format Conversion**: Convert between different document formats
6. **Search Capabilities**: Search within documents for specific content

## Integration Points

The Reader Microservice integrates with other Khive components:

- **CLI Framework**: Follows the standard Khive CLI patterns
- **Service Framework**: Implements the Khive Service protocol
- **Configuration System**: Uses Khive's configuration mechanisms
- **Logging System**: Integrates with Khive's logging infrastructure

## Conclusion

The Reader Microservice architecture provides a robust, flexible foundation for
document processing within the Khive ecosystem. Its modular design, clear
separation of concerns, and comprehensive error handling make it both powerful
and maintainable.
