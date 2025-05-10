# khive clean

## Overview

The `khive clean` command is a Git branch cleanup utility that deletes branches
both locally and remotely after checking out and pulling the default branch. It
provides enhanced branch management with features like cleaning all merged
branches, JSON output, and configuration options.

## Usage

```bash
khive clean <branch> [options]
khive clean --all-merged [--into <base_branch>] [options]
```

## Options

| Option                   | Description                                                                                                  |
| ------------------------ | ------------------------------------------------------------------------------------------------------------ |
| `branch_name`            | Name of the specific branch to delete.                                                                       |
| `--all-merged`           | Clean all local branches already merged into the target base branch.                                         |
| `--into <base_branch>`   | For `--all-merged`, specify the base branch to check merges against (default: auto-detected or from config). |
| `--yes`, `-y`, `--force` | Skip confirmation when using `--all-merged` (DANGER!).                                                       |
| `--project-root PATH`    | Project root directory (default: Git repository root).                                                       |
| `--json-output`          | Output results in JSON format.                                                                               |
| `--dry-run`, `-n`        | Show what would be done without actually running commands.                                                   |
| `--verbose`, `-v`        | Enable verbose logging.                                                                                      |

## Configuration

`khive clean` can be configured using a TOML file located at `.khive/clean.toml`
in your project root. All configuration options are optional and will use
sensible defaults if not specified.

### Configuration Options

```toml
# .khive/clean.toml

# List of branch patterns that should be protected from deletion
# Default: ["release/*", "develop"]
protected_branch_patterns = ["release/*", "develop", "hotfix/*"]

# Default remote name to use for operations
# Default: "origin"
default_remote = "origin"

# Whether to strictly enforce successful pull on default branch
# If true, will abort if pull fails; if false, will continue with warning
# Default: false
strict_pull_on_default = false

# Default base branch for --all-merged when not specified
# If empty, will auto-detect the default branch
# Default: "" (auto-detect)
all_merged_default_base = "main"
```

### Configuration Precedence

CLI arguments override configuration file settings. For example, if
`all_merged_default_base = "main"` is set in the configuration file, but
`--into develop` is passed as a CLI argument, the command will use "develop" as
the base branch.

## Branch Protection

The `khive clean` command includes built-in protection to prevent accidental
deletion of important branches:

1. The default branch (e.g., "main" or "master") is always protected
2. Any branch matching patterns in `protected_branch_patterns` is protected
3. Protected branches will be skipped with a warning when using `--all-merged`

## Default Branch Detection

The command uses a sophisticated approach to detect the default branch:

1. First tries GitHub CLI (`gh repo view`) if available
2. Then tries Git symbolic ref (`git symbolic-ref refs/remotes/origin/HEAD`)
3. Falls back to checking for common names ("main", "master")
4. Ultimate fallback to "main" if all else fails

## Examples

```bash
# Clean a specific feature branch
khive clean feature/old-feature

# Clean all merged branches (with confirmation prompt)
khive clean --all-merged

# Clean all branches merged into develop
khive clean --all-merged --into develop

# Skip confirmation when cleaning all merged branches (use with caution!)
khive clean --all-merged --yes

# Preview what would be cleaned without actually deleting anything
khive clean --all-merged --dry-run

# Get structured JSON output (useful for scripting)
khive clean feature/old-feature --json-output

# Enable verbose logging for detailed information
khive clean feature/old-feature --verbose
```

## JSON Output Format

When using `--json-output`, the command returns a structured JSON object:

```json
{
  "status": "success",
  "message": "All 1 targeted branch(es) processed successfully.",
  "branches_processed": [
    {
      "branch_name": "feature/old-feature",
      "local_delete_status": "OK",
      "remote_delete_status": "OK",
      "message": "Branch 'feature/old-feature' cleaned successfully."
    }
  ],
  "default_branch_info": {
    "name": "main",
    "checkout_status": "OK",
    "pull_status": "OK"
  }
}
```

### Status Codes

The JSON output includes status codes for each operation:

- **Branch Status**: `"success"`, `"partial_failure"`, `"failure"`, `"skipped"`
- **Local/Remote Delete Status**: `"OK"`, `"FAILED"`, `"NOT_FOUND"`,
  `"PROTECTED"`, `"SKIPPED"`, `"OK_DRY_RUN"`
- **Default Branch Operations**: `"OK"`, `"FAILED"`, `"SKIPPED"`,
  `"ALREADY_ON"`, `"OK_DRY_RUN"`

## Error Handling

`khive clean` provides detailed error messages when things go wrong:

- Git command failures include exit codes and error messages
- Configuration errors are reported with helpful context
- Branch protection prevents accidental deletion of important branches

## Exit Codes

- `0`: Clean process completed successfully
- `1`: Error occurred during the clean process or partial failure

## Notes

- The command always checks out and pulls the default branch before cleaning
- When using `--all-merged`, you'll be prompted for confirmation unless `--yes`
  is specified
- The `--dry-run` option is useful for previewing what would be deleted
- The command handles cases where branches might not exist locally or remotely
- JSON output provides machine-readable results, useful for scripting
