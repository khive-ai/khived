# Khive Reader Microservice

The Khive Reader Microservice is a powerful document and web content processing
service that enables seamless extraction and manipulation of text from various
file formats and web resources. It serves as a bridge between raw content and
structured text that can be easily consumed by applications, AI agents, and
other services.

## Overview

The Reader Microservice provides a unified interface for:

- Opening and converting various document formats (PDF, DOCX, HTML, etc.) to
  plain text
- Extracting text from web URLs
- Reading specific portions of documents by character offsets
- Listing directory contents with filtering options
- Caching processed documents for efficient repeated access

This service is designed to be used both as a standalone CLI tool and as a
programmatic API within Python applications.

## Key Features

- **Multi-format Support**: Process PDFs, Word documents, PowerPoint, Excel,
  HTML, Markdown, images (with OCR), and more
- **URL Processing**: Extract content directly from web URLs
- **Efficient Partial Reading**: Read only the portions of documents you need
- **Directory Exploration**: List files with filtering by type and recursive
  options
- **Persistent Caching**: Cache processed documents for quick subsequent access
- **Token Estimation**: Get approximate token counts for processed text
- **JSON-based Interface**: Clean, structured responses for easy integration
- **Error Handling**: Robust error reporting and graceful failure modes

## Installation

To use the Reader Microservice, install Khive with the reader extras:

```bash
# Install with pip
pip install "khive[reader]"

# Or with uv
uv pip install "khive[reader]"
```

This will install all necessary dependencies, including:

- `docling`: For document conversion
- `tiktoken`: For token counting
- `aiofiles`: For asynchronous file operations

## Quick Start

```bash
# Open a local PDF file
khive reader open --path_or_url path/to/document.pdf

# Open a web URL
khive reader open --path_or_url https://example.com/document.pdf

# Read the first 1000 characters from a document
DOC_ID=$(khive reader open --path_or_url document.md | jq -r '.content.doc_info.doc_id')
khive reader read --doc_id $DOC_ID --end_offset 1000

# List Python files in a directory
khive reader list_dir --directory ./src --file_types .py
```

## Documentation

For more detailed information, see:

- [Quickstart Guide](quickstart.md): Get up and running quickly
- [Architecture](architecture.md): Understand how the Reader Microservice works
- [Examples](examples/basic_usage.ipynb): Jupyter notebook with usage examples

## Supported File Formats

The Reader Microservice supports a wide range of file formats through the
`docling` library:

- **Documents**: PDF, DOCX, PPTX, XLSX
- **Web**: HTML, HTM
- **Text**: Markdown (MD), AsciiDoc (ADOC), CSV
- **Images**: JPG, JPEG, PNG, TIFF, BMP (with OCR)

## Use Cases

- **AI Agent Augmentation**: Provide documents and web content to AI agents
- **Content Extraction**: Extract text from various document formats
- **Data Processing**: Pre-process documents for analysis pipelines
- **Web Scraping**: Extract content from web pages in a structured format
- **Document Indexing**: Process documents for search and retrieval systems

## License

Apache-2.0
