#!/usr/bin/env python3
"""
khive_cli.py - unified command-line entry-point for all khive tooling.

Install editable (+entry-point) and you can run e.g.:

    khive fmt -v               # formatter orchestrator
    khive commit "feat: ..."   # stage + commit + push
    khive pr --draft           # push & open/create PR
    khive ci --check           # chatty CI gate
    khive init                 # repo bootstrap
    khive new-doc IP 123       # create doc from template

The CLI merely dispatches to the underlying modules so there’s no duplicate
logic. Unknown flags after a sub-command are passed through untouched.
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Callable, Dict

# Map sub-command → module path (relative import)
# Resolve the package root dynamically so imports work both in-repo and when
# the package is installed site-wide.
_ROOT = __name__.split(".")[0]  # 'khive'

COMMANDS: Dict[str, str] = {
    "fmt": f"{_ROOT}.khive_fmt",
    "commit": f"{_ROOT}.khive_commit",
    "pr": f"{_ROOT}.khive_pr",
    "ci": f"{_ROOT}.khive_ci",
    "init": f"{_ROOT}.khive_init",
    "new-doc": f"{_ROOT}.khive_new_doc",
    "clean": f"{_ROOT}.khive_clean",
    "reader": f"{_ROOT}.khive_reader",
    "search": f"{_ROOT}.khive_search",
    "roo": f"{_ROOT}.khive_roo",
}


def _load(cmd: str) -> ModuleType:
    try:
        return importlib.import_module(COMMANDS[cmd])
    except KeyError:
        raise SystemExit(f"unknown command '{cmd}'. choose from {', '.join(COMMANDS)}")
    except ImportError as e:
        raise SystemExit(f"failed to import module for '{cmd}': {e}")


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv

    if not argv or argv[0] in ("-h", "--help"):
        _root_help()
        return

    cmd, *rest = argv
    mod = _load(cmd)

    # Each khive_* module already exposes a top-level main(); call it.
    import inspect

    # Prefer explicit _cli() (used by async wrappers); fallback to main()
    entry = getattr(mod, "_cli", None) or getattr(mod, "main", None)
    if entry is None:
        raise SystemExit(f"{cmd}: no callable entry-point found (_cli or main)")

    sig = inspect.signature(entry)
    if len(sig.parameters) == 0:
        # Entry-point takes no args; fake argv via sys.argv
        sys.argv = [f"khive {cmd}", *rest]
        entry()  # type: ignore[misc]
    else:
        entry(rest)  # type: ignore[arg-type] ne; no need for runpy fallback
        # Fallback: exec as script file via runpy (rarely needed)
        import importlib.util
        import runpy

        spec = importlib.util.find_spec(COMMANDS[cmd])
        if spec and spec.origin:
            sys.argv = [spec.origin, *rest]
            runpy.run_module(COMMANDS[cmd], run_name="__main__")
        else:
            raise SystemExit(
                f"cannot execute '{cmd}' - no main() and no module file found"
            )


def _root_help():
    print("khive - Swiss-army knife for the khive mono-repo\n")
    print("Usage: khive <command> [args] ...\n")
    print("Core commands:")
    for k in COMMANDS:
        print(f"  {k:<8}  →  python -m {COMMANDS[k]}")
    print("\nUse 'khive <command> -h' to see sub-command options.")


if __name__ == "__main__":
    main()
