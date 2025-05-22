# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
khive_new_doc.py - spawn a Markdown doc from a template.

Overhaul 2025-05-09 ▸ **Enhanced template handling and CLI options**
-------------------------------------------------------------------
* Configuration via `.khive/new_doc.toml`
* Enhanced template discovery across multiple locations
* Flexible placeholder substitution with custom variables
* JSON output option
* List templates option
* Dry-run option
* Force overwrite option

See CLI help for usage details.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
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
try:
    PROJECT_ROOT = Path(
        subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], text=True, stderr=subprocess.PIPE
        ).strip()
    )
except (subprocess.CalledProcessError, FileNotFoundError):
    PROJECT_ROOT = Path.cwd()

KHIVE_CONFIG_DIR = PROJECT_ROOT / ".khive"

# --- ANSI Colors and Logging (Shared) ---
ANSI = {
    "G": "\033[32m" if sys.stdout.isatty() else "",
    "R": "\033[31m" if sys.stdout.isatty() else "",
    "Y": "\033[33m" if sys.stdout.isatty() else "",
    "B": "\033[34m" if sys.stdout.isatty() else "",
    "N": "\033[0m" if sys.stdout.isatty() else "",
}
verbose_mode = False


def log_msg_doc(msg: str, *, kind: str = "B") -> None:
    if verbose_mode:
        print(f"{ANSI[kind]}▶{ANSI['N']} {msg}")


def format_message_doc(prefix: str, msg: str, color_code: str) -> str:
    return f"{color_code}{prefix}{ANSI['N']} {msg}"


def info_msg_doc(msg: str, *, console: bool = True) -> str:
    output = format_message_doc("✔", msg, ANSI["G"])
    if console:
        print(output)
    return output


def warn_msg_doc(msg: str, *, console: bool = True) -> str:
    output = format_message_doc("⚠", msg, ANSI["Y"])
    if console:
        print(output, file=sys.stderr)
    return output


def error_msg_doc(msg: str, *, console: bool = True) -> str:
    output = format_message_doc("✖", msg, ANSI["R"])
    if console:
        print(output, file=sys.stderr)
    return output


def die_doc(
    msg: str, json_data: dict[str, Any] | None = None, json_output_flag: bool = False
) -> None:
    error_msg_doc(msg, console=not json_output_flag)
    if json_output_flag:
        base_data = {"status": "failure", "message": msg}
        if json_data:
            base_data.update(json_data)
        print(json.dumps(base_data, indent=2))
    sys.exit(1)


# --- Configuration ---
@dataclass
class NewDocConfig:
    project_root: Path
    default_destination_base_dir: str = ".khive/reports"
    custom_template_dirs: list[str] = field(
        default_factory=list
    )  # Relative to project_root or absolute
    # Internal, not directly from TOML, but influences search order
    default_search_paths_relative_to_root: list[str] = field(
        default_factory=lambda: [
            "docs/templates",
            ".khive/templates",  # New standard location
            ".khive/prompts/templates",
        ]
    )
    default_vars: dict[str, str] = field(default_factory=dict)

    # CLI args / internal state
    json_output: bool = False
    dry_run: bool = False  # For new_doc, means "show path and final content"
    verbose: bool = False

    @property
    def khive_config_dir(self) -> Path:
        return self.project_root / ".khive"


def load_new_doc_config(
    project_r: Path, cli_args: argparse.Namespace | None = None
) -> NewDocConfig:
    cfg = NewDocConfig(project_root=project_r)
    config_file = cfg.khive_config_dir / "new_doc.toml"

    if config_file.exists():
        log_msg_doc(f"Loading new_doc config from {config_file}")
        try:
            raw_toml = tomllib.loads(config_file.read_text())
            cfg.default_destination_base_dir = raw_toml.get(
                "default_destination_base_dir", cfg.default_destination_base_dir
            )
            cfg.custom_template_dirs = raw_toml.get(
                "custom_template_dirs", cfg.custom_template_dirs
            )
            cfg.default_vars = raw_toml.get("default_vars", cfg.default_vars)
            # default_search_paths_relative_to_root could also be configurable if needed
        except Exception as e:
            warn_msg_doc(f"Could not parse {config_file}: {e}. Using default values.")
            cfg = NewDocConfig(project_root=project_r)  # Reset

    if cli_args:
        cfg.json_output = cli_args.json_output
        cfg.dry_run = cli_args.dry_run
        cfg.verbose = cli_args.verbose
        global verbose_mode
        verbose_mode = cli_args.verbose

    return cfg


