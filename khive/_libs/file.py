from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path


class FileOperationError(Exception):
    """Custom exception for file operation errors."""


class FileUtils:
    @staticmethod
    def unzip_to_temp(
        zip_path: str | Path,
        *,
        suffix: str | None = None,
        prefix: str = "tmp-unzip-",
    ) -> Path:
        """
        Decompress a .zip archive into a fresh temporary directory.

        Args:
            zip_path (str | Path): Path to the .zip file.
            suffix (str | None): Optional suffix for the temp directory's name.
            prefix (str): Prefix for the temp directory's name (default 'tmp-unzip-').
        Returns:
            pathlib.Path: Path object pointing to the populated temporary folder.
        Raises:
            zipfile.BadZipFile: If the archive is corrupt or not a ZIP.
        """
        zip_path = Path(zip_path).expanduser().resolve()

        tmp_dir = Path(tempfile.mkdtemp(suffix=suffix, prefix=prefix))

        try:
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(tmp_dir)
        except Exception:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise FileOperationError(
                f"Failed to extract {zip_path} to {tmp_dir}: {zipfile.BadZipFile}"
            )

        return tmp_dir

    @staticmethod
    def dir_to_files(
        directory: str | Path,
        *,
        file_types: list[str] | None = None,
        max_workers: int | None = None,
        recursive: bool = False,
    ) -> list[Path]:
        """
        Recursively process a directory and return a list of file paths.

        This function walks through the given directory and its subdirectories,
        collecting file paths that match the specified file types (if any).

        Args:
            directory (str | Path): The directory to process.
            file_types (None | list[str]): List of file extensions to include (e.g., ['.txt', '.pdf']).
                If None, include all file types.
            max_workers (None | int): Maximum number of worker threads for concurrent processing.
                If None, uses the default ThreadPoolExecutor behavior.
            recursive (bool): If True, process directories recursively (the default).
                If False, only process files in the top-level directory.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        directory_path = Path(directory)
        if not directory_path.is_dir():
            raise ValueError(f"The provided path is not a valid directory: {directory}")

        def process_file(file_path: Path) -> Path | None:
            try:
                if file_types is None or file_path.suffix in file_types:
                    return file_path
            except Exception as e:
                raise FileOperationError(f"Error processing {file_path}: {e}") from e
            return None

        file_iterator = (
            directory_path.rglob("*") if recursive else directory_path.glob("*")
        )
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [
                    executor.submit(process_file, f)
                    for f in file_iterator
                    if f.is_file()
                ]
                files = [
                    future.result()
                    for future in as_completed(futures)
                    if future.result() is not None
                ]
            return files
        except Exception as e:
            raise FileOperationError(
                f"Error processing directory {directory}: {e}"
            ) from e
