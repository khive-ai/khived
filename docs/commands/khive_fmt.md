# khive fmt

**Purpose**: Opinionated multi-stack code formatter with custom script support.

## Synopsis

```bash
khive fmt [--stack python,rust,docs,deno] [--check] [--dry-run] [--verbose] [--json-output]
```

## Key Features

- **Multi-stack formatting**: Python (ruff), Rust (cargo), Deno/JS/TS, Markdown
- **Custom scripts**: Executes `.khive/scripts/khive_fmt.sh` if present (takes
  precedence)
- **Selective formatting**: Filter by stack types
- **Check mode**: Validate formatting without modifications
- **Batch processing**: Handles large file sets efficiently

## Command Options

| Option           | Type     | Default | Description                                        |
| ---------------- | -------- | ------- | -------------------------------------------------- |
| `--stack`        | `string` | `all`   | Comma-separated stack list (python,rust,docs,deno) |
| `--check`        | `flag`   | `false` | Check formatting without modifying files           |
| `--dry-run`      | `flag`   | `false` | Show planned actions without execution             |
| `--verbose`      | `flag`   | `false` | Enable detailed output                             |
| `--json-output`  | `flag`   | `false` | Output structured JSON results                     |
| `--project-root` | `path`   | `cwd`   | Override project root directory                    |

## Exit Codes

- `0`: Success or check passed
- `1`: Formatting errors or check failed

## Configuration

### Primary Config (`pyproject.toml`)

```toml
[tool."khive fmt"]
enable = ["python", "rust", "docs", "deno"]

[tool."khive fmt".stacks.python]
cmd = "ruff format {files}"
check_cmd = "ruff format --check {files}"
include = ["*.py"]
exclude = ["*_generated.py", ".venv/**"]

[tool."khive fmt".stacks.rust]
cmd = "cargo fmt"
check_cmd = "cargo fmt --check"
include = ["*.rs"]
exclude = []
```

### Override Config (`.khive/fmt.toml`)

```toml
enable = ["python", "rust"]  # Overrides pyproject.toml

[stacks.python]
exclude = ["legacy/**", "*_generated.py"]
```

### Custom Script Integration

**File**: `.khive/scripts/khive_fmt.sh` **Requirements**: Executable
(`chmod +x`)

**Environment Variables** (passed to custom scripts):

```bash
KHIVE_PROJECT_ROOT     # Project root path
KHIVE_CONFIG_DIR       # .khive directory path
KHIVE_DRY_RUN          # "1" if dry-run, "0" otherwise
KHIVE_VERBOSE          # "1" if verbose, "0" otherwise
KHIVE_CHECK_ONLY       # "1" if check mode, "0" otherwise
KHIVE_JSON_OUTPUT      # "1" if JSON output, "0" otherwise
KHIVE_SELECTED_STACKS  # Comma-separated selected stacks
KHIVE_ENABLED_STACKS   # Comma-separated enabled stacks
```

## Output Formats

### JSON Output (`--json-output`)

```json
{
  "status": "success|failure|check_failed|skipped",
  "message": "Formatting completed successfully.",
  "stacks_processed": [
    {
      "stack_name": "python",
      "status": "success",
      "message": "Successfully formatted 15 files for stack 'python'.",
      "files_processed": 15
    }
  ]
}
```

### Text Output (default)

```
✔ Successfully formatted 15 files for stack 'python'.
✔ Successfully formatted files for stack 'rust'.
⚠ No files found for stack 'docs'.
✔ khive fmt finished: Formatting completed successfully.
```

## Stack Configurations

### Python Stack

**Trigger**: `*.py` files **Tool**: `ruff format` **Default Excludes**:
`*_generated.py`, `.venv/**`, `venv/**`, `env/**`, `node_modules/**`

### Rust Stack

**Trigger**: `*.rs` files or `Cargo.toml` presence **Tool**: `cargo fmt`
**Special**: Formats entire project, not individual files

### Docs Stack

**Trigger**: `*.md`, `*.markdown` files **Tool**: `deno fmt` **Default
Excludes**: None

### Deno Stack

**Trigger**: `*.ts`, `*.js`, `*.jsx`, `*.tsx` files **Tool**: `deno fmt`
**Default Excludes**: `*_generated.*`, `node_modules/**`

## Usage Examples

```bash
# Format all detected stacks
khive fmt

# Format only Python and Rust
khive fmt --stack python,rust

# Check formatting without changes
khive fmt --check

# Dry run with verbose output
khive fmt --dry-run --verbose

# JSON output for CI integration
khive fmt --check --json-output

# Custom script execution
# (if .khive/scripts/khive_fmt.sh exists)
khive fmt  # Automatically uses custom script
```

## Status Values

- `success`: All files formatted successfully
- `failure`: Formatting errors occurred
- `check_failed`: Check mode found unformatted files
- `skipped`: No files found or stack disabled
- `error`: Tool not found or execution failed

## Integration Notes

- **Tool Dependencies**: Requires `ruff` for Python, `cargo` for Rust, `deno`
  for JS/TS/Markdown
- **File Discovery**: Uses glob patterns with exclude filtering
- **Batch Processing**: Processes max 500 files per command to avoid system
  limits
- **Custom Scripts**: Take complete precedence over built-in formatters
- **Configuration Hierarchy**: `.khive/fmt.toml` overrides `pyproject.toml`
- **Security**: Custom scripts must be regular files and executable
