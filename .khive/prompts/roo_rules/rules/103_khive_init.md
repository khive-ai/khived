# khive init

## Overview

The `khive init` command bootstraps your development environment by detecting
project types (Python, Node.js, Rust) and running appropriate initialization
commands. It verifies required tools, installs dependencies, and sets up
development environments automatically.

## Usage

```bash
khive init [options]
```

## Options

| Option                | Description                                                                           |
| --------------------- | ------------------------------------------------------------------------------------- |
| `--project-root PATH` | Path to the project root directory (default: current working directory)               |
| `--json-output`       | Output results in JSON format                                                         |
| `--dry-run`, `-n`     | Show what would be done without actually running commands                             |
| `--step STEP`         | Run only specific step(s) by name. Can be repeated (e.g., `--step python --step npm`) |
| `--verbose`, `-v`     | Enable verbose logging                                                                |

## Configuration

`khive init` can be configured using a TOML file located at `.khive/init.toml`
in your project root. All configuration options are optional and will use
sensible defaults if not specified.

### Configuration Options

```toml
# .khive/init.toml

# Skip warnings for missing optional tools (default: false)
ignore_missing_optional_tools = false

# Stacks to disable even if auto-detected (e.g., "python", "npm", "rust")
disable_auto_stacks = []

# Steps to force enable (e.g., "tools", "husky", or stacks like "python")
force_enable_steps = []

# Custom steps
[custom_steps.example_custom_build]
cmd = "echo Hello from khive custom step"
run_if = "file_exists:pyproject.toml" # Condition to run this step
cwd = "." # Working directory relative to project root
```

### Configuration Precedence

CLI arguments override configuration file settings. For example, if
`dry_run = false` is set in the configuration file, but `--dry-run` is passed as
a CLI argument, the command will run in dry-run mode.

## Steps

`khive init` automatically detects which steps to run based on your project
structure:

| Step     | Trigger                 | Action                                                                |
| -------- | ----------------------- | --------------------------------------------------------------------- |
| `tools`  | Always runs             | Verifies required and optional tools are installed                    |
| `python` | `pyproject.toml` exists | Runs `uv sync` to install Python dependencies                         |
| `npm`    | `package.json` exists   | Runs `pnpm install --frozen-lockfile` to install Node.js dependencies |
| `rust`   | `Cargo.toml` exists     | Runs `cargo check --workspace` to verify Rust code                    |
| `husky`  | `package.json` exists   | Sets up Husky git hooks if a `prepare` script exists                  |

### Custom Steps

You can define custom steps in the configuration file. Each custom step can
have:

- `cmd`: The command to run
- `run_if`: A condition to determine if the step should run
- `cwd`: The working directory relative to the project root

#### Condition Types

- `file_exists:path/to/file`: Runs the step if the specified file exists
- `tool_exists:tool_name`: Runs the step if the specified tool is available in
  PATH

## Examples

```bash
# Run initialization with default settings
khive init

# Run in verbose mode to see detailed output
khive init -v

# Run only the Python initialization step
khive init --step python

# Show what would be done without making changes
khive init --dry-run

# Output results in JSON format (useful for scripting)
khive init --json-output
```

## Error Handling

`khive init` provides detailed error messages when things go wrong:

- Missing required tools are reported with clear instructions
- Subprocess failures include exit codes and error messages
- Configuration errors are reported with helpful context

If a step fails, execution will halt and report the error, unless it's the
`tools` step which will continue with warnings for optional tools.

## Exit Codes

- `0`: All steps completed successfully
- `1`: One or more steps failed

## Notes

- The `tools` step checks for required tools based on detected project types
- Required tools include `uv` for Python, `pnpm` for Node.js, and
  `cargo`/`rustc` for Rust
- Optional tools include `gh` (GitHub CLI) and `jq` (JSON processor)
