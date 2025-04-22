#!/usr/bin/env python3
"""
Chatty CI gate for khive.

Adds dependency hints, richer failure logs, and a concise action summary.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Final, NamedTuple

# ─────────────────────────  Config  ──────────────────────────

DEFAULT_THRESHOLD: Final[int] = 80
FRONTEND_DIR, BACKEND_DIR, TEMPLATE_DIR = map(
    Path, ("apps/khive-ui", "src-tauri", "docs/templates")
)

ANSI = {
    k: v
    for k, v in dict(
        BLUE="\033[1;34m",
        YELLOW="\033[1;33m",
        RED="\033[1;31m",
        GREEN="\033[1;32m",
        RESET="\033[0m",
    ).items()
}


def c(col: str, txt: str) -> str:  # colour helper
    return f"{ANSI[col]}{txt}{ANSI['RESET']}"


def log(msg: str) -> None:
    print(f"\n{c('BLUE',  msg)}")


def info(msg: str) -> None:
    print(f"  {msg}")


def warn(msg: str) -> None:
    print(c("YELLOW", "⚠ ") + msg, file=sys.stderr)


def err(msg: str) -> None:
    print(c("RED", "❌ ") + msg, file=sys.stderr)


# ────────────────────────  utils  ────────────────────────────


def cmd_exists(tool: str) -> bool:
    return shutil.which(tool) is not None


class Coverage(NamedTuple):
    covered: int = 0
    total: int = 0

    @property
    def pct(self) -> float:
        return self.covered * 100 / self.total if self.total else 0.0


def run(
    cmd: list[str] | str, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run cmd, capture combined output, never raise."""
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        shell=isinstance(cmd, str),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def _suggest(tool: str) -> str:
    hints = {
        "pnpm": "curl -fsSL https://get.pnpm.io/install.sh | sh",
        "cargo-tarpaulin": "cargo install cargo-tarpaulin",
        "jq": "brew install jq  # or apt-get install jq",
    }
    return hints.get(tool, f"See {tool} docs")


# ───────────────────  Frontend coverage  ─────────────────────


def frontend_cov() -> tuple[Coverage, int]:
    if not FRONTEND_DIR.is_dir():
        warn(f"frontend dir {FRONTEND_DIR} missing - skipping FE tests.")
        return Coverage(), 0
    for t in ("pnpm", "jq"):
        if not cmd_exists(t):
            warn(f"tool “{t}” not found - FE coverage disabled.  → {_suggest(t)}")
            return Coverage(), 0

    cov_file = FRONTEND_DIR / "coverage/coverage-summary.json"
    shutil.rmtree(FRONTEND_DIR / "coverage", ignore_errors=True)

    info(f"→ pnpm test --coverage ({FRONTEND_DIR})")
    res = run(["pnpm", "test", "--", "--coverage", "--reporter=json-summary"])
    if res.returncode:
        warn("frontend tests non-zero exit code " + str(res.returncode))
        print(c("YELLOW", res.stdout[:2000]))  # first ~40 lines
        return Coverage(), res.returncode

    if not cov_file.exists():
        warn("coverage file not produced - check vitest config")
        return Coverage(), 0

    data = json.loads(cov_file.read_text())
    tot = data["total"]["lines"]
    return Coverage(tot["covered"], tot["total"]), 0


# ───────────────────  Backend coverage  ─────────────────────


def backend_cov() -> tuple[Coverage, int]:
    if not BACKEND_DIR.is_dir():
        warn(f"backend dir {BACKEND_DIR} missing - skipping BE tests.")
        return Coverage(), 0
    for t in ("cargo", "cargo-tarpaulin"):
        if not cmd_exists(t):
            warn(f"tool “{t}” not found - BE coverage disabled.  → {_suggest(t)}")
            return Coverage(), 0

    out_json = Path("target/tarpaulin/tarpaulin-report.json")
    out_json.parent.mkdir(parents=True, exist_ok=True)

    info("→ cargo tarpaulin (src-tauri)")
    res = run(
        "cargo tarpaulin --ignore-tests --out Json "
        "--output-dir ../../target/tarpaulin --workspace --engine llvm -- --test-threads=1",
        cwd=BACKEND_DIR,
    )
    if res.returncode:
        warn("backend tests/coverage non-zero exit code " + str(res.returncode))
        print(c("YELLOW", res.stdout[:2000]))
        return Coverage(), res.returncode

    if not out_json.exists():
        warn("tarpaulin-report.json not produced - check run")
        return Coverage(), 0

    files = json.loads(out_json.read_text())["files"]
    cov = Coverage(
        sum(f["lines_covered"] for f in files), sum(f["lines_valid"] for f in files)
    )
    return cov, 0


