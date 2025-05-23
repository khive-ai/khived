# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
khive_ci.py - Enhanced CI command with custom script support.

Features
========
* Multi-stack test execution (Python, Rust)
* Custom CI script support via .khive/scripts/khive_ci.sh
* Proper async execution with timeout handling
* JSON output support
* Configurable via TOML

CLI
---
    khive ci [--test-type python|rust|all] [--timeout 300] [--dry-run] [--verbose] [--json-output]

Exit codes: 0 success · 1 failure.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import stat
import subprocess
import sys
import time
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

# --- ANSI Colors and Logging ---
ANSI = {
    "G": "\033[32m" if sys.stdout.isatty() else "",
    "R": "\033[31m" if sys.stdout.isatty() else "",
    "Y": "\033[33m" if sys.stdout.isatty() else "",
    "B": "\033[34m" if sys.stdout.isatty() else "",
    "N": "\033[0m" if sys.stdout.isatty() else "",
}
verbose_mode = False


def log_msg_ci(msg: str, *, kind: str = "B") -> None:
    if verbose_mode:
        print(f"{ANSI[kind]}▶{ANSI['N']} {msg}")


def format_message_ci(prefix: str, msg: str, color_code: str) -> str:
    return f"{color_code}{prefix}{ANSI['N']} {msg}"


def info_msg_ci(msg: str, *, console: bool = True) -> str:
    output = format_message_ci("✔", msg, ANSI["G"])
    if console:
        print(output)
    return output


def warn_msg_ci(msg: str, *, console: bool = True) -> str:
    output = format_message_ci("⚠", msg, ANSI["Y"])
    if console:
        print(output, file=sys.stderr)
    return output


def error_msg_ci(msg: str, *, console: bool = True) -> str:
    output = format_message_ci("✖", msg, ANSI["R"])
    if console:
        print(output, file=sys.stderr)
    return output


def die_ci(
    msg: str, json_data: dict[str, Any] | None = None, json_output_flag: bool = False
) -> None:
    error_msg_ci(msg, console=not json_output_flag)
    if json_output_flag:
        base_data = {"status": "failure", "message": msg, "test_results": []}
        if json_data:
            base_data.update(json_data)
        print(json.dumps(base_data, indent=2))
    sys.exit(1)


# --- Configuration ---
@dataclass
class CIConfig:
    project_root: Path
    timeout: int = 300
    json_output: bool = False
    dry_run: bool = False
    verbose: bool = False

    @property
    def khive_config_dir(self) -> Path:
        return self.project_root / ".khive"


def load_ci_config(
    project_r: Path, cli_args: argparse.Namespace | None = None
) -> CIConfig:
    cfg = CIConfig(project_root=project_r)

    # Load configuration from .khive/ci.toml if it exists
    config_file = cfg.khive_config_dir / "ci.toml"
    if config_file.exists():
        log_msg_ci(f"Loading CI config from {config_file}")
        try:
            raw_toml = tomllib.loads(config_file.read_text())
            cfg.timeout = raw_toml.get("timeout", cfg.timeout)
        except Exception as e:
            warn_msg_ci(f"Could not parse {config_file}: {e}. Using default values.")

    # Apply CLI arguments
    if cli_args:
        cfg.json_output = cli_args.json_output
        cfg.dry_run = cli_args.dry_run
        cfg.verbose = cli_args.verbose
        if hasattr(cli_args, "timeout") and cli_args.timeout:
            cfg.timeout = cli_args.timeout

        global verbose_mode
        verbose_mode = cli_args.verbose

    return cfg


# --- Data Classes (same as original) ---
@dataclass
class CITestResult:
    """Represents the result of a test execution."""

    test_type: str
    command: str
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    success: bool


@dataclass
class CIResult:
    """Represents the overall result of CI execution."""

    project_root: Path
    test_results: list[CITestResult] = field(default_factory=list)
    discovered_projects: dict[str, dict[str, Any]] = field(default_factory=dict)
    overall_success: bool = True
    total_duration: float = 0.0

    def add_test_result(self, result: CITestResult) -> None:
        """Add a test result and update overall status."""
        self.test_results.append(result)
        self.total_duration += result.duration
        if not result.success:
            self.overall_success = False


