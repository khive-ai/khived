# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
CLI wrapper around khive.services.info.info_service.InfoService.

❱  Examples
-----------

# 1. Search using Exa with options
khive info search --provider exa --query "Python async programming" --options numResults=5 useAutoprompt=true

# 2. Search using Perplexity
khive info search --provider perplexity --query "Latest AI research trends" --options pplx_model=sonar-deep-research

# 3. Consult multiple LLMs with a question
khive info consult --question "Explain quantum computing" --models openai/gpt-o4-mini,anthropic/claude-3.7-sonnet

# 4. Consult with system prompt and options
khive info consult --question "Compare Python vs Rust" --models openai/gpt-o4-mini --system_prompt "You are a programming language expert" --consult_options temperature=0.7 max_tokens=500

All responses are JSON (one line) printed to stdout.
Errors go to stderr and a non-zero exit code.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from typing import Any

# Configure basic logging for the CLI
logging.basicConfig(
    level=logging.INFO, format="%(levelname)s - %(asctime)s - KhiveInfoCLI: %(message)s"
)
logger = logging.getLogger(__name__)

try:
    from khive.services.info.info_service import InfoServiceGroup
    from khive.services.info.parts import (
        ConsultModel,
        ExaSearchRequest,
        InfoAction,
        InfoConsultParams,
        InfoRequest,
        InfoSearchParams,
        PerplexityChatRequest,
        SearchProvider,
    )
    from khive.third_party.pplx_models import PerplexityMessage
except ModuleNotFoundError as e:
    sys.stderr.write(
        f"❌ Required modules not found. Ensure khive.services.info and khive.providers are in PYTHONPATH.\nError: {e}\n"
    )
    sys.exit(1)
except ImportError as e:
    sys.stderr.write(
        f"❌ Error importing from khive.services.info or khive.providers.\nError: {e}\n"
    )
    sys.exit(1)


info_service_instance = InfoServiceGroup()


async def run_info_request_and_print(request_model: InfoRequest) -> None:
    try:
        logger.debug(
            f"CLI sending request: {request_model.model_dump_json(indent=2, exclude_none=True)}"
        )
        response = await info_service_instance.handle_request(request_model)

        print(
            json.dumps(
                response.model_dump(exclude_none=True, by_alias=True),
                ensure_ascii=False,
            )
        )
        sys.exit(0 if response.success else 2)
    except Exception as e:
        logger.error(
            f"CLI request processing failed: {type(e).__name__}: {e}", exc_info=True
        )
        sys.stderr.write(f"❌ CLI Error: {e}\n")
        sys.exit(1)


def parse_key_value_options(options_list: list[str] | None) -> dict[str, Any]:
    """Parses a list of 'key=value' strings into a dictionary with naive type casting."""
    if not options_list:
        return {}
    parsed_options: dict[str, Any] = {}
    for item in options_list:
        if "=" not in item:
            logger.warning(
                f"Skipping malformed option '{item}'. Expected 'key=value' format."
            )
            continue
        key, value = item.split("=", 1)
        # Naive type casting
        if value.lower() == "true":
            parsed_options[key] = True
        elif value.lower() == "false":
            parsed_options[key] = False
        else:
            try:
                parsed_options[key] = int(value)
            except ValueError:
                try:
                    parsed_options[key] = float(value)
                except ValueError:
                    # Check if it's a JSON list or object-like string
                    if (value.startswith("[") and value.endswith("]")) or (
                        value.startswith("{") and value.endswith("}")
                    ):
                        try:
                            parsed_options[key] = json.loads(value)
                        except json.JSONDecodeError:
                            parsed_options[key] = value  # Fallback to string
                    else:
                        parsed_options[key] = value  # Fallback to string
    return parsed_options


