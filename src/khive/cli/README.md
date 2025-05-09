## Table of Contents

1. [Core Philosophy](#core-philosophy)
2. [Quick Start](#quick-start)
3. [Command Catalogue](#command-catalogue)
4. [Usage Examples](#usage-examples)
5. [Configuration](#configuration)
6. [Prerequisites](#prerequisites)
7. [Project Layout](#project-layout)
8. [Contributing](#contributing)
9. [License](#license)

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
$ git clone https://github.com/khive-dev/khive.git
$ cd khive
$ uv pip install -e .        # editable install - puts `khive` on your PATH

# 2 · bootstrap repo (node deps, rust fmt, git hooks, …)
$ khive init -v

# 3 · hack happily
$ khive fmt --check           # smoke-test formatting
$ khive ci --check            # quick pre-commit gate
```

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

For more detailed documentation on the `khive init` command, see
[khive_init.md](../../docs/commands/khive_init.md).

For more detailed documentation on the `khive commit` command, see
[khive_commit.md](../../docs/commands/khive_commit.md).

For more detailed documentation on the `khive clean` command, see
[khive_clean.md](../../docs/commands/khive_clean.md).

For more detailed documentation on the `khive new-doc` command, see
[khive_new_doc.md](../../docs/commands/khive_new_doc.md).

---

## Project Layout

```
khive/
  cli/
    khive_cli.py      # ← unified dispatcher
    khive_init.py     # original implementation modules
    khive_fmt.py
    khive_commit.py
    khive_pr.py
    khive_ci.py
    khive_clean.py
    khive_new_doc.py
    khive_reader.py
    khive_search.py
    khive_mcp.py
    khive_roo.py
  commands/           # ← new command modules directory
    init.py           # standardized command modules
    fmt.py
    commit.py
    pr.py
    ci.py
    clean.py
    new_doc.py
    reader.py
    search.py
    mcp.py
    roo.py
  utils.py            # shared ANSI & helpers
```

The CLI has been restructured with a standardized approach:

1. The main dispatcher (`khive_cli.py`) loads command modules from the
   `khive.commands` package
2. Each command module has a standardized `cli_entry()` function as its entry
   point
3. Command modules in the `commands/` directory use an adapter pattern to
   delegate to the original implementation
4. Module naming has been simplified by removing the `khive_` prefix

This structure makes it easier to add new commands and maintain existing ones,
while ensuring backward compatibility.

---

## Contributing

1. Fork → branch (`feat/…`) → hack
2. `khive fmt && khive ci --check` until green
3. `khive commit "feat(x): …"` + `khive pr`
4. Address review comments → squash-merge ☑️

We follow [Conventional Commits](https://www.conventionalcommits.org/) and
semantic-release tagging.
