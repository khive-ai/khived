# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
from collections import OrderedDict
from collections import OrderedDict as OrderedDictType
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib  # py311+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore
try:
    import toml  # For writing TOML if needed for default config
except ModuleNotFoundError:  # pragma: no cover
    toml = None  # Fallback if toml write not available / needed

# Project root detection (simple CWD, can be enhanced)
PROJECT_ROOT_FALLBACK = Path.cwd()

ANSI = {
    "G": "\033[32m" if sys.stdout.isatty() else "",
    "R": "\033[31m" if sys.stdout.isatty() else "",
    "Y": "\033[33m" if sys.stdout.isatty() else "",
    "B": "\033[34m" if sys.stdout.isatty() else "",
    "N": "\033[0m" if sys.stdout.isatty() else "",
}
verbose_mode = False  # Global for simple verbose logging


# ────────── logging helpers ──────────
def log(msg: str, *, kind: str = "B") -> None:
    if verbose_mode:
        print(f"{ANSI[kind]}▶{ANSI['N']} {msg}")


def format_message(prefix: str, msg: str, color_code: str) -> str:
    return f"{color_code}{prefix}{ANSI['N']} {msg}"


def info(msg: str, *, console: bool = True) -> str:
    output = format_message("✔", msg, ANSI["G"])
    if console:
        print(output)
    return output


def warn(msg: str, *, console: bool = True) -> str:
    output = format_message("⚠", msg, ANSI["Y"])
    if console:
        print(output, file=sys.stderr)
    return output


def error(msg: str, *, console: bool = True) -> str:
    output = format_message("✖", msg, ANSI["R"])
    if console:
        print(output, file=sys.stderr)
    return output


def die(
    msg: str,
    results_list: list[dict[str, Any]] | None = None,
    json_output: bool = False,
    project_root_for_log: Path = PROJECT_ROOT_FALLBACK,
) -> None:
    # Use project_root_for_log if available, otherwise global PROJECT_ROOT_FALLBACK
    # This helps if PROJECT_ROOT hasn't been fully established in config yet
    final_message = error(msg, console=not json_output)
    if json_output:
        if results_list is None:
            results_list = []
        # Ensure message is just the string, not ANSI formatted for JSON
        plain_msg = msg.replace(ANSI["R"], "").replace(ANSI["N"], "").replace("✖ ", "")
        results_list.append({
            "name": "critical_error",
            "status": "FAILED",
            "message": plain_msg,
        })
        print(json.dumps({"status": "failure", "steps": results_list}, indent=2))
    sys.exit(1)


def banner(name: str, console: bool = True) -> str:
    output = f"\n{ANSI['B']}⚙ {name.upper()}{ANSI['N']}"
    if console:
        print(output)
    return output


# ────────── config dataclass ──────────
@dataclass
class CustomStepCfg:
    cmd: str | None = None
    run_if: str | None = None
    cwd: str | None = None  # Relative to project_root


@dataclass
class InitConfig:
    project_root: Path
    ignore_missing_optional_tools: bool = False
    disable_auto_stacks: list[str] = field(default_factory=list)
    force_enable_steps: list[str] = field(default_factory=list)
    custom_steps: dict[str, CustomStepCfg] = field(default_factory=dict)
    json_output: bool = False
    dry_run: bool = False
    steps_to_run_explicitly: list[str] | None = None
    verbose: bool = False  # Added for verbosity control
    stack: str | None = None  # Specific stack to initialize
    extra: str | None = None  # Extra dependencies to include

    @property
    def khive_config_dir(self) -> Path:
        return self.project_root / ".khive"


def _generate_default_init_toml(config_file: Path, project_root: Path) -> None:
    if config_file.exists():
        return
    content_lines = [
        "# khive init configuration",
        "ignore_missing_optional_tools = false",
        "",
        '# Stacks to disable even if auto-detected (e.g., \\"python\\", \\"npm\\", \\"rust\\")',
        "disable_auto_stacks = []",
        "",
        '# Steps to force enable (e.g., \\"tools\\", \\"husky\\", or stacks like \\"python\\")',
        "force_enable_steps = []",
        "",
        "# Custom steps (example)",
        "#[custom_steps.example_custom_build]",
        '#cmd = \\"echo Hello from khive custom step\\"',
        '#run_if = \\"file_exists:pyproject.toml\\" # Condition to run this step',
        '#cwd = \\".\\" # Working directory relative to project root',
    ]
    try:
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("\n".join(content_lines) + "\n")
        info(
            f"Generated default config: {config_file.relative_to(project_root)}",
            console=True,
        )
    except OSError as e:
        warn(f"Could not write default config to {config_file}: {e}", console=True)