# --- Project Detection (exact copy from original) ---
def detect_project_types(project_root: Path) -> dict[str, dict[str, Any]]:
    """
    Detect project types and their test configurations.

    Args:
        project_root: Path to the project root directory

    Returns:
        Dictionary mapping project types to their configurations
    """
    projects = {}

    # Check for Python project
    if (project_root / "pyproject.toml").exists():
        projects["python"] = {
            "test_command": "pytest",
            "test_tool": "pytest",
            "config_file": "pyproject.toml",
            "test_paths": _discover_python_test_paths(project_root),
        }
    elif (project_root / "setup.py").exists() or (
        project_root / "requirements.txt"
    ).exists():
        projects["python"] = {
            "test_command": "pytest",
            "test_tool": "pytest",
            "config_file": None,
            "test_paths": _discover_python_test_paths(project_root),
        }

    # Check for Rust project
    if (project_root / "Cargo.toml").exists():
        projects["rust"] = {
            "test_command": "cargo test",
            "test_tool": "cargo",
            "config_file": "Cargo.toml",
            "test_paths": _discover_rust_test_paths(project_root),
        }

    return projects


def _discover_python_test_paths(project_root: Path) -> list[str]:
    """Discover Python test paths."""
    test_paths = []

    # Common test directories
    common_test_dirs = ["tests", "test", "src/tests"]
    for test_dir in common_test_dirs:
        test_path = project_root / test_dir
        if test_path.exists() and test_path.is_dir():
            test_paths.append(str(test_path.relative_to(project_root)))

    # Look for test files in common patterns, but exclude virtual environments
    test_patterns = ["test_*.py", "*_test.py"]
    for pattern in test_patterns:
        for test_file in project_root.rglob(pattern):
            # Skip virtual environment and other common non-project directories
            if any(
                part in [".venv", "venv", "env", ".env", "node_modules", ".git"]
                for part in test_file.parts
            ):
                continue

            if test_file.is_file():
                test_dir = str(test_file.parent.relative_to(project_root))
                if test_dir not in test_paths and test_dir != ".":
                    test_paths.append(test_dir)

    return test_paths if test_paths else ["."]


def _discover_rust_test_paths(project_root: Path) -> list[str]:
    """Discover Rust test paths."""
    test_paths = []

    # Check for tests directory
    tests_dir = project_root / "tests"
    if tests_dir.exists() and tests_dir.is_dir():
        test_paths.append("tests")

    # Check for src directory (unit tests)
    src_dir = project_root / "src"
    if src_dir.exists() and src_dir.is_dir():
        test_paths.append("src")

    return test_paths if test_paths else ["."]


def validate_test_tools(projects: dict[str, dict[str, Any]]) -> dict[str, bool]:
    """
    Validate that required test tools are available.

    Args:
        projects: Dictionary of detected projects

    Returns:
        Dictionary mapping project types to tool availability
    """
    tool_availability = {}

    for project_type, config in projects.items():
        tool = config["test_tool"]
        tool_availability[project_type] = shutil.which(tool) is not None

    return tool_availability


