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
import sys
from typing import Any

from pydantic import BaseModel, ValidationError

# --------------------------------------------------------------------------- #
# 2. CLI parsing helpers                                                      #
# --------------------------------------------------------------------------- #


def _parse_key_vals(kvs: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
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
    from ..services.search_service import search_service

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
