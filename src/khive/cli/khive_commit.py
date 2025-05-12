# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
khive_commit.py - one-stop commit helper for the khive mono-repo.

Features
========
* **Conventional-Commit enforcement** with helpful error hints.
* **Auto-stage** everything (or `--patch` to pick hunks).
* **Smart skip** - exits 0 when nothing to commit (useful for CI).
* **`--amend`** flag optionally rewrites last commit instead of creating new.
* **`--no-push`** for local-only commits (default pushes to `origin <branch>`).
* **Ensures Git identity** in headless containers (sets fallback name/email).
* **Dry-run** mode prints git commands without executing.
* **Verbose** mode echoes every git command.
* **Structured input** for commit message parts (--type, --scope, --subject, etc.)
* **Search ID injection** for evidence citation
* **Interactive mode** for guided commit creation
* **JSON output** option for machine-readable results
* **Configuration** via .khive/commit.toml
* **Auto-publish branch** if not already tracking a remote.
* **Mode Indication** via `--by` flag, adding a `Committed-by:` trailer.
Synopsis
--------
```bash
khive_commit.py "feat(ui): add dark-mode toggle"           # Auto-publishes new branch if needed
khive_commit.py "fix: missing null-check" --patch --no-push
khive_commit.py "chore!: bump API to v2" --amend -v
khive_commit.py --type feat --scope ui --subject "add dark-mode toggle" --search-id pplx-abc
khive_commit.py --interactive
khive_commit.py --type feat --scope api --subject "new endpoint" --by khive-coder
```
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

# --- Project Root and Config Path ---
# This assumes the script is run from within a Git repository.
# A more robust solution might involve searching upwards for .git.
try:
    PROJECT_ROOT = Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True, stderr=subprocess.PIPE
        ).strip()
    )
except (subprocess.CalledProcessError, FileNotFoundError):
    PROJECT_ROOT = Path.cwd()  # Fallback if not in a git repo or git not found

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


def log_msg(msg: str, *, kind: str = "B") -> None:
    if verbose_mode:
        print(f"{ANSI[kind]}▶{ANSI['N']} {msg}")


def format_message_commit(prefix: str, msg: str, color_code: str) -> str:
    return f"{color_code}{prefix}{ANSI['N']} {msg}"


def info_msg(msg: str, *, console: bool = True) -> str:
    output = format_message_commit("✔", msg, ANSI["G"])
    if console:
        print(output)
    return output


def warn_msg(msg: str, *, console: bool = True) -> str:
    output = format_message_commit("⚠", msg, ANSI["Y"])
    if console:
        print(output, file=sys.stderr)
    return output


def error_msg(msg: str, *, console: bool = True) -> str:
    output = format_message_commit("✖", msg, ANSI["R"])
    if console:
        print(output, file=sys.stderr)
    return output


def die_commit(
    msg: str, json_data: dict[str, Any] | None = None, json_output_flag: bool = False
) -> None:
    error_msg(msg, console=not json_output_flag)
    if json_output_flag:
        base_data = {"status": "failure", "message": msg}
        if json_data:  # Merge if other data like SHA is available
            base_data.update(json_data)
        print(json.dumps(base_data, indent=2))
    sys.exit(1)


# --- Configuration ---
@dataclass
class CommitConfig:
    project_root: Path
    default_push: bool = True
    allow_empty_commits: bool = False
    conventional_commit_types: list[str] = field(
        default_factory=lambda: [
            "feat",
            "fix",
            "build",
            "chore",
            "ci",
            "docs",
            "perf",
            "refactor",
            "revert",
            "style",
            "test",
        ]
    )
    conventional_commit_regex_pattern: str | None = (
        None  # If user wants to override full regex
    )
    fallback_git_user_name: str = "khive-bot"
    fallback_git_user_email: str = "khive-bot@example.com"
    default_stage_mode: str = "all"  # 'all' or 'patch'

    # CLI args / internal state
    json_output: bool = False
    dry_run: bool = False
    verbose: bool = False

    @property
    def khive_config_dir(self) -> Path:
        return self.project_root / ".khive"

    @property
    def conventional_commit_regex(self) -> re.Pattern:
        if self.conventional_commit_regex_pattern:
            return re.compile(self.conventional_commit_regex_pattern)
        types_str = "|".join(map(re.escape, self.conventional_commit_types))
        # Basic Conventional Commit Regex: type(scope)!: subject
        # Allows for optional scope and breaking change indicator !
        return re.compile(rf"^(?:{types_str})(?:\([\w-]+\))?(?:!)?: .+")