# --- Custom Script Support ---
async def check_and_run_custom_ci_script(config: CIConfig) -> CIResult | None:
    """Check for custom CI script and execute it if found."""
    custom_script_path = config.khive_config_dir / "scripts" / "khive_ci.sh"

    if not custom_script_path.exists():
        return None

    # Verify the script is executable
    if not os.access(custom_script_path, os.X_OK):
        warn_msg_ci(
            f"Custom CI script {custom_script_path} exists but is not executable. "
            f"Run: chmod +x {custom_script_path}",
            console=not config.json_output,
        )
        return None

    # Security check
    script_stat = custom_script_path.stat()
    if not stat.S_ISREG(script_stat.st_mode):
        error_msg_ci(
            f"Custom CI script {custom_script_path} is not a regular file",
            console=not config.json_output,
        )
        result = CIResult(project_root=config.project_root)
        result.overall_success = False
        return result

    info_msg_ci(
        f"Using custom CI script: {custom_script_path}", console=not config.json_output
    )

    # Prepare environment variables
    env = os.environ.copy()
    env.update({
        "KHIVE_PROJECT_ROOT": str(config.project_root),
        "KHIVE_CONFIG_DIR": str(config.khive_config_dir),
        "KHIVE_DRY_RUN": "1" if config.dry_run else "0",
        "KHIVE_VERBOSE": "1" if config.verbose else "0",
        "KHIVE_JSON_OUTPUT": "1" if config.json_output else "0",
        "KHIVE_TIMEOUT": str(config.timeout),
    })

    # Build command
    cmd = [str(custom_script_path)]
    if config.dry_run:
        cmd.append("--dry-run")
    if config.verbose:
        cmd.append("--verbose")
    if config.json_output:
        cmd.append("--json-output")
    cmd.extend(["--timeout", str(config.timeout)])

    log_msg_ci(f"Executing custom CI script: {' '.join(cmd)}")

    if config.dry_run:
        info_msg_ci(f"[DRY-RUN] Would execute: {' '.join(cmd)}", console=True)
        result = CIResult(project_root=config.project_root)
        result.test_results.append(
            CITestResult(
                test_type="custom_script",
                command=" ".join(cmd),
                exit_code=0,
                stdout="DRY RUN",
                stderr="",
                duration=0.0,
                success=True,
            )
        )
        return result

    try:
        start_time = time.time()
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=config.project_root,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=config.timeout
        )
        duration = time.time() - start_time

        stdout = stdout_bytes.decode(errors="replace").strip()
        stderr = stderr_bytes.decode(errors="replace").strip()

        # Try to parse JSON output if in JSON mode
        if config.json_output and stdout.strip():
            try:
                custom_result_data = json.loads(stdout.strip())
                if (
                    isinstance(custom_result_data, dict)
                    and "test_results" in custom_result_data
                ):
                    result = CIResult(project_root=config.project_root)
                    result.overall_success = (
                        custom_result_data.get("status") == "success"
                    )

                    for test_data in custom_result_data["test_results"]:
                        test_result = CITestResult(
                            test_type=test_data.get("test_type", "custom"),
                            command=test_data.get("command", ""),
                            exit_code=test_data.get("exit_code", proc.returncode),
                            stdout=test_data.get("stdout", ""),
                            stderr=test_data.get("stderr", ""),
                            duration=test_data.get("duration", duration),
                            success=test_data.get("success", proc.returncode == 0),
                        )
                        result.add_test_result(test_result)

                    return result
            except json.JSONDecodeError:
                pass  # Fall through to handle as plain text

        # Handle as single test result
        result = CIResult(project_root=config.project_root)
        test_result = CITestResult(
            test_type="custom_script",
            command=" ".join(cmd),
            exit_code=proc.returncode,
            stdout=stdout,
            stderr=stderr,
            duration=duration,
            success=proc.returncode == 0,
        )
        result.add_test_result(test_result)

        if proc.returncode != 0:
            if not config.json_output:
                error_msg_ci(
                    f"Custom CI script failed with exit code {proc.returncode}"
                )
                print(f"Command: {' '.join(cmd)}", file=sys.stderr)
                print(f"Working directory: {config.project_root}", file=sys.stderr)
                if stdout:
                    print(f"\n--- Script Output ---\n{stdout}")
                if stderr:
                    print(f"\n--- Error Output ---\n{stderr}", file=sys.stderr)
        elif not config.json_output and stdout:
            print(stdout)

        return result

    except asyncio.TimeoutError:
        duration = time.time() - start_time
        error_msg_ci("Custom CI script timed out", console=not config.json_output)
        result = CIResult(project_root=config.project_root)
        result.overall_success = False
        test_result = CITestResult(
            test_type="custom_script",
            command=" ".join(cmd),
            exit_code=124,
            stdout="",
            stderr=f"Timeout after {config.timeout} seconds",
            duration=duration,
            success=False,
        )
        result.add_test_result(test_result)
        return result
    except Exception as e:
        error_msg_ci(
            f"Failed to execute custom CI script: {e}", console=not config.json_output
        )
        result = CIResult(project_root=config.project_root)
        result.overall_success = False
        test_result = CITestResult(
            test_type="custom_script",
            command=" ".join(cmd),
            exit_code=1,
            stdout="",
            stderr=str(e),
            duration=0.0,
            success=False,
        )
        result.add_test_result(test_result)
        return result


# --- Enhanced Test Execution ---
async def execute_tests_async(
    project_root: Path,
    project_type: str,
    config: dict[str, Any],
    timeout: int = 300,
    verbose: bool = False,
) -> CITestResult:
    """
    Execute tests for a specific project type using async subprocess.

    Args:
        project_root: Path to the project root
        project_type: Type of project (python, rust)
        config: Project configuration
        timeout: Timeout in seconds
        verbose: Enable verbose output

    Returns:
        CITestResult object with execution details
    """
    start_time = time.time()

    # Prepare command (same logic as original)
    if project_type == "python":
        cmd = ["pytest"]
        if verbose:
            cmd.append("-v")
        # Add test paths if specified
        if config.get("test_paths"):
            cmd.extend(config["test_paths"])
    elif project_type == "rust":
        cmd = ["cargo", "test"]
        if verbose:
            cmd.append("--verbose")
    else:
        raise ValueError(f"Unsupported project type: {project_type}")

    try:
        # Use async subprocess for better control
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=project_root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )

        exit_code = proc.returncode
        stdout = stdout_bytes.decode(errors="replace").strip()
        stderr = stderr_bytes.decode(errors="replace").strip()

        duration = time.time() - start_time

        return CITestResult(
            test_type=project_type,
            command=" ".join(cmd),
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration=duration,
            success=exit_code == 0,
        )

    except asyncio.TimeoutError:
        duration = time.time() - start_time
        return CITestResult(
            test_type=project_type,
            command=" ".join(cmd),
            exit_code=124,  # Standard timeout exit code
            stdout="",
            stderr=f"Test execution timed out after {timeout} seconds",
            duration=duration,
            success=False,
        )
    except Exception as e:
        duration = time.time() - start_time
        return CITestResult(
            test_type=project_type,
            command=" ".join(cmd),
            exit_code=1,
            stdout="",
            stderr=f"Error executing tests: {e}",
            duration=duration,
            success=False,
        )


