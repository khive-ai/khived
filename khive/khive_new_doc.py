#!/usr/bin/env python3
"""
khive_new_doc.py - spawn a Markdown doc from a template.

Patch 2025-04-22 ▸ **robust template resolution**
------------------------------------------------
* Fallback search chain:
  1. `--template-dir` flag (highest priority)
  2. `$KHIVE_TEMPLATE_DIR` env var
  3. `<repo-root>/docs/templates` **or** `<repo-root>/dev/docs/templates`
* Repo root is inferred from the location of this script, so it works even
  when the CLI is installed in `.venv` site-packages.
* Error message now lists all attempted paths.

(Bulk of logic unchanged; see bottom for CLI synopsis.)
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from .utils import ANSI

verbose = False


def log(msg: str, colour: str = "B"):
    if verbose:
        print(f"{ANSI[colour]}•{ANSI['N']} {msg}")


def die(msg: str):
    print(f"{ANSI['R']}✖ {msg}{ANSI['N']}", file=sys.stderr)
    sys.exit(1)


# ────────── front-matter parsing (tiny) ──────────
# Accept optional "---" noise before front-matter (some editors add it)
_FM_RE = re.compile(r"^---(?:---)?(.*?)---(.*)$", re.S)


def parse_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    m = _FM_RE.match(text)
    if not m:
        die("template missing front-matter block")
    raw, body = m.groups()
    meta: Dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip().strip('"')
    return meta, body


# ────────── data class ──────────
@dataclass
class Template:
    path: Path
    doc_type: str
    out_subdir: str
    prefix: str
    meta: Dict[str, str]
    body: str


def resolve_template(
    doc_type: str,
    template_dir_flag: Path | None = None,
) -> Template:
    """
    Locate a built‑in Markdown template and return its parsed `Template` object.

    Search precedence (first match wins)

    1. `template_dir_flag`    – `--template-dir` CLI option
    2. `$KHIVE_TEMPLATE_DIR`  – environment variable
    3. `<repo>/docs/templates`
    4. `<repo>/dev/docs/templates`

    *The repo root is inferred from the location of this file, so the function
    works whether the package is imported from source or from a wheel inside a
    virtual‑env.*

    Parameters
    ----------
    doc_type :
        Case‑insensitive acronym declared in the template’s front‑matter
        (`doc_type: CRR`, `IP`, etc.).
    template_dir_flag :
        Optional directory path supplied by the user via `--template-dir`.

    Returns
    -------
    Template
        Parsed template object ready for `create()`.

    Raises
    ------
    SystemExit
        If the template cannot be found or multiple templates collide.
    """

    # ── 1. build candidate directories (highest‑priority first) ──────────
    def _candidate_dirs():
        # 1. explicit CLI flag
        if template_dir_flag:
            yield template_dir_flag.expanduser()

        # 2. environment variable
        env_dir = os.getenv("KHIVE_TEMPLATE_DIR")
        if env_dir:
            yield Path(env_dir).expanduser()

        # 3 & 4. fallbacks relative to repo root
        here = Path(__file__).resolve()
        # find repo root: parent that contains *this* package directory
        # e.g. .../repo_root/khive/khive_new_doc.py  → repo_root
        pkg_root = next(p for p in here.parents if (p / "khive_new_doc.py").exists())
        repo_root = pkg_root.parent

        yield Path(__file__).parent / "templates"  # package‑local fallback
        yield repo_root / "docs" / "templates"
        yield repo_root / "dev" / "docs" / "templates"

    candidate_dirs = list(_candidate_dirs())

    # ── 2. discover templates in priority order ─────────────────────────
    template_map: Dict[str, Template] = {}
    for dir_ in candidate_dirs:
        found = discover([dir_])  # returns {DOC_TYPE → Template}
        for key, tpl in found.items():
            # only add if this doc_type hasn't been satisfied by higher‑priority dir
            template_map.setdefault(key.upper(), tpl)

    if verbose:
        for d in candidate_dirs:
            log(f"searched → {d}", "B")
        for k, v in template_map.items():
            log(f"resolved {k} → {v.path}", "G")

    # ── 3. validate & return ────────────────────────────────────────────
    key = doc_type.upper()
    if key not in template_map:
        attempted = "\n  • ".join(str(p) for p in candidate_dirs)
        die(
            f"Template for '{key}' not found.\n"
            "Searched (in order):\n"
            f"  • {attempted}\n"
            "Available types: " + (", ".join(sorted(template_map.keys())) or "none")
        )

    return template_map[key]


# ────────── discovery ──────────


def discover(dirs: List[Path]) -> Dict[str, Template]:
    """Walk each candidate dir **recursively** for `*_template.md`."""
    mapping: Dict[str, Template] = {}
    for dir_ in dirs:
        if not dir_.is_dir():
            continue
        log(f"searching {dir_}")
        for p in dir_.rglob("*_template.md"):
            try:
                try:
                    meta, body = parse_frontmatter(p.read_text(encoding="utf-8"))
                except SystemExit:
                    continue  # skip bad template
            except Exception as e:
                log(f"skip {p} ({e})", colour="R")
                continue
            # Derive missing keys when possible
            if "doc_type" not in meta:
                # Try to extract acronyms inside parentheses of title
                m = re.search(r"\(([A-Z]{2,})\)", meta.get("title", ""))
                if m:
                    meta["doc_type"] = m.group(1).upper()
            if "output_subdir" not in meta and "doc_type" in meta:
                meta["output_subdir"] = f"{meta['doc_type'].lower()}s"  # simple plural
            # still missing essentials?
            if not {"doc_type", "output_subdir"} <= meta.keys():
                log(f"skip {p.name}: missing doc_type/output_subdir", colour="Y")
                continue
            dt = meta["doc_type"].upper()
            mapping[dt] = Template(
                p, dt, meta["output_subdir"], meta.get("prefix", dt), meta, body
            )
    return mapping


# ────────── placeholder swap ──────────


def substitute(text: str, ident: str) -> str:
    today = dt.date.today().isoformat()
    text = text.replace("{{DATE}}", today).replace("{{IDENTIFIER}}", ident)
    for pat in ["<issue>", "<issue_id>", "<identifier>"]:
        text = re.sub(pat, ident, text, flags=re.I)
    return text


# ────────── main create fn ──────────


def create(tpl: Template, ident: str, dest_base: Path) -> Path:
    out_dir = dest_base / tpl.out_subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{tpl.prefix}-{ident}.md"
    if out_path.exists():
        die(f"file exists: {out_path}")

    content = substitute(tpl.body, ident)
    meta = {**tpl.meta, "date": dt.date.today().isoformat()}
    front = "---\n" + "\n".join(f'{k}: "{v}"' for k, v in meta.items()) + "\n---\n"
    out_path.write_text(front + content, encoding="utf-8")
    print(f"{ANSI['G']}✔ created {out_path.relative_to(Path.cwd())}{ANSI['N']}")
    return out_path


# ────────── cli ──────────


def _cli():
    global verbose
    parser = argparse.ArgumentParser(description="create doc from template")
    parser.add_argument("type", help="doc type (abbr)")
    parser.add_argument("identifier", help="issue number / slug")
    parser.add_argument(
        "--dest", type=Path, default=Path("reports"), help="output base dir"
    )
    parser.add_argument(
        "--template-dir", type=Path, help="override template dir (search root)"
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    a = parser.parse_args()
    verbose = a.verbose

    ident = a.identifier.strip().replace(" ", "-")
    if not ident:
        die("identifier must not be empty")

    tpl = resolve_template(a.type, a.template_dir)
    create(tpl, ident, a.dest.resolve())


if __name__ == "__main__":
    _cli()