def load_commit_config(
    project_r: Path, cli_args: argparse.Namespace | None = None
) -> CommitConfig:
    cfg = CommitConfig(project_root=project_r)
    config_file = cfg.khive_config_dir / "commit.toml"

    if config_file.exists():
        log_msg(f"Loading commit config from {config_file}")
        try:
            raw_toml = tomllib.loads(config_file.read_text())
            cfg.default_push = raw_toml.get("default_push", cfg.default_push)
            cfg.allow_empty_commits = raw_toml.get(
                "allow_empty_commits", cfg.allow_empty_commits
            )
            cfg.conventional_commit_types = raw_toml.get(
                "conventional_commit_types", cfg.conventional_commit_types
            )
            cfg.conventional_commit_regex_pattern = raw_toml.get(
                "conventional_commit_regex_pattern",
                cfg.conventional_commit_regex_pattern,
            )
            cfg.fallback_git_user_name = raw_toml.get(
                "fallback_git_user_name", cfg.fallback_git_user_name
            )
            cfg.fallback_git_user_email = raw_toml.get(
                "fallback_git_user_email", cfg.fallback_git_user_email
            )
            cfg.default_stage_mode = raw_toml.get(
                "default_stage_mode", cfg.default_stage_mode
            )
            if cfg.default_stage_mode not in ["all", "patch"]:
                warn_msg(
                    f"Invalid 'default_stage_mode' ('{cfg.default_stage_mode}') in config. Using 'all'."
                )
                cfg.default_stage_mode = "all"

        except Exception as e:
            warn_msg(f"Could not parse {config_file}: {e}. Using default values.")
            cfg = CommitConfig(project_root=project_r)  # Reset

    if cli_args:
        cfg.json_output = cli_args.json_output
        cfg.dry_run = cli_args.dry_run
        cfg.verbose = cli_args.verbose
        global verbose_mode
        verbose_mode = cli_args.verbose

    return cfg


# --- Git Helpers ---
def git_run(
    cmd_args: list[str],
    *,
    capture: bool = False,
    check: bool = True,
    dry_run: bool = False,
    cwd: Path,
) -> subprocess.CompletedProcess[str] | int:
    full_cmd = ["git", *cmd_args]
    # Centralized logging for dry-run / verbose for git commands
    if dry_run:
        # In dry-run mode, always inform what would be run, regardless of verbosity for this specific message
        print(f"{ANSI['B']}[DRY-RUN] Would run: git {' '.join(cmd_args)}{ANSI['N']}")
        if capture:
            return subprocess.CompletedProcess(full_cmd, 0, stdout="", stderr="")
        return 0

    log_msg(
        "git " + " ".join(cmd_args)
    )  # Log actual command if not dry_run and verbose

    try:
        process = subprocess.run(
            full_cmd, text=True, capture_output=capture, check=check, cwd=cwd
        )
        return process
    except FileNotFoundError:
        die_commit(
            "Git command not found. Is Git installed and in PATH?",
            json_output_flag=True,
        )  # Use a global or passed json_output
    except subprocess.CalledProcessError as e:
        if check:  # if check is True, CalledProcessError is raised, otherwise it's handled by return code
            error_msg(
                f"Git command failed: git {' '.join(cmd_args)}\nStderr: {e.stderr}",
                console=True,
            )
            raise  # Re-raise if check=True and caller should handle
        return e  # Return the error object if check=False so caller can inspect rc


