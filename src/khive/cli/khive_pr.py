# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
khive_pr.py - push branch & create GitHub PR with enhanced agent-driven workflow support.

Highlights
----------
* Auto-detects repo root, branch, default base branch (via `gh repo view`).
* If a PR already exists, prints URL (and `--web` opens browser) - **no dupes**.
* Infers title/body from last Conventional Commit; CLI overrides available.
* Supports configuration via `.khive/pr.toml` for default settings.
* Enhanced PR metadata: reviewers, assignees, labels, draft status.
* Structured JSON output for agent consumption.
* 100% std-lib; relies only on `git` & `gh` executables.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

# --- Project Root and Config Path ---
try:
    PROJECT_ROOT = Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True, stderr=subprocess.PIPE
        ).strip()
    )
except (subprocess.CalledProcessError, FileNotFoundError):
    PROJECT_ROOT = Path.cwd()

KHIVE_CONFIG_DIR = PROJECT_ROOT / ".khive"

# --- ANSI Colors and Logging ---
ANSI = {
    "G": "\033[32m" if sys.stdout.isatty() else "",
    "R": "\033[31m" if sys.stdout.isatty() else "",
    "Y": "\033[33m" if sys.stdout.isatty() else "",
    "B": "\033[34m" if sys.stdout.isatty() else "",
    "N": "\033[0m" if sys.stdout.isatty() else "",
}
verbose_mode = False


def log_msg_pr(msg: str, *, kind: str = "B") -> None:
    if verbose_mode:
        print(f"{ANSI[kind]}▶{ANSI['N']} {msg}")


def format_message_pr(prefix: str, msg: str, color_code: str) -> str:
    return f"{color_code}{prefix}{ANSI['N']} {msg}"


def info_msg_pr(msg: str, *, console: bool = True) -> str:
    output = format_message_pr("✔", msg, ANSI["G"])
    if console:
        print(output)
    return output


def warn_msg_pr(msg: str, *, console: bool = True) -> str:
    output = format_message_pr("⚠", msg, ANSI["Y"])
    if console:
        print(output, file=sys.stderr)
    return output


def error_msg_pr(msg: str, *, console: bool = True) -> str:
    output = format_message_pr("✖", msg, ANSI["R"])
    if console:
        print(output, file=sys.stderr)
    return output


def die_pr(
    msg: str, json_data: dict[str, Any] | None = None, json_output_flag: bool = False
) -> None:
    error_msg_pr(msg, console=not json_output_flag)
    if json_output_flag:
        base_data = {"status": "failure", "message": msg}
        if json_data:
            base_data.update(json_data)
        print(json.dumps(base_data, indent=2))
    sys.exit(1)


# --- Configuration ---
@dataclass
class PRConfig:
    project_root: Path
    default_base_branch: str = "main"
    default_to_draft: bool = False
    default_reviewers: list[str] = field(default_factory=list)
    default_assignees: list[str] = field(default_factory=list)
    default_labels: list[str] = field(default_factory=list)
    prefer_github_template: bool = True
    auto_push_branch: bool = True

    # CLI args / internal state
    json_output: bool = False
    dry_run: bool = False
    verbose: bool = False

    @property
    def khive_config_dir(self) -> Path:
        return self.project_root / ".khive"


