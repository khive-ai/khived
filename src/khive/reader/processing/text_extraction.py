import logging
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class TextExtractor:
    """
    Extracts text content from various document formats.
    """

    def __init__(self):
        self._extractors: dict[str, Callable[[Path], str]] = {
            "application/pdf": self._extract_pdf,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": self._extract_docx,
            "text/html": self._extract_html,
            "text/plain": self._extract_txt,
        }

    def extract_text(self, file_path: Path, mime_type: str) -> str:
        """
        Extracts text from the given file based on its MIME type.

        Args:
            file_path: The path to the document file.
            mime_type: The MIME type of the document.

        Returns:
            The extracted text content as a string.

        Raises:
            ValueError: If the MIME type is unsupported or if text extraction fails.
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            raise ValueError(f"File not found: {file_path}")
        if not file_path.is_file():
            logger.error(f"Path is not a file: {file_path}")
            raise ValueError(f"Path is not a file: {file_path}")

        extractor = self._extractors.get(mime_type)
        if not extractor:
            logger.warning(
                f"Unsupported MIME type for text extraction: {mime_type} for file {file_path}"
            )
            raise ValueError(f"Unsupported MIME type for text extraction: {mime_type}")

        try:
            logger.info(f"Extracting text from {file_path} with MIME type {mime_type}")
            return extractor(file_path)
        except Exception as e:
            logger.error(
                f"Failed to extract text from {file_path} (MIME: {mime_type}): {e}",
                exc_info=True,
            )
            # Consider re-raising a more specific custom exception if needed
            raise ValueError(f"Failed to extract text from {file_path}: {e}")

    def _extract_pdf(self, file_path: Path) -> str:
        """Extracts text from a PDF file."""
        try:
            import PyPDF2

            text_parts = []
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                if reader.is_encrypted:
                    try:
                        # Attempt to decrypt with an empty password, common for some PDFs
                        if reader.decrypt("") == PyPDF2.PasswordType.OWNER_PASSWORD:
                            logger.info(
                                f"Decrypted PDF {file_path} with empty owner password."
                            )
                        elif reader.decrypt("") == PyPDF2.PasswordType.USER_PASSWORD:
                            logger.info(
                                f"Decrypted PDF {file_path} with empty user password."
                            )
                        else:
                            logger.warning(
                                f"PDF {file_path} is encrypted and could not be decrypted with empty password."
                            )
                            # Depending on policy, could return empty string or raise specific error
                            return ""
                    except Exception as decrypt_exc:
                        logger.error(
                            f"Failed to decrypt PDF {file_path}: {decrypt_exc}"
                        )
                        raise ValueError(
                            f"Failed to decrypt PDF {file_path}"
                        ) from decrypt_exc

                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    text_parts.append(
                        page.extract_text() or ""
                    )  # Ensure None is handled
            return "\n".join(text_parts)
        except ImportError:
            logger.error(
                "PyPDF2 library is not installed. Please install it to extract text from PDF files."
            )
            raise ImportError(
                "PyPDF2 library is not installed. Required for PDF extraction."
            )
        except PyPDF2.errors.PdfReadError as e:
            logger.error(f"Error reading PDF file {file_path}: {e}")
            raise ValueError(f"Invalid or corrupted PDF file: {file_path}") from e
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during PDF extraction for {file_path}: {e}",
                exc_info=True,
            )
            raise ValueError(f"Failed to extract text from PDF {file_path}") from e

    def _extract_docx(self, file_path: Path) -> str:
        """Extracts text from a DOCX file."""
        try:
            import docx

            doc = docx.Document(file_path)
            text_parts = [paragraph.text for paragraph in doc.paragraphs]
            return "\n".join(text_parts)
        except ImportError:
            logger.error(
                "python-docx library is not installed. Please install it to extract text from DOCX files."
            )
            raise ImportError(
                "python-docx library is not installed. Required for DOCX extraction."
            )
        except (
            Exception
        ) as e:  # docx library might raise various exceptions for corrupted files
            logger.error(
                f"Failed to extract text from DOCX {file_path}: {e}", exc_info=True
            )
            raise ValueError(f"Failed to extract text from DOCX {file_path}") from e

    def _extract_html(self, file_path: Path) -> str:
        """Extracts text from an HTML file."""
        try:
            import html2text

            h = html2text.HTML2Text()
            h.ignore_links = True  # Common preference, can be made configurable
            h.ignore_images = True
            with open(
                file_path, encoding="utf-8", errors="ignore"
            ) as f:  # Specify encoding
                html_content = f.read()
            return h.handle(html_content)
        except ImportError:
            logger.error(
                "html2text library is not installed. Please install it to extract text from HTML files."
            )
            raise ImportError(
                "html2text library is not installed. Required for HTML extraction."
            )
        except Exception as e:
            logger.error(
                f"Failed to extract text from HTML {file_path}: {e}", exc_info=True
            )
            raise ValueError(f"Failed to extract text from HTML {file_path}") from e

    def _extract_txt(self, file_path: Path) -> str:
        """Extracts text from a plain text file."""
        # Implementation will be added in a subsequent step (T-TE5)
        raise NotImplementedError("TXT extraction not yet implemented.")
