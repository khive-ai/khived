# khive pr

## Overview

The `khive pr` command is a GitHub Pull Request helper that simplifies the
creation and management of PRs with enhanced support for agent-driven workflows.
It automates the process of pushing branches, creating PRs with appropriate
titles and descriptions, and handling existing PRs.

## Key Features

- Auto-detects repository root, branch, and default base branch
- Prevents duplicate PRs by checking for existing ones
- Infers title and body from the last Conventional Commit
- Supports configuration via `.khive/pr.toml`
- Enhanced PR metadata: reviewers, assignees, labels, draft status
- Structured JSON output for agent consumption
- 100% standard library; relies only on `git` & `gh` executables

## Usage

```bash
khive pr [options]
```

## Options

| Option                  | Description                                                                             |
| ----------------------- | --------------------------------------------------------------------------------------- |
| `--title`               | Pull request title. If not provided, uses the last commit subject.                      |
| `--body`                | Pull request body text.                                                                 |
| `--body-from-file PATH` | Path to a file containing the PR body.                                                  |
| `--base BRANCH`         | Base branch for the PR (e.g., main, develop).                                           |
| `--draft`, `--no-draft` | Create as a draft PR or not.                                                            |
| `--reviewer USER`       | Add a reviewer (user or team). Can be repeated.                                         |
| `--assignee USER`       | Add an assignee. Can be repeated.                                                       |
| `--label LABEL`         | Add a label. Can be repeated.                                                           |
| `--web`                 | Open the PR in a web browser after creating or if it exists.                            |
| `--push`                | Force push current branch before PR creation (overrides config auto_push_branch=false). |
| `--no-push`             | Do not push branch before PR creation (overrides config auto_push_branch=true).         |
| `--project-root PATH`   | Project root directory (default: Git repository root).                                  |
| `--json-output`         | Output results in JSON format.                                                          |
| `--dry-run`, `-n`       | Show what would be done without actually running commands.                              |
| `--verbose`, `-v`       | Enable verbose logging.                                                                 |

## PR Creation Workflow

1. **Branch Detection**: Automatically detects the current branch and target
   base branch
2. **Push Branch**: Pushes the current branch to the remote repository (unless
   `--no-push` is specified)
3. **Check for Existing PR**: Checks if a PR already exists for the current
   branch
4. **PR Creation**: If no PR exists, creates a new PR with the specified or
   inferred title and body
5. **PR Metadata**: Adds reviewers, assignees, and labels as specified
6. **Browser Opening**: Opens the PR in a browser if `--web` is specified

## Examples

```bash
# Create a PR using the last commit message as title/body
khive pr

# Create a PR with a custom title
khive pr --title "Add dark mode support"

# Create a PR with custom title and body
khive pr --title "Add dark mode support" --body "This PR implements dark mode as discussed in issue #42."

# Create a PR with body from a file
khive pr --body-from-file pr_description.md

# Create a draft PR
khive pr --draft

# Create a PR with reviewers and assignees
khive pr --reviewer user1 --reviewer team/frontend --assignee user2

# Create a PR with labels
khive pr --label "feature" --label "ui"

# Create a PR targeting a specific base branch
khive pr --base develop

# Create a PR and open it in the browser
khive pr --web

# Create a PR without pushing the branch first
khive pr --no-push

# Dry run to see what would happen
khive pr --dry-run

# Output results in JSON format (for agent consumption)
khive pr --json-output
```

## Exit Codes

- `0`: PR creation or retrieval completed successfully
- `1`: Error occurred during PR creation or retrieval