def load_pr_config(
    project_r: Path, cli_args: argparse.Namespace | None = None
) -> PRConfig:
    cfg = PRConfig(project_root=project_r)
    config_file = cfg.khive_config_dir / "pr.toml"

    if config_file.exists():
        log_msg_pr(f"Loading PR config from {config_file}")
        try:
            raw_toml = tomllib.loads(config_file.read_text())
            cfg.default_base_branch = raw_toml.get(
                "default_base_branch", cfg.default_base_branch
            )
            cfg.default_to_draft = raw_toml.get(
                "default_to_draft", cfg.default_to_draft
            )
            cfg.default_reviewers = raw_toml.get(
                "default_reviewers", cfg.default_reviewers
            )
            cfg.default_assignees = raw_toml.get(
                "default_assignees", cfg.default_assignees
            )
            cfg.default_labels = raw_toml.get("default_labels", cfg.default_labels)
            cfg.prefer_github_template = raw_toml.get(
                "prefer_github_template", cfg.prefer_github_template
            )
            cfg.auto_push_branch = raw_toml.get(
                "auto_push_branch", cfg.auto_push_branch
            )
        except Exception as e:
            warn_msg_pr(f"Could not parse {config_file}: {e}. Using default values.")
            cfg = PRConfig(project_root=project_r)  # Reset

    if cli_args:
        cfg.json_output = cli_args.json_output
        cfg.dry_run = cli_args.dry_run
        cfg.verbose = cli_args.verbose
        global verbose_mode
        verbose_mode = cli_args.verbose

    return cfg


# --- Git and GH CLI Helpers ---
def cli_run(
    cmd_parts: list[str],
    *,
    capture: bool = False,
    check: bool = True,
    dry_run: bool = False,
    cwd: Path,
    tool_name: str = "cli",
) -> subprocess.CompletedProcess[str] | int:
    log_msg_pr(
        f"{tool_name} "
        + " ".join(cmd_parts[1:] if cmd_parts[0] == tool_name else cmd_parts)
    )  # Log without repeating tool_name if present
    if dry_run:
        info_msg_pr(f"[DRY-RUN] Would run: {' '.join(cmd_parts)}", console=True)
        if capture:
            return subprocess.CompletedProcess(
                cmd_parts, 0, stdout="DRY_RUN_OUTPUT", stderr=""
            )
        return 0
    try:
        process = subprocess.run(
            cmd_parts, text=True, capture_output=capture, check=check, cwd=cwd
        )
        return process
    except FileNotFoundError:
        die_pr(
            f"{cmd_parts[0]} command not found. Is it installed and in PATH?",
            json_output_flag=True,
        )  # Use global or passed flag
    except subprocess.CalledProcessError as e:
        if check:
            error_msg_pr(
                f"Command failed: {' '.join(cmd_parts)}\nStderr: {e.stderr}",
                console=True,
            )
            raise
        return e


def git_run_pr(args: list[str], **kwargs) -> subprocess.CompletedProcess[str] | int:
    return cli_run(["git", *args], tool_name="git", **kwargs)


def gh_run_pr(args: list[str], **kwargs) -> subprocess.CompletedProcess[str] | int:
    return cli_run(["gh", *args], tool_name="gh", **kwargs)


def get_current_branch_pr(config: PRConfig) -> str:
    if config.dry_run:
        return "feature/dry-run-branch"
    proc = git_run_pr(
        ["branch", "--show-current"],
        capture=True,
        check=False,
        cwd=config.project_root,
        dry_run=config.dry_run,
    )
    if isinstance(proc, subprocess.CompletedProcess) and proc.returncode == 0:
        return proc.stdout.strip() or "HEAD"  # HEAD if branch name is empty (detached)
    return "HEAD"


def get_default_base_branch_pr(config: PRConfig) -> str:
    if config.dry_run:
        return config.default_base_branch
    # Try gh first
    proc = gh_run_pr(
        ["repo", "view", "--json", "defaultBranchRef", "-q", ".defaultBranchRef.name"],
        capture=True,
        check=False,
        cwd=config.project_root,
        dry_run=config.dry_run,
    )
    if (
        isinstance(proc, subprocess.CompletedProcess)
        and proc.returncode == 0
        and proc.stdout.strip()
    ):
        return proc.stdout.strip()
    # Fallback to config then hardcoded 'main'
    return config.default_base_branch


