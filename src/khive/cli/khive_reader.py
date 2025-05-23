# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
CLI for khive Reader services, including document operations and ingestion.
Uses Typer for command-line interface structure.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Annotated, Any, Final

import typer
from pydantic import HttpUrl, ValidationError

# --------------------------------------------------------------------------- #
# khive reader imports                                                        #
# --------------------------------------------------------------------------- #
try:
    from khive.reader.services.ingestion_service import Document as IngestDocument

    # Placeholder
    from khive.reader.services.ingestion_service import (
        DocumentIngestionService,
        InMemoryDocumentRepository,
    )
    from khive.reader.services.ingestion_service import (
        DocumentStatus as IngestDocumentStatus,
    )
    from khive.reader.storage.minio_client import ObjectStorageClient
    from khive.services.reader.parts import (
        ReaderAction,
        ReaderListDirParams,
        ReaderOpenParams,
        ReaderReadParams,
        ReaderRequest,
        ReaderResponse,
    )
    from khive.services.reader.reader_service import ReaderServiceGroup
except ModuleNotFoundError as e:
    sys.stderr.write(
        f"❌ Required modules not found. Ensure khive.services.reader and related modules are in PYTHONPATH.\nError: {e}\n"
    )
    sys.exit(1)
except ImportError as e:
    sys.stderr.write(
        f"❌ Error importing from khive.services.reader or ingestion service.\nError: {e}\n"
    )
    sys.exit(1)

# --------------------------------------------------------------------------- #
# CLI App Initialization                                                      #
# --------------------------------------------------------------------------- #
app = typer.Typer(
    name="reader",
    help="Khive Reader: Document operations (open, read, list) and ingestion.",
    add_completion=False,
    no_args_is_help=True,
)

# --------------------------------------------------------------------------- #
# Persistent cache for 'open', 'read', 'list' commands                        #
# --------------------------------------------------------------------------- #
CACHE_FILE: Final[Path] = Path.home() / ".khive_reader_cache.json"


def _load_cache() -> dict[str, Any]:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            typer.echo(
                f"Warning: Failed to load cache from {CACHE_FILE}. Starting with an empty cache.",
                err=True,
            )
    return {}


def _save_cache(cache: dict[str, Any]) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


CACHE = _load_cache()
reader_service_group_instance = (
    ReaderServiceGroup()
)  # Global instance for this CLI session


def _print_json_response(data: Any, success: bool = True, exit_code: int | None = None):
    if isinstance(data, (ReaderResponse, IngestDocument)):
        typer.echo(
            json.dumps(
                data.model_dump(exclude_none=True, by_alias=True), ensure_ascii=False
            )
        )
    elif isinstance(data, dict):
        typer.echo(json.dumps(data, ensure_ascii=False))
    else:
        typer.echo(
            json.dumps({"success": success, "detail": str(data)}, ensure_ascii=False)
        )

    if exit_code is not None:
        raise typer.Exit(code=exit_code)
    elif not success:
        raise typer.Exit(code=1)


@app.command("open")
async def open_document(  # Made async
    path_or_url: Annotated[
        str, typer.Option(help="Local path or remote URL to open & convert to text.")
    ],
):
    """Open a file or URL for later reading, returns document info including a doc_id."""
    req_dict = {"path_or_url": path_or_url}
    try:
        params_model = ReaderOpenParams(**req_dict)
        req = ReaderRequest(action=ReaderAction.OPEN, params=params_model)
        res: ReaderResponse = await reader_service_group_instance.handle_request(
            req
        )  # Added await
    except Exception as e:
        _print_json_response(
            {"success": False, "error": str(e), "type": type(e).__name__}, success=False
        )
        return  # Should be unreachable due to typer.Exit in _print_json_response

    if (
        res.success
        and res.content
        and hasattr(res.content, "doc_info")
        and res.content.doc_info
    ):
        doc_id = res.content.doc_info.doc_id
        if doc_id in reader_service_group_instance.documents:
            temp_file_path, _doc_len_internal = reader_service_group_instance.documents[
                doc_id
            ]
            CACHE[doc_id] = {
                "path": temp_file_path,
                "length": res.content.doc_info.length,
                "num_tokens": res.content.doc_info.num_tokens,
            }
            _save_cache(CACHE)
        else:
            typer.echo(
                f"⚠️ Warning: Doc_id '{doc_id}' reported success but not found in service's internal document map for caching path.",
                err=True,
            )
    _print_json_response(res, success=res.success, exit_code=0 if res.success else 2)