def create_perplexity_messages(query: str) -> list[PerplexityMessage]:
    """Helper to create a simple messages list for Perplexity from a query."""
    return [PerplexityMessage(role="user", content=query)]


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="khive info",
        description="Khive Information Service CLI (Search & Consult)",
    )
    action_subparsers = parser.add_subparsers(
        dest="action_command", required=True, help="Main action: 'search' or 'consult'"
    )

    # --- SEARCH Subcommand ---
    search_parser = action_subparsers.add_parser(
        InfoAction.SEARCH.value, help="Perform a web search."
    )
    search_parser.add_argument(
        "--provider",
        type=str,
        required=True,
        help=f"Search provider. Choices: {[p.value for p in SearchProvider]}",
    )
    search_parser.add_argument("--query", required=True, help="Primary search query.")
    search_parser.add_argument(
        "--options",
        nargs="*",  # Allows zero or more options
        metavar="KEY=VALUE",
        help="Additional provider-specific options as key=value pairs (e.g., numResults=5 useAutoprompt=true pplx_model=sonar). "
        "For Perplexity, if 'messages_json' key is provided in options, its value (a JSON string) will be used for messages, overriding --query.",
    )

    # --- CONSULT Subcommand ---
    consult_parser = action_subparsers.add_parser(
        InfoAction.CONSULT.value, help="Consult LLMs."
    )
    consult_parser.add_argument(
        "--question", required=True, help="Question for LLM(s)."
    )
    consult_parser.add_argument(
        "--models",
        type=str,  # Comma-separated string
        required=True,
        help=f"Comma-separated list of LLM models to consult. Known choices include: {[m.value for m in ConsultModel]}. "
        "Any OpenRouter compatible model string can also be used.",
    )
    consult_parser.add_argument(
        "--system_prompt",
        type=str,
        default=None,
        help="Optional system prompt for the LLM consultation.",
    )
    consult_parser.add_argument(
        "--consult_options",
        nargs="*",
        metavar="KEY=VALUE",
        help="Additional options for the consult LLMs (e.g., temperature=0.5 max_tokens=100). Applied to all models if provider supports.",
    )

    args = parser.parse_args()
    action = InfoAction(args.action_command)

    params_for_action: InfoSearchParams | InfoConsultParams
    final_request_payload: InfoRequest

    try:
        if action == InfoAction.SEARCH:
            provider_options = parse_key_value_options(args.options)

            # Validate provider
            try:
                provider = SearchProvider(args.provider)
            except ValueError:
                raise ValueError(
                    f"Invalid search provider: '{args.provider}'. Valid options are: {[p.value for p in SearchProvider]}"
                )

            # The primary query is always present. Provider options can override or add to it.
            provider_specific_payload_dict = {"query": args.query, **provider_options}

            provider_model_instance: ExaSearchRequest | PerplexityChatRequest

            if provider == SearchProvider.EXA:
                # Ensure 'query' is correctly mapped if 'query' was also in options (options take precedence)
                if "query" in provider_options:
                    provider_specific_payload_dict["query"] = provider_options["query"]
                else:
                    provider_specific_payload_dict["query"] = (
                        args.query
                    )  # From dedicated --query flag

                # Remove perplexity-specific options if they accidentally got in via generic options
                provider_specific_payload_dict.pop("pplx_model", None)
                provider_specific_payload_dict.pop("messages_json", None)
                provider_specific_payload_dict.pop("messages", None)

                provider_model_instance = ExaSearchRequest(
                    **provider_specific_payload_dict
                )
            elif provider == SearchProvider.PERPLEXITY:
                # Perplexity expects 'messages'. If 'messages_json' is in options, use that.
                # Otherwise, construct messages from --query.

                from khive.third_party.pplx_models import PerplexityMessage

                if "messages_json" in provider_specific_payload_dict:
                    try:
                        # Parse JSON and convert to PerplexityMessage objects
                        messages_data = json.loads(
                            provider_specific_payload_dict.pop("messages_json")
                        )
                        provider_specific_payload_dict["messages"] = [
                            PerplexityMessage(role=msg["role"], content=msg["content"])
                            for msg in messages_data
                        ]
                        provider_specific_payload_dict.pop(
                            "query", None
                        )  # messages_json overrides query
                    except json.JSONDecodeError as e:
                        raise ValueError(
                            f"Invalid JSON for 'messages_json' option: {e}"
                        ) from e
                elif (
                    "messages" in provider_specific_payload_dict
                ):  # if messages provided directly in options as JSON list string
                    if isinstance(
                        provider_specific_payload_dict["messages"], str
                    ):  # should be already parsed by parse_key_value_options
                        messages_data = json.loads(
                            provider_specific_payload_dict["messages"]
                        )
                        provider_specific_payload_dict["messages"] = [
                            PerplexityMessage(role=msg["role"], content=msg["content"])
                            for msg in messages_data
                        ]
                    provider_specific_payload_dict.pop("query", None)
                else:
                    provider_specific_payload_dict["messages"] = (
                        create_perplexity_messages(args.query)
                    )
                    provider_specific_payload_dict.pop(
                        "query", None
                    )  # Remove raw query as 'messages' is now populated

                # Handle model explicitly for Perplexity
                if "pplx_model" in provider_specific_payload_dict:
                    provider_specific_payload_dict["model"] = (
                        provider_specific_payload_dict.pop("pplx_model")
                    )
                elif (
                    "model" not in provider_specific_payload_dict
                ):  # Use endpoint default if not provided
                    pass  # Let Pydantic model default or endpoint config handle it

                provider_model_instance = PerplexityChatRequest(
                    **provider_specific_payload_dict
                )
            else:
                raise ValueError(
                    f"CLI Error: Unhandled search provider '{provider.value}'."
                )

            params_for_action = InfoSearchParams(
                provider=provider, provider_params=provider_model_instance
            )

        elif action == InfoAction.CONSULT:
            raw_model_strings = [m.strip() for m in args.models.split(",")]

            # Check if any model strings match known ConsultModel values
            known_consult_model_values = {m.value: m for m in ConsultModel}
            consult_models_list = []

            for model_str in raw_model_strings:
                if model_str in known_consult_model_values:
                    # If it's a known model, use the enum value
                    consult_models_list.append(model_str)
                else:
                    # Otherwise, use the string directly
                    logger.warning(
                        f"Using model string '{model_str}' which is not in predefined ConsultModel enum."
                    )
                    consult_models_list.append(model_str)

            consult_options_dict = parse_key_value_options(args.consult_options)

            params_for_action = InfoConsultParams(
                question=args.question,
                models=consult_models_list,
                system_prompt=args.system_prompt,
            )
        else:
            raise ValueError(
                f"CLI Error: Unknown action command '{args.action_command}'."
            )

        final_request_payload = InfoRequest(action=action, params=params_for_action)

    except Exception as e:
        logger.error(
            f"Error constructing request model for action '{args.action_command}': {e}",
            exc_info=True,
        )
        sys.stderr.write(f"❌ Invalid CLI arguments or parameter construction: {e}\n")
        sys.exit(1)

    # Only attempt to run the request if it was successfully created
    if "final_request_payload" in locals():
        asyncio.run(run_info_request_and_print(final_request_payload))


if __name__ == "__main__":
    main()
