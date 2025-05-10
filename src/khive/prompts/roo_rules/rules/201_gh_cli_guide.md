---
title: "Git & GitHub CLI Quick Reference Guide"
by: "Ocean"
scope: "project"
created: "2025-05-05"
updated: "2025-05-05"
version: "1.0"
description: >
    Essential Git and GitHub (`gh`) command-line interface practices and commands
---

# khive Team: Git & GitHub CLI Quick Reference Guide

**Core Principle:** Prioritize using `git` and `gh` CLI commands for repository
interactions.

## 1. Initial Setup & Local Environment Checks

- **Check Status & Branch:**
  ```bash
  git status
  git branch
  ```
- **Check Current Directory:**
  ```bash
  pwd
  ```
- **Switch Branch:**
  ```bash
  git checkout <branch_name>
  ```
- **Update Local `main` from Remote:** (Do this often, especially before
  creating new branches)
  ```bash
  git checkout main
  git fetch origin        # Fetch remote changes without merging
  git pull origin main    # Fetch and merge (or rebase if configured) remote main into local main
  # OR (Use with caution - discards local main changes):
  # git reset --hard origin/main
  ```

## 2. Standard Feature Workflow via CLI

1. **Create Feature Branch:** (Ensure `main` is updated first)
   ```bash
   git checkout main
   # git pull origin main # (If needed)
   git checkout -b feature/<issue_id>-brief-description # e.g., feature/150-add-dark-mode
   ```
2. **(Perform Development Work...)**
3. **Local Validation (MANDATORY before commit/push):**
   ```bash
   # Run linters, formatters, tests as defined for the project
   uv run pre-commit run --all-files
   # pnpm test | cargo test | uv run pytest tests | etc.
   ```
4. **Stage Changes:**
   ```bash
   git add <specific_file>... # Stage specific files
   git add .                   # Stage all changes in current dir (use carefully)
   git add -p                  # Interactively stage changes (recommended for review)
   ```
5. **Commit Changes:** (Follow Conventional Commits - See Section 3)
   ```bash
   git commit -m "type(scope): subject" -m "Body explaining what/why. Closes #<issue_id>. search: <id>..."
   # OR use 'git commit' to open editor for longer messages
   ```
6. **Push Branch to Remote:**
   ```bash
   # First time pushing the new branch:
   git push -u origin feature/<issue_id>-brief-description
   # Subsequent pushes:
   git push
   ```
7. **Create Pull Request:**
   ```bash
   gh pr create --title "type(scope): Title (Closes #<issue_id>)" --body "Description..." --base main --head feature/<issue_id>-brief-description
   # OR use interactive mode:
   # gh pr create
   ```
8. **Monitor PR Checks:**
   ```bash
   gh pr checks <pr_number_or_branch_name>
   # Or gh pr status
   ```
9. **Checkout PR Locally (for review/testing):**
   ```bash
   gh pr checkout <pr_number>
   ```
10. **Address Review Feedback:**
    ```bash
    # Make code changes...
    # Run local validation again!
    git add <changed_files>
    git commit -m "fix(scope): address review comment xyz" -m "Detailed explanation..."
    git push
    ```
11. **Cleanup After Merge:** (PR merged by Orchestrator)
    ```bash
    git checkout main
    git pull origin main # Ensure main is updated
    git branch -d feature/<issue_id>-brief-description # Delete local branch
    git push origin --delete feature/<issue_id>-brief-description # Delete remote branch (optional)
    ```

## 3. Committing: Conventional Commits & Hygiene

- **Format:** `<type>(<scope>): <subject>` **(Mandatory)**
  - `<type>`: `feat`, `fix`, `build`, `chore`, `ci`, `docs`, `style`,
    `refactor`, `perf`, `test`.
  - `<scope>`: Optional module/area (e.g., `ui`, `api`).
  - `<subject>`: Imperative mood, brief description.
- **Body:** Use `git commit` (no `-m`) for multi-line messages. Explain _what_
  and _why_. Reference Issues (`Closes #...`) and **cite searches**
  (`search: ...`).
- **Atomicity:** One logical change per commit.
- **Clean History:** Before pushing a branch for PR or handing off, consider
  cleaning up minor fixups using interactive rebase (`git rebase -i main`). Use
  with caution, especially after pushing.

