# khive init

**Purpose**: Multi-stack project initialization with dependency management and
environment setup.

## Synopsis

```bash
khive init [--stack uv|pnpm|cargo] [--extra all|dev|prod] [--step step1,step2] [--dry-run] [--verbose] [--json-output]
```

## Key Features

- **Auto-detection**: Discovers Python, Node.js, and Rust projects
- **Multi-stack setup**: Initializes uv, pnpm, cargo environments
- **Custom scripts**: Executes `.khive/scripts/khive_init.sh` if present (takes
  precedence)
- **Tool validation**: Checks required and optional development tools
- **Step orchestration**: Configurable execution order with dependencies

## Command Options

| Option           | Type              | Default       | Description                            |
| ---------------- | ----------------- | ------------- | -------------------------------------- |
| `--stack`        | `uv\|pnpm\|cargo` | `auto-detect` | Specific stack to initialize           |
| `--extra`        | `string`          | `none`        | Extra dependencies (stack-specific)    |
| `--step`         | `string[]`        | `auto-detect` | Run specific steps only (repeatable)   |
| `--dry-run`      | `flag`            | `false`       | Show planned actions without execution |
| `--verbose`      | `flag`            | `false`       | Enable detailed output                 |
| `--json-output`  | `flag`            | `false`       | Output structured JSON results         |
| `--project-root` | `path`            | `cwd`         | Override project root directory        |

## Exit Codes

- `0`: Success
- `1`: Initialization failed
- `2`: Completed with warnings (optional)

## Configuration

### Primary Config (`.khive/init.toml`)

```toml
# Tool validation behavior
ignore_missing_optional_tools = false

# Disable auto-detected stacks
disable_auto_stacks = ["python", "npm", "rust"]

# Force enable specific steps
force_enable_steps = ["tools", "husky"]

# Custom initialization steps
[custom_steps.setup_db]
cmd = "docker-compose up -d postgres"
run_if = "file_exists:docker-compose.yml"
cwd = "."
```

### Custom Script Integration

**File**: `.khive/scripts/khive_init.sh` **Requirements**: Executable
(`chmod +x`)

**Environment Variables** (passed to custom scripts):

```bash
KHIVE_PROJECT_ROOT          # Project root path
KHIVE_CONFIG_DIR            # .khive directory path
KHIVE_DRY_RUN               # "1" if dry-run, "0" otherwise
KHIVE_VERBOSE               # "1" if verbose, "0" otherwise
KHIVE_JSON_OUTPUT           # "1" if JSON output, "0" otherwise
KHIVE_DETECTED_STACKS       # Comma-separated detected stacks
KHIVE_DISABLED_STACKS       # Comma-separated disabled stacks
KHIVE_FORCED_STEPS          # Comma-separated forced steps
KHIVE_REQUESTED_STACK       # Specific stack from --stack
KHIVE_REQUESTED_EXTRA       # Extra option from --extra
KHIVE_ENABLED_BUILTIN_STEPS # Comma-separated enabled builtin steps
KHIVE_ENABLED_CUSTOM_STEPS  # Comma-separated enabled custom steps
KHIVE_EXPLICIT_STEPS        # Comma-separated explicit steps
```

## Output Formats

### JSON Output (`--json-output`)

```json
{
  "status": "success|failure|warning",
  "steps": [
    {
      "name": "tools",
      "status": "OK|FAILED|SKIPPED|WARNING|DRY_RUN",
      "message": "Tool check completed. All configured tools present.",
      "return_code": 0,
      "command": "uv sync",
      "stdout": "...",
      "stderr": "..."
    }
  ]
}
```

### Text Output (default)

```
⚙ TOOLS
✔ Tool 'uv' found.
✔ Tool 'pnpm' found.
  -> OK: Tool check completed. All configured tools present.

⚙ PYTHON
▶ [python] $ uv sync (in /path/to/project)
  -> OK: Command 'uv sync' successful.

✔ khive init completed successfully.
```

