# khive info

## Overview

The `khive info` command provides Command Line Interface (CLI) access to the
Information Service, which enables searching the web and consulting Large
Language Models (LLMs). It supports multiple search providers (Exa, Perplexity)
and can query various LLMs through OpenRouter. This tool is designed for both
interactive use and integration into automated workflows, particularly for
research, information gathering, and AI-assisted analysis.

## Key Features

- **Web Search:** Query the web using different search providers with
  customizable options.
- **LLM Consultation:** Ask questions to one or more LLMs with configurable
  parameters.
- **Flexible Options:** Support for provider-specific options through a simple
  key=value interface.
- **Multiple Models:** Ability to consult multiple LLMs simultaneously for
  comparative analysis.
- **Structured JSON I/O:** All interactions produce JSON output, suitable for
  scripting and agent consumption.
- **Pydantic-Driven:** Leverages Pydantic models for robust request and response
  validation.

## Usage

```bash
khive info <action> [action_specific_options] [global_options]
```

**Actions:**

- `search`: Search the web using a specified provider (Exa, Perplexity).
- `consult`: Ask a question to one or more LLMs.

## Global Options (Applicable to all actions)

| Option            | Description                                 |
| ----------------- | ------------------------------------------- |
| `--json-output`   | (Implied) All output is in JSON format.     |
| `--verbose`, `-v` | (For future use) Enable verbose CLI logging |

## Actions and their Options

### `search`

Search the web using a specified provider.

```bash
khive info search --provider <provider> --query <query> [--options KEY=VALUE...]
```

| Option       | Description                                                             |
| ------------ | ----------------------------------------------------------------------- |
| `--provider` | **Required.** The search provider to use. Options: `exa`, `perplexity`. |
| `--query`    | **Required.** The search query or question.                             |
| `--options`  | Optional provider-specific parameters as key=value pairs.               |

**Provider-specific options:**

For Exa (`--provider exa`):

- `numResults=N` - Number of results to return (default: 10)
- `useAutoprompt=true|false` - Whether to use Exa's autoprompt feature (default:
  false)
- `type=keyword|neural|auto` - Search type to use
- And other Exa-specific options (see
  [ExaSearchRequest](https://docs.exa.ai/reference/search) for details)

For Perplexity (`--provider perplexity`):

- `pplx_model=MODEL` - Perplexity model to use (e.g., `sonar`,
  `sonar-medium-chat`, `sonar-deep-research`)
- `messages_json=JSON` - JSON array of message objects (alternative to
  `--query`)
- And other Perplexity-specific options

### `consult`

Ask a question to one or more LLMs.

```bash
khive info consult --question <question> --models <model1,model2,...> [--system_prompt <prompt>] [--consult_options KEY=VALUE...]
```

| Option              | Description                                                  |
| ------------------- | ------------------------------------------------------------ |
| `--question`        | **Required.** The question to ask the LLM(s).                |
| `--models`          | **Required.** Comma-separated list of LLM models to consult. |
| `--system_prompt`   | Optional system prompt to guide the LLM's behavior.          |
| `--consult_options` | Optional LLM-specific parameters as key=value pairs.         |

**Supported models include:**

- `openai/gpt-o4-mini`
- `anthropic/claude-3.7-sonnet`
- `google/gemini-2.5-pro-preview`
- Any valid OpenRouter model identifier

## Examples

```bash
# Search the web using Exa with default options
khive info search --provider exa --query "Latest developments in rust programming language"

# Search using Exa with custom options
khive info search --provider exa --query "Machine learning frameworks comparison" --options numResults=5 useAutoprompt=true

# Search using Perplexity
khive info search --provider perplexity --query "Quantum computing advances 2025"

# Search with Perplexity using a specific model
khive info search --provider perplexity --query "Climate change impacts" --options pplx_model=sonar-deep-research

# Consult a single LLM
khive info consult --question "Explain async/await in JavaScript" --models openai/gpt-o4-mini

# Consult multiple LLMs
khive info consult --question "Compare Python vs Rust for system programming" --models "openai/gpt-o4-mini,anthropic/claude-3.7-sonnet"

# Consult with a system prompt
khive info consult --question "Optimize this SQL query: SELECT * FROM users WHERE created_at > '2025-01-01'" --models openai/gpt-o4-mini --system_prompt "You are a database optimization expert. Keep your answers concise."
```

## Exit Codes

- `0`: Action completed successfully.
- `1`: CLI error (e.g., invalid parameters, module not found, internal
  processing error).
- `2`: The requested info service action was executed but reported
  `success: false` (e.g., API error, rate limit, authentication failure).