# --- Output Formatting (same as original) ---
def format_output(
    result: CIResult, json_output: bool = False, verbose: bool = False
) -> str:
    """
    Format the CI result for output.

    Args:
        result: CIResult object
        json_output: Whether to format as JSON
        verbose: Whether to include verbose details

    Returns:
        Formatted output string
    """
    if json_output:
        output_data = {
            "status": "success" if result.overall_success else "failure",
            "project_root": str(result.project_root),
            "total_duration": result.total_duration,
            "discovered_projects": result.discovered_projects,
            "test_results": [
                {
                    "test_type": tr.test_type,
                    "command": tr.command,
                    "exit_code": tr.exit_code,
                    "success": tr.success,
                    "duration": tr.duration,
                    "stdout": tr.stdout if verbose else "",
                    "stderr": tr.stderr if verbose else "",
                }
                for tr in result.test_results
            ],
        }
        return json.dumps(output_data, indent=2)

    # Human-readable format
    lines = []
    lines.append("khive ci - Continuous Integration Results")
    lines.append("=" * 50)
    lines.append(f"Project Root: {result.project_root}")
    lines.append(f"Total Duration: {result.total_duration:.2f}s")
    lines.append("")

    # Discovered projects
    if result.discovered_projects:
        lines.append("Discovered Projects:")
        for project_type, config in result.discovered_projects.items():
            lines.append(f"  • {project_type.title()}: {config['test_command']}")
            if config.get("test_paths"):
                lines.append(f"    Test paths: {', '.join(config['test_paths'])}")
        lines.append("")

    # Test results
    if result.test_results:
        lines.append("Test Results:")
        for test_result in result.test_results:
            status = "✓ PASS" if test_result.success else "✗ FAIL"
            lines.append(
                f"  {status} {test_result.test_type} ({test_result.duration:.2f}s)"
            )
            lines.append(f"    Command: {test_result.command}")

            if not test_result.success:
                # Always show error output for failed tests
                if test_result.stdout:
                    lines.append(f"    Output: {test_result.stdout}")
                if test_result.stderr:
                    lines.append(f"    Error: {test_result.stderr}")
            elif verbose:
                # Show output for successful tests only in verbose mode
                if test_result.stdout:
                    lines.append(f"    Output: {test_result.stdout}")
                if test_result.stderr:
                    lines.append(f"    Warnings: {test_result.stderr}")
        lines.append("")

    # Overall status
    overall_status = "SUCCESS" if result.overall_success else "FAILURE"
    lines.append(f"Overall Status: {overall_status}")

    return "\n".join(lines)