def ensure_git_identity(config: CommitConfig) -> None:
    for key, default_val in [
        ("user.name", config.fallback_git_user_name),
        ("user.email", config.fallback_git_user_email),
    ]:
        proc = git_run(
            ["config", "--get", key],
            capture=True,
            check=False,
            dry_run=config.dry_run,
            cwd=config.project_root,
        )
        if (
            isinstance(proc, subprocess.CompletedProcess)
            and proc.returncode == 0
            and proc.stdout.strip()
        ):
            continue  # Identity already set
        log_msg(f"Git {key} not set. Setting to fallback: {default_val}")
        git_run(
            ["config", key, default_val],
            dry_run=config.dry_run,
            cwd=config.project_root,
        )


def get_current_branch(config: CommitConfig) -> str:
    if config.dry_run:
        return "feature/dry-run-branch"  # More descriptive dummy for dry run
    proc = git_run(
        ["branch", "--show-current"], capture=True, check=False, cwd=config.project_root
    )
    if (
        isinstance(proc, subprocess.CompletedProcess)
        and proc.returncode == 0
        and proc.stdout.strip()
    ):
        return proc.stdout.strip()
    # Fallback for detached HEAD or error; might need more robust handling
    head_sha_proc = git_run(
        ["rev-parse", "--short", "HEAD"],
        capture=True,
        check=True,
        cwd=config.project_root,
    )
    if isinstance(head_sha_proc, subprocess.CompletedProcess):
        return f"detached-HEAD-{head_sha_proc.stdout.strip()}"
    return "HEAD"


def stage_changes(stage_mode: str, config: CommitConfig) -> bool:
    """Returns True if changes were staged or already staged."""
    # Check if anything is unstaged first
    dirty_tree_rc = git_run(
        ["diff", "--quiet"],
        check=False,
        dry_run=config.dry_run,
        cwd=config.project_root,
    )
    is_dirty = (isinstance(dirty_tree_rc, int) and dirty_tree_rc == 1) or (
        isinstance(dirty_tree_rc, subprocess.CompletedProcess)
        and dirty_tree_rc.returncode == 1
    )

    if is_dirty:
        if stage_mode == "patch":
            info_msg(
                "Staging changes interactively ('git add -p')...",
                console=not config.json_output,
            )
            # git add -p is interactive, so it's hard to truly dry-run.
            # For dry-run, we'll just log. For real run, it will block.
            if config.dry_run:
                log_msg("[DRY-RUN] Would run 'git add -p'")
            else:
                # subprocess.run with check=False, as user might quit -p
                p_process = subprocess.run(
                    ["git", "add", "-p"], cwd=config.project_root
                )
                if p_process.returncode != 0:
                    warn_msg(
                        "Interactive staging ('git add -p') exited non-zero. Staging might be incomplete.",
                        console=not config.json_output,
                    )
        else:  # 'all'
            info_msg(
                "Staging all changes ('git add -A')...", console=not config.json_output
            )
            git_run(["add", "-A"], dry_run=config.dry_run, cwd=config.project_root)
    else:
        info_msg(
            "Working tree is clean (no unstaged changes).",
            console=not config.json_output,
        )

    # Check if anything is staged for commit
    staged_rc = git_run(
        ["diff", "--cached", "--quiet"],
        check=False,
        dry_run=config.dry_run,
        cwd=config.project_root,
    )
    has_staged_changes = (isinstance(staged_rc, int) and staged_rc == 1) or (
        isinstance(staged_rc, subprocess.CompletedProcess) and staged_rc.returncode == 1
    )

    if not has_staged_changes and is_dirty:
        info_msg(
            "No changes were staged (e.g., 'git add -p' was exited without staging).",
            console=not config.json_output,
        )
        return False
    if not has_staged_changes and not is_dirty:
        # Nothing was dirty, nothing is staged.
        return False  # No changes to commit

    return True  # Changes are staged (either newly or previously)


