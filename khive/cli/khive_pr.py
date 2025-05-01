#!/usr/bin/env python3
"""
khive_pr.py - push branch & open / create GitHub PR in one shot.

Highlights
----------
* Auto-detects repo root, branch, default base branch (via `gh repo view`).
* If a PR already exists, prints URL (and `--web` opens browser) - **no dupes**.
* Infers title/body from last Conventional Commit; CLI overrides available.
* `--draft`, `--no-push`, `--dry-run`, `-v` verbose.
* 100 % std-lib; relies only on `git` & `gh` executables.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List

ANSI = {
    k: (v if sys.stdout.isatty() else "")
    for k, v in {
        "G": "\033[32m",
        "R": "\033[31m",
        "B": "\033[34m",
        "N": "\033[0m",
    }.items()
}

TYPES = "feat|fix|build|chore|ci|docs|perf|refactor|revert|style|test"
PAT = re.compile(rf"^(?:{TYPES})(?:\([\w-]+\))?(?:!)?: (.+)")
verbose, DRY = False, False

# ────────── utils ──────────


def log(msg: str, colour: str = "B"):
    if verbose:
        print(f"{ANSI[colour]}•{ANSI['N']} {msg}")


def die(msg: str):
    print(f"{ANSI['R']}✖ {msg}{ANSI['N']}", file=sys.stderr)
    sys.exit(1)


def run(
    cmd: List[str] | str, *, capture=False, check=True
) -> subprocess.CompletedProcess[str] | int:
    args = cmd.split() if isinstance(cmd, str) else cmd
    log("$ " + " ".join(args))
    if DRY:
        return 0
    return subprocess.run(args, text=True, capture_output=capture, check=check)


# ────────── helper funcs ──────────


def git(args: List[str] | str, **kw):
    return run(["git", *(args.split() if isinstance(args, str) else args)], **kw)


def gh(args: List[str] | str, **kw):
    return run(["gh", *(args.split() if isinstance(args, str) else args)], **kw)


def repo_root() -> Path:
    return Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True
        ).strip()
    )


def current_branch() -> str:
    return (
        subprocess.check_output(["git", "branch", "--show-current"], text=True).strip()
        or "HEAD"
    )


def default_base() -> str:
    try:
        out = gh(
            "repo view --json defaultBranchRef -q .defaultBranchRef.name", capture=True
        )
        if isinstance(out, subprocess.CompletedProcess):
            return out.stdout.strip() or "main"
    except Exception:
        pass
    return "main"


def existing_pr(branch: str) -> str | None:
    out = gh(["pr", "view", branch, "--json", "url"], capture=True, check=False)
    if isinstance(out, subprocess.CompletedProcess) and out.returncode == 0:
        try:
            return json.loads(out.stdout)["url"]
        except Exception:
            return None
    return None


def last_commit_subject_body() -> tuple[str, str]:
    out = subprocess.check_output(["git", "log", "-1", "--pretty=%B"], text=True)
    subject, _, body = out.partition("\n\n")
    return subject.strip(), body.strip()


def temp_body(cli_body: str | None, commit_body: str | None) -> str:
    if cli_body is not None:
        return cli_body
    if commit_body:
        return commit_body
    return """## Description\n\n<replace>"""


# ────────── main ──────────


def main():
    global verbose, DRY
    p = argparse.ArgumentParser(description="create / open PR via gh")
    p.add_argument("--base")
    p.add_argument("--title")
    p.add_argument("--body")
    p.add_argument("--draft", action="store_true")
    p.add_argument(
        "--web", action="store_true", help="open PR in browser even if exists"
    )
    p.add_argument("--no-push", action="store_true")
    p.add_argument("--verbose", "-v", action="store_true")
    p.add_argument("--dry-run", "-n", action="store_true")
    a = p.parse_args()

    verbose, DRY = a.verbose, a.dry_run
    for tool, url in ("git", "https://git-scm.com"), ("gh", "https://cli.github.com"):
        if not shutil.which(tool):
            die(f"{tool} not found - install from {url}")

    root = repo_root()
    os.chdir(root)
    br = current_branch()
    base = a.base or default_base()
    if br == base:
        die("feature branch equals base; checkout another branch")

    if not a.no_push:
        git(["push", "--set-upstream", "origin", br])

    url = existing_pr(br)
    if url:
        print(f"{ANSI['G']}✔ PR exists: {url}{ANSI['N']}")
        if a.web:
            gh(["pr", "view", url, "--web"], check=False)
        return

    subj, body = last_commit_subject_body()
    conv = PAT.match(subj)
    title = a.title or (conv.group(1) if conv else subj) or "Pull Request"
    body_txt = temp_body(a.body, body)

    with tempfile.NamedTemporaryFile("w+", delete=False, encoding="utf-8") as tf:
        tf.write(body_txt)
        tf.flush()
        cmd = ["pr", "create", "--title", title, "--body-file", tf.name, "--base", base]
        if a.draft:
            cmd.append("--draft")
        gh(cmd)
        os.unlink(tf.name)


if __name__ == "__main__":
    main()
