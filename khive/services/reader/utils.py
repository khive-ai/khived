from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging


def dir_to_files(
    directory: str | Path,
    file_types: list[str] | None = None,
    max_workers: int | None = None,
    ignore_errors: bool = False,
    verbose: bool = False,
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
        ignore_errors (bool): If True, log warnings for errors instead of raising exceptions.
        verbose (bool): If True, print verbose output.
        recursive (bool): If True, process directories recursively (the default).
            If False, only process files in the top-level directory.

    Returns:
        List[Path]: A list of Path objects representing the files found.

    Raises:
        ValueError: If the provided directory doesn't exist or isn't a directory.
    """
    directory_path = Path(directory)
    if not directory_path.is_dir():
        raise ValueError(f"The provided path is not a valid directory: {directory}")

    def process_file(file_path: Path) -> Path | None:
        try:
            if file_types is None or file_path.suffix in file_types:
                return file_path
        except Exception as e:
            if ignore_errors:
                if verbose:
                    logging.warning(f"Error processing {file_path}: {e}")
            else:
                raise ValueError(f"Error processing {file_path}: {e}") from e
        return None

    file_iterator = directory_path.rglob("*") if recursive else directory_path.glob("*")
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(process_file, f) for f in file_iterator if f.is_file()
            ]
            files = [
                future.result()
                for future in as_completed(futures)
                if future.result() is not None
            ]

        if verbose:
            logging.info(f"Processed {len(files)} files from {directory}")

        return files
    except Exception as e:
        raise ValueError(f"Error processing directory {directory}: {e}") from e
