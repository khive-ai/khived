# khive commit

## Overview

The `khive commit` command is a Git commit helper for the khive mono-repo that
enforces Conventional Commits, handles staging, ensures Git identity, and
manages pushing to remote repositories. It provides a streamlined workflow for
creating well-formatted commits with proper metadata.

## Usage

```bash
khive commit [message] [options]
khive commit --type <type> --scope <scope> --subject <subject> [options]
khive commit --interactive [options]
```

## Options

| Option                                  | Description                                                                                |
| --------------------------------------- | ------------------------------------------------------------------------------------------ |
| `message`                               | Full commit message (header + optional body). If used, structured flags below are ignored. |
| `--type`                                | Conventional commit type (e.g., feat, fix, docs).                                          |
| `--scope`                               | Optional scope of the change (e.g., ui, api).                                              |
| `--subject`                             | Subject line of the commit.                                                                |
| `--body`                                | Detailed body of the commit message.                                                       |
| `--breaking-change-description`, `--bc` | Description of the breaking change. Implies '!' in header.                                 |
| `--closes`                              | Issue number this commit closes (e.g., 123).                                               |
| `--search-id`                           | Search ID for evidence citation (e.g., pplx-abc).                                          |
| `--interactive`, `-i`                   | Interactively build commit message and stage files.                                        |
| `--patch-stage`, `-p`                   | Use 'git add -p' for interactive staging. Overrides default_stage_mode.                    |
| `--all-stage`, `-A`                     | Use 'git add -A' to stage all. Overrides default_stage_mode.                               |
| `--amend`                               | Amend the previous commit.                                                                 |
| `--allow-empty`                         | Allow an empty commit (used with 'git commit --allow-empty').                              |
| `--push`                                | Force push after commit (overrides config default_push=false).                             |
| `--no-push`                             | Prevent push after commit (overrides config default_push=true).                            |
| `--project-root PATH`                   | Project root directory (default: Git repository root).                                     |
| `--json-output`                         | Output results in JSON format.                                                             |
| `--dry-run`, `-n`                       | Show what would be done without actually running commands.                                 |
| `--verbose`, `-v`                       | Enable verbose logging.                                                                    |

## Configuration

`khive commit` can be configured using a TOML file located at
`.khive/commit.toml` in your project root. All configuration options are
optional and will use sensible defaults if not specified.

### Configuration Options

```toml
# .khive/commit.toml

# Whether to push after commit by default (default: true)
default_push = true

# Whether to allow empty commits by default (default: false)
allow_empty_commits = false

# List of valid conventional commit types
conventional_commit_types = [
    "feat", "fix", "build", "chore", "ci", "docs",
    "perf", "refactor", "revert", "style", "test"
]

# Optional custom regex pattern for conventional commits
# If not specified, a pattern is generated from conventional_commit_types
# conventional_commit_regex_pattern = "^(feat|fix|docs)(\([\w-]+\))?(!)?:\ .+"

# Fallback Git user identity if not configured
fallback_git_user_name = "khive-bot"
fallback_git_user_email = "khive-bot@example.com"

# Default staging mode: "all" or "patch" (default: "all")
default_stage_mode = "all"
```

### Configuration Precedence

CLI arguments override configuration file settings. For example, if
`default_push = true` is set in the configuration file, but `--no-push` is
passed as a CLI argument, the command will not push after committing.

## Commit Message Format

`khive commit` enforces the
[Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<optional scope>)!: <subject>

<optional body>

BREAKING CHANGE: <optional breaking change description>

(search: <search-id>) Closes #<issue-number>
```

- **type**: The type of change (e.g., feat, fix, docs)
- **scope**: The scope of the change (e.g., ui, api)
- **!**: Indicates a breaking change
- **subject**: A short description of the change
- **body**: A more detailed description of the change
- **BREAKING CHANGE**: Description of the breaking change
- **search-id**: Reference to search evidence (e.g., pplx-abc)
- **issue-number**: Reference to an issue this commit closes

## Examples

```bash
# Simple commit with positional message
khive commit "feat(ui): add dark-mode toggle"

# Commit with structured arguments
khive commit --type feat --scope ui --subject "add dark-mode toggle" --search-id pplx-abc

# Interactive commit creation
khive commit --interactive

# Commit with patch staging (select changes interactively)
khive commit "fix: missing null-check" --patch-stage --no-push

# Amend previous commit
khive commit "chore!: bump API to v2" --amend -v

# Commit with breaking change
khive commit --type feat --scope api --subject "redesign auth flow" --breaking-change-description "Changes token format" --closes 123

# Dry run to see what would happen
khive commit "docs: update README" --dry-run
```

## Error Handling

`khive commit` provides detailed error messages when things go wrong:

- Invalid commit messages are rejected with helpful error messages
- Git command failures include exit codes and error messages
- Configuration errors are reported with helpful context

## Exit Codes

- `0`: Commit (and optional push) completed successfully, or nothing to commit
- `1`: Error occurred during commit or push

## Notes

- The command automatically ensures Git identity is configured, using fallback
  values if needed
- Empty commits are skipped by default unless `--allow-empty` is specified
- When using `--interactive`, you'll be guided through creating a conventional
  commit
- The `--json-output` option provides machine-readable results, useful for
  scripting
- The command supports both positional message and structured arguments
- Search ID injection standardizes the format for evidence citation