def get_last_commit_details_pr(config: PRConfig) -> tuple[str, str]:
    if config.dry_run:
        return "Dry run commit subject", "Dry run commit body"
    proc = git_run_pr(
        ["log", "-1", "--pretty=%B"],
        capture=True,
        check=True,
        cwd=config.project_root,
        dry_run=config.dry_run,
    )  # %B is subject + body
    if isinstance(proc, subprocess.CompletedProcess):
        full_message = proc.stdout.strip()
        parts = full_message.split("\n\n", 1)
        subject = parts[0]
        body = parts[1] if len(parts) > 1 else ""
        return subject.strip(), body.strip()
    return "Error fetching commit subject", "Error fetching commit body"


def get_existing_pr_details(
    branch_name: str, config: PRConfig
) -> dict[str, Any] | None:
    if config.dry_run:
        return None  # Simulate no existing PR for dry run creation
    # Query for specific fields to keep JSON small
    json_fields = "url,number,title,baseRefName,headRefName,isDraft,state"
    proc = gh_run_pr(
        ["pr", "view", branch_name, "--json", json_fields],
        capture=True,
        check=False,
        cwd=config.project_root,
        dry_run=config.dry_run,
    )
    if isinstance(proc, subprocess.CompletedProcess) and proc.returncode == 0:
        try:
            pr_data = json.loads(proc.stdout)
            return {
                "status": "exists",
                "message": f"Pull request for branch '{branch_name}' already exists.",
                "pr_url": pr_data.get("url"),
                "pr_number": pr_data.get("number"),
                "pr_title": pr_data.get("title"),
                "pr_base_branch": pr_data.get("baseRefName"),
                "pr_head_branch": pr_data.get("headRefName"),
                "is_draft": pr_data.get("isDraft"),
                "pr_state": pr_data.get("state"),  # e.g. OPEN, MERGED, CLOSED
                "action_taken": "retrieved_existing",
            }
        except json.JSONDecodeError:
            warn_msg_pr(
                f"Could not parse JSON from 'gh pr view {branch_name}'.",
                console=not config.json_output,
            )
    return None


