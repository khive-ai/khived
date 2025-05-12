# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from enum import Enum

from pydantic import BaseModel, Field

__all__ = (
    "DocumentInfo",
    "PartialChunk",
    "ReaderAction",
    "ReaderFileRequestParams",
    "ReaderListDirParams",
    "ReaderListDirResponseContent",
    "ReaderOpenParams",
    "ReaderOpenResponseContent",
    "ReaderReadParams",
    "ReaderReadResponseContent",
    "ReaderRequest",
    "ReaderResponse",
    "ReaderResponseContent",
)


class ReaderAction(str, Enum):
    """
    This enumeration indicates the *type* of action the LLM wants to perform.
    - 'open': Convert a file/URL to text and store it internally for partial reads
    - 'read': Return a partial slice of the already-opened doc, a doc contains content,
        length in chars, and **ESTIMATED** number of tokens
    """

    OPEN = "open"
    READ = "read"
    LIST_DIR = "list_dir"


class ReaderOpenParams(BaseModel):
    """
    Automatically extract data from a file or URL and store it in the tool's cache.
    The tool is capable of extracting data from various file formats, such as: text-based files, PDF, DOCX, HTML, IMAGES, and more. You can also provide a URL to a webpage, and the tool will extract the text content from that page. for example: `https://arxiv.org/abs/2301.00001.pdf`
    """

    path_or_url: str = Field(..., description="Local file path or remote URL to open. ")


class ReaderReadParams(BaseModel):
    doc_id: str = Field(
        ..., description="Unique ID referencing a previously opened document."
    )

    start_offset: int | None = Field(
        None, description="Character start offset in the doc for partial reading."
    )

    end_offset: int | None = Field(
        None, description="Character end offset in the doc for partial reading."
    )


class ReaderListDirParams(BaseModel):
    directory: str = Field(
        ...,
        description="Directory path to list.",
        examples=["/path/to/directory", "/path/to/directory/subdirectory"],
    )
    recursive: bool | None = Field(
        False,
        description="Whether to recursively list files in subdirectories. Defaults to False.",
    )
    file_types: list[str] | None = Field(
        None,
        description="List files with specific extensions.",
        examples=[".txt", ".pdf"],
    )


ReaderFileRequestParams = ReaderListDirParams | ReaderReadParams | ReaderOpenParams


class ReaderRequest(BaseModel):
    """
    The request model for the 'ReaderTool'.
    It indicates:
      - whether we are 'open'-ing a doc or 'read'-ing from a doc
      - which file/URL we want to open (if action='open')
      - which doc_id and offsets we want to read (if action='read')
      - what files exist in a directory (if action='list_dir')
    """

    action: ReaderAction = Field(
        ...,
        description=(
            "Action to perform. Must be one of: "
            "- 'open': Convert a file/URL to text and store it internally for partial reads. "
            "- 'read': Return a partial slice of the already-opened doc."
            "- 'list_dir': List files in a directory."
        ),
    )

    params: ReaderFileRequestParams = Field(
        ..., description="Parameters for the action"
    )


class DocumentInfo(BaseModel):
    """
    Returned info when we 'open' a doc.
    doc_id: The unique string to reference this doc in subsequent 'read' calls
    length: The total character length of the converted text
    """

    doc_id: str
    length: int | None = None
    num_tokens: int | None = None


class PartialChunk(BaseModel):
    """
    Represents a partial slice of text from [start_offset..end_offset).
    """

    start_offset: int | None = None
    end_offset: int | None = None
    content: str | None = None


class ReaderOpenResponseContent(BaseModel):
    doc_info: DocumentInfo | None = Field(
        None,
        description=(
            "Populated only if action='open' succeeded, letting the LLM know doc_id & total length."
        ),
    )


class ReaderReadResponseContent(BaseModel):
    chunk: PartialChunk | None = Field(
        None,
        description=(
            "Populated only if action='read' succeeded, providing the partial slice of text."
        ),
    )


class ReaderListDirResponseContent(BaseModel):
    files: list[str] | None = Field(
        None,
        description=(
            "List of files in the directory, populated only if action='list_dir' succeeded."
        ),
    )


ReaderResponseContent = (
    ReaderListDirResponseContent | ReaderReadResponseContent | ReaderOpenResponseContent
)


class ReaderResponse(BaseModel):
    """
    The response from the 'ReaderTool'.
    - If action='open' succeeded, doc_info is filled (doc_id & length).
    - If action='read' succeeded, chunk is filled (the partial text).
    - If failure occurs, success=False & error hold details.
    """

    success: bool = Field(
        ...,
        description=("Indicates if the requested action was performed successfully."),
    )
    error: str | None = Field(
        None,
        description=("Describes any error that occurred, if success=False."),
    )
    content: ReaderResponseContent | None = Field(
        None,
        description="Populated only if action succeeded, providing the relevant content.",
    )
