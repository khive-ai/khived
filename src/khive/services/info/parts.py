# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from khive.connections.providers.exa_ import ExaSearchRequest
from khive.connections.providers.perplexity_ import PerplexityChatRequest


class InfoAction(str, Enum):
    """
    Enumerates the primary actions the Information Service can perform.

    - search: Find information on a specific topic using web search providers.
    - consult: Ask a specific question or present a problem to one or more LLMs.
    """

    SEARCH = "search"
    CONSULT = "consult"


class SearchProvider(str, Enum):
    """
    Enumerates the supported web search providers for the 'SEARCH' action.
    """

    PERPLEXITY = "perplexity"
    EXA = "exa"


class ConsultModel(str, Enum):
    """
    Enumerates supported Large Language Models for the 'CONSULT' action.
    - openai/gpt-o4-mini
    - google/gemini-2.5-pro-preview
    - anthropic/claude-3.7-sonnet
    """

    GPT_O4_MINI = "openai/gpt-o4-mini"
    GEMINI_2_5_PRO = "google/gemini-2.5-pro-preview"
    CLAUDE_SONNET_4 = "anthropic/claude-sonnet-4"


class InfoSearchParams(BaseModel):
    provider: SearchProvider = SearchProvider.PERPLEXITY
    provider_params: ExaSearchRequest | PerplexityChatRequest


class InfoConsultParams(BaseModel):
    """Parameters for the 'CONSULT' action."""

    system_prompt: str | None = Field(
        None, description="Optional system prompt to guide the LLM's behavior."
    )
    question: str = Field(
        ..., description="The specific question or topic to consult the LLM(s) about."
    )
    models: list[ConsultModel] = Field(
        description="A list of one or more LLMs to consult.",
    )

    @field_validator("models", mode="before")
    def check_models(cls, v):
        v = [v] if not isinstance(v, list) else v
        return v


class InfoRequest(BaseModel):
    """
    Request model for the Information Service (`InfoService`).
    Specifies the action ('search' or 'consult') and its parameters.
    """

    action: InfoAction = Field(
        ..., description="The high-level action: 'search' or 'consult'."
    )
    params: InfoSearchParams | InfoConsultParams = Field(
        ...,
        description="Parameters for the action. Must be InfoSearchActionParams if action is 'search', or InfoConsultParams if action is 'consult'.",
    )


class InfoResponse(BaseModel):
    """Response model from the Information Service (`InfoService`)."""

    success: bool = Field(..., description="True if the action was successful.")
    action_performed: InfoAction | None = Field(
        None, description="The action processed."
    )
    error: str | None = Field(None, description="Error message if 'success' is False.")
    content: dict[str, Any] | None = Field(
        None,
        description="Output of the action. Structure depends on 'action_performed'."
        "For 'search', may contain 'provider_response' with data from Perplexity/Exa. "
        "For 'consult', may map model slugs to their answers.",
    )
