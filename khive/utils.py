import sys
from pathlib import Path
from typing import Iterable, Tuple, Union

ANSI = {
    "G": "\033[32m" if sys.stdout.isatty() else "",
    "R": "\033[31m" if sys.stdout.isatty() else "",
    "Y": "\033[33m" if sys.stdout.isatty() else "",
    "B": "\033[34m" if sys.stdout.isatty() else "",
    "N": "\033[0m" if sys.stdout.isatty() else "",
}

_DELIMS: Tuple[str, ...] = ("---", "+++")
Encoding = str  # alias for readability


def read_md_body(path: Union[str, Path], *, encoding: Encoding = "utf-8") -> str:
    """
    Return the Markdown body of *path*, stripping a leading front-matter block
    that is delimited by '---' or '+++' lines.

    Parameters
    ----------
    path : str | pathlib.Path
        File system path to a Markdown (.md) file.
    encoding : str, default "utf-8"
        Text encoding used when reading the file.

    Returns
    -------
    str
        The Markdown body (without front-matter). If no valid front-matter
        block is present, the whole file is returned unchanged.

    Notes
    -----
    • A valid block starts on the first line with a delimiter in `_DELIMS`
      *and* is closed by the same delimiter on a later line.
    • Nested front-matter or malformed delimiters are left untouched to avoid
      accidental data loss.
    """
    path = Path(path)
    with path.open("r", encoding=encoding) as fh:
        lines: list[str] = fh.readlines()

    if not lines:
        return ""  # empty file

    first = lines[0].strip()
    if first in _DELIMS:  # potential front-matter
        try:
            # find index of the *next* identical delimiter
            end_idx: int = next(
                i for i, line in enumerate(lines[1:], start=1) if line.strip() == first
            )
        except StopIteration:
            # No closing delimiter found → assume malformed; return full text
            return "".join(lines)

        # Slice everything *after* the closing delimiter
        body_lines: Iterable[str] = lines[end_idx + 1 :]
        return "".join(body_lines)

    # No front-matter at all
    return "".join(lines)
