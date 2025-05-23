# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import importlib
import sys
from types import ModuleType

# --- Configuration for Command Discovery ---

# Define the package path where command modules are located.
# Command modules are expected to be in the khive.commands package
COMMAND_MODULE_BASE_PATH = "khive.commands"

# Maps the user-typed command to the Python module name within COMMAND_MODULE_BASE_PATH.
# The corresponding .py file should exist (e.g., "init" -> "init.py")
# Each module is expected to have an entry point function (see ENTRY_POINT_FUNCTION_NAME)
COMMANDS: dict[str, str] = {
    "init": "init",  # -> khive.commands.init
    "commit": "commit",  # -> khive.commands.commit
    "pr": "pr",  # -> khive.commands.pr
    "clean": "clean",  # -> khive.commands.clean
    "new-doc": "new_doc",  # -> khive.commands.new_doc
    "fmt": "fmt",  # -> khive.commands.fmt
    "roo": "roo",  # If khive_roo.py is kept for old functionality
    "info": "info",
    "reader": "reader",
    "ci": "ci",
    "mcp": "mcp",  # -> khive.commands.mcp
}

# Expected name of the entry point function in each command module.
# This function will be called to execute the command.
# It's recommended this function handles its own argparse.
ENTRY_POINT_FUNCTION_NAME = "cli_entry"

# One-line descriptions for the root help message.
COMMAND_DESCRIPTIONS: dict[str, str] = {
    "init": "Initializes and bootstraps the khive project environment.",
    "commit": "Creates Conventional Commits with staging and push options.",
    "pr": "Creates or views GitHub Pull Requests for the current branch.",
    "clean": "Deletes local and remote Git branches.",
    "new-doc": "Scaffolds new Markdown documents from templates.",
    "fmt": "Formats code across multiple stacks (Python, Rust, Deno, Markdown).",
    "search": "Validates and executes Exa/Perplexity searches.",
    "mcp": "Runs configuration-driven MCP servers.",
    "roo": "Legacy ROO mode generator.",
    "info": "Information service for web search and LLM consultation.",
    "reader": "Opens and reads documents via docling.",
}


# --- Helper Functions ---
def _get_full_module_path(module_name: str) -> str:
    """
    Get the full module path for a command module.

    Args:
        module_name: The name of the module (without the package prefix)

    Returns:
        The full module path (e.g., "khive.commands.init")
    """
    return f"{COMMAND_MODULE_BASE_PATH}.{module_name}"


def _load_command_module(cmd_name: str) -> ModuleType | None:
    """
    Loads the module for a given command.

    Args:
        cmd_name: The name of the command to load

    Returns:
        The loaded module, or None if the module could not be loaded
    """
    if cmd_name not in COMMANDS:
        print(f"Error: Unknown command '{cmd_name}'.", file=sys.stderr)
        _print_root_help()
        return None

    module_file_name = COMMANDS[cmd_name]
    full_module_path = _get_full_module_path(module_file_name)

    try:
        module = importlib.import_module(full_module_path)
        return module
    except ImportError as e:
        print(
            f"Error: Could not import module for command '{cmd_name}' ({full_module_path}).\nDetails: {e}",
            file=sys.stderr,
        )
        return None
    except Exception as e:  # Catch other potential errors during import
        print(
            f"Error: An unexpected issue occurred while trying to load command '{cmd_name}'.\nDetails: {e}",
            file=sys.stderr,
        )
        return None


def _print_root_help() -> None:
    """
    Prints the main help message for the khive CLI.
    """
    print("khive - Unified CLI for the Khive Development Environment\n")
    print("Usage: khive <command> [options...]\n")
    print("Available commands:")

    # Determine padding for alignment
    max_cmd_len = 0
    if COMMANDS:  # Check if COMMANDS is not empty
        max_cmd_len = max(len(cmd) for cmd in COMMANDS)

    for cmd_name, module_file_name in COMMANDS.items():
        description = COMMAND_DESCRIPTIONS.get(cmd_name, "No description available.")
        print(f"  {cmd_name:<{max_cmd_len + 2}} {description}")

    print("\nUse 'khive <command> --help' for more information on a specific command.")


# --- Main Dispatch Logic ---
def main(argv: list[str] | None = None) -> None:
    """
    Main entry point for the khive CLI.
    Dispatches to subcommand modules.
    `argv` should be sys.argv[1:]

    Args:
        argv: Command line arguments (defaults to sys.argv[1:])
    """
    if argv is None:  # If called directly without args (e.g. from script)
        argv = sys.argv[1:]

    if not argv or argv[0] in ("-h", "--help"):
        _print_root_help()
        return

    command_name, *sub_argv = argv

    module = _load_command_module(command_name)
    if not module:
        sys.exit(1)  # Module loading failed, error already printed

    entry_point_func = getattr(module, ENTRY_POINT_FUNCTION_NAME, None)
    if not entry_point_func or not callable(entry_point_func):
        print(
            f"Error: Command '{command_name}' module ('{module.__name__}') does not have a callable "
            f"'{ENTRY_POINT_FUNCTION_NAME}' entry point.",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- Argument Passing to Subcommand ---
    # The subcommand's entry_point (e.g., cli_entry) is expected to use argparse,
    # which reads from sys.argv. We need to set sys.argv appropriately for it.
    original_sys_argv = list(sys.argv)  # Preserve original

    # Construct the sys.argv that the subcommand's argparse will see.
    # It expects the "program name" as the first element.
    # Here, "khive <command_name>" acts as the program name for the subcommand.
    # Fix for test_cli_dispatcher_passes_arguments_to_command
    sys.argv = [f"khive {command_name}"]
    sys.argv.extend(sub_argv)

    try:
        # Call the subcommand's entry point. It should handle its own SystemExit
        # from argparse (--help) or errors.
        entry_point_func()
    except SystemExit as e:
        # If argparse in subcommand called sys.exit (e.g. for --help or error),
        # respect that exit code.
        sys.exit(e.code if e.code is not None else 0)
    except Exception:
        # Catch unexpected errors from within the subcommand for graceful reporting
        print(
            f"\nError: An unexpected error occurred while executing command '{command_name}':",
            file=sys.stderr,
        )
        import traceback

        traceback.print_exc()  # Print full traceback for debugging
        sys.exit(1)
    finally:
        sys.argv = original_sys_argv  # Restore original sys.argv


if __name__ == "__main__":
    main()
