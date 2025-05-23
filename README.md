# Khive: Autonomous software engineering department with github/roo

[![PyPI version](https://img.shields.io/pypi/v/khive.svg)](https://pypi.org/project/khive/)
![PyPI - Downloads](https://img.shields.io/pypi/dm/khive?color=blue)
![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
[![License](https://img.shields.io/badge/license-Apache--2.0-brightgreen.svg)](LICENSE)

> **Khive** is an opinionated toolbox that keeps multi-language agent projects
> **fast, consistent, and boring-in-a-good-way**. One command - `khive` - wraps
> all the little scripts you inevitably write for formatting, CI gating, Git
> hygiene and doc scaffolding, then gives them a coherent UX that works the same
> on your laptop **and** inside CI.

---

## Table of Contents

1. [Core Philosophy](#core-philosophy)
2. [Quick Start](#quick-start)
3. [Setup](#setup)
4. [Command Catalogue](#command-catalogue)
5. [Usage Examples](#usage-examples)
6. [Configuration](#configuration)
7. [Prerequisites](#prerequisites)
8. [Project Layout](#project-layout)
9. [Services](#services)
   - [Reader Microservice](docs/reader/README.md)
   - [Info Service](docs/services/info_service.md)
10. [Contributing](#contributing)

---

## Core Philosophy

- **Single entry-point** → `khive <command>`
- **Convention over config** → sensible defaults, TOML for the rest
- **CI/local parity** → the CLI and the GH workflow run the _same_ code
- **Idempotent helpers** → safe to run repeatedly; exit 0 on "nothing to do"
- **No lock-in** → wraps existing ecosystem tools instead of reinventing them

---

## Quick Start

```bash
# 1 · clone & install
$ git clone https://github.com/khive-ai/khive.d.git
$ cd khive
$ uv pip install -e .        # editable install - puts `khive` on your PATH

# 2 · bootstrap repo (node deps, rust fmt, git hooks, …)
$ khive init -v

# 3 · hack happily
$ khive fmt --check           # smoke-test formatting
$ khive ci --check            # quick pre-commit gate
```

---

## Setup

### API Keys

To use the information retrieval and LLM consultation features, you'll need to
set up the following API keys:

- **PERPLEXITY_API_KEY** and **EXA_API_KEY** for `khive info search` to work
- **OPENROUTER_API_KEY** for `khive info consult` to work

You can set these as environment variables or add them to a `.env` file in your
project root.

### Additional Dependencies

For document reading capabilities:

```bash
# Install reader dependencies
$ pip install "khive[reader]"

# Or install all optional dependencies
$ pip install "khive[all]"
```

The Reader Microservice supports a wide range of file formats:

- **Documents**: PDF, DOCX, PPTX, XLSX
- **Web**: HTML, HTM
- **Text**: Markdown (MD), AsciiDoc (ADOC), CSV
- **Images**: JPG, JPEG, PNG, TIFF, BMP (with OCR)

For more information about the Reader Microservice, see the
[Reader documentation](docs/reader/README.md).

---

## Command Catalogue

| Command         | What it does (TL;DR)                                                                        |
| --------------- | ------------------------------------------------------------------------------------------- |
| `khive init`    | Verifies toolchain, installs JS & Python deps, runs `cargo check`, wires Husky hooks.       |
| `khive fmt`     | Opinionated multi-stack formatter (`ruff` + `black`, `cargo fmt`, `deno fmt`, `markdown`).  |
| `khive commit`  | Stages → (optional patch-select) → conventional commit → (optional) push.                   |
| `khive pr`      | Pushes branch & opens/creates GitHub PR (uses `gh`).                                        |
| `khive ci`      | Local CI gate - lints, tests, coverage, template checks. Mirrors GH Actions.                |
| `khive clean`   | Deletes a finished branch locally & remotely - never nukes default branch.                  |
| `khive new-doc` | Scaffolds markdown docs (ADR, RFC, IP…) from templates with front-matter placeholders.      |
| `khive reader`  | Opens/reads arbitrary docs (PDF, DOCX, HTML, etc.) via `docling`; returns JSON over stdout. |
| `khive info`    | Information service for web search (`info search`) and LLM consultation (`info consult`).   |

Run `khive <command> --help` for full flag reference.

---

## Usage Examples

```bash
# format *everything*, fixing files in-place
khive fmt

# format only Rust & docs, check-only
khive fmt --stack rust,docs --check

# staged patch commit, no push (good for WIP)
khive commit "feat(ui): dark-mode toggle" --patch --no-push

# open PR in browser as draft
khive pr --draft --web

# run the same CI suite GH will run
khive ci

# delete old feature branch safely
khive clean feature/old-experiment --dry-run

# spin up a new RFC doc: docs/rfcs/RFC-001-streaming-api.md
khive new-doc RFC 001-streaming-api

# open a PDF & read slice 0-500 chars
DOC_ID=$(khive reader open --path_or_url paper.pdf | jq -r '.content.doc_info.doc_id')
khive reader read --doc_id "$DOC_ID" --end_offset 500

# open a web URL and extract its content
DOC_ID=$(khive reader open --path_or_url https://example.com/article | jq -r '.content.doc_info.doc_id')
khive reader read --doc_id "$DOC_ID"

# list Python files in a directory recursively
khive reader list_dir --directory ./src --recursive --file_types .py

# search the web using Exa
khive info search --provider exa --query "Latest developments in rust programming language"

# consult multiple LLMs
khive info consult --question "Compare Python vs Rust for system programming" --models openai/gpt-o4-mini,anthropic/claude-sonnet-4
```

---

## Configuration

Khive reads **TOML** from your project root. All keys are optional - keep the
file minimal and override only what you need.

### `pyproject.toml` snippets

```toml
[tool.khive fmt]
# enable/disable stacks globally
enable = ["python", "rust", "docs", "deno"]

[tool.khive fmt.stacks.python]
cmd = "ruff format {files}"   # custom formatter
check_cmd = "ruff format --check {files}"
include = ["*.py"]
exclude = ["*_generated.py"]
```

```toml
[tool.khive-init]
# selective steps
steps = ["check_tools", "install_python", "install_js", "cargo_check"]

# extra custom step - runs after built-ins
[[tool.khive-init.extra]]
name = "docs-build"
cmd  = "pnpm run docs:build"
```

---

## Prerequisites

Khive _helps_ you install tooling but cannot conjure it from thin air. Make sure
these binaries are reachable via `PATH`:

- **Python 3.11+** & [`uv`](https://github.com/astral-sh/uv)
- **Rust toolchain** - `cargo`, `rustc`, `rustfmt`, optional `cargo-tarpaulin`
- **Node + pnpm** - for JS/TS stacks & Husky hooks
- **Deno ≥ 1.42** - used for Markdown & TS fmt
- **Git** + **GitHub CLI `gh`** - Git ops & PR automation
- **jq** - report post-processing, coverage merging

Run `khive init --check` to verify everything at once.

---

## Project Layout

The khive project is organized into several key directories:

```
khive/
├── src/khive/                # Main source code
│   ├── cli/                  # CLI entry points and command implementations
│   ├── commands/             # Command adapters and business logic
│   ├── services/             # Core services (info, reader, etc.)
│   │   ├── info/             # Information service (search, consult)
│   │   └── reader/           # Document reader service
│   ├── connections/          # API connection handling
│   ├── providers/            # Provider-specific implementations
│   ├── protocols/            # Interface definitions
│   ├── prompts/              # Templates and prompts
│   └── third_party/          # Third-party integrations
├── docs/                     # Documentation
│   ├── commands/             # Command-specific documentation
│   ├── connections/          # Connections layer documentation
│   │   ├── overview.md                   # Overview of the connections layer
│   │   ├── endpoint.md                   # Endpoint class documentation
│   │   ├── endpoint_config.md            # EndpointConfig class documentation
│   │   ├── header_factory.md             # HeaderFactory class documentation
│   │   ├── match_endpoint.md             # match_endpoint function documentation
│   │   └── api_client.md                 # AsyncAPIClient class documentation
│   ├── core-concepts/        # Core architectural concepts
│   │   ├── async_resource_management.md  # Async resource management documentation
│   │   ├── async_queue.md                # Bounded async queue with backpressure documentation
│   │   └── resilience_patterns.md        # Circuit breaker and retry patterns documentation
│   └── ...                   # General documentation
├── tests/                    # Test suite
└── ...                       # Configuration files, etc.
```

The architecture follows a modular design where:

- `cli/` contains the command-line interfaces
- `commands/` contains the business logic for each command
- `services/` contains the core services that power the commands
- Each command exposes a `cli_entry()` function that serves as its entry point

---

## Contributing

1. Fork → branch (`feat/…`) → hack
2. `khive fmt && khive ci --check` until green
3. `khive commit "feat(x): …"` + `khive pr`
4. Address review comments → squash-merge ☑️

We follow [Conventional Commits](https://www.conventionalcommits.org/) and
semantic-release tagging.

For more detailed contribution guidelines, see
[CONTRIBUTING.md](CONTRIBUTING.md).
