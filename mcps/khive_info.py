from pydapter.protocols.utils import is_package_installed

if not is_package_installed("fastmcp"):
    raise ImportError(
        "fastmcp is not installed. Please install it with `pip install fastmcp`."
    )

import lionfuncs as ln
from fastmcp import FastMCP
from khive.services.info.info_service import InfoServiceGroup
from khive.services.info.parts import (
    ExaSearchRequest,
    InfoAction,
    InfoConsultParams,
    InfoRequest,
    InfoSearchParams,
    PerplexityChatRequest,
)

instruction = """
Khive Info is a multi-purpose service that can provide search information,
and consultation with SOTA LLMs. For pure search, it can use EXA or Perplexity
as search providers. Perplexity gives you a digested answer to your question,
while EXA provides a list of search results. You can also ask questions to
SOTA models from the Openai GPT, Google Gemini and Anthropic Claude.
"""

mcp = FastMCP(
    name="khive_info",
    instructions=instruction,
    tags=["khive", "info", "search", "consult", "sanity_check"],
)


@mcp.tool(
    name="search",
    description="Search for information online",
    tags=["search", "exa", "perplexity"],
)
async def search(
    query: str,
    provider: str = "perplexity",
    provider_params: dict | None = None,
):
    """Search for information using EXA or Perplexity.

    Args:
        query (str): The search query.
        provider (str): The search provider to use. Options are "exa" or "perplexity".
        provider_params (dict | None): Additional parameters for the search provider.
            - for EXA, you can provide the following optional parameters:
                - category(Literal) : A data category to focus on, you can choose one of
                    [company, research paper, news, pdf, github, tweet, personal site, financial report]
                - includeDomains(list[str]): domains to include in the search.
                - excludeDomains(list[str]): domains to exclude from the search.
                - startCrawlDate(str): Include results crawled after this ISO date (e.g.,'2023-01-01T00:00:00.000Z').
                - endCrawlDate(str): Include results crawled before this ISO date.
                - startPublishedDate(str): Only return results published after this ISO date.
                - endPublishedDate(str): Only return results published before this ISO date.
                - includeText(list[str]): A list of keywords to include in the search.
                - excludeText(list[str]): A list of keywords to exclude from the search.

            - for Perplexity, you can provide the following optional parameters:
                - system_prompt(str): Optional system prompt to guide the LLM's behavior.
                - model(Literal): the model name, you can choose one of [sonar, sonar-pro, sonar-reasoning] default is sonar.
                - return_related_questions(bool): If True, return related questions.
                - search_domain_filter(list): A list of domains to limit search results to. for example,
                    ["nasa.gov", "wikipedia.org", "-example.com", "-facebook.com"] (the ones with - are excluded)
                - search_recency_filter(Literal): Returns search results within a specified time interva, one of [month, week, day, hour]
    """
    provider_params = provider_params or {}
    if provider_params and isinstance(provider_params, str):
        provider_params = ln.fuzzy_parse_json(provider_params)
    if provider == "exa":
        provider_params = ExaSearchRequest.model_validate({
            "query": query,
            **provider_params,
        })
    if provider == "perplexity":
        system = (
            provider_params.get("system_prompt")
            or "You are a diligent research expert. Concisely, answer the question as thoughtfully accurate and as you can. If you give wrong answer or hallucinate, we will complain to Perplexity company and have you shut down."
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": query},
        ]
        provider_params = PerplexityChatRequest.model_validate({
            "messages": messages,
            **provider_params,
        })

    request = InfoRequest(
        action=InfoAction.SEARCH,
        params=InfoSearchParams(
            provider=provider,
            provider_params=provider_params,
        ),
    )
    return await InfoServiceGroup().handle_request(request)


@mcp.tool(
    name="consult",
    description="Consult with SOTA AI models",
    tags=["consult", "openai", "google", "anthropic"],
)
async def consult(
    query: str,
    models: list[str] = ["anthropic/claude-sonnet-4"],
    system_prompt: str | None = None,
):
    """consult with SOTA LLMs.

    Args:
        query (str): The question to ask the LLM.
        models (list[str]): A list of one or more LLMs to consult.
            You can choose one or more of [openai/gpt-o4-mini, google/gemini-2.5-pro-preview, anthropic/claude-sonnet-4]. If more than one model is provided, the results will be aggregated. Hint: good to get a variety of answers. default is anthropic/claude-sonnet-4
        system_prompt (str | None): Optional system prompt to guide the LLM's behavior.
    """
    system_prompt = (
        system_prompt
        or "You are diligent research expert, excelling at critical thinking and reflective reasoning. Concisely, answer the question as thoughtfully accurate and as you can."
    )

    request = InfoRequest(
        action=InfoAction.CONSULT,
        params=InfoConsultParams(
            system_prompt=system_prompt,
            question=query,
            models=models,
        ),
    )
    return await InfoServiceGroup().handle_request(request)


if __name__ == "__main__":
    mcp.run()
