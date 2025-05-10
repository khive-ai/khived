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

## Configuration

`khive pr` can be configured using a TOML file located at `.khive/pr.toml` in
your project root. All configuration options are optional and will use sensible
defaults if not specified.

### Configuration Options

```toml
# .khive/pr.toml

# Default base branch for PRs (default: "main")
default_base_branch = "main"

# Whether to create PRs as drafts by default (default: false)
default_to_draft = false

# Default reviewers to add to PRs
default_reviewers = ["reviewer1", "reviewer2"]

# Default assignees to add to PRs
default_assignees = ["assignee1"]

# Default labels to add to PRs
default_labels = ["label1", "label2"]

# Whether to use GitHub PR templates if available (default: true)
prefer_github_template = true

# Whether to automatically push the branch before PR creation (default: true)
auto_push_branch = true
```

### Configuration Precedence

CLI arguments override configuration file settings. For example, if
`auto_push_branch = true` is set in the configuration file, but `--no-push` is
passed as a CLI argument, the command will not push before creating the PR.

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

## JSON Output Format

When using `--json-output`, the command returns a structured JSON object with
the following fields:

```json
{
  "status": "success",
  "message": "Pull request created successfully.",
  "pr_url": "https://github.com/owner/repo/pull/123",
  "pr_number": 123,
  "pr_title": "feat: add dark mode",
  "pr_base_branch": "main",
  "pr_head_branch": "feature/dark-mode",
  "is_draft": false,
  "pr_state": "OPEN",
  "action_taken": "created"
}
```

For existing PRs, the `status` field will be `"exists"` and `action_taken` will
be `"retrieved_existing"` or `"opened_in_browser"` if `--web` was specified.

## Error Handling

`khive pr` provides detailed error messages when things go wrong:

- Missing Git or GitHub CLI tools
- Detached HEAD state
- Branch push failures
- PR creation failures
- Configuration parsing errors

## Exit Codes

- `0`: PR creation or retrieval completed successfully
- `1`: Error occurred during PR creation or retrieval

## Notes

- The command requires both `git` and `gh` CLI tools to be installed and
  available in the PATH
- The GitHub CLI (`gh`) must be authenticated with appropriate permissions
- When no PR body is provided, the command will use the last commit body or
  GitHub PR template if available
- The command supports both human-readable output and structured JSON output for
  agent consumption
