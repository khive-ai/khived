import argparse
import os
import pathlib
import subprocess
import sys

import yaml

ROOT = pathlib.Path.cwd()
CONF_DIRS = [
    pathlib.Path(p)
    for p in (
        os.getenv("KHIVE_CONFIG") or "",
        ".khive",
        pathlib.Path(os.getenv("XDG_CONFIG_HOME", "~/.config")).expanduser() / "khive",
    )
    if p
]


def find_file(name):
    for d in CONF_DIRS:
        f = ROOT / d / name if d.is_relative_to(ROOT) else d / name
        if f.exists():
            return f
    return None


def load_yaml(path):
    with open(path) as fh:
        return yaml.safe_load(fh) or {}


def run_pc(args):  # thin shell around pre-commit CLI
    return subprocess.call(["pre-commit", *args], cwd=ROOT)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--stack", action="append")
    ns = ap.parse_args(argv)

    # --init : create template file if missing
    if ns.init:
        tpl = find_file("pre-commit-base.yaml")
        dest = ROOT / ".pre-commit-config.yaml"
        if dest.exists():
            sys.exit("pre-commit config already present → skip")
        dest.write_text(tpl.read_text())
        sys.exit("scaffolded .pre-commit-config.yaml ✔")

    stacks_cfg = load_yaml(find_file("stacks.yaml"))
    wanted = set(ns.stack or stacks_cfg.get("stacks", {}).keys())
    hooks = [
        h
        for s in wanted
        for h in stacks_cfg["stacks"].get(s, {}).get("hooks", [])
        if stacks_cfg["stacks"][s]["enable"]
    ]

    cmd = ["run", "--all-files"]
    if ns.check:
        cmd += ["--hook-stage", "manual", "--show-diff-on-failure"]
    for h in hooks:
        cmd += ["--hook-id", h]
    sys.exit(run_pc(cmd))
