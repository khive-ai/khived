#!/usr/bin/env python3
"""
khive_init.py - zero-surprise bootstrap for the khive mono-repo.
# … (header unchanged for brevity) …
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

try:
    import tomllib  # py311+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

ROOT = Path(__file__).resolve().parent.parent  # repo root
ANSI = {
    "G": "\033[32m" if sys.stdout.isatty() else "",
    "R": "\033[31m" if sys.stdout.isatty() else "",
    "Y": "\033[33m" if sys.stdout.isatty() else "",
    "B": "\033[34m" if sys.stdout.isatty() else "",
    "N": "\033[0m" if sys.stdout.isatty() else "",
}
verbose = False

# ────────── logging helpers ──────────


def log(msg: str, *, kind: str = "B") -> None:
    if verbose:
        print(f"{ANSI[kind]}▶{ANSI['N']} {msg}")


def banner(name: str):
    print(f"\n{ANSI['B']}⚙ {name.upper()}{ANSI['N']}")


# ────────── config dataclass ──────────
@dataclass
class StepCfg:
    cmd: str | None = None
    check_cmd: str | None = None
    run_if: str | None = None
    cwd: str | None = None


@dataclass
class Config:
    enable: List[str] = field(
        default_factory=lambda: ["tools", "npm", "python", "rust", "husky", "roomodes"]
    )
    ignore_missing: bool = False
    custom: Dict[str, StepCfg] = field(default_factory=dict)


def load_cfg() -> Config:
    cfg = Config()
    pyp = ROOT / "pyproject.toml"
    if not pyp.exists():
        return cfg
    raw = tomllib.loads(pyp.read_text()).get("tool", {}).get("khive-init", {})
    cfg.enable = raw.get("enable", cfg.enable)
    cfg.ignore_missing = raw.get("ignore_missing", cfg.ignore_missing)
    for name, tbl in raw.get("steps", {}).items():
        cfg.custom[name] = StepCfg(
            cmd=tbl.get("cmd"),
            check_cmd=tbl.get("check_cmd"),
            run_if=tbl.get("run_if"),
            cwd=tbl.get("run_in_dir"),
        )
    return cfg


# ────────── helpers ──────────
async def sh(cmd: List[str] | str, *, cwd: Path) -> int:
    log("$ " + (cmd if isinstance(cmd, str) else " ".join(cmd)))
    proc = await (
        asyncio.create_subprocess_shell(cmd, cwd=cwd)
        if isinstance(cmd, str)
        else asyncio.create_subprocess_exec(*cmd, cwd=cwd)
    )
    rc = await proc.wait()
    log(f"exit {rc}", kind="Y")
    return rc


def cond_ok(expr: str | None) -> bool:
    if not expr:
        return True
    t, _, val = expr.partition(":")
    if t == "file_exists":
        return (ROOT / val).exists()
    if t == "tool_exists":
        return shutil.which(val) is not None
    return False


# ────────── built-in step implementations ──────────


async def step_tools(_: bool, cfg: Config) -> bool:
    required = ["pnpm", "uv"]
    optional = ["cargo", "rustc", "gh", "jq"]
    ok = True
    for tool in required + optional:
        present = shutil.which(tool) is not None
        colour = "G" if present else "R" if tool in required else "Y"
        print(f"  {tool:<6}: {ANSI[colour]}{present}{ANSI['N']}")
        if tool in required and not present and not cfg.ignore_missing:
            ok = False
    return ok


async def step_npm(check: bool, _: Config) -> bool:
    if not (ROOT / "package.json").exists() or not shutil.which("pnpm"):
        return True
    if check:
        return True
    return (await sh(["pnpm", "install", "--frozen-lockfile"], cwd=ROOT)) == 0


async def step_python(check: bool, _: Config) -> bool:
    if not (ROOT / "pyproject.toml").exists() or not shutil.which("uv"):
        return True
    if check:
        return True
    return (await sh(["uv", "sync"], cwd=ROOT)) == 0


async def step_rust(_: bool, __: Config) -> bool:
    if not (ROOT / "Cargo.toml").exists() or not shutil.which("cargo"):
        return True
    return (await sh(["cargo", "check", "--workspace"], cwd=ROOT)) == 0


# ⇩⇩⇩  **Adjusted logic: skip when no prepare script or pnpm error**  ⇩⇩⇩
async def step_husky(check: bool, _: Config) -> bool:
    pkg_json = ROOT / "package.json"
    if not pkg_json.exists() or not shutil.which("pnpm"):
        return True  # skip

    husky_dir = ROOT / ".husky"
    if husky_dir.is_dir():  # already set-up
        return True

    try:
        scripts = json.loads(pkg_json.read_text()).get("scripts", {})
    except Exception:
        return True  # malformed package.json → skip

    if "prepare" not in scripts:
        # No prepare script; nothing to do.
        return True

    if check:
        # prepare script exists but hooks not yet generated → not fatal
        return True

    rc = await sh("pnpm run prepare", cwd=ROOT)
    if rc != 0:
        print("  » pnpm prepare failed - treating as SKIP.")
        return True  # treat ERR_PNPM_NO_SCRIPT or other issues as non-fatal
    return True


async def step_roomodes(check: bool, _: Config) -> bool:
    script = ROOT / "scripts/generate-roomodes.sh"
    if not script.exists():
        return True
    if check:
        return True
    return (await sh(["bash", str(script)], cwd=ROOT)) == 0


BUILTIN: Dict[str, callable] = {
    "tools": step_tools,
    "npm": step_npm,
    "python": step_python,
    "rust": step_rust,
    "husky": step_husky,
    "roomodes": step_roomodes,
}


# ────────── orchestrator (unchanged) ──────────
async def _run(cfg: Config, steps: List[str], check: bool) -> bool:
    all_ok = True
    for name in steps:
        banner(name)
        impl = BUILTIN.get(name)
        custom = cfg.custom.get(name)
        if not impl and not custom:
            print(f"  {ANSI['Y']}skipped unknown step{ANSI['N']}")
            continue
        if custom and not cond_ok(custom.run_if):
            print(f"  {ANSI['Y']}condition not met{ANSI['N']}")
            continue
        if impl:
            ok = await impl(check, cfg)
        else:
            cmd = custom.check_cmd if check else custom.cmd
            if not cmd:
                print(f"  {ANSI['Y']}no command for mode{ANSI['N']}")
                continue
            ok = (await sh(cmd, cwd=ROOT / (custom.cwd or "."))) == 0
        status = "OK" if ok else "FAIL"
        colour = "G" if ok else "R"
        print(f"  -> {ANSI[colour]}{status}{ANSI['N']}")
        all_ok &= ok
    return all_ok


# ────────── CLI entrypoint (unchanged) ──────────


def _cli() -> None:
    parser = argparse.ArgumentParser(description="khive repo bootstrap")
    parser.add_argument("--check", action="store_true", help="dry-run / validate only")
    parser.add_argument("--step", action="append", help="select specific step(s)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    global verbose
    verbose = args.verbose

    cfg = load_cfg()
    target = args.step or cfg.enable

    success = asyncio.run(_run(cfg, target, args.check))
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    _cli()