## 4. Branching Strategy via CLI

- **Create:** `git checkout -b <branch_name>` (usually from `main`).
- **Switch:** `git checkout <branch_name>`.
- **List:** `git branch` (local), `git branch -r` (remote), `git branch -a`
  (all).
- **Delete Local:** `git branch -d <branch_name>` (safe),
  `git branch -D <branch_name>` (force).
- **Delete Remote:** `git push origin --delete <branch_name>`.
- **Patch Branches:** If needed for complex fixes on an existing feature branch:
  ```bash
  git checkout feature/<issue_id>-... # Go to the feature branch
  git checkout -b feature/<issue_id>-...-patch-1 # Create patch branch
  # ...Make fixes, commit...
  git checkout feature/<issue_id>-... # Go back to the main feature branch
  git merge feature/<issue_id>-...-patch-1 # Merge the patch branch in
  git branch -d feature/<issue_id>-...-patch-1 # Delete the patch branch
  ```

## 5. Pull Requests (PRs) via `gh` CLI

- **Create:** `gh pr create` (interactive is often easiest).
- **List:** `gh pr list`.
- **View:** `gh pr view <pr_number_or_branch>`.
- **Checkout:** `gh pr checkout <pr_number>`.
- **Diff:** `gh pr diff <pr_number>`.
- **Status/Checks:** `gh pr status`, `gh pr checks <pr_number>`.
- **Comment:** `gh pr comment <pr_number> --body "..."`.
- **Review:** `gh pr review <pr_number>` (options: `--approve`,
  `--request-changes`, `--comment`).

## 6. Tooling Quick Reference Table (`git` & `gh`)

| Action                          | Recommended CLI Command(s)                                      |
| :------------------------------ | :-------------------------------------------------------------- |
| Check Status / Branch           | `git status`, `git branch`                                      |
| Switch Branch                   | `git checkout <branch>`                                         |
| Create Branch                   | `git checkout -b <new_branch>` (from current)                   |
| Update from Remote              | `git fetch origin`, `git pull origin <branch>`                  |
| Stage Changes                   | `git add <file>`, `git add .`, `git add -p` (interactive)       |
| Commit Changes                  | `git commit -m "<Conventional Commit Message>"` or `git commit` |
| Push Changes                    | `git push origin <branch>`, `git push -u origin <branch>`       |
| Create PR                       | `gh pr create`                                                  |
| Checkout PR Locally             | `gh pr checkout <pr_number>`                                    |
| View PR Status / Checks         | `gh pr status`, `gh pr checks <pr_number>`                      |
| Comment/Review PR               | `gh pr comment <pr_number>`, `gh pr review <pr_number>`         |
| List Issues / PRs               | `gh issue list`, `gh pr list`                                   |
| View Issue / PR                 | `gh issue view <id>`, `gh pr view <id>`                         |
| Delete Local Branch             | `git branch -d <branch>`                                        |
| Delete Remote Branch (Optional) | `git push origin --delete <branch>`                             |

---

**Remember:** Always run local validation before committing/pushing. Keep
commits atomic and use Conventional Commit messages. Clean up branches after
merging. Use the CLI!

---

## 7. Pull-Request Lifecycle Management

### 7.1 Draft → Ready for Review

| Action                | Command                                |
| :-------------------- | :------------------------------------- |
| Open a draft PR       | `gh pr create --draft --title "..."`   |
| Mark draft **ready**  | `gh pr ready` ([GitHub CLI][1])        |
| Convert back to draft | `gh pr ready --undo` ([GitHub CLI][1]) |

### 7.2 Keep the PR “green”

1. **Re-sync with `main` frequently**

   ```bash
   git fetch origin
   git rebase origin/main     # preferred – linear history
   # or use gh helper when conflicts are trivial
   gh pr merge --rebase --auto
   ```

   The `--rebase`, `--squash`, or plain `--merge` flags control the merge mode.
   ([GitHub CLI][2], [GitHub Docs][3])
