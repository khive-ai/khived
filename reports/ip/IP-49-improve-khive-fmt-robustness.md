---
title: "Implementation Plan: Improve khive fmt robustness"
doc_type: IP
issue: 49
author: "khive-implementer"
date: "2025-05-10"
status: "Draft"
---

# Implementation Plan: Improve khive fmt robustness

## 1. Overview

This implementation plan addresses Issue #49, which identifies robustness issues
with the `khive fmt` command:

1. Python formatting: `ruff` attempts to format files in `.venv`, leading to
   encoding errors
2. Rust formatting: `cargo fmt` fails if no `Cargo.toml` is found at the project
   root

The goal is to make `khive fmt` more robust by skipping inapplicable stacks or
problematic files with informational messages, rather than erroring out for the
entire stack.

## 2. Current Implementation Analysis

The current implementation in `src/khive/cli/khive_fmt.py` has the following
structure:

1. `load_fmt_config()` loads configuration from pyproject.toml and
   .khive/fmt.toml
2. `find_files()` identifies files to format based on include/exclude patterns
3. `format_stack()` formats files for a specific stack
4. `_main_fmt_flow()` orchestrates the formatting process across all enabled
   stacks

### Issues identified:

1. **Python Formatting**: The default Python stack configuration doesn't exclude
   `.venv` directories, leading to encoding errors when `ruff` attempts to
   format files in virtual environments.

2. **Rust Formatting**: The `format_stack()` function doesn't check for the
   existence of `Cargo.toml` before running `cargo fmt`, causing errors when the
   command is run in projects without Rust.

3. **Error Handling**: When a formatter fails for a specific file, the entire
   stack is marked as failed, even if other files could be successfully
   formatted.

## 3. Proposed Changes

### 3.1 Python Formatting: Exclude Virtual Environments

Update the default Python stack configuration to exclude common virtual
environment directories and dependency directories:

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

### 3.2 Rust Formatting: Check for Cargo.toml

Modify the `format_stack()` function to check for the existence of `Cargo.toml`
before running `cargo fmt`:

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

    # Cargo fmt doesn't take file arguments, it formats the whole project
    cmd_parts = cmd_template.split()
    cmd = cmd_parts

    # Rest of the existing code...
```

### 3.3 Improve Error Handling

Enhance the error handling in the `format_stack()` function to continue
processing other files when one file fails, particularly for encoding issues:

```python
# Process batch result
try:
    if isinstance(proc, int) and proc == 0:
        files_processed += batch_size
    elif isinstance(proc, subprocess.CompletedProcess):
        if proc.returncode == 0:
            files_processed += batch_size
        else:
            # Check if this is an encoding error
            if "UnicodeDecodeError" in proc.stderr or "encoding" in proc.stderr.lower():
                warn_msg(f"Encoding error in batch {i // MAX_FILES_PER_BATCH + 1}, skipping affected files", console=not config.json_output)
                # We don't mark all_success as False for encoding errors
                files_processed += batch_size
            else:
                all_success = False
                if proc.stderr:
                    stderr_messages.append(proc.stderr)
                # If not in check_only mode, stop on first error
                if not config.check_only:
                    break
except Exception as e:
    warn_msg(f"Error processing batch {i // MAX_FILES_PER_BATCH + 1}: {str(e)}", console=not config.json_output)
    all_success = False
    stderr_messages.append(str(e))
    if not config.check_only:
        break
```

## 4. Implementation Steps

1. Update the default Python stack configuration to exclude virtual environment
   directories
2. Add a check for `Cargo.toml` existence before running `cargo fmt`
3. Enhance error handling to continue processing when encoding errors occur
4. Add tests for the new functionality:
   - Test that `.venv` directories are excluded from Python formatting
   - Test that Rust formatting is skipped when no `Cargo.toml` exists
   - Test that the command continues with other stacks when one fails

## 5. Testing Strategy

### 5.1 Unit Tests

Add the following unit tests to `tests/cli/test_khive_fmt.py`:

1. `test_python_excludes_venv`: Verify that `.venv` directories are excluded
   from Python formatting
2. `test_rust_skips_without_cargo_toml`: Verify that Rust formatting is skipped
   when no `Cargo.toml` exists
3. `test_continue_after_encoding_error`: Verify that the command continues
   processing after an encoding error

### 5.2 Manual Testing

1. Run `khive fmt` in a project with a `.venv` directory to verify that files in
   the virtual environment are skipped
2. Run `khive fmt` in a project without a `Cargo.toml` file to verify that Rust
   formatting is skipped
3. Run `khive fmt` in a project with files that have encoding issues to verify
   that the command continues processing other files

## 6. Risks and Mitigations

| Risk                                                                               | Mitigation                                                                                         |
| ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Excluding too many directories could prevent legitimate files from being formatted | Carefully select exclusion patterns to target only virtual environments and dependency directories |
| Skipping Rust formatting might be unexpected for users                             | Provide clear warning messages when Rust formatting is skipped                                     |
| Continuing after encoding errors might mask legitimate issues                      | Log clear warning messages about skipped files due to encoding issues                              |

## 7. Alternatives Considered

1. **Use ruff's built-in exclusion mechanism**: We could rely on ruff's own
   exclusion patterns, but this would require users to configure ruff
   separately, which goes against the goal of having `khive fmt` provide
   sensible defaults.

2. **Fail fast on any error**: We could maintain the current behavior of failing
   on any error, but this would not address the robustness issues identified in
   Issue #49.

3. **Add a --continue-on-error flag**: We could add a flag to control whether to
   continue on errors, but this adds complexity to the command interface.

## 8. References

- Issue #49: Improve `khive fmt` robustness
- [Ruff documentation on file exclusion](https://docs.astral.sh/ruff/settings/#exclude)
- [Cargo fmt documentation](https://doc.rust-lang.org/cargo/commands/cargo-fmt.html)

## 9. Implementation Timeline

- Day 1: Implement changes to exclude virtual environments and check for
  Cargo.toml
- Day 2: Enhance error handling and add tests
- Day 3: Manual testing and PR submission
