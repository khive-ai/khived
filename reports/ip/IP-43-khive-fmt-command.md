---
title: "Implementation Plan: khive fmt command"
issue: 43
author: "khive-implementer"
date: "2025-05-10"
status: "Completed"
---

# Implementation Plan: khive fmt command

## 1. Overview

This implementation plan outlines the approach for adding the `khive fmt`
command to the khive CLI. The command will provide an opinionated multi-stack
formatter that supports Python, Rust, Deno, and Markdown files, with
configurable options and a check-only mode.

## 2. Requirements

Based on the README.md and task description, the `khive fmt` command should:

1. Format code across multiple stacks (Python, Rust, Deno, Markdown)
2. Support selective formatting via `--stack` flag (e.g., `--stack rust,docs`)
3. Support check-only mode via `--check` flag
4. Be configurable via TOML
5. Follow the existing patterns for CLI commands in the khive project
6. Include appropriate tests

## 3. Design

### 3.1 Command Structure

Following the existing pattern in the khive project, we'll create:

1. A CLI interface file: `src/khive/cli/khive_fmt.py`
2. A command implementation file: `src/khive/commands/fmt.py`
3. Update the CLI dispatcher to include the new command

The command implementation file will be a thin adapter that delegates to the CLI
interface file, consistent with other commands in the project.

### 3.2 Configuration

The command will support configuration via:

1. `pyproject.toml` under the `[tool.khive fmt]` section
2. A dedicated `.khive/fmt.toml` file (which takes precedence)

Configuration options will include:

```toml
# Enable/disable stacks globally
enable = ["python", "rust", "docs", "deno"]

# Stack-specific configurations
[stacks.python]
cmd = "ruff format {files}"
check_cmd = "ruff format --check {files}"
include = ["*.py"]
exclude = ["*_generated.py"]
```

### 3.3 Default Formatters

| Stack  | Default Formatter | Command               |
| ------ | ----------------- | --------------------- |
| Python | ruff              | `ruff format {files}` |
| Rust   | cargo fmt         | `cargo fmt`           |
| Docs   | deno fmt          | `deno fmt {files}`    |
| Deno   | deno fmt          | `deno fmt {files}`    |

### 3.4 Command Line Interface

```
khive fmt [--stack stack1,stack2,...] [--check] [--dry-run] [--json-output] [--verbose]
```

## 4. Implementation Steps

1. Create the CLI interface file `src/khive/cli/khive_fmt.py`
   - Implement configuration loading
   - Implement file discovery
   - Implement formatter execution
   - Implement CLI argument parsing

2. Create the command implementation file `src/khive/commands/fmt.py`
   - Delegate to the CLI interface

3. Update the CLI dispatcher in `src/khive/cli/khive_cli.py`
   - Add the new command to the `COMMANDS` dictionary
   - Add a description to the `COMMAND_DESCRIPTIONS` dictionary

4. Create tests in `tests/cli/test_khive_fmt.py`
   - Test configuration loading
   - Test file discovery
   - Test formatter execution
   - Test CLI entry point

5. Create documentation in `docs/commands/khive_fmt.md`
   - Document usage
   - Document configuration options
   - Provide examples

## 5. Testing Strategy

We'll use pytest with mocking to test the command without actually running
formatters. Tests will cover:

1. Configuration loading from different sources
2. File discovery with include/exclude patterns
3. Formatter execution with different options
4. Error handling for missing formatters
5. CLI entry point with different arguments

## 6. Dependencies

The command depends on external formatters:

- `ruff` for Python formatting
- `cargo fmt` for Rust formatting
- `deno fmt` for Deno and Markdown formatting

These dependencies are not installed by the command but are expected to be
available in the environment.

## 7. Risks and Mitigations

| Risk                                 | Mitigation                                                          |
| ------------------------------------ | ------------------------------------------------------------------- |
| External formatters not installed    | Gracefully handle missing formatters with clear error messages      |
| Formatters have different interfaces | Abstract formatter execution to handle different command structures |
| Large projects may have many files   | Implement efficient file discovery and filtering                    |

## 8. Implementation Notes

- The command will use subprocess to execute formatters
- File discovery will use glob patterns with include/exclude filters
- Configuration will be loaded from TOML files with sensible defaults
- The command will support JSON output for scripting

## 9. Conclusion

The `khive fmt` command will provide a unified interface for formatting code
across multiple stacks, with configurable options and a check-only mode. It
follows the existing patterns for CLI commands in the khive project and includes
appropriate tests and documentation.