# --- Template Data Class and Parsing ---


_FM_RE = re.compile(r"^---(?:---)?(.*?)---(.*)$", re.DOTALL)  # From original


@dataclass
class Template:
    path: Path
    doc_type: str  # Derived or from front-matter
    title: str  # From front-matter or filename
    output_subdir: str  # Derived or from front-matter
    filename_prefix: str  # Derived (e.g., doc_type) or from front-matter
    meta: dict[str, str]  # Original front-matter
    body_template: str


def parse_frontmatter(text: str, template_path: Path) -> tuple[dict[str, str], str]:
    match = _FM_RE.match(text)
    if not match:
        warn_msg_doc(
            f"Template {template_path.name} missing or has malformed front-matter. Treating as raw template.",
            console=True,
        )
        return {}, text  # Return empty meta and full text as body

    raw_fm, body = match.groups()
    meta: dict[str, str] = {}
    for line in raw_fm.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, body.strip()


# --- Template Discovery ---
def discover_templates(
    config: NewDocConfig, cli_template_dir: Path | None = None
) -> list[Template]:
    search_dirs: list[Path] = []
    if cli_template_dir:  # Highest priority
        search_dirs.append(cli_template_dir.resolve())

    for custom_dir_str in config.custom_template_dirs:
        custom_path = Path(custom_dir_str)
        search_dirs.append(
            custom_path
            if custom_path.is_absolute()
            else config.project_root / custom_path
        )

    # Env var can still be an option, but let's prioritize config file
    env_dir_str = os.getenv("KHIVE_TEMPLATE_DIR")
    if env_dir_str:
        search_dirs.append(Path(env_dir_str).expanduser().resolve())

    # Default search paths relative to project root
    for rel_path_str in config.default_search_paths_relative_to_root:
        search_dirs.append(config.project_root / rel_path_str)

    # Also search relative to the script itself (package_local fallback)
    script_dir_templates = Path(__file__).resolve().parent / "templates"
    if script_dir_templates.is_dir():
        search_dirs.append(script_dir_templates)

    log_msg_doc(
        f"Template search directories (in order of priority): {[str(p) for p in search_dirs]}"
    )

    found_templates: dict[
        Path, Template
    ] = {}  # Use path to ensure uniqueness if same template in multiple dirs
    for dir_path in search_dirs:
        if not dir_path.is_dir():
            log_msg_doc(f"Template directory not found or not a directory: {dir_path}")
            continue
        log_msg_doc(f"Searching for templates in: {dir_path}")
        for p in dir_path.rglob(
            "*.md"
        ):  # Could be configurable suffix, e.g., "*_template.md"
            if p in found_templates:
                continue  # Already found from higher priority dir
            try:
                content = p.read_text(encoding="utf-8")
                meta, body = parse_frontmatter(content, p)

                doc_type = meta.get(
                    "doc_type", p.stem.replace("_template", "").upper()
                )  # Default doc_type from filename
                title = meta.get(
                    "title", p.stem.replace("_template", "").replace("_", " ").title()
                )
                output_subdir = meta.get("output_subdir", f"{doc_type.lower()}s")
                filename_prefix = meta.get("filename_prefix", doc_type.upper())

                found_templates[p] = Template(
                    path=p,
                    doc_type=doc_type,
                    title=title,
                    output_subdir=output_subdir,
                    filename_prefix=filename_prefix,
                    meta=meta,
                    body_template=body,
                )
                log_msg_doc(f"Discovered template: {p.name} (doc_type: {doc_type})")
            except Exception as e:
                warn_msg_doc(
                    f"Skipping template {p.name} due to error: {e}",
                    console=not config.json_output,
                )

    return list(found_templates.values())