def build_commit_message_from_args(
    args: argparse.Namespace, config: CommitConfig
) -> str | None:
    if args.message:  # Positional message takes precedence if provided
        return args.message

    if not args.type or not args.subject:
        # Insufficient structured args for a minimal commit message.
        # Interactive mode would handle this, or error out if not interactive.
        return None

    header = args.type
    if args.scope:
        header += f"({args.scope})"
    if args.breaking_change_description:  # Or just args.breaking if it's a flag
        header += "!"
    header += f": {args.subject}"

    body_parts = []
    if args.body:
        body_parts.append(args.body)

    if args.breaking_change_description:
        body_parts.append(f"BREAKING CHANGE: {args.breaking_change_description}")

    # Append search ID and closes issues
    extra_info = []
    if args.search_id:
        extra_info.append(f"(search: {args.search_id})")  # Standardize format
    if args.closes:
        extra_info.append(f"Closes #{args.closes}")

    trailers = []
    if args.by:
        trailers.append(f"Committed-by: {args.by}")

    if extra_info:  # Add as a new paragraph in the body if body exists, or as the body
        if body_parts:
            body_parts.append("")  # Ensure separation
        body_parts.append(" ".join(extra_info))

    full_message = header
    if body_parts:
        full_message += "\n\n" + "\n".join(body_parts)

    return full_message.strip()


def interactive_commit_prompt(config: CommitConfig) -> str | None:
    info_msg(
        "Starting interactive commit message builder...", console=not config.json_output
    )
    try:
        commit_type = (
            input(
                f"Enter commit type ({', '.join(config.conventional_commit_types)}): "
            )
            .strip()
            .lower()
        )
        while commit_type not in config.conventional_commit_types:
            commit_type = (
                input(
                    f"Invalid type. Choose from ({', '.join(config.conventional_commit_types)}): "
                )
                .strip()
                .lower()
            )

        scope = input("Enter scope (optional, e.g., 'ui', 'api'): ").strip()
        subject = ""
        while not subject:
            subject = input("Enter subject (max 72 chars, imperative mood): ").strip()

        print(
            "Enter body (multi-line, press Ctrl-D or Ctrl-Z then Enter on Windows to finish):"
        )
        body_lines = []
        while True:
            try:
                line = input()
                body_lines.append(line)
            except EOFError:
                break
        body = "\n".join(body_lines).strip()

        is_breaking = (
            input("Is this a breaking change? (yes/no): ").strip().lower() == "yes"
        )
        breaking_desc = ""
        if is_breaking:
            breaking_desc = input("Describe the breaking change: ").strip()

        closes_issue = input("Issue ID this closes (e.g., 123, optional): ").strip()
        search_id = input("Search ID for evidence (e.g., pplx-abc, optional): ").strip()
        committed_by = input(
            "Committed by (mode slug, optional, e.g., khive-implementer): "
        ).strip()

        # Construct message (similar to build_commit_message_from_args)
        header = commit_type
        if scope:
            header += f"({scope})"
        if is_breaking:
            header += "!"
        header += f": {subject}"

        full_body_parts = []
        if body:
            full_body_parts.append(body)
        if breaking_desc:
            full_body_parts.append(f"BREAKING CHANGE: {breaking_desc}")

        extra_info = []
        if search_id:
            extra_info.append(f"(search: {search_id})")
        if closes_issue:
            extra_info.append(f"Closes #{closes_issue}")
        if extra_info:
            if full_body_parts:
                full_body_parts.append("")
            full_body_parts.append(" ".join(extra_info))

        final_message = header
        if full_body_parts:
            final_message += "\n\n" + "\n".join(full_body_parts)

        if committed_by:
            # Ensure a blank line before the trailer if there's any body
            if full_body_parts or "\n\n" not in final_message:
                if final_message.count("\n") >= 2 and not final_message.endswith(
                    "\n\n"
                ):
                    final_message += "\n"
                final_message += "\n"
            else:  # Header only
                final_message += "\n\n"
            final_message += f"Committed-by: {committed_by}"

        info_msg("\nConstructed commit message:", console=not config.json_output)
        if not config.json_output:
            print(final_message)
        if input("Confirm commit message? (yes/no): ").strip().lower() != "yes":
            info_msg("Commit aborted by user.", console=not config.json_output)
            return None
        return final_message.strip()

    except KeyboardInterrupt:
        info_msg(
            "\nInteractive commit aborted by user.", console=not config.json_output
        )
        return None