# --- Main CI Function ---
async def run_ci_async(
    project_root: Path,
    json_output: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
    test_type: str = "all",
    timeout: int = 300,
) -> int:
    """
    Run continuous integration checks with async support.

    Args:
        project_root: Path to the project root
        json_output: Output results in JSON format
        dry_run: Show what would be done without executing
        verbose: Enable verbose output
        test_type: Type of tests to run (python, rust, all)
        timeout: Timeout for test execution

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    config = CIConfig(
        project_root=project_root,
        json_output=json_output,
        dry_run=dry_run,
        verbose=verbose,
        timeout=timeout,
    )

    # Check for custom CI script first
    custom_result = await check_and_run_custom_ci_script(config)
    if custom_result is not None:
        output = format_output(custom_result, json_output=json_output, verbose=verbose)
        print(output)
        return 0 if custom_result.overall_success else 1

    # Use original logic for built-in CI
    result = CIResult(project_root=project_root)

    try:
        # Discover projects (exact same logic as original)
        discovered_projects = detect_project_types(project_root)
        result.discovered_projects = discovered_projects

        if not discovered_projects:
            if json_output:
                output_data = {
                    "status": "no_tests",
                    "message": "No test projects discovered",
                    "project_root": str(project_root),
                }
                print(json.dumps(output_data, indent=2))
            else:
                print("No test projects discovered in the current directory.")
            return 0

        # Filter projects based on test_type
        if test_type != "all":
            discovered_projects = {
                k: v for k, v in discovered_projects.items() if k == test_type
            }

        # Validate tools
        tool_availability = validate_test_tools(discovered_projects)
        missing_tools = [
            project_type
            for project_type, available in tool_availability.items()
            if not available
        ]

        if missing_tools:
            error_msg = f"Missing required tools for: {', '.join(missing_tools)}"
            if json_output:
                output_data = {
                    "status": "error",
                    "message": error_msg,
                    "missing_tools": missing_tools,
                }
                print(json.dumps(output_data, indent=2))
            else:
                print(f"Error: {error_msg}", file=sys.stderr)
            return 1

        if dry_run:
            if json_output:
                output_data = {
                    "status": "dry_run",
                    "discovered_projects": discovered_projects,
                    "would_execute": [
                        f"{config['test_command']} for {project_type}"
                        for project_type, config in discovered_projects.items()
                    ],
                }
                print(json.dumps(output_data, indent=2))
            else:
                print("Dry run - would execute:")
                for project_type, config in discovered_projects.items():
                    print(f"  • {config['test_command']} for {project_type}")
            return 0

        # Execute tests using async version
        for project_type, proj_config in discovered_projects.items():
            if not verbose and not json_output:
                print(f"Running {project_type} tests...")

            test_result = await execute_tests_async(
                project_root=project_root,
                project_type=project_type,
                config=proj_config,
                timeout=timeout,
                verbose=verbose,
            )

            result.add_test_result(test_result)

            # Show test output immediately if not in JSON mode
            if not json_output:
                if test_result.success:
                    if verbose and test_result.stdout:
                        print(test_result.stdout)
                else:
                    # Always show output for failed tests
                    print(
                        f"\n{ANSI['R']}Test execution failed for {project_type}:{ANSI['N']}"
                    )
                    print(f"Command: {test_result.command}")
                    if test_result.stdout:
                        print(f"\nOutput:\n{test_result.stdout}")
                    if test_result.stderr:
                        print(f"\nError:\n{test_result.stderr}")
                    print()  # Extra newline for separation

        # Output results
        output = format_output(result, json_output=json_output, verbose=verbose)
        print(output)

        return 0 if result.overall_success else 1

    except Exception as e:
        error_msg = f"CI execution failed: {e}"
        if json_output:
            output_data = {"status": "error", "message": error_msg, "exit_code": 1}
            print(json.dumps(output_data, indent=2))
        else:
            print(f"Error: {error_msg}", file=sys.stderr)
        return 1


# --- CLI Entry Point ---
def main() -> None:
    """
    Main entry point for the khive ci command.
    """
    parser = argparse.ArgumentParser(
        description="Run continuous integration checks including test discovery and execution."
    )

    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help="Path to the project root directory (default: current working directory).",
    )

    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output results in JSON format.",
    )

    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be done without actually running tests.",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging.",
    )

    parser.add_argument(
        "--test-type",
        choices=["python", "rust", "all"],
        default="all",
        help="Specify which test types to run (default: all).",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout for test execution in seconds (default: 300).",
    )

    args = parser.parse_args()
    global verbose_mode
    verbose_mode = args.verbose

    try:
        # Resolve project root path
        project_root = args.project_root.resolve()
        if not project_root.is_dir():
            error_msg = (
                f"Project root does not exist or is not a directory: {project_root}"
            )
            if args.json_output:
                result = {"status": "error", "message": error_msg, "exit_code": 1}
                print(json.dumps(result, indent=2))
            else:
                print(f"Error: {error_msg}", file=sys.stderr)
            sys.exit(1)

        # Run the CI command with async support
        exit_code = asyncio.run(
            run_ci_async(
                project_root=project_root,
                json_output=args.json_output,
                dry_run=args.dry_run,
                verbose=args.verbose,
                test_type=args.test_type,
                timeout=args.timeout,
            )
        )

        sys.exit(exit_code)

    except KeyboardInterrupt:
        if args.json_output:
            result = {
                "status": "interrupted",
                "message": "Command interrupted by user",
                "exit_code": 130,
            }
            print(json.dumps(result, indent=2))
        else:
            print("\nCommand interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        if args.json_output:
            result = {"status": "error", "message": error_msg, "exit_code": 1}
            print(json.dumps(result, indent=2))
        else:
            print(f"Error: {error_msg}", file=sys.stderr)
        sys.exit(1)


def cli_entry() -> None:
    """Entry point for khive CLI integration."""
    main()


if __name__ == "__main__":
    main()
