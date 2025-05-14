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
| `khive clean`   | Deletes a finished branch locally & remotely - never nukes default branch.                                                                                                                                                    |
| `khive new-doc` | Scaffolds markdown docs from templates with enhanced template discovery, custom variables, and flexible placeholder substitution. Supports JSON output, dry-run, and force overwrite options.                                 |
| `khive reader`  | Opens/reads arbitrary docs via `docling`; returns JSON over stdout.                                                                                                                                                           |
| `khive info`    | executes Exa/Perplexity searches; consult with peer experts                                                                                                                                                                   |

Run `khive <command> --help` for full flag reference.

- you can do `khive init --stack uv --extra abc` for example to install the
  extra dependencies that exists. typically easier to add a `all` section under
  pyproject [project.optional-dependencies] and then can directly do
  `khive init --stack uv --extra all` to install all the extra dependencies for
  a python project for example.
- hint: if `khive init` didn't sync the full dependencies, you can use the
  package cli to further refine.
- You must do `uv run pre-commit` until no errors, before commit.
- for `khive commit`, usually the pre-commit hook might block it from
  successfully running. you can just run `khive commit` again and again until it
  succeeds. It solves all the issues, just needs to be run multiple times.

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

# search for info from Exa
khive info search --provider exa --query "Latest developments in rust programming language"

# Consult multiple LLMs
khive info consult --question "Compare Python vs Rust for system programming" --models "openai/gpt-o4-mini,anthropic/claude-3.7-sonnet"
```

---

For more detailed documentation on the various `khive` commands, see

```
github link: `https://github.com/khive-ai/khive.d/tree/main/docs/commands`
github owner: `khive-ai`
repo name: `khive.d`
```