# --- Main Workflow ---
def _main_commit_flow(args: argparse.Namespace, config: CommitConfig) -> dict[str, Any]:
    results: dict[str, Any] = {
        "status": "failure",
        "message": "Process did not complete.",
    }

    if not shutil.which("git"):
        results["message"] = "Git command not found."
        return results

    os.chdir(config.project_root)  # Ensure we are in the project root
    ensure_git_identity(config)

    if not args.amend:
        stage_mode = args.patch_stage or config.default_stage_mode
        staged_something = stage_changes(stage_mode, config)
        if not staged_something:
            if (
                config.allow_empty_commits and args.allow_empty
            ):  # Need --allow-empty for git commit too
                info_msg(
                    "No changes staged, but proceeding with empty commit as allowed.",
                    console=not config.json_output,
                )
            else:
                results["status"] = "skipped"
                results["message"] = (
                    "Nothing to commit (working tree clean or no changes staged)."
                )
                info_msg(results["message"], console=not config.json_output)
                return results

    commit_message: str | None = None
    if args.interactive:
        commit_message = interactive_commit_prompt(config)
        if not commit_message:
            results["status"] = "skipped"
            results["message"] = "Commit aborted during interactive message creation."
            return results
    else:
        commit_message = build_commit_message_from_args(args, config)

    if not commit_message:
        results["message"] = "No commit message provided or constructed."
        if args.interactive:  # Should have been handled by interactive_commit_prompt
            results["message"] = (
                "Interactive message creation failed to produce a message."
            )
        elif not args.message:  # implies structured args were expected but insufficient
            results["message"] = (
                "Insufficient arguments to build commit message (e.g. --type and --subject required if not using positional message or --interactive)."
            )
        return results

    if not config.conventional_commit_regex.match(
        commit_message.splitlines()[0]
    ):  # Check only header
        results["message"] = (
            f"Commit message header does not follow Conventional Commits pattern: '{commit_message.splitlines()[0]}'"
        )
        results["details"] = (
            f"Expected pattern (example): {config.conventional_commit_regex.pattern}"
        )
        return results

    # Perform the commit
    commit_cmd_args = ["commit", "-m", commit_message]
    if args.amend:
        commit_cmd_args.append("--amend")
        # For amend, we might not want --allow-empty if that's how git behaves
    if (
        args.allow_empty and not args.amend
    ):  # Only add --allow-empty if requested and not amending
        commit_cmd_args.append("--allow-empty")

    commit_proc = git_run(
        commit_cmd_args,
        dry_run=config.dry_run,
        capture=True,
        check=False,
        cwd=config.project_root,
    )

    if isinstance(commit_proc, int) and commit_proc == 0:  # Dry run success
        results["commit_sha"] = "DRY_RUN_SHA"
        info_msg("Commit successful (dry run).", console=not config.json_output)
    elif (
        isinstance(commit_proc, subprocess.CompletedProcess)
        and commit_proc.returncode == 0
    ):
        # Get commit SHA
        sha_proc = git_run(
            ["rev-parse", "HEAD"],
            capture=True,
            dry_run=config.dry_run,
            cwd=config.project_root,
        )
        results["commit_sha"] = (
            sha_proc.stdout.strip()
            if isinstance(sha_proc, subprocess.CompletedProcess)
            else "UNKNOWN_SHA"
        )
        info_msg(
            f"Committed successfully. SHA: {results['commit_sha']}",
            console=not config.json_output,
        )
    else:
        stderr = (
            commit_proc.stderr
            if isinstance(commit_proc, subprocess.CompletedProcess)
            else "Unknown error"
        )
        results["message"] = f"Git commit command failed. Stderr: {stderr}"
        results["details"] = stderr
        return results

    # Handle push
    # Corrected logic for should_push_flag
    should_push_flag = args.push if args.push is not None else config.default_push

    if not should_push_flag:
        results["status"] = "success"
        results["message"] = (
            f"Commit {results.get('commit_sha', 'successful')}. Push skipped by user/config."
        )
        results["push_status"] = "SKIPPED"
        info_msg("Push skipped.", console=not config.json_output)
        return results

    current_branch = get_current_branch(config)
    push_args_final = ["push"]
    action_verb = "Pushing"
    log_suffix = ""

    if config.dry_run:
        # For dry run, informatively show the --set-upstream possibility
        push_args_final.extend(["--set-upstream", "origin", current_branch])
        action_verb = "Publishing and setting upstream for"
        log_suffix = " (dry run, -u shown for info)"
    else:
        # Actual check for existing upstream configuration for the current branch
        remote_proc = git_run(
            ["config", f"branch.{current_branch}.remote"],
            capture=True,
            check=False,
            dry_run=False,
            cwd=config.project_root,  # Internal check, not dry_run
        )
        merge_proc = git_run(
            ["config", f"branch.{current_branch}.merge"],
            capture=True,
            check=False,
            dry_run=False,
            cwd=config.project_root,  # Internal check, not dry_run
        )

        is_remote_set = (
            isinstance(remote_proc, subprocess.CompletedProcess)
            and remote_proc.returncode == 0
            and remote_proc.stdout.strip()
        )
        is_merge_set = (
            isinstance(merge_proc, subprocess.CompletedProcess)
            and merge_proc.returncode == 0
            and merge_proc.stdout.strip()
        )

        if not (is_remote_set and is_merge_set):
            push_args_final.extend(["--set-upstream", "origin", current_branch])
            action_verb = "Publishing and setting upstream for"
        else:
            push_args_final.extend(["origin", current_branch])
            # action_verb remains "Pushing"

    action_description = (
        f"{action_verb} branch '{current_branch}' to origin{log_suffix}"
    )

    # The git_run command itself will print "[DRY-RUN] Would run: git..." if dry_run is true.
    # This info_msg provides a higher-level context.
    if not config.json_output:  # Only print if not json output
        # For dry-run, this clarifies the "Would run..." message from git_run.
        # For actual run, this states the intent before execution.
        info_msg(action_description, console=True)

    push_proc = git_run(
        push_args_final,
        dry_run=config.dry_run,
        capture=True,
        check=False,
        cwd=config.project_root,
    )

    # Determine the base message for success to avoid repetition
    base_success_message_part = action_description.split(" (dry run")[
        0
    ]  # Remove dry run suffix for actual msg

    if isinstance(push_proc, int) and push_proc == 0:  # Dry run success from git_run
        results["push_status"] = "OK_DRY_RUN"
        # Message already printed by info_msg above for dry_run context
        # And git_run would have printed "Would run..."
        # We just need a confirmation it would have been successful.
        info_msg(
            f"{base_success_message_part} - successful (dry run).",
            console=not config.json_output,
        )

    elif (
        isinstance(push_proc, subprocess.CompletedProcess) and push_proc.returncode == 0
    ):  # Actual success
        results["push_status"] = "OK"
        info_msg(
            f"{base_success_message_part} - successful.", console=not config.json_output
        )
    else:  # Failure (actual or from dry_run if git_run somehow returned non-zero int for dry_run, though unlikely)
        stderr = (
            push_proc.stderr
            if isinstance(push_proc, subprocess.CompletedProcess)
            else "Unknown error during push operation"
        )
        results["push_status"] = "FAILED"

        failure_action_description = base_success_message_part.lower()
        if config.dry_run:
            failure_action_description += " (dry run)"

        results["message"] = (
            f"Commit {results.get('commit_sha', 'successful')}, but {failure_action_description} failed for branch '{current_branch}'. Stderr: {stderr}"
        )
        warn_msg(results["message"], console=not config.json_output)
        results["push_details"] = stderr
        return results

    results["status"] = "success"
    results["message"] = (
        f"Commit {results.get('commit_sha', 'successful')}. {base_success_message_part} successful"
    )
    if config.dry_run:
        results["message"] += " (dry run)."
    results["branch_pushed"] = current_branch
    return results


