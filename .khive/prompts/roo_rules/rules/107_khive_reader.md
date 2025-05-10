# khive reader

## Overview

The `khive reader` command provides Command Line Interface (CLI) access to a
powerful document and web content reading service. It can open various file
types (PDF, DOCX, HTML, text, images with OCR, etc.) and URLs, convert their
content to text, and allow for partial reads of this text. Opened documents are
cached locally, enabling efficient subsequent access.

This tool is designed for both interactive use and integration into automated
workflows, particularly for providing textual content to AI agents or other
processing scripts.

## Key Features

- **Versatile Content Opening:** Supports a wide range of local file formats and
  remote URLs.
- **Text Extraction:** Converts diverse content sources into plain text.
- **Partial Reading:** Allows reading specific character offsets from opened
  documents.
- **Directory Listing:** Can list files within a specified directory, optionally
  recursively and filtered by type, and treat the listing as a readable
  document.
- **Persistent Caching:** Opened documents (their extracted text) are cached
  locally (in `~/.khive_reader_cache.json` and temporary files) for quick access
  across multiple CLI invocations.
- **Structured JSON I/O:** All interactions produce JSON output, suitable for
  scripting and agent consumption.
- **Pydantic-Driven:** Leverages Pydantic models for robust request and response
  validation.

## Install

```
uv pip install "khive[reader]"
```

## Usage

```bash
khive reader <action> [action_specific_options] [global_options]
```

**Actions:**

- `open`: Opens a file or URL, converts it to text, and caches it.
- `read`: Reads a portion of a previously opened document.
- `list_dir`: Lists directory contents and treats the listing as an openable
  document.

## Global Options (Applicable to all actions)

| Option            | Description                                 |
| ----------------- | ------------------------------------------- |
| `--json-output`   | (Implied) All output is in JSON format.     |
| `--verbose`, `-v` | (For future use) Enable verbose CLI logging |

## Actions and their Options

### `open`

Opens a file or URL.

```bash
khive reader open --path_or_url <path_or_url_to_open>
```

| Option          | Description                                          |
| --------------- | ---------------------------------------------------- |
| `--path_or_url` | **Required.** Local file path or remote URL to open. |

**Output (on success):**

```json
{
  "success": true,
  "content": {
    "doc_info": {
      "doc_id": "DOC_123456789", // Unique ID for this document
      "length": 15000, // Total characters in the extracted text
      "num_tokens": 3500 // Estimated number of tokens
    }
  }
}
```

### `read`

Reads a slice from a previously opened document.

```bash
khive reader read --doc_id <id> [--start_offset <num>] [--end_offset <num>]
```

| Option           | Description                                                                      |
| ---------------- | -------------------------------------------------------------------------------- |
| `--doc_id`       | **Required.** The unique ID returned by a previous `open` or `list_dir` command. |
| `--start_offset` | Character start offset (inclusive, default: 0).                                  |
| `--end_offset`   | Character end offset (exclusive, default: end of document).                      |

**Output (on success):**

```json
{
  "success": true,
  "content": {
    "chunk": {
      "start_offset": 100,
      "end_offset": 200,
      "content": "text content from 100 to 199..."
    }
  }
}
```

### `list_dir`

Lists files in a directory. The output of the listing is itself treated as a
document that gets "opened" and assigned a `doc_id`.

```bash
khive reader list_dir --directory <path> [--recursive] [--file_types <ext1> <ext2>...]
```

| Option         | Description                                                                                         |
| -------------- | --------------------------------------------------------------------------------------------------- |
| `--directory`  | **Required.** The path to the directory to list.                                                    |
| `--recursive`  | Recursively list files in subdirectories. (Flags: `--recursive` / `--no-recursive`, default: false) |
| `--file_types` | Optional list of file extensions to include (e.g., `.txt` `.pdf`).                                  |

**Output (on success):** (Similar to `open`, as the listing becomes a new
document)

```json
{
  "success": true,
  "content": {
    "doc_info": {
      "doc_id": "DIR_987654321", // Unique ID for this directory listing document
      "length": 512, // Total characters in the concatenated file listing
      "num_tokens": 120 // Estimated tokens for the listing
    }
  }
}
```

## Examples

```bash
# Open a local Markdown file
khive reader open --path_or_url ./docs/README.md

# Open a remote PDF
khive reader open --path_or_url https://arxiv.org/pdf/2301.00001.pdf

# Read the first 500 characters of a document (assuming DOC_123 was returned by a previous open)
khive reader read --doc_id DOC_123 --end_offset 500

# Read characters 1000 to 1500 from DOC_ABC
khive reader read --doc_id DOC_ABC --start_offset 1000 --end_offset 1500

# List all Python files in the 'src' directory, non-recursively
khive reader list_dir --directory ./src --file_types .py

# Recursively list all files in 'project_data'
khive reader list_dir --directory ./project_data --recursive

# Read the content of a previously generated directory listing (e.g., DIR_XYZ)
khive reader read --doc_id DIR_XYZ
```

## Caching Behavior

- When a document is successfully opened (`open` or `list_dir`), its extracted
  text is saved to a temporary file on the system.
- A mapping from the `doc_id` to this temporary file's path, its length, and
  token count is stored in `~/.khive_reader_cache.json`.
- This allows subsequent `read` commands, even in different terminal sessions or
  script executions, to access the content without re-processing the original
  source, as long as the temporary file and cache entry exist.
- The underlying `ReaderService` attempts to clean up these temporary files upon
  its own internal management, but the cache file provides a persistent
  reference.

## Error Handling

- If an action fails, the output JSON will have `success: false` and an `error`
  field describing the issue.
  ```json
  {
    "success": false,
    "error": "doc_id not found in memory",
    "content": null
  }
  ```
- Errors related to file access, URL fetching, content conversion, or invalid
  parameters are reported.
- The CLI exits with a non-zero status code on failure.

## Exit Codes

- `0`: Action completed successfully.
- `1`: An error occurred (e.g., invalid parameters, module not found, internal
  processing error).
- `2`: The requested reader service action was executed but reported
  `success: false` (e.g., file not found by service, conversion error).

## Notes

- The `khive reader` relies on the `khive.services.reader.ReaderService` and its
  dependencies (like `docling` and `tiktoken`). Ensure these are correctly
  installed.
- Supported file formats for the `open` action depend on the underlying
  `docling` library's capabilities.
- All output is a single line of JSON printed to `stdout`. Diagnostic messages
  or errors may go to `stderr`.
