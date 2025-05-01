#!/usr/bin/env python3
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

Synopsis
--------
```bash
khive_commit.py "feat(ui): add dark-mode toggle"
khive_commit.py "fix: missing null-check" --patch --no-push
khive_commit.py "chore!: bump API to v2" --amend -v
```
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List

ROOT = Path.cwd()
ANSI = {
    "G": "\033[32m" if sys.stdout.isatty() else "",
    "R": "\033[31m" if sys.stdout.isatty() else "",
    "Y": "\033[33m" if sys.stdout.isatty() else "",
    "B": "\033[34m" if sys.stdout.isatty() else "",
    "N": "\033[0m" if sys.stdout.isatty() else "",
}

# conventional commit pattern
types = "feat|fix|build|chore|ci|docs|perf|refactor|revert|style|test"
PAT = re.compile(rf"^(?:{types})(?:\([\w-]+\))?(?:!)?: .+")

verbose = False


def log(msg: str, *, colour: str = "B") -> None:
    print(f"{ANSI[colour]}•{ANSI['N']} {msg}") if verbose else None


def die(msg: str) -> None:
    print(f"{ANSI['R']}✖ {msg}{ANSI['N']}", file=sys.stderr)
    sys.exit(1)


# ────────── git helper ──────────


def git(
    cmd: List[str] | str, *, capture: bool = False, check: bool = True
) -> subprocess.CompletedProcess[str] | int:
    if isinstance(cmd, str):
        args = cmd.split()
    else:
        args = cmd
    log("git " + " ".join(args))
    if DRY_RUN:
        return 0
    return subprocess.run(
        ["git", *args], text=True, capture_output=capture, check=check
    )


# ────────── functions ──────────


def ensure_identity():
    fallback_name = "khive-bot"
    fallback_email = "khive-bot@example.com"
    for what, key, default in (
        ("user.name", "name", fallback_name),
        ("user.email", "email", fallback_email),
    ):
        try:
            proc = git(["config", "--get", what], capture=True, check=False)
            have = (
                proc.stdout.strip()
                if isinstance(proc, subprocess.CompletedProcess)
                else ""
            )
        except Exception:
            have = ""
        if not have:
            log(f"setting {what}={default}")
            git(["config", what, default])


def working_tree_dirty() -> bool:
    rc = git(["diff", "--quiet"], check=False)
    return (
        isinstance(rc, int)
        and rc == 1
        or isinstance(rc, subprocess.CompletedProcess)
        and rc.returncode == 1
    )


def staged_nothing() -> bool:
    rc = git(["diff", "--cached", "--quiet"], check=False)
    return (
        isinstance(rc, int)
        and rc == 0
        or isinstance(rc, subprocess.CompletedProcess)
        and rc.returncode == 0
    )


# ────────── main workflow ──────────


def _cli() -> None:
    global verbose, DRY_RUN
    ap = argparse.ArgumentParser(
        description="Commit helper with Conventional-Commit linting"
    )
    ap.add_argument("message", help="commit message (Conventional Commit)")
    ap.add_argument("--patch", action="store_true", help="use git add -p instead of -A")
    ap.add_argument(
        "--amend", action="store_true", help="amend last commit instead of creating new"
    )
    ap.add_argument("--no-push", action="store_true", help="skip pushing after commit")
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--dry-run", "-n", action="store_true")
    args = ap.parse_args()

    verbose = args.verbose
    DRY_RUN = args.dry_run

    if not PAT.match(args.message):
        die("commit message does not follow Conventional Commits")

    if not shutil.which("git"):
        die("git not found")

    # auto-detect repo root
    root = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True
    ).strip()
    os.chdir(root)

    if working_tree_dirty():
        # stage changes
        git(["add", "-p"] if args.patch else ["add", "-A"])
    else:
        print("✨ working tree clean")

    if staged_nothing():
        print("ℹ nothing to commit - exiting 0")
        return

    ensure_identity()

    commit_cmd = ["commit", "--quiet", "-m", args.message]
    if args.amend:
        commit_cmd.append("--amend")
    git(commit_cmd)
    print(f"{ANSI['G']}✔ committed{ANSI['N']}")

    if args.no_push:
        return

    # push current branch
    branch = (
        subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
        or "HEAD"
    )
    git(["push", "origin", branch])
    print(f"{ANSI['G']}✔ pushed{ANSI['N']}")


if __name__ == "__main__":
    DRY_RUN = False
    _cli()
