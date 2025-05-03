import tempfile
from pathlib import Path

from khive.utils import calculate_text_tokens

from .models import (
    DocumentInfo,
    PartialChunk,
    ReaderAction,
    ReaderListDirParams,
    ReaderOpenParams,
    ReaderOpenResponseContent,
    ReaderReadParams,
    ReaderRequest,
    ReaderResponse,
)

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


__all__ = ("ReaderService", "ReaderRequest", "global_reader_service")


class ReaderService:
    """
    A tool that can:
      - open a doc (File/URL) -> returns doc_id, doc length
      - read partial text from doc -> returns chunk
    """

    # List of file extensions supported by docling

    def __init__(self):
        from docling.document_converter import DocumentConverter

        self.converter: DocumentConverter = DocumentConverter()
        self.documents = {}  # doc_id -> (temp_file_path, doc_length, num_tokens)

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
        except Exception as e:
            return ReaderResponse(
                success=False,
                error=f"Conversion error: {e!s}",
                content=ReaderOpenResponseContent(doc_info=None),
            )

        doc_id = f"DOC_{abs(hash(params.path_or_url))}"
        return self._save_to_temp(text, doc_id)

    async def _read_doc(self, params: ReaderReadParams) -> ReaderResponse: ...

    async def _list_dir(self, params: ReaderListDirParams) -> ReaderResponse: ...

    async def _save_to_temp(self, text, doc_id) -> ReaderResponse:
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, mode="w", encoding="utf-8"
        )
        temp_file.write(text)
        doc_len = len(text)
        temp_file.close()

        # store info
        self.documents[doc_id] = (temp_file.name, doc_len)

        return ReaderResponse(
            success=True,
            content=ReaderOpenResponseContent(
                doc_info=DocumentInfo(
                    doc_id=doc_id,
                    length=doc_len,
                    num_tokens=calculate_text_tokens(text),
                )
            ),
        )

    def handle_request(self, request: ReaderRequest) -> ReaderResponse:
        """
        A function that takes ReaderRequest to either:
        - open a doc (File/URL) -> returns doc_id, doc length
        - read partial text from doc -> returns chunk
        """
        if isinstance(request, dict):
            request = ReaderRequest(**request)
        if request.action == "open":
            return self._open_doc(request.path_or_url)
        if request.action == "read":
            return self._read_doc(
                request.doc_id, request.start_offset, request.end_offset
            )
        if request.action == "list_dir":
            return self._list_dir(
                request.path_or_url, request.recursive, request.file_types
            )
        return ReaderResponse(success=False, error="Unknown action type")

    def _open_doc(self, params: ReaderOpenParams) -> ReaderResponse:
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
            )

        try:
            result = self.converter.convert(params.path_or_url)
            text = result.document.export_to_markdown()
        except Exception as e:
            return ReaderResponse(success=False, error=f"Conversion error: {e!s}")

        doc_id = f"DOC_{abs(hash(params.path_or_url))}"
        return self._save_to_temp(text, doc_id)

    def _read_doc(self, params: ReaderReadParams) -> ReaderResponse:

        if params.doc_id not in self.documents:
            return ReaderResponse(success=False, error="doc_id not found in memory")

        path, length = self.documents[params.doc_id]
        # clamp offsets
        s = max(0, params.start_offset if params.start_offset is not None else 0)
        e = min(length, params.end_offset if params.end_offset is not None else length)

        try:
            with open(path, encoding="utf-8") as f:
                f.seek(s)
                content = f.read(e - s)
        except Exception as ex:
            return ReaderResponse(success=False, error=f"Read error: {ex!s}")

        return ReaderResponse(
            success=True,
            chunk=PartialChunk(start_offset=s, end_offset=e, content=content),
        )

    def _list_dir(self, params: ReaderListDirParams):
        from .utils import dir_to_files

        files = dir_to_files(
            params.directory, recursive=params.recursive, file_types=params.file_types
        )
        files = "\n".join([str(f) for f in files])
        doc_id = f"DIR_{abs(hash(params.directory))}"
        return self._save_to_temp(files, doc_id)


global_reader_service = ReaderService()