## Built-in Steps

### tools

**Purpose**: Validate required and optional development tools **Required Tools**
(based on detected stacks):

- `uv`: Python environment/package management
- `pnpm`: Node package management
- `cargo`, `rustc`: Rust build tools

**Optional Tools**:

- `gh`: GitHub CLI
- `jq`: JSON processor

**Behavior**: Fails if required tools missing, warns for optional tools

### python

**Trigger**: `pyproject.toml` exists **Command**: `uv sync` **Requirements**:
`uv` tool available **Extra Options**:

- `all`: Include all optional dependency groups (`--all-extras`)
- `<group>`: Include specific dependency group (`--extra <group>`)

### npm

**Trigger**: `package.json` exists **Command**: `pnpm install --frozen-lockfile`
**Requirements**: `pnpm` tool available **Extra Options**:

- `all`: Install all dependencies (`--production=false`)
- `dev`: Install dev dependencies (`--dev`)
- `prod`: Install production only (`--production`)

### rust

**Trigger**: `Cargo.toml` exists **Command**: `cargo check --workspace`
**Requirements**: `cargo` tool available **Extra Options**:

- `all`: Build with all features (`--all-features`)
- `dev`: Check with dev profile (`--profile dev`)
- `test`: Run tests (`cargo test`)
- `<feature>`: Enable specific feature (`--features <feature>`)

### husky

**Trigger**: `package.json` with `prepare` script exists **Command**:
`pnpm run prepare` **Requirements**: `pnpm` tool available **Purpose**: Set up
Git hooks via Husky

## Stack-Specific Initialization

### Python Stack (`--stack uv`)

```bash
# Basic Python environment setup
khive init --stack uv

# Include all optional dependencies
khive init --stack uv --extra all

# Include specific dependency group
khive init --stack uv --extra test
```

### Node.js Stack (`--stack pnpm`)

```bash
# Basic Node.js setup
khive init --stack pnpm

# Install all dependencies including dev
khive init --stack pnpm --extra all

# Production dependencies only
khive init --stack pnpm --extra prod
```

### Rust Stack (`--stack cargo`)

```bash
# Basic Rust setup
khive init --stack cargo

# Build with all features
khive init --stack cargo --extra all

# Run tests during initialization
khive init --stack cargo --extra test
```

## Usage Examples

```bash
# Auto-detect and initialize all stacks
khive init

# Initialize specific stack with extras
khive init --stack uv --extra all

# Run only specific steps
khive init --step tools --step python

# Dry run to see what would happen
khive init --dry-run --verbose

# JSON output for CI integration
khive init --json-output

# Custom script execution
# (if .khive/scripts/khive_init.sh exists)
khive init  # Automatically uses custom script
```

## Step Status Values

- `OK`: Step completed successfully
- `FAILED`: Step failed, halts execution
- `SKIPPED`: Step not applicable or disabled
- `WARNING`: Step completed with issues
- `DRY_RUN`: Dry run mode, shows planned action

## Custom Step Conditions

### run_if Expressions

- `file_exists:<path>`: Check if file exists
- `tool_exists:<tool>`: Check if tool is in PATH

### Example Custom Steps

```toml
[custom_steps.docker_setup]
cmd = "docker-compose up -d"
run_if = "file_exists:docker-compose.yml"
cwd = "."

[custom_steps.database_migrate]
cmd = "npm run db:migrate"
run_if = "tool_exists:npm"
cwd = "backend"
```

## Integration Notes

- **Tool Dependencies**: Auto-detects required tools based on project files
- **Execution Order**: tools → python → npm → rust → husky → custom steps
- **Failure Handling**: Stops on critical failures, continues on warnings
- **Custom Scripts**: Take complete precedence over built-in initialization
- **Configuration Priority**: CLI args override `.khive/init.toml`
- **Security**: Custom scripts must be regular files and executable
