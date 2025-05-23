from typing import Literal

from pydapter.protocols.utils import is_package_installed

if not is_package_installed("fastmcp"):
    raise ImportError(
        "fastmcp is not installed. Please install it with `pip install fastmcp`."
    )


from fastmcp import FastMCP

from khive.services.reader.parts import (
    ReaderAction,
    ReaderListDirParams,
    ReaderOpenParams,
    ReaderRequest,
)
from khive.services.reader.reader_service import ReaderServiceGroup

instructions = """
Khive Reader is a multi-purpose service for reading external information.
It extracts, parses data and stores it in the tool's cache. It supports 
text-based files, PDF, DOCX, HTML, IMAGES, and more. You can also provide
a URL to a webpage, and the tool will extract the text content from that 
page. for example: `https://arxiv.org/abs/2301.00001.pdf`
"""

mcp = FastMCP(
    name="khive_reader",
    instructions=instructions,
    tags=["khive", "reader", "open", "read", "list_dir"],
)


@mcp.tool(
    name="open",
    description="Open a file or URL and extract its content.",
)
async def open(
    path_or_url: str,
    start_offset: int | None = None,
    end_offset: int | None = None,
):
    """
    Automatically extract data from a file or URL and store it in disk cache.
    If either or both `start_offset` and `end_offset` are provided, the tool will read
    the content from the specified offsets. If both are None, it will return the
    file open action status, such as doc_id, file size, and other metadata.

    Args:
        path_or_url (str): Local file path or remote URL to open.
        start_offset (int | None): read the content from this character offset.
        end_offset (int | None): read the content until this character offset.
    """
    group = ReaderServiceGroup()
    open_request = ReaderRequest(
        action=ReaderAction.OPEN,
        params=ReaderOpenParams(path_or_url=path_or_url),
    )
    open_response = await group.handle_request(open_request)
    if open_response.success is False:
        return open_response

    if start_offset is None and end_offset is None:
        return open_response

    read_request = ReaderRequest(
        action=ReaderAction.READ,
        params=ReaderOpenParams(
            doc_id=open_response.content.doc_info.doc_id,
            start_offset=start_offset,
            end_offset=end_offset,
        ),
    )

    read_response = await group.handle_request(read_request)
    return [open_response, read_response]


@mcp.tool(
    name="read",
    description="Read a document from the cache.",
)
async def read(
    doc_id: str,
    start_offset: int | None = None,
    end_offset: int | None = None,
):
    """Read a document from the cache. If the document is not in the cache, will return error. If neither `start_offset` nor `end_offset` are provided, the tool will read the entire content of the document. (not recommended for large documents, should always provide offsets as safe guards, )

    Args:
        doc_id (str): Unique ID referencing a previously opened document.
        start_offset (int | None): read the content from this character offset.
        end_offset (int | None): read the content until this character offset.
    """
    request = ReaderRequest(
        action=ReaderAction.READ,
        params=ReaderOpenParams(
            doc_id=doc_id,
            start_offset=start_offset,
            end_offset=end_offset,
        ),
    )
    return await ReaderServiceGroup().handle_request(request)


@mcp.tool(
    name="list_dir",
    description="List files in a directory.",
)
async def list_dir(
    directory: str,
    recursive: bool | None = False,
    file_types: list[str] = None,
    start_offset: int | None = None,
    end_offset: int | None = None,
):
    """
    List files in a directory, save into a doc in cache, which can be read via `read` tool.
    If no `file_types` are provided, all files types will be listed. If either or both `start_offset` and `end_offset` are provided, the tool will read the content from the specified offsets. If both are None, it will return the list dir action status, such as doc_id, file size, and other metadata.

    Args:
        directory (str): Directory path to list.
        recursive (bool | None): Whether to recursively list files in subdirectories. Defaults to False.
        file_types (list[str] | None): List files with specific extensions. For example: [".txt", ".pdf"]
        start_offset (int | None): read the content from this character offset.
        end_offset (int | None): read the content until this character offset.
    """
    group = ReaderServiceGroup()
    list_dir_request = ReaderRequest(
        action=ReaderAction.LIST_DIR,
        params=ReaderListDirParams(
            directory=directory,
            recursive=recursive,
            file_types=file_types,
        ),
    )

    list_dir_response = await group.handle_request(list_dir_request)

    if list_dir_response.success is False:
        return list_dir_response

    if start_offset is None and end_offset is None:
        return list_dir_response

    read_request = ReaderRequest(
        action=ReaderAction.READ,
        params=ReaderOpenParams(
            doc_id=list_dir_response.content.doc_info.doc_id,
            start_offset=start_offset,
            end_offset=end_offset,
        ),
    )

    read_response = await group.handle_request(read_request)
    return [list_dir_response, read_response]


@mcp.tool(
    name="list_cache",
    description="List files in the cache.",
    tags=["khive", "reader", "list_cache"],
)
async def list_cache(
    doc_type: Literal["all", "dir", "doc"] = "all",
    max_num: int | None = 20,
) -> list[str]:
    """
    list the files in cache,

    Args:
        type (Literal["all", "dir", "doc"]): The type of files to list.
            Can be one of ["all", "dir", "doc"]. Defaults to "all".
        max_num (int | None): The maximum number of files to list. Defaults to 20.
    """
    index = ReaderServiceGroup()._load_index()
    files = list(index.keys())

    if doc_type == "dir":
        files = [f for f in files if f.startswith("DIR_")]
    if doc_type == "doc":
        files = [f for f in files if not f.startswith("DOC_")]

    if max_num is not None and max_num < len(files):
        files = files[:max_num]
    return files


if __name__ == "__main__":
    mcp.run()