def load_init_config(
    project_r: Path, cli_args: argparse.Namespace | None = None
) -> InitConfig:
    cfg = InitConfig(project_root=project_r)  # Start with dataclass defaults
    config_file = cfg.khive_config_dir / "init.toml"

    if not config_file.exists() and not (
        cli_args and cli_args.dry_run
    ):  # Don't generate config in dry run
        _generate_default_init_toml(config_file, project_r)

    if config_file.exists():
        log(f"Loading init config from {config_file}")
        try:
            raw_toml = tomllib.loads(config_file.read_text())
            cfg.ignore_missing_optional_tools = raw_toml.get(
                "ignore_missing_optional_tools", cfg.ignore_missing_optional_tools
            )
            cfg.disable_auto_stacks = raw_toml.get("disable_auto_stacks", [])
            if not isinstance(cfg.disable_auto_stacks, list):
                warn(
                    f"Config 'disable_auto_stacks' in {config_file} is not a list. Using default.",
                    console=True,
                )
                cfg.disable_auto_stacks = []
            cfg.force_enable_steps = raw_toml.get("force_enable_steps", [])
            if not isinstance(cfg.force_enable_steps, list):
                warn(
                    f"Config 'force_enable_steps' in {config_file} is not a list. Using default.",
                    console=True,
                )
                cfg.force_enable_steps = []

            for name, tbl in raw_toml.get("custom_steps", {}).items():
                cfg.custom_steps[name] = CustomStepCfg(
                    cmd=tbl.get("cmd"), run_if=tbl.get("run_if"), cwd=tbl.get("cwd")
                )
        except Exception as e:
            warn(
                f"Could not parse {config_file}: {e}. Using default values.",
                console=True,
            )
            cfg = InitConfig(project_root=project_r)  # Reset to ensure clean defaults

    # Override with CLI args if provided
    if cli_args:
        cfg.json_output = cli_args.json_output
        cfg.dry_run = cli_args.dry_run
        cfg.steps_to_run_explicitly = cli_args.step
        cfg.verbose = cli_args.verbose
        cfg.stack = cli_args.stack
        cfg.extra = cli_args.extra
        global verbose_mode
        verbose_mode = cli_args.verbose

    return cfg