# --- Main Workflow ---
def _main_pr_flow(args: argparse.Namespace, config: PRConfig) -> dict[str, Any]:
    results: dict[str, Any] = {
        "status": "failure",
        "message": "PR process did not complete.",
    }

    if not shutil.which("git") or not shutil.which("gh"):
        results["message"] = "Git or GH CLI not found. Both are required."
        return results

    os.chdir(config.project_root)
    current_branch = get_current_branch_pr(config)
    if current_branch == "HEAD":  # Detached HEAD
        results["message"] = (
            "Cannot create PR from a detached HEAD. Checkout a branch first."
        )
        return results

    target_base_branch = args.base or get_default_base_branch_pr(config)

    if current_branch == target_base_branch:
        results["message"] = (
            f"Current branch ('{current_branch}') is the same as the base branch ('{target_base_branch}'). Checkout a feature branch."
        )
        return results

    # Push branch if needed
    should_push = (
        (not args.no_push) if args.no_push is not None else config.auto_push_branch
    )
    if should_push:
        info_msg_pr(
            f"Pushing current branch '{current_branch}' to origin...",
            console=not config.json_output,
        )
        push_proc = git_run_pr(
            ["push", "--set-upstream", "origin", current_branch],
            capture=True,
            check=False,
            cwd=config.project_root,
            dry_run=config.dry_run,
        )
        if not (isinstance(push_proc, int) and push_proc == 0) and not (
            isinstance(push_proc, subprocess.CompletedProcess)
            and push_proc.returncode == 0
        ):
            stderr = (
                push_proc.stderr
                if isinstance(push_proc, subprocess.CompletedProcess)
                else "Unknown push error"
            )
            results["message"] = (
                f"Failed to push branch '{current_branch}'. Error: {stderr}"
            )
            return results
        info_msg_pr(
            f"Branch '{current_branch}' pushed successfully.",
            console=not config.json_output,
        )

    # Check for existing PR
    existing_pr = get_existing_pr_details(current_branch, config)
    if existing_pr:
        info_msg_pr(
            existing_pr["message"] + f" URL: {existing_pr['pr_url']}",
            console=not config.json_output,
        )
        if args.web:
            info_msg_pr(
                f"Opening PR #{existing_pr['pr_number']} in browser...",
                console=not config.json_output,
            )
            gh_run_pr(
                ["pr", "view", str(existing_pr["pr_number"]), "--web"],
                check=False,
                cwd=config.project_root,
                dry_run=config.dry_run,
            )  # Allow fail if browser can't open
            existing_pr["action_taken"] = "opened_in_browser"
        return existing_pr

    # Construct PR Title and Body
    commit_subject, commit_body = get_last_commit_details_pr(config)
    pr_title = args.title or commit_subject or f"PR for branch {current_branch}"

    pr_body = ""
    if args.body_from_file:
        try:
            pr_body = Path(args.body_from_file).read_text()
        except OSError as e:
            warn_msg_pr(
                f"Could not read PR body from file {args.body_from_file}: {e}",
                console=not config.json_output,
            )
            pr_body = args.body or commit_body or "Pull Request Body"  # Fallback
    elif args.body:
        pr_body = args.body
    elif config.prefer_github_template:
        gh_template_path = config.project_root / ".github" / "pull_request_template.md"
        if gh_template_path.exists():
            try:
                pr_body = gh_template_path.read_text()
            except OSError:
                pass  # Ignore if not readable, fall through

    if not pr_body:  # If still empty after attempts
        pr_body = commit_body or f"Changes from branch {current_branch}."

    # Create PR command
    gh_cmd = [
        "pr",
        "create",
        "--base",
        target_base_branch,
        "--head",
        current_branch,
        "--title",
        pr_title,
    ]

    # Body handling: use temp file for `gh pr create --body-file` as it's more robust for multiline
    with tempfile.NamedTemporaryFile(
        "w+", delete=False, encoding="utf-8", dir="." if config.dry_run else None
    ) as tf:
        tf.write(pr_body)
        body_file_path = tf.name  # Get path before closing
    gh_cmd.extend(["--body-file", body_file_path])

    is_draft = args.draft if args.draft is not None else config.default_to_draft
    if is_draft:
        gh_cmd.append("--draft")

    reviewers = args.reviewer or config.default_reviewers
    if reviewers:
        gh_cmd.extend([item for r in reviewers for item in ("--reviewer", r)])

    assignees = args.assignee or config.default_assignees
    if assignees:
        gh_cmd.extend([item for a in assignees for item in ("--assignee", a)])

    labels = args.label or config.default_labels
    if labels:
        gh_cmd.extend([item for l in labels for item in ("--label", l)])

    info_msg_pr("Creating pull request...", console=not config.json_output)
    create_proc = gh_run_pr(
        gh_cmd,
        capture=True,
        check=False,
        cwd=config.project_root,
        dry_run=config.dry_run,
    )

    try:
        os.unlink(body_file_path)  # Clean up temp body file
    except OSError:
        pass  # Ignore if already gone or permission issue (esp. dry_run)

    if isinstance(create_proc, int) and create_proc == 0:  # Dry run success
        results = {
            "status": "success_dry_run",
            "message": "PR creation (dry run) successful.",
            "pr_title": pr_title,
            "pr_base_branch": target_base_branch,
            "pr_head_branch": current_branch,
            "is_draft": is_draft,
            "action_taken": "simulated_creation",
        }
    elif (
        isinstance(create_proc, subprocess.CompletedProcess)
        and create_proc.returncode == 0
    ):
        pr_url = create_proc.stdout.strip()  # gh pr create usually outputs the URL
        # To get number, we might need to view it again, or parse URL.
        # For simplicity, let's assume URL is the primary artifact.
        # A more robust way is `gh pr view <branch> --json url,number` after creation.
        # Let's try that for more details.
        created_pr_details = get_existing_pr_details(
            current_branch, config
        )  # Re-fetch to get all details
        if created_pr_details:
            created_pr_details["status"] = "success"
            created_pr_details["message"] = "Pull request created successfully."
            created_pr_details["action_taken"] = "created"
            results = created_pr_details
            info_msg_pr(
                f"PR created: {results['pr_url']}", console=not config.json_output
            )
        else:  # Should not happen if create was successful
            results = {
                "status": "success",
                "message": "PR created, but details could not be fetched.",
                "pr_url": pr_url,
                "action_taken": "created",
            }
            info_msg_pr(
                f"PR created (URL only): {pr_url}", console=not config.json_output
            )

    else:
        stderr = (
            create_proc.stderr
            if isinstance(create_proc, subprocess.CompletedProcess)
            else "Unknown PR creation error"
        )
        results["message"] = f"Failed to create PR. Error: {stderr}"
        return results

    if args.web and results.get("pr_url"):
        info_msg_pr(
            f"Opening PR {results['pr_url']} in browser...",
            console=not config.json_output,
        )
        gh_run_pr(
            ["pr", "view", results["pr_url"], "--web"],
            check=False,
            cwd=config.project_root,
            dry_run=config.dry_run,
        )
        results["action_taken"] = "created_and_opened_in_browser"

    return results