# ─────────────────────  Template lint  ──────────────────────
PLACEHOLDER_RE = re.compile(r"(\{\{PLACEHOLDER:[^}]+\}\})|\[Component[^]]+\]", re.I)
FORBIDDEN = [r"search_group_", r"idp-", r"roo-"]


def lint_templates() -> int:
    if not TEMPLATE_DIR.exists():
        warn("template dir missing - skip lint.")
        return 0
    bad = []
    for md in TEMPLATE_DIR.rglob("*.md"):
        if md.name.endswith("_template.md"):
            # Skip canonical templates - they contain placeholders by design
            continue
        txt = md.read_text(encoding="utf8")
        if PLACEHOLDER_RE.search(txt):
            bad.append(f"{md.relative_to(TEMPLATE_DIR)}: unreplaced placeholder")
        for pat in FORBIDDEN:
            if re.search(pat, txt, re.I):
                bad.append(f"{md.relative_to(TEMPLATE_DIR)}: forbidden pattern “{pat}”")
    if bad:
        err("template-lint failed:")
        print("\n".join("  • " + b for b in bad))
        return 1
    info("template lint passed")
    return 0


# ──────────────────────────  Main  ──────────────────────────


def ci(threshold: int, check_only: bool = False) -> int:
    mode = "quick check" if check_only else "full CI"
    log(f"🚀 khive CI ({mode}, threshold {threshold} %) - {datetime.now():%Y-%m-%d %T}")

    failures: list[str] = []

    # Always run template linting
    lint_rc = lint_templates()
    if lint_rc:
        failures.append("template lint")

    if check_only:
        # In check-only mode, we only run linters and quick checks
        log("🔍 Running quick checks only (--check flag)")

        # Check for required tools without running tests
        for tool in ["pnpm", "cargo", "jq", "cargo-tarpaulin"]:
            if not cmd_exists(tool):
                warn(f'tool "{tool}" not found - {_suggest(tool)}')

        # Add more quick checks here if needed

    else:
        # Run full test suite with coverage
        fe_cov, fe_rc = frontend_cov()
        be_cov, be_rc = backend_cov()
        total = Coverage(fe_cov.covered + be_cov.covered, fe_cov.total + be_cov.total)

        log("📊 Coverage summary")
        tbl = f"""
| Stack     | % Lines | Covered | Total | Status |
|-----------|:------:|:-------:|:-----:|:------:|
| Frontend  | {fe_cov.pct:6.2f}% | {fe_cov.covered:^7} | {fe_cov.total:^5} | {"✅" if fe_rc==0 else "❌"} |
| Backend   | {be_cov.pct:6.2f}% | {be_cov.covered:^7} | {be_cov.total:^5} | {"✅" if be_rc==0 else "❌"} |
| **All**   | **{total.pct:6.2f}%** | **{total.covered:^7}** | **{total.total:^5}** | — |"""
        print(textwrap.dedent(tbl))

        if fe_rc or be_rc:
            failures.append("tests failing")
        if total.total and total.pct < threshold:
            failures.append(f"coverage {total.pct:.2f}% < {threshold}%")

    # summary footer
    if failures:
        err("CI FAILED ➜ " + ", ".join(failures))
        for f in failures:
            print("   · " + f)
        return 1
    log(c("GREEN", "All green - good job!"))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--threshold",
        type=int,
        default=DEFAULT_THRESHOLD,
        help="combined coverage threshold (default: 80)",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="run only linters and quick checks (skip full test suite)",
    )
    args = ap.parse_args()
    if not 0 <= args.threshold <= 100:
        err("--threshold must be 0-100")
        sys.exit(2)
    sys.exit(ci(args.threshold, check_only=args.check))


if __name__ == "__main__":
    main()