def find_template(type_or_filename: str, templates: list[Template]) -> Template | None:
    # Try matching filename first (more specific)
    for tpl in templates:
        if tpl.path.name == type_or_filename or tpl.path.stem == type_or_filename:
            return tpl
    # Then try matching doc_type (case-insensitive)
    for tpl in templates:
        if tpl.doc_type.lower() == type_or_filename.lower():
            return tpl
    return None


# --- Placeholder Substitution ---
def substitute_placeholders(
    text: str, identifier: str, custom_vars: dict[str, str]
) -> str:
    # Standard placeholders
    placeholders = {
        "DATE": dt.date.today().isoformat(),
        "IDENTIFIER": identifier,
        # For compatibility with original script's patterns
        "<issue>": identifier,
        "<issue_id>": identifier,
        "<identifier>": identifier,
    }
    # Add custom vars, allowing them to override standard ones if names clash
    placeholders.update(custom_vars)

    # Simple {{KEY}} substitution
    for key, value in placeholders.items():
        text = text.replace(f"{{{{{key}}}}}", value)  # Match {{KEY}}
        text = text.replace(f"{{{key}}}", value)  # Match {KEY} for simpler cases
        # For <key> style, they are already in placeholders if needed
        if key not in [
            "<issue>",
            "<issue_id>",
            "<identifier>",
        ]:  # Avoid double substitution for these
            text = re.sub(f"<{re.escape(key)}>", value, text, flags=re.IGNORECASE)

    # Handle special case placeholders directly
    for special_key in ["<issue>", "<issue_id>", "<identifier>"]:
        if special_key in text:
            text = text.replace(special_key, placeholders.get(special_key, ""))

    # Remove any unfulfilled {{PLACEHOLDER:...}} patterns (from common templates)
    text = re.sub(r"\{\{PLACEHOLDER:[^}]*\}\}", "", text)
    return text


