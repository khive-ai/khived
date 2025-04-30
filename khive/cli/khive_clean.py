#!/usr/bin/env python3
"""
khive clean.py - Delete a branch (local + remote) after
checking out / pulling the default branch.

CLI
---
    khive_clean.py <branch> [--dry-run]

Exit codes: 0 success · 1 error.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Final

# ───────────────────────── Colors & logging ──────────────────────────


def _ansi(code: str) -> str:
    return code if sys.stdout.isatty() and os.name != "nt" else ""


C = {
    "BLUE": _ansi("\033[1;34m"),
    "YELL": _ansi("\033[1;33m"),
    "RED": _ansi("\033[1;31m"),
    "RESET": _ansi("\033[0m"),
}


def log(msg: str) -> None:
    print(f"\n{C['BLUE']}{msg}{C['RESET']}")


def info(msg: str) -> None:
    print(f"  {msg}")


def warn(msg: str) -> None:
    print(f"{C['YELL']}⚠ {msg}{C['RESET']}", file=sys.stderr)


def die(msg: str) -> None:
    print(f"{C['RED']}❌ {msg}{C['RESET']}", file=sys.stderr) or sys.exit(1)


# ───────────────────────── Shell helpers ─────────────────────────────


def run(
    cmd: list[str] | str,
    capture: bool = False,
    check: bool = False,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Wrapper around subprocess.run with UTF-8 and shell=False by default."""
    if isinstance(cmd, str):
        shell, args = True, cmd
    else:
        shell, args = False, cmd
    return subprocess.run(
        args,
        cwd=cwd,
        shell=shell,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        check=check,
    )


def cmd_ok(name: str) -> bool:
    return shutil.which(name) is not None


# ───────────────────────── Default-branch detection ──────────────────


def detect_default_branch(repo_root: Path) -> str:
    """Return repo's default branch name or die."""
    # 1) GitHub CLI (fast, remote-authoritative)
    if cmd_ok("gh"):
        cp = run(
            ["gh", "repo", "view", "--json", "defaultBranch", "-q", ".defaultBranch"],
            capture=True,
        )
        if cp.returncode == 0 and cp.stdout.strip():
            info(f"Default branch via gh: '{cp.stdout.strip()}'")
            return cp.stdout.strip()

    # 2) git symbolic-ref of origin/HEAD
    cp = run("git symbolic-ref refs/remotes/origin/HEAD", capture=True)
    if cp.returncode == 0 and cp.stdout.strip():
        name = cp.stdout.strip().split("/")[-1]
        info(f"Default branch via origin/HEAD: '{name}'")
        return name

    # 3) common fallbacks
    for cand in ("main", "master", "develop"):
        if (
            run(
                ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{cand}"]
            ).returncode
            == 0
        ):
            info(f"Default branch fallback: '{cand}'")
            return cand

    die("Cannot determine default branch (tried gh, origin/HEAD, main/master/develop).")


# ───────────────────────── Core logic ────────────────────────────────


def clean(branch: str, repo_root: Path, dry: bool) -> None:
    default = detect_default_branch(repo_root)
    if branch == default:
        die(f"Refusing to delete the default branch '{default}'")

    # Current branch
    cp = run("git symbolic-ref --short -q HEAD", capture=True)
    if cp.returncode != 0 or not cp.stdout.strip():
        die("Could not determine current branch (detached HEAD?).")
    current = cp.stdout.strip()

    log(f"🧹 Cleaning branch '{branch}' (default = '{default}')")

    # Checkout default if needed
    if current != default:
        info(f"Checkout '{default}'")
        if not dry and run(["git", "checkout", default]).returncode:
            die(f"Failed to checkout '{default}'. Resolve conflicts first.")
    else:
        info(f"Already on '{default}'")

    # Pull latest
    info(f"Pull latest '{default}'")
    if not dry and run(["git", "pull", "origin", default]).returncode:
        warn("Pull failed - continuing anyway.")

    # Delete local
    if run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"]
    ).returncode:
        info(f"Local branch '{branch}' not present.")
    else:
        info(f"Delete local '{branch}'")
        if not dry and run(["git", "branch", "-D", branch]).returncode:
            warn("Local delete failed - may need manual intervention.")

    # Delete remote
    info(f"Delete remote '{branch}'")
    if dry:
        info("  (dry-run: skipping push)")
    else:
        pr = run(["git", "push", "origin", "--delete", branch])
        if pr.returncode == 0:
            info("  Remote branch deleted.")
        else:
            # Was it already gone?
            lr = run(["git", "ls-remote", "--exit-code", "--heads", "origin", branch])
            if lr.returncode:  # not found
                info("  Remote branch did not exist.")
            else:
                warn("Remote delete failed - permissions or protection rules?")

    log(f"✅ Branch '{branch}' cleanup done.")


# ────────────────────────── main ───────────────────────────────


def main(argv: list[str] | None = None) -> None:
    if not cmd_ok("git"):
        die("git not found in PATH.")
    parser = argparse.ArgumentParser(description="Delete a branch local+remote.")
    parser.add_argument("branch", help="Branch to delete")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show actions without executing."
    )
    args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    os.chdir(repo_root)

    clean(args.branch, repo_root, args.dry_run)


if __name__ == "__main__":
    main()
