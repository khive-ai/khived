# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path
from typing import Any

import aiofiles

from khive.services.reader.parts import (
    DocumentInfo,
    ReaderAction,
    ReaderListDirParams,
    ReaderOpenParams,
    ReaderOpenResponseContent,
    ReaderReadParams,
    ReaderRequest,
    ReaderResponse,
)
from khive.services.reader.utils import calculate_text_tokens
from khive.types import Service
from khive.utils import is_package_installed

_HAS_DOCLING = is_package_installed("docling")


DOCLING_SUPPORTED_FORMATS = {
    ".pdf",  # Document formats
    ".docx",
    ".pptx",
    ".xlsx",
    ".html",  # Web formats
    ".htm",
    ".md",  # Text formats
    ".markdown",
    ".adoc",
    ".asciidoc",
    ".csv",
    ".jpg",  # Image formats (with OCR)
    ".jpeg",
    ".png",
    ".tiff",
    ".bmp",
}


__all__ = (
    "ReaderRequest",
    "ReaderServiceGroup",
)


class ReaderServiceGroup(Service):
    """
    A tool that can:
      - open a doc (File/URL) -> returns doc_id, doc length
      - read partial text from doc -> returns chunk
    """

    # List of file extensions supported by docling

    def __init__(self, *, converter=None):
        """
        Initialize the ReaderService.

        Parameters
        ----------
        converter : DocumentConverter, optional
            Inject a converter for easier testing; falls back to Docling's
            default when omitted.
        """
        if not _HAS_DOCLING:
            raise ModuleNotFoundError(
                "Docling is not installed. Please install it with `pip install docling`."
            )

        from docling.document_converter import DocumentConverter  # type: ignore[import]

        self.converter = converter or DocumentConverter()

        # Create cache directory if it doesn't exist
        self.cache_dir = Path.cwd() / ".khive" / "reader_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Path to the index file
        self.index_path = self.cache_dir / "index.json"

        # Load existing index or create a new one
        self.documents_index = self._load_index()

        # For compatibility with CLI's caching mechanism that expects this attribute
        # This is distinct from documents_index and cache_dir used for service's own persistence.
        self.documents: dict[
            str, tuple[str, int]
        ] = {}  # Stores (temp_file_path, doc_length)

    async def handle_request(self, request: ReaderRequest) -> ReaderResponse:
        if request.action == ReaderAction.OPEN:
            return await self._open_doc(request.params)
        if request.action == ReaderAction.READ:
            return await self._read_doc(request.params)
        if request.action == ReaderAction.LIST_DIR:
            return await self._list_dir(request.params)
        return ReaderResponse(
            success=False,
            error="Unknown action type, must be one of: open, read, list_dir",
        )

    async def _open_doc(self, params: ReaderOpenParams) -> ReaderResponse:
        # Check if it's a URL
        is_url = params.path_or_url.startswith(("http://", "https://", "ftp://"))

        # Check if it's a local file with a supported extension
        is_supported_file = False
        if not is_url:
            path = Path(params.path_or_url)
            if path.exists() and path.is_file():
                extension = path.suffix.lower()
                is_supported_file = extension in DOCLING_SUPPORTED_FORMATS

        # If it's not a URL and not a supported file, return an error
        if not is_url and not is_supported_file:
            return ReaderResponse(
                success=False,
                error=f"Unsupported file format: {params.path_or_url}. Docling supports: {', '.join(DOCLING_SUPPORTED_FORMATS)}",
                content=ReaderOpenResponseContent(doc_info=None),
            )

        try:
            result = self.converter.convert(params.path_or_url)
            text = result.document.export_to_markdown()

            # Ensure text is a string - defensive in case export_to_markdown returns something unexpected
            if not isinstance(text, str):
                text = str(text)

        except Exception as e:
            return ReaderResponse(
                success=False,
                error=f"Conversion error: {e!s}",
                content=ReaderOpenResponseContent(doc_info=None),
            )

        doc_id = f"DOC_{abs(hash(params.path_or_url))}"
        return await self._save_to_temp(text, doc_id)

    async def _read_doc(self, params: ReaderReadParams) -> ReaderResponse:
        if params.doc_id not in self.documents_index:
            return ReaderResponse(success=False, error="doc_id not found in cache")

        doc_info = self.documents_index[params.doc_id]
        file_path = self.cache_dir / f"{params.doc_id}.txt"
        length = doc_info["length"]

        # clamp offsets
        s = max(0, params.start_offset if params.start_offset is not None else 0)
        e = min(length, params.end_offset if params.end_offset is not None else length)

        try:
            # Check if the file exists
            if not file_path.exists():
                return ReaderResponse(
                    success=False, error=f"File not found: {file_path}"
                )

            # Read the file content asynchronously
            async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
                # If we need the whole file
                if s == 0 and e == length:
                    content = await f.read()
                else:
                    # For partial reads, we need to read up to the end offset
                    content = await f.read(e)
                    # Then slice to get the start offset
                    content = content[s:]

            # Print debug info
            print(
                f"Reading doc {params.doc_id} from {s} to {e}, content length: {len(content)}"
            )

            # Import the necessary class
            from .parts import PartialChunk, ReaderReadResponseContent

            # Create a PartialChunk object
            chunk = PartialChunk(start_offset=s, end_offset=e, content=content)

            # Return the response with the chunk in the content field
            return ReaderResponse(
                success=True,
                content=ReaderReadResponseContent(chunk=chunk),
            )

        except Exception as ex:
            return ReaderResponse(success=False, error=f"Read error: {ex!s}")

    async def _list_dir(self, params: ReaderListDirParams) -> ReaderResponse:
        from .parts import ReaderListDirResponseContent
        from .utils import dir_to_files

        try:
            files_list = dir_to_files(
                params.directory,
                recursive=params.recursive,
                file_types=params.file_types,
            )

            # Convert to string representation for storage
            files_str = "\n".join([str(f) for f in files_list])
            doc_id = f"DIR_{abs(hash(params.directory))}"

            # Save to temp file for potential future reads
            await self._save_to_temp(files_str, doc_id)

            # Return the files directly in the response
            return ReaderResponse(
                success=True,
                content=ReaderListDirResponseContent(
                    files=[str(f) for f in files_list]
                ),
            )
        except Exception as ex:
            return ReaderResponse(
                success=False,
                error=f"List directory error: {ex!s}",
            )

    async def _save_to_temp(self, text, doc_id) -> ReaderResponse:
        # Defensive: ensure text is a string
        if not isinstance(text, str):
            raise TypeError("Converted document must be string markdown")

        # Create a file in the cache directory
        file_path = self.cache_dir / f"{doc_id}.txt"

        try:
            # Write to file asynchronously
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(text)

            doc_len = len(text)
            num_tokens = calculate_text_tokens(text)

            # Update the index
            self.documents_index[doc_id] = {
                "length": doc_len,
                "num_tokens": num_tokens,
                "path": str(file_path),
            }

            # Save the updated index asynchronously
            await self._save_index_async()

            return ReaderResponse(
                success=True,
                content=ReaderOpenResponseContent(
                    doc_info=DocumentInfo(
                        doc_id=doc_id,
                        length=doc_len,
                        num_tokens=num_tokens,
                    )
                ),
            )
        except Exception as ex:
            return ReaderResponse(
                success=False,
                error=f"Failed to save document: {ex!s}",
                content=ReaderOpenResponseContent(doc_info=None),
            )

    def _load_index(self) -> dict[str, dict[str, Any]]:
        """Load the document index from disk or create a new one if it doesn't exist."""
        if self.index_path.exists():
            try:
                with open(self.index_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                # If there's an error loading the index, start fresh
                return {}
        return {}

    async def _save_index_async(self) -> None:
        """Save the document index to disk asynchronously."""
        try:
            async with aiofiles.open(self.index_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(self.documents_index, indent=2))
        except Exception as ex:
            print(f"Warning: Failed to save document index asynchronously: {ex!s}")