# --- CLI Entrypoint ---
def main() -> None:
    parser = argparse.ArgumentParser(
        description="khive Git commit helper with Conventional Commit and auto branch publishing."
    )

    # Message construction options
    group_msg = parser.add_argument_group(
        "Commit Message Construction (choose one style)"
    )
    group_msg.add_argument(
        "message",
        nargs="?",
        default=None,
        help="Full commit message (header + optional body). If used, structured flags below are ignored.",
    )
    group_struct = parser.add_argument_group(
        "Structured Commit Message Parts (used if positional 'message' is not given)"
    )
    group_struct.add_argument(
        "--type", help="Conventional commit type (e.g., feat, fix)."
    )
    group_struct.add_argument("--scope", help="Optional scope of the change.")
    group_struct.add_argument("--subject", help="Subject line of the commit.")
    group_struct.add_argument("--body", help="Detailed body of the commit message.")
    group_struct.add_argument(
        "--breaking-change-description",
        "--bc",
        help="Description of the breaking change. Implies '!' in header.",
    )
    group_struct.add_argument(
        "--closes", help="Issue number this commit closes (e.g., 123)."
    )
    group_struct.add_argument(
        "--search-id", help="Search ID for evidence (e.g., pplx-abc)."
    )
    group_struct.add_argument(
        "--by",
        help="Mode slug indicating the committer's 'persona' (e.g., khive-implementer, khive-researcher).",
    )

    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactively build commit message and stage files.",
    )

    # Staging options
    group_stage = parser.add_mutually_exclusive_group()
    group_stage.add_argument(
        "--patch-stage",
        "-p",
        action="store_const",
        const="patch",
        help="Use 'git add -p' for interactive staging. Overrides default_stage_mode.",
    )
    group_stage.add_argument(
        "--all-stage",
        "-A",
        action="store_const",
        const="all",
        dest="patch_stage",
        help="Use 'git add -A' to stage all. Overrides default_stage_mode.",
    )

    # Git command modifiers
    parser.add_argument(
        "--amend", action="store_true", help="Amend the previous commit."
    )
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Allow an empty commit (used with 'git commit --allow-empty').",
    )

    # Push control (mutually exclusive with explicit preference)
    group_push = parser.add_mutually_exclusive_group()
    group_push.add_argument(
        "--push",
        action="store_true",
        dest="push",
        default=None,
        help="Force push after commit (overrides config default_push=false).",
    )
    group_push.add_argument(
        "--no-push",
        action="store_false",
        dest="push",
        help="Prevent push after commit (overrides config default_push=true).",
    )

    # General CLI options
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
        die_commit(
            f"Project root not a directory: {args.project_root}",
            json_output_flag=args.json_output,
        )

    config = load_commit_config(args.project_root, args)

    # If interactive, staging mode might also become interactive
    if (
        args.interactive and args.patch_stage is None
    ):  # If interactive and no staging flag, prefer patch
        args.patch_stage = "patch"

    if args.message and (args.type or args.scope or args.subject or args.body):
        warn_msg(
            "Positional 'message' provided along with structured flags (--type, --scope, etc.). Positional message will be used.",
            console=not config.json_output,
        )

    if not args.interactive and not args.message and not (args.type and args.subject):
        die_commit(
            "No commit message strategy: Provide a positional message, or --type and --subject, or use --interactive.",
            json_output_flag=config.json_output,
        )

    results = _main_commit_flow(args, config)

    if config.json_output:
        print(json.dumps(results, indent=2))
    else:  # Human-readable summary already printed by _main_commit_flow and helpers
        if results["status"] == "success":
            info_msg(
                f"khive commit finished: {results.get('message', 'Success.')}",
                console=True,
            )
        elif results["status"] == "skipped":
            info_msg(
                f"khive commit skipped: {results.get('message', 'Skipped.')}",
                console=True,
            )
        # else: Error already printed by die_commit or _main_commit_flow for failures

    if results["status"] == "failure":
        sys.exit(1)


if __name__ == "__main__":
    DRY_RUN = False  # For backward compatibility
    main()
