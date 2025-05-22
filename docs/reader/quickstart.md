# Khive Reader Microservice: Quickstart Guide

This guide will help you get started with the Khive Reader Microservice, a
powerful tool for extracting and processing text from various document formats
and web resources.

## Installation

First, install Khive with the reader extras:

```bash
# Install with pip
pip install "khive[reader]"

# Or with uv (recommended)
uv pip install "khive[reader]"
```

## Basic Usage

The Reader Microservice provides three main actions:

- `open`: Convert a file or URL to text and cache it
- `read`: Read a portion of a previously opened document
- `list_dir`: List directory contents and treat the listing as a document

### Opening Documents

You can open local files or remote URLs:

```bash
# Open a local file
khive reader open --path_or_url path/to/document.pdf

# Open a remote URL
khive reader open --path_or_url https://example.com/document.pdf
```

The command returns a JSON response with a `doc_id` that you'll use to read the
document:

```json
{
  "success": true,
  "content": {
    "doc_info": {
      "doc_id": "DOC_123456789",
      "length": 15000,
      "num_tokens": 3500
    }
  }
}
```

### Reading Documents

Once you have a `doc_id`, you can read portions of the document:

```bash
# Read the entire document
khive reader read --doc_id DOC_123456789

# Read the first 1000 characters
khive reader read --doc_id DOC_123456789 --end_offset 1000

# Read characters 1000-2000
khive reader read --doc_id DOC_123456789 --start_offset 1000 --end_offset 2000
```

The command returns the requested text slice:

```json
{
  "success": true,
  "content": {
    "chunk": {
      "start_offset": 1000,
      "end_offset": 2000,
      "content": "The extracted text content..."
    }
  }
}
```

### Listing Directories

You can list files in a directory and treat the listing as a document:

```bash
# List all files in a directory
khive reader list_dir --directory ./src

# List recursively
khive reader list_dir --directory ./src --recursive

# Filter by file type
khive reader list_dir --directory ./src --file_types .py .md
```

The command returns a `doc_id` for the directory listing:

```json
{
  "success": true,
  "content": {
    "doc_info": {
      "doc_id": "DIR_987654321",
      "length": 512,
      "num_tokens": 120
    }
  }
}
```

You can then read this listing like any other document:

```bash
khive reader read --doc_id DIR_987654321
```

## Practical Examples

### Extract and Process a PDF

```bash
# Open the PDF
DOC_ID=$(khive reader open --path_or_url research-paper.pdf | jq -r '.content.doc_info.doc_id')

# Get document length
DOC_LENGTH=$(khive reader open --path_or_url research-paper.pdf | jq -r '.content.doc_info.length')

# Read the abstract (first 1000 characters)
khive reader read --doc_id $DOC_ID --end_offset 1000

# Read the conclusion (last 2000 characters)
khive reader read --doc_id $DOC_ID --start_offset $(($DOC_LENGTH - 2000))
```

### Process Web Content

```bash
# Open a web page
DOC_ID=$(khive reader open --path_or_url https://example.com/article | jq -r '.content.doc_info.doc_id')

# Read the content
khive reader read --doc_id $DOC_ID
```

### Find and Process Specific File Types

```bash
# List all Python files in a project
DIR_ID=$(khive reader list_dir --directory ./project --recursive --file_types .py | jq -r '.content.doc_info.doc_id')

# Get the file listing
FILES=$(khive reader read --doc_id $DIR_ID | jq -r '.content.chunk.content')

# Process each file
echo "$FILES" | while read -r file; do
  echo "Processing $file"
  FILE_ID=$(khive reader open --path_or_url "$file" | jq -r '.content.doc_info.doc_id')
  khive reader read --doc_id $FILE_ID
done
```

## Error Handling

The Reader Microservice provides clear error messages when something goes wrong:

```json
{
  "success": false,
  "error": "File not found: path/to/nonexistent.pdf",
  "content": null
}
```

Always check the `success` field in the response to handle errors appropriately.

## Next Steps

- Explore the [architecture documentation](architecture.md) to understand how
  the Reader Microservice works
- Check out the [example notebook](examples/basic_usage.ipynb) for more usage
  examples
- Read the [full CLI documentation](../commands/khive_reader.md) for detailed
  command reference
