# khive ci

**Purpose**: Automated CI/CD execution for multi-language projects with custom
script support.

## Synopsis

```bash
khive ci [--test-type python|rust|all] [--timeout 300] [--dry-run] [--verbose] [--json-output]
```

## Key Features

- **Auto-detection**: Discovers Python (`pyproject.toml`, `setup.py`) and Rust
  (`Cargo.toml`) projects
- **Custom scripts**: Executes `.khive/scripts/khive_ci.sh` if present (takes
  precedence)
- **Async execution**: Non-blocking test execution with configurable timeouts
- **Structured output**: JSON format for machine consumption

## Command Options

| Option           | Type                | Default | Description                            |
| ---------------- | ------------------- | ------- | -------------------------------------- |
| `--test-type`    | `python\|rust\|all` | `all`   | Filter project types to test           |
| `--timeout`      | `int`               | `300`   | Test execution timeout (seconds)       |
| `--dry-run`      | `flag`              | `false` | Show planned actions without execution |
| `--verbose`      | `flag`              | `false` | Enable detailed output                 |
| `--json-output`  | `flag`              | `false` | Output structured JSON results         |
| `--project-root` | `path`              | `cwd`   | Override project root directory        |

## Exit Codes

- `0`: Success
- `1`: Test failures or execution errors
- `130`: User interruption (Ctrl+C)
- `124`: Timeout exceeded

## Configuration

### TOML Config (`.khive/ci.toml`)

```toml
timeout = 600  # Override default timeout
```

### Custom Script Integration

**File**: `.khive/scripts/khive_ci.sh` **Requirements**: Executable (`chmod +x`)

**Environment Variables** (passed to custom scripts):

```bash
KHIVE_PROJECT_ROOT    # Project root path
KHIVE_CONFIG_DIR      # .khive directory path
KHIVE_DRY_RUN         # "1" if dry-run, "0" otherwise
KHIVE_VERBOSE         # "1" if verbose, "0" otherwise
KHIVE_JSON_OUTPUT     # "1" if JSON output, "0" otherwise
KHIVE_TIMEOUT         # Timeout value in seconds
```

## Output Formats

### JSON Output (`--json-output`)

```json
{
  "status": "success|failure|no_tests|error",
  "project_root": "/path/to/project",
  "total_duration": 45.2,
  "discovered_projects": {
    "python": {
      "test_command": "pytest",
      "test_tool": "pytest",
      "test_paths": ["tests", "src/tests"]
    }
  },
  "test_results": [
    {
      "test_type": "python",
      "command": "pytest -v tests",
      "exit_code": 0,
      "success": true,
      "duration": 23.4,
      "stdout": "test output...",
      "stderr": ""
    }
  ]
}
```

### Text Output (default)

```
khive ci - Continuous Integration Results
==================================================
Project Root: /path/to/project
Total Duration: 45.20s

Discovered Projects:
  • Python: pytest
    Test paths: tests, src/tests

Test Results:
  ✓ PASS python (23.40s)
    Command: pytest -v tests

Overall Status: SUCCESS
```

## Project Detection Logic

### Python Projects

**Triggers**: `pyproject.toml`, `setup.py`, or `requirements.txt` **Test
Command**: `pytest` **Test Discovery**:

- Directories: `tests/`, `test/`, `src/tests/`
- Files: `test_*.py`, `*_test.py` (excluding virtual environments)

### Rust Projects

**Triggers**: `Cargo.toml` **Test Command**: `cargo test` **Test Discovery**:
`tests/` directory, `src/` directory

## Usage Examples

```bash
# Run all detected tests
khive ci

# Python tests only with verbose output
khive ci --test-type python --verbose

# Dry run with JSON output
khive ci --dry-run --json-output

# Extended timeout for slow tests
khive ci --timeout 600

# Custom script execution
# (if .khive/scripts/khive_ci.sh exists)
khive ci  # Automatically uses custom script
```

## Integration Notes

- **Git Integration**: Detects project root via `git rev-parse --show-toplevel`
- **Tool Dependencies**: Requires `pytest` for Python, `cargo` for Rust
- **Custom Scripts**: Take complete precedence over built-in test detection
- **Error Handling**: Graceful degradation for missing tools or network issues
- **Security**: Custom scripts must be regular files and executable