# ────────── Shell execution helper ──────────
async def sh(
    cmd_list: list[str] | str,
    *,
    cwd: Path,
    step_name: str = "shell_command",
    console: bool = True,
) -> dict[str, Any]:
    cmd_str = " ".join(cmd_list) if isinstance(cmd_list, list) else cmd_list
    log(f"[{step_name}] $ {cmd_str} (in {cwd})")

    process = await (
        asyncio.create_subprocess_shell(
            cmd_str, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if isinstance(cmd_str, str)
        else asyncio.create_subprocess_exec(
            *cmd_list, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    )
    stdout_bytes, stderr_bytes = await process.communicate()
    rc = process.returncode

    stdout = stdout_bytes.decode(errors="replace").strip()
    stderr = stderr_bytes.decode(errors="replace").strip()

    status = "OK" if rc == 0 else "FAILED"
    message = f"Command '{cmd_str}' {'successful' if status == 'OK' else f'failed (exit code {rc})'}."
    if stderr and status == "FAILED":
        message += f" Stderr: {stderr}"

    log(f"[{step_name}] exit {rc} ({status})", kind="Y" if status == "OK" else "R")
    if verbose_mode and stdout and console:
        print(f"  stdout: {stdout}")
    if stderr and status == "FAILED" and console:
        print(format_message("  stderr:", stderr, ANSI["R"]))

    return {
        "name": step_name,
        "status": status,
        "return_code": rc,
        "command": cmd_str,
        "stdout": stdout,
        "stderr": stderr,
        "message": message,
    }


# ────────── Condition checker for run_if ──────────
def cond_ok(expr: str | None, project_root: Path, console: bool = True) -> bool:
    if not expr:
        return True
    try:
        t, _, val = expr.partition(":")
        if t == "file_exists":
            return (project_root / val).exists()
        if t == "tool_exists":
            return shutil.which(val) is not None
        warn(f"Unknown run_if condition type: {t}", console=console)
        return False
    except Exception as e:
        warn(f"Error evaluating run_if '{expr}': {e}", console=console)
        return False


# ────────── Built-in Step Implementations ──────────
# Each step should be an async function: async def step_name(config: InitConfig) -> Dict[str, Any]:
# It should return a dictionary compatible with the 'sh' function's output for consistency.


async def step_tools(config: InitConfig) -> dict[str, Any]:
    step_name = "tools"
    messages = []
    overall_status = "OK"

    project_has_python = (
        config.project_root / "pyproject.toml"
    ).exists() and "python" not in config.disable_auto_stacks
    project_has_npm = (
        config.project_root / "package.json"
    ).exists() and "npm" not in config.disable_auto_stacks
    project_has_rust = (
        config.project_root / "Cargo.toml"
    ).exists() and "rust" not in config.disable_auto_stacks

    required_tools: list[tuple[str, str]] = []  # (tool_name, purpose)
    if project_has_python:
        required_tools.append(("uv", "Python environment/package management"))
    if project_has_npm:
        required_tools.append(("pnpm", "Node package management"))
    if project_has_rust:
        required_tools.append(("cargo", "Rust build tool/package manager"))
        required_tools.append(("rustc", "Rust compiler"))

    optional_tools: list[tuple[str, str]] = [
        ("gh", "GitHub CLI"),
        ("jq", "JSON processor"),
    ]

    for tool, purpose in required_tools:
        if not shutil.which(tool):
            msg = f"Required tool '{tool}' ({purpose}) not found."
            messages.append(error(msg, console=not config.json_output))
            overall_status = "FAILED"
        else:
            messages.append(
                info(f"Tool '{tool}' found.", console=not config.json_output)
            )

    if overall_status == "FAILED":  # Stop if required tools are missing
        return {
            "name": step_name,
            "status": "FAILED",
            "message": "Missing required tools. " + " ".join(messages),
        }

    for tool, purpose in optional_tools:
        if not shutil.which(tool):
            msg = f"Optional tool '{tool}' ({purpose}) not found."
            if config.ignore_missing_optional_tools:
                messages.append(
                    log(msg)
                )  # Changed from info to log for less noise if ignored
            else:
                messages.append(warn(msg, console=not config.json_output))
                # overall_status = "WARNING" # Could add a warning status if needed
        else:
            messages.append(
                info(f"Tool '{tool}' found.", console=not config.json_output)
            )

    final_message = "Tool check completed."
    if overall_status == "FAILED":
        final_message = "Tool check failed: missing required tools."
    elif any("⚠" in m for m in messages if "optional tool" in m.lower()):
        final_message += " Some optional tools are missing."
    else:
        final_message += " All configured tools present."

    return {
        "name": step_name,
        "status": overall_status,
        "message": final_message,
        "details": messages,
    }


async def step_python(config: InitConfig) -> dict[str, Any]:
    step_name = "python"
    if not (config.project_root / "pyproject.toml").exists():
        return {
            "name": step_name,
            "status": "SKIPPED",
            "message": "No pyproject.toml found.",
        }
    if not shutil.which("uv"):
        return {
            "name": step_name,
            "status": "SKIPPED",
            "message": "uv tool not found (required for python step).",
        }

    # Handle stack-specific initialization
    if config.stack == "uv":
        cmd = ["uv", "sync"]

        # Handle extra dependencies
        if config.extra:
            if config.extra == "all":
                # Include all optional dependency groups
                cmd.extend(["--all-extras"])
            else:
                # Include specific dependency group
                cmd.extend(["--extra", config.extra])

        return await sh(
            cmd,
            cwd=config.project_root,
            step_name=f"{step_name}_uv",
            console=not config.json_output,
        )

    # Default behavior
    return await sh(
        ["uv", "sync"],
        cwd=config.project_root,
        step_name=step_name,
        console=not config.json_output,
    )


async def step_npm(config: InitConfig) -> dict[str, Any]:
    step_name = "npm"
    if not (config.project_root / "package.json").exists():
        return {
            "name": step_name,
            "status": "SKIPPED",
            "message": "No package.json found.",
        }
    if not shutil.which("pnpm"):
        return {
            "name": step_name,
            "status": "SKIPPED",
            "message": "pnpm tool not found (required for npm step).",
        }

    # Handle stack-specific initialization
    if config.stack == "pnpm":
        cmd = ["pnpm", "install"]

        # Handle extra dependencies
        if config.extra:
            if config.extra == "all":
                # Install all dependencies including dev
                cmd.append("--production=false")
            elif config.extra == "dev":
                # Install dev dependencies
                cmd.append("--dev")
            elif config.extra == "prod":
                # Install only production dependencies
                cmd.append("--production")
            else:
                # Install specific dependency group if supported
                warn(
                    f"Unknown extra option '{config.extra}' for pnpm. Using default install.",
                    console=not config.json_output,
                )
        else:
            # Default to frozen lockfile for regular installs
            cmd.append("--frozen-lockfile")

        return await sh(
            cmd,
            cwd=config.project_root,
            step_name=f"{step_name}_pnpm",
            console=not config.json_output,
        )
    # Default behavior
    return await sh(
        ["pnpm", "install", "--frozen-lockfile"],
        cwd=config.project_root,
        step_name=step_name,
        console=not config.json_output,
    )


async def step_rust(config: InitConfig) -> dict[str, Any]:
    step_name = "rust"
    if not (config.project_root / "Cargo.toml").exists():
        return {
            "name": step_name,
            "status": "SKIPPED",
            "message": "No Cargo.toml found.",
        }
    if not shutil.which("cargo"):
        return {
            "name": step_name,
            "status": "SKIPPED",
            "message": "cargo tool not found (required for rust step).",
        }

    # Handle stack-specific initialization
    if config.stack == "cargo":
        cmd = ["cargo"]

        # Handle extra dependencies or features
        if config.extra:
            if config.extra == "all":
                # Build with all features
                cmd.extend(["build", "--all-features", "--workspace"])
            elif config.extra == "dev":
                # Run cargo check with dev profile
                cmd.extend(["check", "--workspace", "--profile", "dev"])
            elif config.extra == "test":
                # Run tests
                cmd.extend(["test", "--workspace"])
            else:
                # Assume extra is a specific feature to enable
                cmd.extend(["check", "--workspace", "--features", config.extra])
        else:
            # Default behavior
            cmd.extend(["check", "--workspace"])

        return await sh(
            cmd,
            cwd=config.project_root,
            step_name=f"{step_name}_cargo",
            console=not config.json_output,
        )

    # Default behavior
    return await sh(
        ["cargo", "check", "--workspace"],
        cwd=config.project_root,
        step_name=step_name,
        console=not config.json_output,
    )


async def step_husky(config: InitConfig) -> dict[str, Any]:
    step_name = "husky"
    pkg_json_path = config.project_root / "package.json"
    if not pkg_json_path.exists():
        return {
            "name": step_name,
            "status": "SKIPPED",
            "message": "No package.json found (required for Husky).",
        }
    if not shutil.which("pnpm"):
        return {
            "name": step_name,
            "status": "SKIPPED",
            "message": "pnpm not found (required for Husky setup via pnpm).",
        }

    husky_dir = config.project_root / ".husky"
    if husky_dir.is_dir():
        return {
            "name": step_name,
            "status": "OK",
            "message": "Husky already set up (.husky directory exists).",
        }

    try:
        pkg_data = json.loads(pkg_json_path.read_text())
        scripts = pkg_data.get("scripts", {})
    except json.JSONDecodeError:
        return {
            "name": step_name,
            "status": "FAILED",
            "message": "Malformed package.json, cannot check for 'prepare' script.",
        }

    if "prepare" not in scripts:
        return {
            "name": step_name,
            "status": "SKIPPED",
            "message": "No 'prepare' script in package.json for Husky.",
        }

    # Attempt to run pnpm run prepare
    result = await sh(
        "pnpm run prepare",
        cwd=config.project_root,
        step_name=f"{step_name}_prepare",
        console=not config.json_output,
    )
    if result["status"] == "FAILED":
        # Treat ERR_PNPM_NO_SCRIPT or other pnpm issues as non-fatal for this step, but report.
        warn_msg = f"Husky 'pnpm run prepare' failed (exit code {result['return_code']}). Husky setup might be incomplete. Stderr: {result['stderr']}"
        warn(warn_msg, console=not config.json_output)
        return {
            "name": step_name,
            "status": "WARNING",
            "message": warn_msg,
            "details": result,
        }

    # Verify if .husky dir was created; pnpm run prepare might do other things
    if husky_dir.is_dir():
        return {
            "name": step_name,
            "status": "OK",
            "message": "Husky setup successful via 'pnpm run prepare'.",
        }
    warn_msg = "'pnpm run prepare' succeeded but .husky directory was not created. Husky setup may be incomplete."
    warn(warn_msg, console=not config.json_output)
    return {"name": step_name, "status": "WARNING", "message": warn_msg}


BUILTIN_STEPS: OrderedDictType[
    str, Callable[[InitConfig], Awaitable[dict[str, Any]]]
] = OrderedDict([
    ("tools", step_tools),
    ("python", step_python),
    ("npm", step_npm),
    ("rust", step_rust),
    ("husky", step_husky),
])

import os
import stat


async def check_and_run_custom_init_script(
    config: InitConfig,
) -> list[dict[str, Any]] | None:
    """
    Check for custom initialization script and execute it if found.
    Returns the step results list if custom script was executed, None otherwise.
    """
    custom_script_path = config.khive_config_dir / "scripts" / "khive_init.sh"

    if not custom_script_path.exists():
        return None

    # Verify the script is executable
    if not os.access(custom_script_path, os.X_OK):
        warn(
            f"Custom init script {custom_script_path} exists but is not executable. "
            f"Run: chmod +x {custom_script_path}",
            console=not config.json_output,
        )
        return None

    # Security check: ensure it's a regular file and not world-writable
    script_stat = custom_script_path.stat()
    if not stat.S_ISREG(script_stat.st_mode):
        error_msg = f"Custom init script {custom_script_path} is not a regular file"
        error(error_msg, console=not config.json_output)
        return [
            {
                "name": "custom_init_script",
                "status": "FAILED",
                "message": error_msg,
            }
        ]

    if script_stat.st_mode & stat.S_IWOTH:
        warn(
            f"Custom init script {custom_script_path} is world-writable, which may be a security risk",
            console=not config.json_output,
        )

    info(
        f"Using custom initialization script: {custom_script_path}",
        console=not config.json_output,
    )

    # Detect what stacks/steps would normally be enabled
    detected_stacks = []
    if (config.project_root / "pyproject.toml").exists():
        detected_stacks.append("python")
    if (config.project_root / "package.json").exists():
        detected_stacks.append("npm")
    if (config.project_root / "Cargo.toml").exists():
        detected_stacks.append("rust")

    # Determine what steps would normally run
    normal_steps = determine_steps_to_run(config)
    enabled_builtin_steps = [
        name for name, (step_type, _) in normal_steps.items() if step_type == "builtin"
    ]
    enabled_custom_steps = [
        name for name, (step_type, _) in normal_steps.items() if step_type == "custom"
    ]

    # Prepare environment variables for the script
    env = os.environ.copy()
    env.update({
        "KHIVE_PROJECT_ROOT": str(config.project_root),
        "KHIVE_CONFIG_DIR": str(config.khive_config_dir),
        "KHIVE_DRY_RUN": "1" if config.dry_run else "0",
        "KHIVE_VERBOSE": "1" if config.verbose else "0",
        "KHIVE_JSON_OUTPUT": "1" if config.json_output else "0",
        "KHIVE_DETECTED_STACKS": ",".join(detected_stacks),
        "KHIVE_DISABLED_STACKS": ",".join(config.disable_auto_stacks),
        "KHIVE_FORCED_STEPS": ",".join(config.force_enable_steps),
        "KHIVE_REQUESTED_STACK": config.stack or "",
        "KHIVE_REQUESTED_EXTRA": config.extra or "",
        "KHIVE_ENABLED_BUILTIN_STEPS": ",".join(enabled_builtin_steps),
        "KHIVE_ENABLED_CUSTOM_STEPS": ",".join(enabled_custom_steps),
        "KHIVE_EXPLICIT_STEPS": (
            ",".join(config.steps_to_run_explicitly)
            if config.steps_to_run_explicitly
            else ""
        ),
    })

    # Build command with original CLI arguments
    cmd = [str(custom_script_path)]

    # Pass through relevant CLI flags
    if config.dry_run:
        cmd.append("--dry-run")
    if config.verbose:
        cmd.append("--verbose")
    if config.json_output:
        cmd.append("--json-output")
    if config.stack:
        cmd.extend(["--stack", config.stack])
    if config.extra:
        cmd.extend(["--extra", config.extra])
    if config.steps_to_run_explicitly:
        for step in config.steps_to_run_explicitly:
            cmd.extend(["--step", step])

    log(f"Executing custom init script: {' '.join(cmd)}")
    log(f"Working directory: {config.project_root}")
    log(f"Detected stacks: {detected_stacks}")
    log("Environment variables: KHIVE_*")
    if config.verbose:
        for key, value in env.items():
            if key.startswith("KHIVE_"):
                log(f"  {key}={value}")

    if config.dry_run:
        info(f"[DRY-RUN] Would execute: {' '.join(cmd)}", console=True)
        return [
            {
                "name": "custom_init_script",
                "status": "DRY_RUN",
                "message": "Custom init script execution completed (dry run)",
                "command": " ".join(cmd),
                "detected_stacks": detected_stacks,
                "enabled_steps": enabled_builtin_steps + enabled_custom_steps,
            }
        ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=config.project_root,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(),
            timeout=600,  # 10 minute timeout for init scripts
        )

        stdout = stdout_bytes.decode(errors="replace").strip()
        stderr = stderr_bytes.decode(errors="replace").strip()

        # If the script outputs JSON and we're in JSON mode, try to parse it
        if config.json_output and stdout.strip():
            try:
                custom_result = json.loads(stdout.strip())
                # Ensure it has the expected structure for init results
                if isinstance(custom_result, dict) and "steps" in custom_result:
                    # Add metadata about the custom script
                    for step in custom_result["steps"]:
                        if isinstance(step, dict):
                            step["custom_script"] = str(custom_script_path)
                    return custom_result["steps"]
                elif isinstance(custom_result, list):
                    # Array of step results
                    for step in custom_result:
                        if isinstance(step, dict):
                            step["custom_script"] = str(custom_script_path)
                    return custom_result
            except json.JSONDecodeError:
                # Fall through to handle as plain text
                pass

        # Handle non-JSON output or JSON parsing failure
        if proc.returncode == 0:
            # Script succeeded
            if not config.json_output and stdout.strip():
                print(stdout.strip())

            result = {
                "name": "custom_init_script",
                "status": "OK",
                "message": "Custom init script execution completed successfully",
                "command": " ".join(cmd),
                "custom_script": str(custom_script_path),
                "detected_stacks": detected_stacks,
                "enabled_steps": enabled_builtin_steps + enabled_custom_steps,
            }

            if config.json_output:
                result["stdout"] = stdout.strip()
                result["stderr"] = stderr.strip()

            return [result]
        else:
            # Script failed - provide detailed error information
            if not config.json_output:
                error(
                    f"Custom init script failed with exit code {proc.returncode}",
                    console=True,
                )

                # Show the command that was executed
                print(f"Command: {' '.join(cmd)}", file=sys.stderr)
                print(f"Working directory: {config.project_root}", file=sys.stderr)

                # Always show stdout if there was any (shows progress before failure)
                if stdout.strip():
                    print("\n--- Script Output (stdout) ---", file=sys.stderr)
                    print(stdout.strip(), file=sys.stderr)

                # Always show stderr if there was any (shows the actual error)
                if stderr.strip():
                    print("\n--- Error Output (stderr) ---", file=sys.stderr)
                    print(stderr.strip(), file=sys.stderr)
                else:
                    print("\n--- No error output captured ---", file=sys.stderr)
                    print(
                        "The script may have failed silently or the error was sent to a different stream.",
                        file=sys.stderr,
                    )

            result = {
                "name": "custom_init_script",
                "status": "FAILED",
                "message": f"Custom init script failed with exit code {proc.returncode}",
                "command": " ".join(cmd),
                "custom_script": str(custom_script_path),
                "return_code": proc.returncode,
                "detected_stacks": detected_stacks,
                "enabled_steps": enabled_builtin_steps + enabled_custom_steps,
            }

            if config.json_output:
                result["stdout"] = stdout.strip()
                result["stderr"] = stderr.strip()

            return [result]

    except asyncio.TimeoutError:
        error_msg = "Custom init script timed out after 10 minutes"
        error(error_msg, console=not config.json_output)
        if not config.json_output:
            print(f"Command: {' '.join(cmd)}", file=sys.stderr)
            print(f"Working directory: {config.project_root}", file=sys.stderr)

        return [
            {
                "name": "custom_init_script",
                "status": "FAILED",
                "message": error_msg,
                "command": " ".join(cmd),
                "custom_script": str(custom_script_path),
                "timeout": True,
                "detected_stacks": detected_stacks,
                "enabled_steps": enabled_builtin_steps + enabled_custom_steps,
            }
        ]
    except Exception as e:
        error_msg = f"Failed to execute custom init script: {e}"
        error(error_msg, console=not config.json_output)
        if not config.json_output:
            print(f"Command: {' '.join(cmd)}", file=sys.stderr)
            print(f"Working directory: {config.project_root}", file=sys.stderr)
            print(f"Exception type: {type(e).__name__}", file=sys.stderr)

        return [
            {
                "name": "custom_init_script",
                "status": "FAILED",
                "message": error_msg,
                "command": " ".join(cmd),
                "custom_script": str(custom_script_path),
                "exception": str(e),
                "exception_type": type(e).__name__,
                "detected_stacks": detected_stacks,
                "enabled_steps": enabled_builtin_steps + enabled_custom_steps,
            }
        ]


# ────────── Orchestrator ──────────
def determine_steps_to_run(config: InitConfig) -> OrderedDictType[str, tuple[str, Any]]:
    """Determines the sequence of steps (builtin and custom) to run."""
    steps: OrderedDictType[str, tuple[str, Any]] = (
        OrderedDict()
    )  # step_name -> (type, callable/cmd_config)

    # Handle explicit step selection from CLI
    if config.steps_to_run_explicitly:
        for step_name in config.steps_to_run_explicitly:
            if step_name in BUILTIN_STEPS:
                steps[step_name] = ("builtin", BUILTIN_STEPS[step_name])
            elif step_name in config.custom_steps:
                steps[step_name] = ("custom", config.custom_steps[step_name])
            else:
                warn(
                    f"Explicitly requested step '{step_name}' is unknown.",
                    console=not config.json_output,
                )
        return steps

    # If a specific stack is specified, prioritize it
    if config.stack:
        # Always include tools check
        steps["tools"] = ("builtin", BUILTIN_STEPS["tools"])

        # Map stack name to step name
        stack_to_step = {
            "uv": "python",
            "pnpm": "npm",
            "cargo": "rust",
        }

        if config.stack in stack_to_step:
            step_name = stack_to_step[config.stack]
            steps[step_name] = ("builtin", BUILTIN_STEPS[step_name])

            # Include husky if npm/pnpm is selected
            if (
                config.stack == "pnpm"
                and (config.project_root / "package.json").exists()
            ):
                steps["husky"] = ("builtin", BUILTIN_STEPS["husky"])

        else:
            warn(
                f"Unknown stack '{config.stack}'. Valid options are: uv, pnpm, cargo.",
                console=not config.json_output,
            )

        # Add custom steps
        for name, custom_cfg in config.custom_steps.items():
            if name not in steps:
                steps[name] = ("custom", custom_cfg)

        return steps

    # Auto-detection logic
    # 1. Built-in steps (in defined order)
    for name, func in BUILTIN_STEPS.items():
        is_forced = name in config.force_enable_steps
        is_disabled_stack = False
        if name in ["python", "npm", "rust"]:  # These are "stacks"
            is_disabled_stack = name in config.disable_auto_stacks

        run_this_step = False
        # Auto-detection conditions (simplified for this example; step functions handle detailed checks)
        if name == "tools":
            run_this_step = True  # Always consider 'tools' unless forced off somehow or no stacks active
        elif (
            (name == "python" and (config.project_root / "pyproject.toml").exists())
            or (name == "npm" and (config.project_root / "package.json").exists())
            or (
                (name == "rust" and (config.project_root / "Cargo.toml").exists())
                or (name == "husky" and (config.project_root / "package.json").exists())
            )
        ):
            run_this_step = True

        if (run_this_step and not is_disabled_stack) or is_forced:
            steps[name] = ("builtin", func)

    # 2. Custom steps (append after built-ins)
    for name, custom_cfg in config.custom_steps.items():
        if (
            name not in steps
        ):  # Avoid duplicates if somehow forced/named same as builtin
            steps[name] = ("custom", custom_cfg)

    return steps


# Modify the _run function to check for custom script first
async def _run(config: InitConfig) -> list[dict[str, Any]]:
    # Check for custom init script first
    custom_results = await check_and_run_custom_init_script(config)
    if custom_results is not None:
        return custom_results

    # Original implementation continues here...
    all_results: list[dict[str, Any]] = []

    ordered_steps_to_process = determine_steps_to_run(config)

    if not ordered_steps_to_process:
        msg = "No steps selected or auto-detected to run."
        if not config.json_output:
            print(msg)
        all_results.append({
            "name": "orchestrator",
            "status": "SKIPPED",
            "message": msg,
        })
        return all_results

    for step_name, (step_type, step_action) in ordered_steps_to_process.items():
        if not config.json_output:
            banner(step_name)

        step_result: dict[str, Any]

        if config.dry_run:
            cmd_to_run = "N/A (builtin python function)"
            cwd_info = ""
            if step_type == "custom":
                custom_cfg: CustomStepCfg = step_action
                cmd_to_run = custom_cfg.cmd or "No command defined"
                if custom_cfg.cwd:
                    cwd_info = f" in {config.project_root / custom_cfg.cwd}"

            dry_run_msg = f"[DRY-RUN] Would run {step_type} step '{step_name}'. Command: {cmd_to_run}{cwd_info}"
            if not config.json_output:
                print(f"  {dry_run_msg}")
            step_result = {
                "name": step_name,
                "status": "DRY_RUN",
                "message": dry_run_msg,
            }
        else:
            if step_type == "builtin":
                step_func: Callable[[InitConfig], Awaitable[dict[str, Any]]] = (
                    step_action
                )
                if (
                    step_name == "tools"
                    and "python" in config.disable_auto_stacks
                    and "npm" in config.disable_auto_stacks
                    and "rust" in config.disable_auto_stacks
                    and "tools" not in config.force_enable_steps
                ):
                    step_result = {
                        "name": step_name,
                        "status": "SKIPPED",
                        "message": "All stacks disabled, tools check skipped.",
                    }
                else:
                    step_result = await step_func(config)

            elif step_type == "custom":
                custom_cfg: CustomStepCfg = step_action
                if not cond_ok(
                    custom_cfg.run_if,
                    config.project_root,
                    console=not config.json_output,
                ):
                    msg = f"Condition '{custom_cfg.run_if}' not met."
                    if not config.json_output:
                        print(f"  {ANSI['Y']}{msg}{ANSI['N']}")
                    step_result = {
                        "name": step_name,
                        "status": "SKIPPED",
                        "message": msg,
                    }
                elif not custom_cfg.cmd:
                    msg = "No command defined for custom step."
                    if not config.json_output:
                        print(f"  {ANSI['Y']}{msg}{ANSI['N']}")
                    step_result = {
                        "name": step_name,
                        "status": "SKIPPED",
                        "message": msg,
                    }
                else:
                    custom_cwd = config.project_root / (custom_cfg.cwd or ".")
                    step_result = await sh(
                        custom_cfg.cmd,
                        cwd=custom_cwd,
                        step_name=step_name,
                        console=not config.json_output,
                    )
            else:  # Should not happen
                step_result = {
                    "name": step_name,
                    "status": "ERROR",
                    "message": "Unknown step type.",
                }

        all_results.append(step_result)

        # Display step status for human-readable output
        if not config.json_output and not config.dry_run:
            status_color = (
                ANSI["G"]
                if step_result["status"] == "OK"
                else (
                    ANSI["Y"]
                    if step_result["status"] in ["SKIPPED", "WARNING", "DRY_RUN"]
                    else ANSI["R"]
                )
            )
            print(
                f"  -> {status_color}{step_result['status']}{ANSI['N']}: {step_result.get('message', 'No message.')}"
            )

        if (
            step_result["status"] == "FAILED" and step_name != "tools"
        ):  # Allow tool check to fail but report, then stop for others
            # For tools, step_tools itself determines if it's a fatal failure
            if step_name == "tools" and "Missing required tools" not in step_result.get(
                "message", ""
            ):
                pass  # Not a fatal tool failure, continue
            else:
                error_msg = f"Step '{step_name}' failed. Halting execution."
                if not config.json_output:
                    error(error_msg)
                # Add this as a final orchestrator message if not already there
                if not any(r["name"] == "orchestrator_halt" for r in all_results):
                    all_results.append({
                        "name": "orchestrator_halt",
                        "status": "FAILED",
                        "message": error_msg,
                    })
                break

    return all_results


# ────────── CLI Entrypoint ──────────
def main() -> None:
    parser = argparse.ArgumentParser(description="khive project initialization tool.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Path to the project root directory (default: current working directory).",
    )
    parser.add_argument(
        "--json-output", action="store_true", help="Output results in JSON format."
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be done without actually running commands.",
    )
    parser.add_argument(
        "--step",
        action="append",
        help="Run only specific step(s) by name. Can be repeated. (e.g., --step python --step npm)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging."
    )
    parser.add_argument(
        "--stack",
        type=str,
        help="Specify which stack to initialize. Options: 'uv' (Python), 'pnpm' (Node.js), 'cargo' (Rust).",
    )
    parser.add_argument(
        "--extra",
        type=str,
        help="""Extra dependencies or options to include:
        - For 'uv': 'all' (all extras), or a specific extra group name
        - For 'pnpm': 'all' (all deps), 'dev' (dev deps), 'prod' (production deps)
        - For 'cargo': 'all' (all features), 'dev' (dev profile), 'test' (run tests), or a specific feature name""",
    )
    args = parser.parse_args()

    global verbose_mode
    verbose_mode = args.verbose  # Set global verbosity

    # Resolve project_root once
    resolved_project_root = args.project_root.resolve()
    if not resolved_project_root.is_dir():
        # Use die without full config if project root is bad from the start
        die(
            f"Project root does not exist or is not a directory: {resolved_project_root}",
            json_output=args.json_output,
            project_root_for_log=resolved_project_root,
        )

    config = load_init_config(
        resolved_project_root, args
    )  # Pass CLI args to config loader

    results = asyncio.run(_run(config))

    overall_status = "success"
    for result in results:
        if result["status"] == "FAILED":
            overall_status = "failure"
            break
        if result["status"] == "WARNING" and overall_status == "success":
            overall_status = "warning"  # Not a failure but not clean success

    if config.json_output:
        print(json.dumps({"status": overall_status, "steps": results}, indent=2))
    else:
        final_banner_color = (
            ANSI["G"]
            if overall_status == "success"
            else ANSI["Y"]
            if overall_status == "warning"
            else ANSI["R"]
        )
        final_message_text = (
            "khive init completed successfully."
            if overall_status == "success"
            else (
                "khive init completed with warnings."
                if overall_status == "warning"
                else "khive init failed."
            )
        )
        print(f"\n{final_banner_color}{final_message_text}{ANSI['N']}")

    if overall_status == "failure":
        sys.exit(1)
    # Consider exiting 2 for warnings if desired:
    # if overall_status == "warning": sys.exit(2)


if __name__ == "__main__":
    # This ensures that if the script is run directly, it behaves as expected.
    # The khive_cli.py dispatcher would call _cli() or main() on the imported module.
    # For consistency, let's assume khive_cli.py will call a function named 'main_entry'.
    main()


# To be called by khive_cli.py
def main_entry(argv: list[str] | None = None) -> None:
    """
    Provides a consistent entry point for khive_cli.py to call,
    parsing SystemExit internally.
    `argv` should exclude the script name itself, similar to sys.argv[1:].
    """
    # Note: argparse handles sys.argv by default if argv is None.
    # If khive_cli.py passes its own `rest` list, it needs to be compatible.
    # For this script structure, _cli() directly uses sys.argv.
    # If khive_cli.py calls this, it should manage sys.argv itself or _cli() needs modification.
    # Simplest path: khive_cli.py does `mod._cli()` after setting `sys.argv`.
    # Or, _cli can take an optional argv list.
    # For now, assuming _cli() is the direct target if this file is run as a script/module.
    # The provided khive_cli.py structure seems to try and call a `_cli` or `main` that
    # might take `rest` or nothing. Let's adapt _cli to fit that pattern too.

    # Adjusting _cli to accept optional argv for better integration:
    # No, the original _cli uses argparse.parse_args() which uses sys.argv by default.
    # If khive_cli.py wants to pass arguments, it should manipulate sys.argv before calling _cli().
    # The structure of `khive_cli.py` where it sometimes calls `entry()` or `entry(rest)`
    # is a bit complex. This script's `_cli()` is designed to be called without arguments,
    # relying on `argparse` to use `sys.argv`.

    # The existing main() in other khive scripts seems to be the pattern.
    # Let's rename _cli to main for consistency if that's the preferred entry point name.
    # For now, sticking with _cli and assuming khive_cli.py is adapted or this is run standalone.

    # If argv is provided (from khive_cli.py), set sys.argv appropriately for argparse
    original_argv = None
    if argv is not None:
        original_argv = sys.argv
        # The first element of sys.argv is traditionally the script name.
        # argparse in _cli will use sys.argv.
        script_name = "khive init"  # Or determine more dynamically if needed
        sys.argv = [script_name] + argv

    try:
        main()
    finally:
        if original_argv is not None:
            sys.argv = original_argv  # Restore original sys.argv
