#!/usr/bin/env python3
"""
CLI wrapper around khive.reader.ReaderTool.

❱  Examples
-----------

# 1.  Open a file / URL  → returns {"success":true,"doc_info":{…}}
reader_cli.py open  --source README.md

# 2.  Read slice 200-400 characters from that document
reader_cli.py read  --doc DOC_123456 --start 200 --end 400

# 3.  Non-recursive directory listing of *.md files
reader_cli.py list  --path docs --types .md

All responses are JSON (one line) printed to stdout.
Errors go to stderr and a non-zero exit code.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Final

from pydantic import ValidationError

# --------------------------------------------------------------------------- #
# khive reader                                                                #
# --------------------------------------------------------------------------- #
try:
    from .reader_tool import ReaderRequest, ReaderService  # noqa: E402
except ModuleNotFoundError:
    sys.stderr.write(
        "❌ reader_tool.py not found - make sure it's in the same directory\n"
    )
    sys.exit(1)

# --------------------------------------------------------------------------- #
# Persistent cache (maps doc_id  →  converted-text-file-path & length)        #
# --------------------------------------------------------------------------- #
CACHE_FILE: Final[Path] = Path.home() / ".khive_reader_cache.json"


def _load_cache() -> dict[str, Any]:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except Exception:
            pass  # fall through to new cache
    return {}


def _save_cache(cache: dict[str, Any]) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2))


CACHE = _load_cache()

# --------------------------------------------------------------------------- #
# Instantiate tool (kept in-process)                                          #
# --------------------------------------------------------------------------- #
reader_tool = ReaderService()


def _handle_request(req_dict: dict[str, Any]) -> None:
    """Validate, call ReaderTool, persist cache if needed, pretty-print JSON."""
    try:
        req = ReaderRequest(**req_dict)  # validation
        res = reader_tool.handle_request(req)
    except ValidationError as ve:
        sys.stderr.write(f"❌ Parameter validation failed:\n{ve}\n")
        sys.exit(1)

    # Persist mapping for open/list_dir so later 'read' works across CLI calls
    if res.success and res.doc_info:
        CACHE[res.doc_info.doc_id] = {
            "path": reader_tool.documents[res.doc_info.doc_id][0],
            "length": res.doc_info.length,
        }
        _save_cache(CACHE)

    # Pretty JSON to STDOUT
    print(json.dumps(res.model_dump(exclude_none=True), ensure_ascii=False))
    sys.exit(0 if res.success else 2)


# --------------------------------------------------------------------------- #
# Command-line parsing                                                        #
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(prog="reader_cli.py", description="khive Reader")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # --- open --------------------------------------------------------------- #
    sp_open = sub.add_parser("open", help="Open a file or URL for later reading")
    sp_open.add_argument(
        "--source",
        required=True,
        help="Local path or remote URL to open & convert to text",
    )

    # --- read --------------------------------------------------------------- #
    sp_read = sub.add_parser("read", help="Read a slice of an opened document")
    sp_read.add_argument("--doc", required=True, help="doc_id returned by 'open'")
    sp_read.add_argument("--start", type=int, default=0, help="Start offset (chars)")
    sp_read.add_argument("--end", type=int, help="End offset (chars, exclusive)")

    # --- list_dir ----------------------------------------------------------- #
    sp_ls = sub.add_parser("list", help="List directory contents")
    sp_ls.add_argument("--path", required=True, help="Directory to list")
    sp_ls.add_argument(
        "--recursive", action="store_true", help="Recurse into sub-directories"
    )
    sp_ls.add_argument(
        "--types",
        nargs="*",
        metavar="EXT",
        help="Only list files with these extensions (e.g. .md .txt)",
    )

    ns = ap.parse_args()

    # Build ReaderRequest dict
    if ns.cmd == "open":
        _handle_request(
            {
                "action": "open",
                "path_or_url": ns.source,
            }
        )
    elif ns.cmd == "read":
        # Resolve doc in cache if we only have numeric hash label
        if ns.doc not in reader_tool.documents and ns.doc in CACHE:
            # restore mapping into live tool for this process
            path = CACHE[ns.doc]["path"]
            length = CACHE[ns.doc]["length"]
            reader_tool.documents[ns.doc] = (path, length)

        _handle_request(
            {
                "action": "read",
                "doc_id": ns.doc,
                "start_offset": ns.start,
                "end_offset": ns.end,
            }
        )
    elif ns.cmd == "list":
        _handle_request(
            {
                "action": "list_dir",
                "path_or_url": ns.path,
                "recursive": ns.recursive,
                "file_types": ns.types,
            }
        )
    else:  # unreachable
        ap.error("Unknown command")


if __name__ == "__main__":
    main()
