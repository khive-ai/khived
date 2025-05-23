#!/usr/bin/env python3
"""
CLI wrapper around khive.services.reader.reader_service.ReaderService.

❱  Examples
-----------

# 1.  Open a file / URL  → returns {"success":true,"content":{"doc_info":{…}}}
reader_cli.py open  --path_or_url README.md

# 2.  Read slice 200-400 characters from that document
reader_cli.py read  --doc_id DOC_123456 --start_offset 200 --end_offset 400

# 3.  Non-recursive directory listing of *.md files
reader_cli.py list  --directory docs --file_types .md

# 4. Recursive directory listing
reader_cli.py list --directory project_src --recursive

All responses are JSON (one line) printed to stdout.
Errors go to stderr and a non-zero exit code.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Final

# --------------------------------------------------------------------------- #
# khive reader                                                                #
# --------------------------------------------------------------------------- #
try:
    # Assuming parts.py and reader_service.py are in khive.services.reader
    from khive.services.reader.parts import (  # Import specific param models
        ReaderAction,
        ReaderListDirParams,
        ReaderOpenParams,
        ReaderReadParams,
        ReaderRequest,  # Main request model
        ReaderResponse,  # Main response model
    )
    from khive.services.reader.reader_service import ReaderServiceGroup
except ModuleNotFoundError as e:
    sys.stderr.write(
        f"❌ Required modules not found. Ensure khive.services.reader is in PYTHONPATH.\nError: {e}\n"
    )
    sys.exit(1)
except ImportError as e:
    sys.stderr.write(f"❌ Error importing from khive.services.reader.\nError: {e}\n")
    sys.exit(1)


# --------------------------------------------------------------------------- #
# Persistent cache (maps doc_id  →  {path: temp_file_path, length: int, num_tokens: int | None}) #
# --------------------------------------------------------------------------- #
CACHE_FILE: Final[Path] = Path.home() / ".khive_reader_cache.json"


def _load_cache() -> dict[str, Any]:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            sys.stderr.write(
                f"Failed to load cache from {CACHE_FILE}. Starting with an empty cache."
            )
    return {}


def _save_cache(cache: dict[str, Any]) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


CACHE = _load_cache()

# --------------------------------------------------------------------------- #
# Instantiate service (kept in-process)                                       #
# --------------------------------------------------------------------------- #
# This global instance will persist self.documents within a single CLI execution
# but not across multiple CLI executions unless we repopulate it from CACHE.
reader_service = ReaderServiceGroup()


async def _handle_request_and_print(req_dict: dict[str, Any]) -> None:
    """Validate, call ReaderService, persist cache if needed, pretty-print JSON."""
    try:
        # Construct the request with the correct nested params structure
        action = req_dict.pop("action")  # Extract action
        params_model = None
        if action == ReaderAction.OPEN:
            params_model = ReaderOpenParams(**req_dict)
        elif action == ReaderAction.READ:
            params_model = ReaderReadParams(**req_dict)
        elif action == ReaderAction.LIST_DIR:
            params_model = ReaderListDirParams(**req_dict)
        else:
            sys.stderr.write(
                f"❌ Internal CLI error: Unknown action type '{action}' for param model mapping.\n"
            )
            sys.exit(1)

        req = ReaderRequest(action=action, params=params_model)
        res: ReaderResponse = await reader_service.handle_request(req)

    except Exception as e:  # Catch Pydantic ValidationError and other potential errors
        sys.stderr.write(
            f"❌ Request construction or handling failed:\n{type(e).__name__}: {e}\n"
        )
        sys.exit(1)

    # Persist mapping for open/list_dir so later 'read' works across CLI calls
    if (
        res.success
        and res.content
        and hasattr(res.content, "doc_info")
        and res.content.doc_info
    ):
        doc_id = res.content.doc_info.doc_id
        # The reader_service.documents stores (temp_file.name, doc_len)
        # We need to access that internal temp_file.name to cache it.
        if doc_id in reader_service.documents:
            temp_file_path, _doc_len_internal = reader_service.documents[
                doc_id
            ]  # num_tokens not stored in service's self.documents yet
            CACHE[doc_id] = {
                "path": temp_file_path,  # This is the crucial part from the service's internal state
                "length": res.content.doc_info.length,
                "num_tokens": res.content.doc_info.num_tokens,  # Cache this too
            }
            _save_cache(CACHE)
        else:
            sys.stderr.write(
                f"⚠️ Warning: Doc_id '{doc_id}' reported success but not found in service's internal document map for caching path.\n"
            )

    # Pretty JSON to STDOUT
    # Use res.model_dump() for Pydantic models
    print(
        json.dumps(res.model_dump(exclude_none=True, by_alias=True), ensure_ascii=False)
    )
    sys.exit(0 if res.success else 2)


# --------------------------------------------------------------------------- #
# Command-line parsing                                                        #
# --------------------------------------------------------------------------- #
async def _main() -> None:
    ap = argparse.ArgumentParser(prog="reader_cli.py", description="khive Reader CLI")
    sub = ap.add_subparsers(
        dest="action_command", required=True, help="Action to perform"
    )

    # --- open --------------------------------------------------------------- #
    sp_open = sub.add_parser(
        ReaderAction.OPEN.value, help="Open a file or URL for later reading"
    )
    sp_open.add_argument(
        "--path_or_url",  # Matches ReaderOpenParams field
        required=True,
        help="Local path or remote URL to open & convert to text",
    )

    # --- read --------------------------------------------------------------- #
    sp_read = sub.add_parser(
        ReaderAction.READ.value, help="Read a slice of an opened document"
    )
    sp_read.add_argument(
        "--doc_id", required=True, help="doc_id returned by 'open' or 'list_dir'"
    )  # Matches ReaderReadParams
    sp_read.add_argument(
        "--start_offset", type=int, default=None, help="Start offset (chars)"
    )  # Matches ReaderReadParams
    sp_read.add_argument(
        "--end_offset", type=int, default=None, help="End offset (chars, exclusive)"
    )  # Matches ReaderReadParams

    # --- list_dir ----------------------------------------------------------- #
    sp_ls = sub.add_parser(
        ReaderAction.LIST_DIR.value,
        help="List directory contents and store as a document",
    )
    sp_ls.add_argument(
        "--directory", required=True, help="Directory to list"
    )  # Matches ReaderListDirParams
    sp_ls.add_argument(
        "--recursive",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Recurse into sub-directories",  # Matches ReaderListDirParams
    )
    sp_ls.add_argument(
        "--file_types",  # Matches ReaderListDirParams
        nargs="*",
        metavar="EXT",
        default=None,
        help="Only list files with these extensions (e.g. .md .txt)",
    )

    args = ap.parse_args()
    action_str = args.action_command  # This is 'open', 'read', or 'list_dir'

    # Prepare request dictionary based on the subcommand
    request_params_dict: dict[str, Any] = {}
    if action_str == ReaderAction.OPEN.value:
        request_params_dict = {"path_or_url": args.path_or_url}
    elif action_str == ReaderAction.READ.value:
        # Resolve doc_id from cache if it's not in the live service instance
        # This allows 'read' to work across different CLI invocations for the same doc_id
        if args.doc_id not in reader_service.documents and args.doc_id in CACHE:
            cached_doc_info = CACHE[args.doc_id]
            # Repopulate the live service's document mapping for this process
            # The service stores (temp_file_path, doc_length)
            reader_service.documents[args.doc_id] = (
                cached_doc_info["path"],
                cached_doc_info["length"],
            )
            # Note: The actual content is in the temp file; the service reads it on demand.
            # num_tokens is not directly used by the service's read logic, but was cached.

        request_params_dict = {
            "doc_id": args.doc_id,
            "start_offset": args.start_offset,
            "end_offset": args.end_offset,
        }
    elif action_str == ReaderAction.LIST_DIR.value:
        request_params_dict = {
            "directory": args.directory,
            "recursive": args.recursive,
            "file_types": args.file_types,
        }
    else:  # Should be caught by argparse
        ap.error(f"Unknown command: {action_str}")
        sys.exit(1)  # Should not be reached

    # Add the action string to the dict that will be passed to build the Pydantic model
    full_request_dict = {"action": ReaderAction(action_str), **request_params_dict}
    await _handle_request_and_print(full_request_dict)


def main() -> None:
    """Main entry point for the CLI."""
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        sys.stderr.write("❌ Operation cancelled by user.\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"❌ Unexpected error: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
