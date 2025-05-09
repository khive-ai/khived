# server.py
from fastmcp import FastMCP
from pydapter import AsyncAdaptable
from pydapter.extras.async_qdrant_ import AsyncQdrantAdapter

mcp = FastMCP("Demo 🚀")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


if __name__ == "__main__":
    mcp.run()