2. **Watch CI checks until they pass**

   ````bash
   gh pr checks <pr> --watch --fail-fast
   ``` :contentReference[oaicite:3]{index=3}
   ````

### 7.3 Editing an Open PR (metadata, base, reviewers)

```bash
# Add labels, reviewers, or move to another milestone
gh pr edit <pr> --add-label bug --add-reviewer @alice --milestone "Q3 Sprint 1"
# Rename the PR
gh pr edit <pr> --title "feat(api): streaming SSE endpoint"
```

All edit flags are in the manual. ([GitHub CLI][4])

### 7.4 Merging & Auto-Merge

```bash
# Trigger an immediate merge when all required checks succeed
gh pr merge <pr> --squash --auto --subject "feat(api): SSE endpoint"
```

Choose **squash** for one commit, **merge** to keep history, or **rebase** for
linear history (team default). ([GitHub CLI][2])

---

## 8. Issue Management Workflow

### 8.1 Creating Well-Formed Issues

```bash
gh issue create \
  --title "dashboard UI: overflow on iPhone SE" \
  --body "Steps to reproduce …" \
  --label bug ui --assignee @me \
  --milestone "Q3 Sprint 1"
```

All flags support labels, assignees, milestones, and projects. ([GitHub CLI][5])

### 8.2 Listing, Filtering, and Triage

| Need                       | Command                                                                    |
| :------------------------- | :------------------------------------------------------------------------- |
| All open bugs this sprint  | `gh issue list --label bug --milestone "Q3 Sprint 1"` ([GitHub CLI][6])    |
| My closed issues last week | `gh issue list --state closed --assignee @me --since 1w` ([GitHub CLI][6]) |
| Anything unlabeled         | `gh issue list --label ""`                                                 |

GitHub’s search syntax (`state:open label:"good first issue"`) also works in CLI
or web. ([GitHub Docs][7])

### 8.3 Labels & Milestones

- Use the default **`bug` `enhancement` `documentation`** labels plus custom
  domain labels (e.g., `cli`, `api`).
- `good first issue` populates the repository’s _Contribute_ page for newcomers.
  ([GitHub Docs][8])

### 8.4 Linking PRs ↔ Issues

Include a closing keyword in PR description or commit message:

```text
Closes #42          # English
Fixes khive#108     # Cross-repo
Resolves #55
```

GitHub auto-closes the issue on merge. ([GitHub Docs][9], [GitHub Docs][10])

---

### Quick “Issue Hygiene” Checklist

| When            | Action (CLI)                                                                               |
| :-------------- | :----------------------------------------------------------------------------------------- |
| New bug arrives | `gh issue edit <id> --label bug --assignee @responsible`                                   |
| Clarify scope   | Comment asking for repro steps or log, then add `needs-info` label                         |
| Ready for work  | Add milestone + `status:accepted` label                                                    |
| Stale > 30 days | Ping assignee ➝ if no response `gh issue close <id> --comment "closing due to inactivity"` |

---

**Takeaway:** Treat PRs and Issues as **atomic, traceable work units**. Use `gh`
to create, label, edit, and merge without leaving the terminal, keep CI green
with `gh pr checks --watch`, and let closing keywords link the artifacts
automatically. This enforces clean history and transparent project tracking
while minimizing context switches.

[1]: https://cli.github.com/manual/gh_pr_ready "gh pr ready - GitHub CLI"
[2]: https://cli.github.com/manual/gh_pr_merge "gh pr merge - GitHub CLI"
[3]: https://docs.github.com/articles/about-pull-request-merges "About pull request merges - GitHub Docs"
[4]: https://cli.github.com/manual/gh_pr_edit "gh pr edit - GitHub CLI"
[5]: https://cli.github.com/manual/gh_issue_create "gh issue create - GitHub CLI"
[6]: https://cli.github.com/manual/gh_issue_list "gh issue list - GitHub CLI | Take GitHub to the command line"
[7]: https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/filtering-and-searching-issues-and-pull-requests "Filtering and searching issues and pull requests - GitHub Docs"
[8]: https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/managing-labels "Managing labels - GitHub Docs"
[9]: https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/using-keywords-in-issues-and-pull-requests "Using keywords in issues and pull requests - GitHub Docs"
[10]: https://docs.github.com/en/issues/tracking-your-work-with-issues/administering-issues/closing-an-issue "Closing an issue - GitHub Docs"
