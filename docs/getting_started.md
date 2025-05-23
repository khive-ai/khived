# Getting Started with Khive

Khive is an extensible development environment that brings AI-native tooling,
multi-stack formatting, and intelligent project initialization to your workflow.
This guide will get you up and running in minutes.

## Quick Start

### 1. Install Khive

**Using uv (recommended):**

```bash
# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install khive with all features
uv pip install "khive[all]"
```

**Or add to your project:**

```bash
uv add --dev "khive[all]"
```

### 2. Initialize Your Project

Run khive in any project directory to set it up:

```bash
khive init
```

This will:

- Detect your project type (Python, Node.js, Rust)
- Install required development tools
- Set up Git hooks (if you have a package.json with Husky)
- Create the `.khive` configuration directory

**Example output:**

```
⚙ TOOLS
✔ Tool 'uv' found.
✔ Tool 'pnpm' found.

⚙ PYTHON  
▶ [python] $ uv sync
  -> OK: Command 'uv sync' successful.

✔ khive init completed successfully.
```

### 3. Format Your Code

Khive automatically detects and formats multiple languages:

```bash
# Format all supported files
khive fmt

# Format specific stacks
khive fmt --stack python,rust

# Check formatting without changes
khive fmt --check
```

**Supported formats:**

- **Python**: Uses `ruff format`
- **Rust**: Uses `cargo fmt`
- **JavaScript/TypeScript**: Uses `deno fmt`
- **Markdown**: Uses `deno fmt`

### 4. Run Your Tests

Khive discovers and runs tests across multiple stacks:

```bash
# Run all detected tests
khive ci

# Run specific stack tests
khive ci --test-type python

# See what would run without executing
khive ci --dry-run
```

**Test discovery:**

- **Python**: Finds `pytest`, discovers `tests/` directories
- **Rust**: Runs `cargo test`, discovers `tests/` and `src/` tests

### 5. Set up API Keys (Optional)

For advanced features like AI search and consultation, create a `.env` file:

```bash
# .env
OPENROUTER_API_KEY=your_openrouter_key
PERPLEXITY_API_KEY=your_perplexity_key
EXA_API_KEY=your_exa_key
```

Get API keys from:

- [OpenRouter](https://openrouter.ai/) - For AI model access
- [Perplexity](https://perplexity.ai/) - For AI-powered search
- [Exa](https://exa.ai/) - For web search

## Core Commands

### `khive init`

**Initialize your development environment**

```bash
khive init                    # Auto-detect and set up all stacks
khive init --stack python    # Set up Python environment only
khive init --extra all       # Include all optional dependencies
```

### `khive fmt`

**Format your code consistently**

```bash
khive fmt                     # Format all files
khive fmt --check            # Check without modifying
khive fmt --stack python     # Format Python files only
```

### `khive ci`

**Run your tests and checks**

```bash
khive ci                      # Run all tests
khive ci --test-type rust     # Run Rust tests only
khive ci --timeout 600       # Set custom timeout
```

### `khive mcp`

**Manage AI-native tools (Advanced)**

```bash
khive mcp list               # List configured MCP servers
khive mcp tools server       # Show available tools
khive mcp call server tool --arg value  # Execute tools
```

## Customization

### Custom Scripts

Override any khive command with your own scripts:

```bash
# Create custom scripts directory
mkdir -p .khive/scripts

# Custom initialization
cat > .khive/scripts/khive_init.sh << 'EOF'
#!/bin/bash
echo "Running custom initialization..."
# Your custom setup logic here
EOF

chmod +x .khive/scripts/khive_init.sh
```

Now `khive init` will run your custom script instead of the built-in one.

### Configuration

Customize behavior with configuration files:

```toml
# .khive/init.toml
ignore_missing_optional_tools = true
disable_auto_stacks = ["rust"]
force_enable_steps = ["tools", "python"]
```

```toml
# pyproject.toml
[tool."khive fmt"]
enable = ["python", "docs"]

[tool."khive fmt".stacks.python]
exclude = ["*_generated.py", "legacy/**"]
```

## Common Workflows

### New Python Project

```bash
# Initialize Python environment
khive init --stack uv --extra all

# Format code
khive fmt

# Run tests
khive ci
```

### Multi-Language Project

```bash
# Set up all detected stacks
khive init

# Format everything
khive fmt

# Run all tests
khive ci --json-output  # For CI integration
```

### Check Before Commit

```bash
# Validate formatting and tests
khive fmt --check && khive ci
```

## What's Next?

Once you're comfortable with the basics:

1. **Explore MCP Integration** - Connect AI tools to your development workflow
2. **Custom Scripts** - Create team-specific initialization and CI processes
3. **AI Assistant Setup** - Integrate with Roo or other AI development
   assistants
4. **Team Configuration** - Share configurations across your development team

## Getting Help

- **Check command help**: `khive <command> --help`
- **Verbose output**: Add `--verbose` to any command
- **JSON output**: Add `--json-output` for machine-readable results
- **Dry run**: Add `--dry-run` to see what would happen

## Troubleshooting

**Tool not found errors:**

```bash
# Install missing tools
pip install ruff pytest      # For Python
cargo install               # For Rust (if needed)
npm install -g deno         # For JavaScript/TypeScript
```

**No tests discovered:**

- Make sure test files follow naming conventions (`test_*.py`, `*_test.py`)
- Check that test directories exist (`tests/`, `test/`)

**Permission errors:**

```bash
# Make custom scripts executable
chmod +x .khive/scripts/*.sh
```

That's it! You're now ready to use Khive for faster, more consistent
development. The tool grows with your needs - start simple and add advanced
features as your workflow evolves.
