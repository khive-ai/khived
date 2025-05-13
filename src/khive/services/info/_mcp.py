import asyncio
import inspect
import json
from functools import wraps

from fastmcp import FastMCP
from pydapter import AsyncAdaptable
from pydapter.extras.async_qdrant_ import AsyncQdrantAdapter

from khive.providers.oai_ import OpenaiEmbedEndpoint
from khive.services.info.info_service import InfoService
from khive.traits import Embedable, Identifiable, Temporal

mcp = FastMCP(name="KHIVE-INFO-SERVICE")
endpoint = OpenaiEmbedEndpoint()


class Memory(Identifiable, Temporal, Embedable, AsyncAdaptable):
    content: str

    async def generated_embedding(self):
        response = await endpoint.call({"input": self.content})
        self.embedding = response.data[0].embedding
        return self


Memory.register_async_adapter(AsyncQdrantAdapter)


info_service = InfoService()


@mcp.tool("info")
@save_to_memory(collection="info_memory")  # <- just this one line
async def handle_request(request):
    return await info_service.handle_request(request)


@mcp.tool("search_doc")
async def search_documents(query_text: str, top_k=2):
    response = endpoint.call({"input": query_text})
    embedding = response.data[0].embedding

    print(f"Searching for documents similar to: '{query_text}'")

    # Search in Qdrant using the QdrantAdapter
    results = await Memory.adapt_from_async(
        {
            "collection": "info_memory",
            "query_vector": embedding,
            "top_k": top_k,
            "url": "http://localhost:6333",
        },
        obj_key="async_qdrant",
    )

    print(f"Found {len(results)} similar documents:")
    for i, doc in enumerate(results):
        print(f"{i+1}. {doc.title}")
        print(f"   Content: {doc.content}")
        print(f"   Tags: {', '.join(doc.tags)}")
        print()

    return results


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
