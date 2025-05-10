# PR: Improve khive fmt robustness

## Issue #49

This PR addresses robustness issues with the `khive fmt` command:

1. **Python Formatting:** `ruff` was attempting to format files in `.venv`, leading to encoding errors
2. **Rust Formatting:** `cargo fmt` was failing if no `Cargo.toml` was found at the project root
3. **Error Handling:** The command was failing entirely when one stack had issues

## Changes

### 1. Python Formatting: Exclude Virtual Environments

Updated the default Python stack configuration to exclude common virtual environment directories and dependency directories:

```python
"python": StackConfig(
    name="python",
    cmd="ruff format {files}",
    check_cmd="ruff format --check {files}",
    include=["*.py"],
    exclude=[
        "*_generated.py",
        ".venv/**",
        "venv/**",
        "env/**",
        ".env/**",
        "node_modules/**",
        "target/**",
    ],
),
```

### 2. Rust Formatting: Check for Cargo.toml

Added a check for the existence of `Cargo.toml` before running `cargo fmt`:

```python
# Special handling for different formatters
if tool_name == "cargo":
    # Check if Cargo.toml exists
    cargo_toml_path = config.project_root / "Cargo.toml"
    if not cargo_toml_path.exists():
        result["status"] = "skipped"
        result["message"] = f"Skipping Rust formatting: No Cargo.toml found at {cargo_toml_path}"
        warn_msg(result["message"], console=not config.json_output)
        return result
```

### 3. Improved Error Handling

Enhanced the error handling to continue processing when encoding errors occur:

```python
# Check if this is an encoding error
if proc.stderr and ("UnicodeDecodeError" in proc.stderr or "encoding" in proc.stderr.lower()):
    warn_msg(
        f"Encoding error in batch {i // MAX_FILES_PER_BATCH + 1}, skipping affected files", 
        console=not config.json_output
    )
    # We don't mark all_success as False for encoding errors
    # but we do record the message
    stderr_messages.append(f"[WARNING] Encoding issues in some files: {proc.stderr}")
    files_processed += batch_size
```

## Testing

Added tests to verify:
1. `.venv` directories are excluded from Python formatting
2. The command continues processing after encoding errors

## Manual Testing

Verified that:
1. Running `khive fmt` in a project with a `.venv` directory skips files in the virtual environment
2. Running `khive fmt` in a project without a `Cargo.toml` file skips Rust formatting with an informational message
3. Running `khive fmt` in a project with files that have encoding issues continues processing other files