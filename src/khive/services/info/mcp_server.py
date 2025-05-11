from typing import Literal
from fastmcp import FastMCP, Context
from pydantic import BaseModel

from khive.services.info.parts import InfoRequest

from khive.services.info.service import InfoService, PerplexityChatRequest, ExaSearchRequest, InfoConsultParams

from khive.protocols import Identifiable, Event


class ServiceMeta():
    ...





class MCPRequest(BaseModel):
    
    
    
    ...
    
    
class MCPResponse(BaseModel):
    ...







mcp = FastMCP(name="khive_info")

service = InfoService()











class KhiveMCPRequest(BaseModel):
    service: str
    action: str
    provider: str
    request: dict

class KhiveMCPResponse(BaseModel):

    request_type: Literal["tool", "resource", "prompt"]
    error: str | None = None
    success: bool = True



@mcp.resource(
    uri="resource://{action}/providers"
)
async def get_providers(action: str, ctx: Context):
    """
    get the available providers for a specific action
    
    Args:
        action (str): The action type, either 'search' or 'consult'.
    """
    if action == "search":
        return {"providers": ["perplexity", "exa"]}
    if action == "consult":
        return {"providers": ["openai", "gemini", "claude"]}
    return {"error": f"INVALID ACTION: {action}"}

@mcp.resource()
async def get_provider_param_schema(
    action: str,
    provider: str,
    ctx: Context,
):
    """
    Get the parameter schema for a specific action and provider.
    
    Args:
        action (str): The action type, either 'search' or 'consult'.
        provider (str): The provider type
    
    Returns:
        dict: A dictionary containing the parameter schema for the specified action and provider.
    """
    providers = await get_providers(action, ctx)
    if "error" in providers:
        return providers








@mcp.resource(
    uri="resource://{action}/{provider}/param_schema"
)
async def get_payload_schema(action: str, provider: str, ctx: Context):
    providers = await get_providers(action, ctx)
    if "error" in providers:
        return providers
    if provider not in providers["providers"]:
        return {"error": f"INVALID PROVIDER: {provider} for action {action}"}










@mcp.resource(
    uri="resource://{action}/{provider}/params"
)
async def get_params(action: str, provider: str, ctx: Context):
    providers = await get_providers(action, ctx)
    if "error" in providers:
        return providers
    if provider not in providers["providers"]:
        return {"error": f"INVALID PROVIDER: {provider} for action {action}"}
    if action == "search":
        if provider == "perplexity":
            
            
            
            
            
            return PerplexityChatRequest.model_json_schema()
        if provider == "exa":
            return ExaSearchRequest.model_json_schema()
    if action == "consult":
        
        
        
        
        return InfoConsultParams.model_json_schema()
        
        
        
        
        
        
        return {"error": f"INVALID PROVIDER: {provider}"}
    
    
    
    
    
    ...

    
    
    
    
    
    
    ...








@mcp.resource(
    uri="resource://{action}/{provider}/params"
)
async def get_schema(action: str, provider: str, ctx: Context):
    """
    Get the schema for a specific action and provider.
    
    Args:
        action (str): The action type, either 'search' or 'consult'.
        provider (str): The provider type, e.g., 'perplexity' or 'exa'.

    
    
    
    
    
    
        action (str): The action type, either 'search' or 'consult'.
        provider (str): The provider type, e.g., 'perplexity' or 'exa'.

    Available actions:
    
    
    
    
    
    """
    
    
    
    
    ...


















@mcp.tool()
async def handle_request(request: InfoRequest):
    response = await service.handle_request(request)
    return response



if __name__ == "__main__":
    mcp.run()