@app.command("read")
async def read_document(  # Made async
    doc_id: Annotated[
        str, typer.Option(help="doc_id returned by 'open' or 'list_dir'.")
    ],
    start_offset: Annotated[
        int | None, typer.Option(help="Start offset (chars).")
    ] = None,
    end_offset: Annotated[
        int | None, typer.Option(help="End offset (chars, exclusive).")
    ] = None,
):
    """Read a slice of an opened document."""
    if doc_id not in reader_service_group_instance.documents and doc_id in CACHE:
        cached_doc_info = CACHE[doc_id]
        reader_service_group_instance.documents[doc_id] = (
            cached_doc_info["path"],
            cached_doc_info["length"],
        )

    req_dict = {
        "doc_id": doc_id,
        "start_offset": start_offset,
        "end_offset": end_offset,
    }
    try:
        params_model = ReaderReadParams(**req_dict)
        req = ReaderRequest(action=ReaderAction.READ, params=params_model)
        res: ReaderResponse = await reader_service_group_instance.handle_request(
            req
        )  # Added await
    except Exception as e:
        _print_json_response(
            {"success": False, "error": str(e), "type": type(e).__name__}, success=False
        )
        return
    _print_json_response(res, success=res.success, exit_code=0 if res.success else 2)


@app.command("list")
async def list_directory(  # Made async
    directory: Annotated[str, typer.Option(help="Directory to list.")],
    recursive: Annotated[
        bool,
        typer.Option(
            "--recursive/--no-recursive", help="Recurse into sub-directories."
        ),
    ] = False,
    file_types: Annotated[
        list[str] | None,
        typer.Option(help="Only list files with these extensions (e.g. .md .txt)."),
    ] = None,
):
    """List directory contents and store as a document, returning document info."""
    req_dict = {
        "directory": directory,
        "recursive": recursive,
        "file_types": file_types or [],  # Ensure it's a list
    }
    try:
        params_model = ReaderListDirParams(**req_dict)
        req = ReaderRequest(action=ReaderAction.LIST_DIR, params=params_model)
        res: ReaderResponse = await reader_service_group_instance.handle_request(
            req
        )  # Added await
    except Exception as e:
        _print_json_response(
            {"success": False, "error": str(e), "type": type(e).__name__}, success=False
        )
        return

    if (
        res.success
        and res.content
        and hasattr(res.content, "doc_info")
        and res.content.doc_info
    ):  # Similar caching logic as 'open'
        doc_id = res.content.doc_info.doc_id
        if doc_id in reader_service_group_instance.documents:
            temp_file_path, _doc_len_internal = reader_service_group_instance.documents[
                doc_id
            ]
            CACHE[doc_id] = {
                "path": temp_file_path,
                "length": res.content.doc_info.length,
                "num_tokens": res.content.doc_info.num_tokens,
            }
            _save_cache(CACHE)
    _print_json_response(res, success=res.success, exit_code=0 if res.success else 2)


