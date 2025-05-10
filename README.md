# Khive · Developer Toolkit for Polyglot Agent Monorepos

[![CI Status](https://img.shields.io/github/actions/workflow/status/khive-dev/khive/ci.yml?branch=main&label=CI)](https://github.com/khive-dev/khive/actions)
[![Coverage](https://img.shields.io/badge/coverage-80%2B-blue.svg)](#)
[![License](https://img.shields.io/badge/license-Apache--2.0-brightgreen.svg)](LICENSE)

> **Khive** is an opinionated toolbox that keeps multi-language agent projects
> **fast, consistent, and boring-in-a-good-way**. One command - `khive` - wraps
> all the little scripts you inevitably write for formatting, CI gating, Git
> hygiene and doc scaffolding, then gives them a coherent UX that works the same
> on your laptop **and** inside CI.

The toolkit is written in pure Python (3.11+), has **zero runtime
dependencies**, and delegates real work to best-of-breed tools like `ruff`,
`cargo`, `deno`, and `pnpm`.

--

- need PERPLEXITY_API_KEY and EXA_API_KEY for `khive info search` to work
- need OPENROUTER_API_KEY for `khive info consult` to work
- to use reader, `pip install "khive[reader]"` or `pip install "khive[all]"` to
  install all dependencies

---

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

| Command         | What it does (TL;DR)                                                                       |
| --------------- | ------------------------------------------------------------------------------------------ |
| `khive init`    | Verifies toolchain, installs JS & Python deps, runs `cargo check`, wires Husky hooks.      |
| `khive fmt`     | Opinionated multi-stack formatter (`ruff` + `black`, `cargo fmt`, `deno fmt`, `markdown`). |
| `khive commit`  | Stages → (optional patch-select) → conventional commit → (optional) push.                  |
| `khive pr`      | Pushes branch & opens/creates GitHub PR (uses `gh`).                                       |
| `khive ci`      | Local CI gate - lints, tests, coverage, template checks. Mirrors GH Actions.               |
| `khive clean`   | Deletes a finished branch locally & remotely - never nukes default branch.                 |
| `khive new-doc` | Scaffolds markdown docs (ADR, RFC, IP…) from templates with front-matter placeholders.     |
| `khive reader`  | Opens/reads arbitrary docs via `docling`; returns JSON over stdout.                        |
| `khive search`  | Validates & (optionally) executes Exa/Perplexity searches.                                 |

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
- **Deno ≥ 1.42** - used for Markdown & TS fmt
- **Git** + **GitHub CLI `gh`** - Git ops & PR automation
- **jq** - report post-processing, coverage merging

Run `khive init --check` to verify everything at once.

---

## Project Layout

```
khive/
  khive_cli.py      # ← unified dispatcher
  khive_init.py     # env bootstrapper
  khive_fmt.py      # formatter orchestrator
  khive_commit.py   # conventional commit helper
  khive_pr.py       # PR automation via gh
  khive_ci.py       # test / lint / coverage gate
  khive_clean.py    # branch janitor
  khive_new_doc.py  # markdown scaffolder
  khive_reader.py   # docling wrapper CLI
  khive_search.py   # Exa / Perplexity search CLI
  utils.py          # shared ANSI & helpers
```

All scripts expose a `main()` entry-point; `khive_cli.py` maps sub-commands via
its `COMMANDS` dict so extension is trivial.

---

## Contributing

1. Fork → branch (`feat/…`) → hack
2. `khive fmt && khive ci --check` until green
3. `khive commit "feat(x): …"` + `khive pr`
4. Address review comments → squash-merge ☑️

We follow [Conventional Commits](https://www.conventionalcommits.org/) and
semantic-release tagging.
