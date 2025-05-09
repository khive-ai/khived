from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class PerplexityModels(str, Enum):
    """
    Models available in Perplexity's API.

    sonar: Lightweight, cost-effective search model designed for quick, grounded
        answers
    sonar-pro: Advanced search model optimized for complex queries and deeper content
        understanding.
    sonar-reasoning: Quick problem-solving and reasoning model, ideal for evaluating
        complex queries.
    sonar-deep-research: Best suited for exhaustive research, generating detailed
        reports and in-depth insights.
    """

    SONAR = "sonar"
    SONAR_PRO = "sonar-pro"
    SONAR_REASONING = "sonar-reasoning"
    SONAR_DEEP_RESEARCH = "sonar-deep-research"


class PerplexityMessage(BaseModel):
    """A single message in the conversation."""

    role: Literal["system", "user", "assistant"] = Field(
        ...,
        description="The role of the speaker. Must be system, user, or assistant.",
    )
    content: str = Field(
        ..., description="The contents of the message in this turn of conversation"
    )


class WebSearchOptions(BaseModel):
    search_context_size: Literal["low", "medium", "high"] = Field(
        default="low",
        description="Determines how much search context is retrieved for the model. "
        "Options are: low (minimizes context for cost savings but less comprehensive "
        "answers), medium (balanced approach suitable for most queries), and high "
        "(maximizes context for comprehensive answers but at higher cost).",
    )


class PerplexityChatRequest(BaseModel):
    """
    Represents the request body for Perplexity's Chat Completions endpoint.
    Endpoint: POST https://api.perplexity.ai/chat/completions
    """

    model: PerplexityModels = Field(
        PerplexityModels.SONAR,
        description="The model name, e.g. 'sonar', (the only model available at the "
        "time when this request model was updated, check doc for latest info).",
    )
    messages: list[PerplexityMessage] = Field(
        ..., description="A list of messages forming the conversation so far."
    )

    # Optional parameters
    frequency_penalty: float | None = Field(
        default=1,
        ge=0,
        le=2.0,
        description=(
            "Decreases likelihood of repetition based on prior frequency. Applies a "
            "penalty to tokens based on how frequently they've appeared in the text "
            "so far. Values typically range from 0 (no penalty) to 2.0 (strong "
            "penalty). Higher values (e.g., 1.5) reduce repetition of the same words"
            " and phrases. Useful for preventing the model from getting stuck in loops"
        ),
    )
    presence_penalty: float | None = Field(
        default=None,
        ge=0,
        le=2.0,
        description=(
            "Positive values increase the likelihood of discussing new topics. Applies "
            "a penalty to tokens that have already appeared in the text, encouraging "
            "the model to talk about new concepts. Values typically range from 0 (no"
            " penalty) to 2.0 (strong penalty). Higher values reduce repetition but "
            "may lead to more off-topic text."
        ),
    )
    max_tokens: int | None = Field(
        default=None,
        description=(
            "The maximum number of completion tokens returned by the API. Controls the "
            "length of the model's response. If the response would exceed this limit, "
            "it will be truncated. "
        ),
    )
    return_related_questions: bool | None = Field(
        default=False,
        description="Determines whether related questions should be returned.",
    )
    search_domain_filter: list[Any] | None = Field(
        default=None,
        description="A list of domains to limit search results to. Currently limited "
        "to 10 domains for Allowlisting and Denylisting. For Denylisting, add a - at "
        "the beginning of the domain string. for more info, "
        "see: https://docs.perplexity.ai/guides/search-domain-filters",
        examples=["nasa.gov", "wikipedia.org", "-example.com", "-facebook.com"],
    )
    search_recency_filter: str | None = Field(
        default=None,
        description=(
            "Returns search results within a specified time interval: 'month', 'week', "
            "'day', or 'hour'."
        ),
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        lt=2.0,
        description=(
            "The amount of randomness in the response, valued between 0 and 2. Lower "
            "values (e.g., 0.1) make the output more focused, deterministic, and less "
            "creative. Higher values (e.g., 1.5) make the output more random and "
            "creative. Use lower values for factual/information retrieval tasks and "
            "higher values for creative applications."
        ),
    )
    top_k: int | None = Field(
        default=None,
        ge=0,
        le=2048,
        description=(
            "Top-K filtering. 0 disables top-k filtering. If set, only the top K "
            "tokens are considered. We recommend altering either top_k or top_p, "
            "but not both."
        ),
    )
    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "The nucleus sampling threshold, valued between 0 and 1. Controls the "
            "diversity of generated text by considering only the tokens whose "
            "cumulative probability exceeds the top_p value. Lower values (e.g., 0.5) "
            "make the output more focused and deterministic, while higher values "
            "(e.g., 0.95) allow for more diverse outputs. Often used as an alternative"
            " to temperature."
        ),
    )
