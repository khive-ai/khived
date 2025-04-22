#!/usr/bin/env python3
"""
Validate a search payload for Exa / Perplexity and (optionally) execute it via
`khive.search_service`.

▸  Build JSON only      :  ./search_helpers.py --tool exa  --query "…" …
▸  Build JSON *and run* :  ./search_helpers.py --tool exa  --query "…" --run …

Extra fields can be supplied as key=value pairs, e.g.

    --tool exa --query "Rust async" numResults=5 type=neural
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from pydantic_core import PydanticCustomError

# --------------------------------------------------------------------------- #
# 1. Pydantic models (same shapes used by the MCP tools)                      #
# --------------------------------------------------------------------------- #


class CategoryEnum(str, Enum):
    company = "company"
    research_paper = "research paper"
    news = "news"
    pdf = "pdf"
    github = "github"
    tweet = "tweet"
    personal_site = "personal site"
    linkedin_profile = "linkedin profile"
    financial_report = "financial report"


class LivecrawlEnum(str, Enum):
    never = "never"
    fallback = "fallback"
    always = "always"


class SearchTypeEnum(str, Enum):
    keyword = "keyword"
    neural = "neural"
    auto = "auto"


class ContentsText(BaseModel):
    model_config = ConfigDict(extra="forbid")
    includeHtmlTags: Optional[bool] = False
    maxCharacters: Optional[int] = Field(None, ge=1)


class ContentsHighlights(BaseModel):
    model_config = ConfigDict(extra="forbid")
    highlightsPerUrl: Optional[int] = Field(1, ge=1)
    numSentences: Optional[int] = Field(5, ge=1)
    query: Optional[str] = None


class ContentsSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: Optional[str] = None


class ContentsExtras(BaseModel):
    model_config = ConfigDict(extra="forbid")
    links: Optional[int] = Field(None, ge=1)
    imageLinks: Optional[int] = Field(None, ge=1)


class Contents(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: Optional[ContentsText] = None
    highlights: Optional[ContentsHighlights] = None
    summary: Optional[ContentsSummary] = None
    livecrawl: Optional[LivecrawlEnum] = LivecrawlEnum.never
    livecrawlTimeout: Optional[int] = Field(10_000, ge=1_000)
    subpages: Optional[int] = Field(None, ge=1)
    subpageTarget: Optional[str | List[str]] = None
    extras: Optional[ContentsExtras] = None


class ExaSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(..., min_length=1)
    category: Optional[CategoryEnum] = None
    type: Optional[SearchTypeEnum] = SearchTypeEnum.auto
    useAutoprompt: Optional[bool] = False
    numResults: Optional[int] = Field(10, ge=1, le=25)
    includeDomains: Optional[List[str]] = None
    excludeDomains: Optional[List[str]] = None
    startCrawlDate: Optional[str] = None
    endCrawlDate: Optional[str] = None
    startPublishedDate: Optional[str] = None
    endPublishedDate: Optional[str] = None
    includeText: Optional[str] = None
    excludeText: Optional[str] = None
    contents: Optional[Contents] = None

    @field_validator("includeText", "excludeText", mode="before")
    def _limit_words(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v.split()) > 5:
            raise PydanticCustomError(
                "value_error", "Text filter exceeds 5-word limit", {"value": v}
            )
        return v


class PerplexityRole(str, Enum):
    system = "system"
    user = "user"
    assistant = "assistant"


class PerplexityMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: PerplexityRole
    content: str = Field(..., min_length=1)


class PerplexityChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str = "sonar"
    messages: List[PerplexityMessage]
    frequency_penalty: Optional[float] = Field(None, gt=0)
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1)
    stream: Optional[bool] = None
    temperature: Optional[float] = Field(None, ge=0.0, lt=2.0)
    top_k: Optional[int] = Field(None, ge=0, le=2048)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0)

    def to_dict(self):
        return self.model_dump(exclude_none=True)


# --------------------------------------------------------------------------- #
# 2. CLI parsing helpers                                                      #
# --------------------------------------------------------------------------- #


def _parse_key_vals(kvs: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for kv in kvs:
        if kv == "--run":  # handled elsewhere
            continue
        if "=" in kv:
            k, v = kv.split("=", 1)
            # naive type casting
            if v.lower() in {"true", "false"}:
                out[k] = v.lower() == "true"
            else:
                try:
                    out[k] = int(v)
                    continue
                except ValueError:
                    pass
                try:
                    out[k] = float(v)
                    continue
                except ValueError:
                    pass
                out[k] = v
        else:
            # treat bare words as boolean flags → key=True
            out[kv.lstrip("-")] = True
    return out


def _cli() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--tool", required=True, choices=["exa", "perplexity"])
    p.add_argument("--query", required=True)
    p.add_argument(
        "--run",
        action="store_true",
        help="If set, immediately execute the search and print API response",
    )
    p.add_argument("extras", nargs="*", help="Extra key=value pairs")
    return p.parse_args()


# --------------------------------------------------------------------------- #
# 3. Optional live execution via SearchService                                #
# --------------------------------------------------------------------------- #


async def _call_api(tool: str, request_obj: BaseModel) -> None:
    from .search_service import search_service

    if tool == "exa":
        result = await search_service.exa_search(request_obj)  # type: ignore
    else:
        result = await search_service.perplexity_search(request_obj)  # type: ignore
    print(json.dumps(result, indent=2, ensure_ascii=False))


# --------------------------------------------------------------------------- #
# 4. Main                                                                     #
# --------------------------------------------------------------------------- #


def main() -> None:
    ns = _cli()
    kvs = _parse_key_vals(ns.extras)
    payload = {"query": ns.query, **kvs}

    try:
        if ns.tool == "exa":
            req = ExaSearchRequest(**payload)
        else:  # perplexity
            if "messages" not in payload:
                payload["messages"] = [
                    {"role": "system", "content": "Be precise and factual."},
                    {"role": "user", "content": ns.query},
                ]
            payload.pop("query", None)
            req = PerplexityChatCompletionRequest(**payload)  # type: ignore

        if not ns.run:
            # emit JSON for MCP call
            print(req.model_dump_json(indent=2, exclude_none=True))
        else:
            # hit the live API
            asyncio.run(_call_api(ns.tool, req))

    except ValidationError as e:
        print("❌ Parameter validation failed:\n", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