# --- CLI Entrypoint ---
def main() -> None:
    parser = argparse.ArgumentParser(description="khive Git PR helper.")

    # PR content
    parser.add_argument("--title", help="Pull request title.")
    body_group = parser.add_mutually_exclusive_group()
    body_group.add_argument("--body", help="Pull request body text.")
    body_group.add_argument(
        "--body-from-file", type=Path, help="Path to a file containing the PR body."
    )

    # PR settings
    parser.add_argument("--base", help="Base branch for the PR (e.g., main, develop).")
    parser.add_argument(
        "--draft",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Create as a draft PR. (--draft / --no-draft)",
    )

    # Assignees/Reviewers/Labels
    parser.add_argument(
        "--reviewer",
        action="append",
        help="Add a reviewer (user or team). Can be repeated.",
    )
    parser.add_argument(
        "--assignee", action="append", help="Add an assignee. Can be repeated."
    )
    parser.add_argument(
        "--label", action="append", help="Add a label. Can be repeated."
    )

    # Actions
    parser.add_argument(
        "--web",
        action="store_true",
        help="Open the PR in a web browser after creating or if it exists.",
    )
    push_group = parser.add_mutually_exclusive_group()
    push_group.add_argument(
        "--push",
        dest="no_push",
        action="store_false",
        default=None,
        help="Force push current branch before PR creation (overrides config auto_push_branch=false).",
    )
    push_group.add_argument(
        "--no-push",
        dest="no_push",
        action="store_true",
        help="Do not push branch before PR creation (overrides config auto_push_branch=true).",
    )

    # General
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Project root directory.",
    )
    parser.add_argument(
        "--json-output", action="store_true", help="Output results in JSON format."
    )
    parser.add_argument(
        "--dry-run", "-n", action="store_true", help="Show what would be done."
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging."
    )

    args = parser.parse_args()
    global verbose_mode
    verbose_mode = args.verbose

    if not args.project_root.is_dir():
        die_pr(
            f"Project root not a directory: {args.project_root}",
            json_output_flag=args.json_output,
        )

    config = load_pr_config(args.project_root, args)
    results = _main_pr_flow(args, config)

    if config.json_output:
        print(json.dumps(results, indent=2))
    # Human-readable summary is mostly handled by _main_pr_flow and helpers.
    # A final status message can be good.
    elif results.get("status") in ["success", "exists", "success_dry_run"]:
        info_msg_pr(
            f"khive pr finished: {results.get('message', 'Operation successful.')}",
            console=True,
        )
    # Failures are handled by die_pr or error messages within the flow.

    if results.get("status") == "failure":  # Check specific status string
        sys.exit(1)


if __name__ == "__main__":
    main()