# --- Main Document Creation Logic ---
def create_document(
    template: Template,
    identifier: str,  # The slug for the document, e.g., "001-my-feature"
    config: NewDocConfig,
    cli_dest_base_dir: Path | None,
    custom_vars_cli: dict[str, str],
    force_overwrite: bool,
) -> dict[str, Any]:
    # Initialize results; status will be explicitly set to "success", "error", or "success_dry_run"
    results: dict[str, Any] = {"status": "error", "message": "Operation failed"}

    # Merge default_vars from config with CLI vars (CLI takes precedence)
    final_custom_vars = {**config.default_vars, **custom_vars_cli}

    # Determine output directory and path
    base_output_dir = cli_dest_base_dir or (
        config.project_root / config.default_destination_base_dir
    )
    output_dir = base_output_dir / template.output_subdir

    # Sanitize identifier for filename (simple sanitization)
    safe_identifier = re.sub(r"[^\w\-.]", "_", identifier)
    output_filename = f"{template.filename_prefix}-{safe_identifier}.md"
    output_path = output_dir / output_filename

    # Substitute placeholders in body
    rendered_body = substitute_placeholders(
        template.body_template, identifier, final_custom_vars
    )

    # Prepare front-matter for the new document
    # Start with template's original meta, then update/add
    new_doc_meta = template.meta.copy()
    new_doc_meta["date"] = dt.date.today().isoformat()  # Standard field
    new_doc_meta["title"] = substitute_placeholders(
        new_doc_meta.get("title", identifier), identifier, final_custom_vars
    )

    # Allow custom_vars to override/set front-matter fields as well
    for k, v_raw in final_custom_vars.items():
        # Substitute placeholders within the var's value itself
        v_substituted = substitute_placeholders(
            v_raw,
            identifier,
            {
                **final_custom_vars,
                "DATE": new_doc_meta["date"],
                "IDENTIFIER": identifier,
            },
        )
        new_doc_meta[k] = v_substituted

    front_matter_lines = ["---"]
    for k, v in new_doc_meta.items():
        # Basic quoting for strings, otherwise direct value
        v_str = str(v)
        if (
            any(
                c in v_str
                for c in [
                    ":",
                    "{",
                    "}",
                    "[",
                    "]",
                    ",",
                    "&",
                    "*",
                    "#",
                    "?",
                    "|",
                    "-",
                    "<",
                    ">",
                    "=",
                    "!",
                    "%",
                    "@",
                    "`",
                ]
            )
            or " " in v_str
        ):
            v_str = v_str.replace('"', '\\"')  # Basic CSV-like quoting for safety
        front_matter_lines.append(f"{k}: {v_str}")
    front_matter_lines.append("---")
    rendered_front_matter = "\n".join(front_matter_lines)

    final_content = f"{rendered_front_matter}\n\n{rendered_body}"

    if config.dry_run:
        results["status"] = "success_dry_run"
        results["message"] = (
            f"[DRY-RUN] Would create document at: {output_path.relative_to(config.project_root)}"
        )
        results["created_file_path"] = str(output_path.relative_to(config.project_root))
        results["template_used"] = str(template.path)
        if config.verbose and not config.json_output:
            print("\n--- [DRY-RUN] Content Start ---")
            print(final_content)
            print("--- [DRY-RUN] Content End ---\n")
        return results

    if output_path.exists() and not force_overwrite:
        msg = f"Output file '{output_path.relative_to(config.project_root)}' already exists. Use --force to overwrite."
        if not config.json_output:
            error_msg_doc(msg)
        return {
            "status": "error",
            "message": msg,
            "output_path": str(output_path.relative_to(config.project_root)),
        }

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path.write_text(final_content, encoding="utf-8")
        results["status"] = "success"
        results["message"] = (
            f"Document created: {output_path.relative_to(config.project_root)}"
        )
        results["created_file_path"] = str(output_path.relative_to(config.project_root))
        results["template_used"] = str(
            template.path.relative_to(config.project_root)
            if template.path.is_relative_to(config.project_root)
            else template.path
        )
        info_msg_doc(results["message"], console=not config.json_output)
    except PermissionError as e:
        msg = f"Permission denied: Cannot create directory or write file at '{output_path}'. Details: {e}"
        results["status"] = "error"
        results["message"] = msg
        if not config.json_output:
            error_msg_doc(msg)
    except FileExistsError as e:  # Raised by mkdir if a path component is a file
        msg = f"Path conflict: A component of the destination path '{output_dir}' is a file, but a directory is needed. Details: {e}"
        results["status"] = "error"
        results["message"] = msg
        if not config.json_output:
            error_msg_doc(msg)
    except (
        NotADirectoryError
    ) as e:  # Raised if a base path component is not a directory
        msg = f"Invalid path: A component of the base destination path '{base_output_dir}' or template output subdir '{template.output_subdir}' is not a directory. Details: {e}"
        results["status"] = "error"
        results["message"] = msg
        if not config.json_output:
            error_msg_doc(msg)
    except OSError as e:  # Catch other OS-level errors related to file system
        msg = f"Filesystem error: Could not create directory or write file at '{output_path}'. Details: {e}"
        results["status"] = "error"
        results["message"] = msg
        if not config.json_output:
            error_msg_doc(msg)
    except Exception as e:  # Fallback for any other unexpected error
        msg = (
            f"An unexpected error occurred while creating document '{output_path}': {e}"
        )
        results["status"] = "error"
        results["message"] = msg
        if not config.json_output:
            error_msg_doc(msg)

    return results


