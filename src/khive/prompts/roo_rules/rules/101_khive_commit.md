# khive commit

## Overview

The `khive commit` command is a Git commit helper for the khive mono-repo that
enforces Conventional Commits, handles staging, ensures Git identity, and
manages pushing to remote repositories. It provides a streamlined workflow for
creating well-formatted commits with proper metadata.

## Usage

- mandatory flag, --by "@khive-abc"

```bash
khive commit [message] [options] --by "@khive-abc"
khive commit --type <type> --scope <scope> --subject <subject> [options] --by "@khive-abc"
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
```

## Exit Codes

- `0`: Commit (and optional push) completed successfully, or nothing to commit
- `1`: Error occurred during commit or push
