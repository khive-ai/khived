#!/usr/bin/env python3
"""
khive_fmt.py - Lean, fast, developer-friendly formatter orchestrator **with tasteful logging**.

Supported stacks (built-ins):
  • python   → ruff + black
  • docs     → deno fmt for *.md/*.mdx
  • rust     → cargo fmt
  • deno     → deno fmt for *.ts/tsx/jsx/json

Highlights
----------
* `--verbose / -v` flag prints each command before execution and shows exit-codes.
* Per-stack banner summarises how many files were matched and the action taken.
* Colourised OK / FAIL table remains concise for CI logs.
* Still **zero optional deps** - colours are simple ANSI sequences.

Usage::
  khive_fmt.py            # fix-in-place serial
  khive_fmt.py --check    # parallel read-only
  khive_fmt.py -v --check --stack python

Add a console-script if you want `khive fmt` on `$PATH`:

```toml
[project.scripts]
khive fmt = "khive_fmt:main"
```
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Coroutine, Dict, List

from .utils import ANSI

try:
    import tomllib  # py311+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

ROOT = Path.cwd()


verbose = False  # set from CLI


def log(msg: str) -> None:
    if verbose:
        print(f"{ANSI['B']}▶{ANSI['N']} {msg}")


# ────────── Models & Config ──────────
@dataclass
class StackCfg:
    cmd: str | None = None
    check_cmd: str | None = None
    include: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)


@dataclass
class Cfg:
    enable: List[str] = field(
        default_factory=lambda: ["python", "docs", "rust", "deno"]
    )
    stacks: Dict[str, StackCfg] = field(default_factory=dict)


def load_cfg() -> Cfg:
    cfg = Cfg()
    pyproj = ROOT / "pyproject.toml"
    if not pyproj.exists():
        return cfg
    data = tomllib.loads(pyproj.read_text())
    raw = data.get("tool", {}).get("khive-fmt", {})
    cfg.enable = raw.get("enable", cfg.enable)
    for name, tbl in raw.get("stacks", {}).items():
        cfg.stacks[name] = StackCfg(
            cmd=tbl.get("cmd"),
            check_cmd=tbl.get("check_cmd"),
            include=tbl.get("include", []),
            exclude=tbl.get("exclude", []),
        )
    return cfg


# ────────── Helpers ──────────
async def _run(cmd: List[str], *, cwd: Path) -> int:
    log("$ " + " ".join(cmd))
    proc = await asyncio.create_subprocess_exec(*[c for c in cmd if c], cwd=cwd)
    rc = await proc.wait()
    log(f"exit {rc}")
    return rc or 0


def _match(path: Path, patterns: List[str]) -> bool:
    return any(path.match(p) for p in patterns) if patterns else True


def _select_files(include: List[str], exclude: List[str]) -> List[Path]:
    selected: List[Path] = []
    for pat in include or ["**/*"]:
        for p in ROOT.glob(pat):
            if p.is_file() and _match(p, include) and not _match(p, exclude):
                selected.append(p)
    return selected


# ────────── Stack implementations ──────────
async def _banner(name: str, files: List[str], check: bool) -> None:
    action = "CHECK" if check else "FIX  "
    log(f"[{name.upper():6}] {action} → {len(files)} file(s)")


async def python_stack(check: bool, cfg: StackCfg) -> int:
    files = [
        str(p)
        for p in _select_files(cfg.include or ["**/*.py", "**/*.pyi"], cfg.exclude)
    ]
    if not files:
        return 0
    await _banner("python", files, check)
    ruff_cmd = ["ruff", "check"] + (["--fix"] if not check else []) + files
    if await _run(ruff_cmd, cwd=ROOT):
        return 1 if check else 0
    black_cmd = ["black"] + (["--check"] if check else []) + files
    return await _run(black_cmd, cwd=ROOT)


async def docs_stack(check: bool, cfg: StackCfg) -> int:
    files = [
        str(p)
        for p in _select_files(cfg.include or ["**/*.md", "**/*.mdx"], cfg.exclude)
    ]
    if not files:
        return 0
    await _banner("docs", files, check)
    cmd = ["deno", "fmt"] + (["--check"] if check else []) + files
    return await _run(cmd, cwd=ROOT)


async def rust_stack(check: bool, _cfg: StackCfg) -> int:
    if not (ROOT / "Cargo.toml").exists():
        return 0
    await _banner("rust", ["workspace"], check)
    cmd = ["cargo", "fmt"] + (["--", "--check"] if check else [])
    return await _run(cmd, cwd=ROOT)


async def deno_stack(check: bool, cfg: StackCfg) -> int:
    files = [
        str(p)
        for p in _select_files(
            cfg.include or ["**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx", "**/*.json"],
            cfg.exclude,
        )
    ]
    if not files:
        return 0
    await _banner("deno", files, check)
    cmd = ["deno", "fmt"] + (["--check"] if check else []) + files
    return await _run(cmd, cwd=ROOT)


# Map names → coroutine
BUILTINS: Dict[str, Callable[[bool, StackCfg], Coroutine[None, None, int]]] = {
    "python": python_stack,
    "docs": docs_stack,
    "rust": rust_stack,
    "deno": deno_stack,
}


# ────────── Orchestrator ──────────
async def _main(argv: list[str] | None = None) -> None:
    global verbose
    ap = argparse.ArgumentParser(description="Run khive formatters")
    ap.add_argument("--check", action="store_true", help="Validate only, no changes")
    ap.add_argument("--stack", action="append", help="Run specific stack(s)")
    ap.add_argument(
        "--verbose", "-v", action="store_true", help="Show commands and details"
    )
    args = ap.parse_args(argv)

    verbose = args.verbose or bool(os.environ.get("KHIVE_FMT_VERBOSE"))

    cfg = load_cfg()
    stacks = args.stack or cfg.enable

    results: Dict[str, int] = {}

    if args.check:
        coros = [
            BUILTINS.get(s, lambda *_: 0)(True, cfg.stacks.get(s, StackCfg()))
            for s in stacks
        ]
        for name, coro in zip(stacks, asyncio.as_completed(coros)):
            results[name] = await coro
    else:
        for s in stacks:
            impl = BUILTINS.get(s)
            if not impl:
                results[s] = 0
                continue
            rc = await impl(False, cfg.stacks.get(s, StackCfg()))
            results[s] = rc
            if rc:
                break  # fail-fast

    # summary table
    for n, rc in results.items():
        colour = ANSI["R"] if rc else ANSI["G"]
        print(f"{n:<8} : {colour}{'FAIL' if rc else 'OK'}{ANSI['N']}")

    if any(rc for rc in results.values()):
        sys.exit(1)


# ────────── CLI entrypoint ──────────


def main() -> None:  # used by console_scripts
    """Sync shim for entry-points (khive fmt)."""
    asyncio.run(_main())


if __name__ == "__main__":
    main()