# --- CLI Entrypoint ---
def main() -> None:
    parser = argparse.ArgumentParser(
        description="khive document scaffolder from templates."
    )

    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        "type_or_template_name",
        nargs="?",
        help="Document type (e.g., 'CRR', 'TDS') or template filename (e.g., 'RR_template.md'). Used with 'identifier'.",
    )
    action_group.add_argument(
        "--list-templates", action="store_true", help="List all discoverable templates."
    )

    parser.add_argument(
        "identifier",
        nargs="?",
        help="Identifier/slug for the new document (e.g., '001-new-api'). Required if not --list-templates.",
    )

    parser.add_argument(
        "--dest",
        type=Path,
        help="Output base directory (overrides config default_destination_base_dir).",
    )
    parser.add_argument(
        "--template-dir",
        type=Path,
        help="Additional directory to search for templates (highest priority).",
    )
    parser.add_argument(
        "--var",
        action="append",
        metavar="KEY=VALUE",
        help='Set custom variables for template substitution (e.g., --var title="My Title" --var author=Me). Can be repeated.',
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite output file if it already exists.",
    )

    # General
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
        die_doc(
            f"Project root not a directory: {args.project_root}",
            json_output_flag=args.json_output,
        )

    config = load_new_doc_config(args.project_root, args)

    # --- Action: List Templates ---
    if args.list_templates:
        templates = discover_templates(config, args.template_dir)
        if not templates:
            info_msg_doc(
                "No templates found in configured/default search paths.",
                console=not config.json_output,
            )
            if config.json_output:
                print(json.dumps({"status": "success", "templates": []}, indent=2))
            return

        output_templates = []
        if not config.json_output:
            print("Available templates:")
        for tpl in sorted(templates, key=lambda t: (t.doc_type, t.path.name)):
            rel_path = (
                tpl.path.relative_to(config.project_root)
                if tpl.path.is_relative_to(config.project_root)
                else tpl.path
            )
            if not config.json_output:
                print(f"  - Type/Alias: {ANSI['Y']}{tpl.doc_type}{ANSI['N']}")
                print(f"    File: {tpl.path.name} (Title: '{tpl.title}')")
                print(f"    Path: {rel_path}")
                print(
                    f"    Output Subdir: {tpl.output_subdir}, Filename Prefix: {tpl.filename_prefix}"
                )
            output_templates.append({
                "doc_type": tpl.doc_type,
                "title": tpl.title,
                "filename": tpl.path.name,
                "path": str(rel_path),
                "output_subdir": tpl.output_subdir,
                "filename_prefix": tpl.filename_prefix,
            })
        if config.json_output:
            print(
                json.dumps(
                    {"status": "success", "templates": output_templates}, indent=2
                )
            )
        return

    # --- Action: Create Document ---
    if not args.type_or_template_name or not args.identifier:
        parser.error(
            "Both 'type_or_template_name' and 'identifier' are required unless --list-templates is used."
        )

    custom_vars_cli: dict[str, str] = {}
    if args.var:
        for item in args.var:
            if "=" not in item:
                warn_msg_doc(
                    f"Ignoring malformed --var '{item}'. Expected KEY=VALUE format.",
                    console=not config.json_output,
                )
                continue
            key, value = item.split("=", 1)
            custom_vars_cli[key.strip()] = value.strip()

    all_templates = discover_templates(config, args.template_dir)
    if not all_templates:
        die_doc(
            "No templates found. Cannot create document.",
            json_output_flag=config.json_output,
        )

    selected_template = find_template(args.type_or_template_name, all_templates)
    if not selected_template:
        available_types = sorted(
            list({t.doc_type for t in all_templates if t.doc_type})
        )
        available_files = sorted(list({t.path.name for t in all_templates}))
        msg = (
            f"Template '{args.type_or_template_name}' not found.\n"
            f"  Available doc_types: {', '.join(available_types) or 'None'}\n"
            f"  Available filenames: {', '.join(available_files) or 'None'}"
        )
        die_doc(msg, json_output_flag=config.json_output)

    results = create_document(
        selected_template,
        args.identifier.strip().replace(" ", "-"),
        config,
        args.dest,
        custom_vars_cli,
        args.force,
    )

    if config.json_output:
        print(json.dumps(results, indent=2))
    # Human-readable error messages for non-JSON mode are now handled
    # within create_document (for its specific errors) or by die_doc (for earlier CLI errors).
    # create_document calls info_msg_doc on success.

    # Exit with error code if status indicates failure/error
    # Note: die_doc exits on its own. This handles results from create_document.
    if results.get("status") not in ["success", "success_dry_run"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
