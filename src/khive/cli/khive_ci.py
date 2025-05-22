# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
khive_ci.py - CLI entry point for the khive ci command.

This module provides the command-line interface for running continuous integration
checks including test discovery and execution for Python and Rust projects.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from khive.commands.ci import run_ci


def main() -> None:
    """
    Main entry point for the khive ci command.
    
    Parses command line arguments and delegates to the ci command implementation.
    """
    parser = argparse.ArgumentParser(
        description="Run continuous integration checks including test discovery and execution."
    )
    
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
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
    
    try:
        # Resolve project root path
        project_root = args.project_root.resolve()
        if not project_root.is_dir():
            error_msg = f"Project root does not exist or is not a directory: {project_root}"
            if args.json_output:
                result = {
                    "status": "error",
                    "message": error_msg,
                    "exit_code": 1
                }
                print(json.dumps(result, indent=2))
            else:
                print(f"Error: {error_msg}", file=sys.stderr)
            sys.exit(1)
        
        # Run the CI command
        exit_code = run_ci(
            project_root=project_root,
            json_output=args.json_output,
            dry_run=args.dry_run,
            verbose=args.verbose,
            test_type=args.test_type,
            timeout=args.timeout,
        )
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        if args.json_output:
            result = {
                "status": "interrupted",
                "message": "Command interrupted by user",
                "exit_code": 130
            }
            print(json.dumps(result, indent=2))
        else:
            print("\nCommand interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        if args.json_output:
            result = {
                "status": "error",
                "message": error_msg,
                "exit_code": 1
            }
            print(json.dumps(result, indent=2))
        else:
            print(f"Error: {error_msg}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()