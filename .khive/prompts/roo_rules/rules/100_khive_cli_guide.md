---
title: "Git & GitHub CLI Quick Reference Guide"
by: "Ocean"
scope: "project"
created: "2025-05-05"
updated: "2025-05-05"
version: "1.0"
description: >
    Essential Git and GitHub (`gh`) command-line interface practices and commands
---

## Core Philosophy

- **Single entry-point** → `khive <command>`
- **Convention over config** → sensible defaults, TOML for the rest
- **CI/local parity** → the CLI and the GH workflow run the _same_ code
- **Idempotent helpers** → safe to run repeatedly; exit 0 on "nothing to do"
- **No lock-in** → wraps existing ecosystem tools instead of reinventing them

---

## Command Catalogue

| Command         | What it does (TL;DR)                                                                                                                                                                                                          |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `khive init`    | Bootstraps development environment by detecting project types, verifying tools, installing dependencies, and setting up project-specific configurations. Supports Python, Node.js, and Rust projects with customizable steps. |
| `khive fmt`     | Opinionated multi-stack formatter (`ruff` + `black`, `cargo fmt`, `deno fmt`, `markdown`).                                                                                                                                    |
| `khive commit`  | Enforces Conventional Commits with structured input, interactive mode, search ID injection, configuration via TOML, and JSON output. Handles staging, Git identity, and push control.                                         |
| `khive pr`      | Pushes branch & opens/creates GitHub PR (uses `gh`).                                                                                                                                                                          |
| `khive ci`      | Local CI gate - lints, tests, coverage, template checks. Mirrors GH Actions.                                                                                                                                                  |
| `khive clean`   | Deletes a finished branch locally & remotely - never nukes default branch.                                                                                                                                                    |
| `khive new-doc` | Scaffolds markdown docs from templates with enhanced template discovery, custom variables, and flexible placeholder substitution. Supports JSON output, dry-run, and force overwrite options.                                 |
| `khive reader`  | Opens/reads arbitrary docs via `docling`; returns JSON over stdout.                                                                                                                                                           |
| `khive search`  | Validates & (optionally) executes Exa/Perplexity searches.                                                                                                                                                                    |
| `khive mcp`     | Runs configuration-driven MCP servers.                                                                                                                                                                                        |
| `khive roo`     | Legacy ROO mode generator.                                                                                                                                                                                                    |

Run `khive <command> --help` for full flag reference.

---

## Usage Examples

```bash
# format *everything*, fixing files in-place
khive fmt

# format only Rust & docs, check-only
khive fmt --stack rust,docs --check

# run init with verbose output and only the Python step
khive init -v --step python

# run init in dry-run mode to see what would happen
khive init --dry-run

# staged patch commit, no push (good for WIP)
khive commit "feat(ui): dark-mode toggle" --patch --no-push

# structured commit with search ID citation
khive commit --type fix --scope api --subject "handle null responses" --search-id pplx-abc123

# interactive commit creation with guided prompts
khive commit --interactive

# open PR in browser as draft
khive pr --draft --web

# run the same CI suite GH will run
khive ci

# delete old feature branch safely
khive clean feature/old-experiment --dry-run

# list all available document templates
khive new-doc --list-templates

# create a new RFC doc with custom variables
khive new-doc RFC 001-streaming-api --var author="Jane Smith" --var status="Draft"

# preview document without creating it
khive new-doc TDS 17-new-feature --dry-run --verbose

# create document with JSON output (useful for scripting)
khive new-doc IP 18-new-component --json-output

# open a PDF & read slice 0-500 chars
DOC=$(khive reader open --source paper.pdf | jq -r .doc_id)
khive reader read --doc "$DOC" --end 500
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
# Configuration for khive init (.khive/init.toml)
ignore_missing_optional_tools = false
disable_auto_stacks = ["rust"]  # Disable auto-detection of Rust projects
force_enable_steps = ["tools"]  # Always run the tools check

# Custom step - runs after built-ins
```

```toml
[tool.khive-commit]
# Configuration for khive commit (.khive/commit.toml)
default_push = false  # Don't push by default
allow_empty_commits = false
conventional_commit_types = ["feat", "fix", "docs", "chore", "test"]
fallback_git_user_name = "khive-bot"
fallback_git_user_email = "khive-bot@example.com"
default_stage_mode = "patch"  # Use interactive staging by default
[custom_steps.docs_build]
cmd = "pnpm run docs:build"
run_if = "file_exists:package.json"
cwd = "."
```

```toml
[tool.khive-new-doc]
# Configuration for khive new-doc (.khive/new_doc.toml)
default_destination_base_dir = "reports"
custom_template_dirs = ["templates", "/abs/path/templates"]

[tool.khive-new-doc.default_vars]
author = "Your Name"
project = "Project Name"
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

Run `khive init -v` to verify everything at once with detailed output.

For more detailed documentation on the various `khive` commands, see

```
github link: `https://github.com/khive-ai/khive.d/tree/main/docs/commands`
github owner: `khive-ai`
repo name: `khive.d`
```