async def _ingest_document_async(
    source_uri_str: str, metadata_file_path: str | None, json_output_flag: bool
):
    try:
        source_uri = HttpUrl(source_uri_str)
    except ValidationError as e:
        if json_output_flag:
            _print_json_response(
                {
                    "success": False,
                    "error": f"Invalid source URI: {source_uri_str}",
                    "details": str(e),
                },
                success=False,
            )
        else:
            typer.secho(
                f"❌ Invalid source URI: {source_uri_str}\n{e}",
                fg=typer.colors.RED,
                err=True,
            )
        raise typer.Exit(code=1)

    metadata_content: dict[str, Any] | None = None
    if metadata_file_path:
        try:
            metadata_path = Path(metadata_file_path)
            if not metadata_path.exists():
                err_msg = f"Metadata file not found: {metadata_file_path}"
                if json_output_flag:
                    _print_json_response(
                        {"success": False, "error": err_msg}, success=False
                    )
                else:
                    typer.secho(f"❌ {err_msg}", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=1)
            with open(metadata_path, encoding="utf-8") as f:
                metadata_content = json.load(f)
        except json.JSONDecodeError as e:
            err_msg = (
                f"Error decoding JSON from metadata file {metadata_file_path}: {e}"
            )
            if json_output_flag:
                _print_json_response(
                    {"success": False, "error": err_msg}, success=False
                )
            else:
                typer.secho(f"❌ {err_msg}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        except Exception as e:
            err_msg = f"Error reading metadata file {metadata_file_path}: {e}"
            if json_output_flag:
                _print_json_response(
                    {"success": False, "error": err_msg}, success=False
                )
            else:
                typer.secho(f"❌ {err_msg}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)

    minio_endpoint_url = os.getenv("MINIO_ENDPOINT_URL")
    minio_access_key = os.getenv("MINIO_ACCESS_KEY")
    minio_secret_key = os.getenv("MINIO_SECRET_KEY")
    minio_bucket_name = os.getenv(
        "MINIO_BUCKET_NAME_READER_INGEST", "khive-reader-ingest"
    )

    if not all([
        minio_endpoint_url,
        minio_access_key,
        minio_secret_key,
        minio_bucket_name,
    ]):
        err_msg = (
            "MinIO client configuration not fully set. Please set MINIO_ENDPOINT_URL, "
            "MINIO_ACCESS_KEY, MINIO_SECRET_KEY, and MINIO_BUCKET_NAME_READER_INGEST env vars."
        )
        if json_output_flag:
            _print_json_response({"success": False, "error": err_msg}, success=False)
        else:
            typer.secho(f"❌ {err_msg}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    try:
        storage_client = ObjectStorageClient(
            endpoint_url=minio_endpoint_url,
            access_key=minio_access_key,
            secret_key=minio_secret_key,
            bucket_name=minio_bucket_name,
            secure=minio_endpoint_url.startswith("https"),
        )
        if not storage_client.ensure_bucket_exists():
            err_msg = f"Failed to ensure MinIO bucket '{minio_bucket_name}' exists."
            if json_output_flag:
                _print_json_response(
                    {"success": False, "error": err_msg}, success=False
                )
            else:
                typer.secho(f"❌ {err_msg}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
    except Exception as e:
        err_msg = f"Failed to initialize ObjectStorageClient: {e}"
        if json_output_flag:
            _print_json_response(
                {"success": False, "error": err_msg, "type": type(e).__name__},
                success=False,
            )
        else:
            typer.secho(f"❌ {err_msg}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    document_repository = InMemoryDocumentRepository()  # Placeholder
    ingestion_service = DocumentIngestionService(document_repository, storage_client)

    try:
        ingested_doc: (
            IngestDocument | None
        ) = await ingestion_service.ingest_document_from_url(
            source_uri=source_uri,
            metadata_file_content=metadata_content,
        )
        if ingested_doc:
            if json_output_flag:
                # Directly print and exit for simplicity in debugging runner behavior
                typer.echo(
                    ingested_doc.model_dump_json(by_alias=True, exclude_none=True)
                )
            else:
                typer.secho("Document Ingestion Summary:", fg=typer.colors.GREEN)
                typer.echo(f"  ID: {ingested_doc.id}")
                typer.echo(f"  Source URI: {ingested_doc.source_uri}")
                typer.echo(f"  Status: {ingested_doc.status.value}")
                typer.echo(f"  Storage Path: {ingested_doc.storage_path or 'N/A'}")
                typer.echo(f"  Size (bytes): {ingested_doc.size_bytes or 'N/A'}")
                if ingested_doc.error_message:
                    typer.secho(
                        f"  Error: {ingested_doc.error_message}", fg=typer.colors.YELLOW
                    )
            # Ensure this is the only exit path for success in this block
            # The previous _print_json_response might have interfered with runner's exit code capture
            # if it didn't raise an exit itself.
            raise typer.Exit(code=0)
        else:  # ingested_doc is None
            err_msg = f"Document ingestion failed for URI: {source_uri_str}"
            if json_output_flag:
                _print_json_response(
                    {"success": False, "error": err_msg}, success=False
                )
            else:
                typer.secho(f"❌ {err_msg}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
    except Exception as e:
        err_msg = f"An error occurred during ingestion: {type(e).__name__}: {e}"
        if json_output_flag:
            _print_json_response(
                {"success": False, "error": err_msg, "type": type(e).__name__},
                success=False,
            )
        else:
            typer.secho(f"❌ {err_msg}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


@app.command("ingest")
def ingest_document_command(
    source_uri: Annotated[
        str, typer.Option(help="The source URI (URL) of the document to ingest.")
    ],
    metadata_file: Annotated[
        Path | None,
        typer.Option(
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
            help="Optional path to a JSON file containing metadata for the document.",
        ),
    ] = None,  # Removed exists=True
    json_output: Annotated[
        bool,
        typer.Option("--json-output", help="Output ingestion result in JSON format."),
    ] = False,
):
    """Ingest a document from a source URI into the system."""
    metadata_file_str = str(metadata_file) if metadata_file else None
    asyncio.run(_ingest_document_async(source_uri, metadata_file_str, json_output))


if __name__ == "__main__":
    app()
