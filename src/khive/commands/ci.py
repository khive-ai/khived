# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
ci.py - Implementation of the khive ci command.

This module provides the core functionality for continuous integration checks
including test discovery and execution for Python and Rust projects.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


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
            self.overall_success = False


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


def execute_tests(
    project_root: Path,
    project_type: str,
    config: dict[str, Any],
    timeout: int = 300,
    verbose: bool = False,
) -> CITestResult:
    """
    Execute tests for a specific project type.

    Args:
        project_root: Path to the project root
        project_type: Type of project (python, rust)
        config: Project configuration
        timeout: Timeout in seconds
        verbose: Enable verbose output

    Returns:
        CITestResult object with execution details
    """
    import time

    start_time = time.time()

    # Prepare command
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
        # Execute the command
        # For real-time output, we don't capture stdout/stderr here.
        # They will be inherited from the parent process and print directly.
        process = subprocess.Popen(cmd, cwd=project_root, stdout=sys.stdout, stderr=sys.stderr)
        
        try:
            # Wait for the process to complete with a timeout
            process.wait(timeout=timeout)
            exit_code = process.returncode
            # stdout and stderr are streamed, so we'll have empty strings here for the result object
            stdout_cap = ""
            stderr_cap = ""
        except subprocess.TimeoutExpired:
            process.kill() # Ensure the process is killed if it times out
            process.wait() # Wait for the process to terminate
            exit_code = 124 # Standard timeout exit code
            stdout_cap = ""
            stderr_cap = f"Test execution timed out after {timeout} seconds"
        
        duration = time.time() - start_time

        return CITestResult(
            test_type=project_type,
            command=" ".join(cmd),
            exit_code=exit_code,
            stdout=stdout_cap, # Will be empty as output is streamed
            stderr=stderr_cap, # Will be empty or timeout message
            duration=duration,
            success=exit_code == 0,
        )

    except subprocess.TimeoutExpired:
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

            if not test_result.success or verbose:
                if test_result.stderr:
                    lines.append(f"    Error: {test_result.stderr}")
                if verbose and test_result.stdout:
                    lines.append(f"    Output: {test_result.stdout}")
        lines.append("")

    # Overall status
    overall_status = "SUCCESS" if result.overall_success else "FAILURE"
    lines.append(f"Overall Status: {overall_status}")

    return "\n".join(lines)


def run_ci(
    project_root: Path,
    json_output: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
    test_type: str = "all",
    timeout: int = 300,
) -> int:
    """
    Run continuous integration checks.

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
    result = CIResult(project_root=project_root)

    try:
        # Discover projects
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

        # Execute tests
        for project_type, config in discovered_projects.items():
            if not verbose and not json_output:
                print(f"Running {project_type} tests...")

            test_result = execute_tests(
                project_root=project_root,
                project_type=project_type,
                config=config,
                timeout=timeout,
                verbose=verbose,
            )

            result.add_test_result(test_result)

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


def cli_entry() -> None:
    """
    Entry point for the ci command.

    This function delegates to the CLI implementation.
    """
    from khive.cli.khive_ci import main

    main()


if __name__ == "__main__":
    cli_entry()
