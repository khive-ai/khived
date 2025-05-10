# khive fmt

## Overview

The `khive fmt` command is an opinionated multi-stack formatter that formats
code across different language stacks (Python, Rust, Deno, Markdown). It
provides a unified interface for running various formatters with sensible
defaults, while allowing for customization via configuration files.

## Features

- Formats code across multiple stacks (Python, Rust, Deno, Markdown)
- Supports selective formatting via `--stack` flag
- Supports check-only mode via `--check` flag
- Configurable via TOML
- Handles missing formatters gracefully
- Provides JSON output for scripting

## Usage

```bash
khive fmt [options]
```

## Options

| Option                | Description                                                       |
| --------------------- | ----------------------------------------------------------------- |
| `--stack STACKS`      | Comma-separated list of stacks to format (e.g., python,rust,docs) |
| `--check`             | Check formatting without modifying files                          |
| `--project-root PATH` | Project root directory (default: Git repository root)             |
| `--json-output`       | Output results in JSON format                                     |
| `--dry-run`, `-n`     | Show what would be done without actually running commands         |
| `--verbose`, `-v`     | Enable verbose logging                                            |

## Configuration

`khive fmt` can be configured using TOML in two locations:

1. In `pyproject.toml` under the `[tool.khive fmt]` section
2. In a dedicated `.khive/fmt.toml` file (which takes precedence)

### Configuration Options

```toml
# In pyproject.toml or .khive/fmt.toml

# Enable/disable stacks globally
enable = ["python", "rust", "docs", "deno"]

# Stack-specific configurations
[stacks.python]
cmd = "ruff format {files}"
check_cmd = "ruff format --check {files}"
include = ["*.py"]
exclude = ["*_generated.py"]

[stacks.rust]
cmd = "cargo fmt"
check_cmd = "cargo fmt --check"
include = ["*.rs"]
exclude = []

[stacks.docs]
cmd = "deno fmt {files}"
check_cmd = "deno fmt --check {files}"
include = ["*.md", "*.markdown"]
exclude = []

[stacks.deno]
cmd = "deno fmt {files}"
check_cmd = "deno fmt --check {files}"
include = ["*.ts", "*.js", "*.jsx", "*.tsx"]
exclude = ["*_generated.*", "node_modules/**"]
```

### Configuration Precedence

1. CLI arguments override configuration file settings
2. `.khive/fmt.toml` overrides `pyproject.toml`
3. Default configurations are used for any unspecified settings

## Default Formatters

| Stack  | Default Formatter | Command               |
| ------ | ----------------- | --------------------- |
| Python | ruff              | `ruff format {files}` |
| Rust   | cargo fmt         | `cargo fmt`           |
| Docs   | deno fmt          | `deno fmt {files}`    |
| Deno   | deno fmt          | `deno fmt {files}`    |

## Examples

```bash
# Format all enabled stacks
khive fmt

# Format only Python and Rust code
khive fmt --stack python,rust

# Check formatting without modifying files
khive fmt --check

# Check formatting for specific stacks
khive fmt --stack docs,deno --check

# Verbose output with dry run
khive fmt -v -n

# Output results in JSON format
khive fmt --json-output
```

## JSON Output Format

When using `--json-output`, the command returns a structured JSON object:

```json
{
  "status": "success",
  "message": "Formatting completed successfully.",
  "stacks_processed": [
    {
      "stack_name": "python",
      "status": "success",
      "message": "Successfully formatted 10 files for stack 'python'.",
      "files_processed": 10
    },
    {
      "stack_name": "rust",
      "status": "success",
      "message": "Successfully formatted 5 files for stack 'rust'.",
      "files_processed": 5
    }
  ]
}
```

### Status Codes

The JSON output includes status codes for each operation:

- **Overall Status**: `"success"`, `"failure"`, `"check_failed"`, `"skipped"`
- **Stack Status**: `"success"`, `"error"`, `"check_failed"`, `"skipped"`

## Error Handling

`khive fmt` provides detailed error messages when things go wrong:

- Missing formatters are reported with helpful messages
- Formatting errors include the stderr output from the formatter
- Configuration errors are reported with helpful context

## Exit Codes

- `0`: Formatting completed successfully
- `1`: Error occurred during formatting or check failed

## Notes

- The command automatically detects the project root using Git
- Formatters must be installed separately (ruff, cargo, deno)
- The `{files}` placeholder in commands is replaced with the list of files to
  format
- Some formatters (like `cargo fmt`) don't accept file arguments and format the
  whole project
