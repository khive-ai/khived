# Khive CLI Architecture

## Overview

The Khive CLI has been restructured to improve maintainability, extensibility,
and standardization. This document describes the new architecture and how to
work with it.

## Key Components

### 1. Central Dispatcher (`khive_cli.py`)

The central dispatcher is responsible for:

- Parsing the command-line arguments
- Loading the appropriate command module
- Executing the command's entry point
- Handling errors and providing helpful error messages

Located at `src/khive/cli/khive_cli.py`, the dispatcher uses a
configuration-driven approach to map user commands to their respective Python
modules.

### 2. Command Modules

Command modules are now located in the `src/khive/commands/` directory. Each
command module:

- Has a standardized name (without the `khive_` prefix)
- Provides a standardized entry point function called `cli_entry()`
- Uses an adapter pattern to delegate to the original implementation

For example, the `init` command is implemented in `src/khive/commands/init.py`
and delegates to the original implementation in `src/khive/cli/khive_init.py`.

## Command Discovery and Execution Flow

1. User runs a command: `khive <command> [options...]`
2. The central dispatcher (`khive_cli.py`) is invoked
3. The dispatcher looks up the command in its `COMMANDS` dictionary
4. The corresponding module is loaded from the `khive.commands` package
5. The `cli_entry()` function is called in the loaded module
6. The command is executed, and the result is returned to the user

## Adding a New Command

To add a new command to the Khive CLI:

1. Create a new module in the `src/khive/commands/` directory (e.g.,
   `new_command.py`)
2. Implement the command's functionality in `src/khive/cli/khive_new_command.py`
3. Create an adapter in the command module that delegates to the original
   implementation:

```python
#!/usr/bin/env python3
"""
new_command.py - Description of what the command does.

This is an adapter module that delegates to the original implementation
in khive.cli.khive_new_command.
"""

from __future__ import annotations

# Import the original implementation
from khive.cli.khive_new_command import main as original_main


def cli_entry() -> None:
    """
    Entry point for the new_command command.

    This function delegates to the original implementation.
    """
    original_main()


if __name__ == "__main__":
    cli_entry()
```

4. Add the command to the `COMMANDS` dictionary in `src/khive/cli/khive_cli.py`:

```python
COMMANDS: dict[str, str] = {
    # ... existing commands ...
    "new-command": "new_command",  # -> khive.commands.new_command
}
```

5. Add a description to the `COMMAND_DESCRIPTIONS` dictionary in
   `src/khive/cli/khive_cli.py`:

```python
COMMAND_DESCRIPTIONS: dict[str, str] = {
    # ... existing descriptions ...
    "new-command": "Description of what the new command does.",
}
```

## Command Module Structure

Each command module should follow this structure:

```python
#!/usr/bin/env python3
"""
command_name.py - Brief description of the command.

Detailed description of what the command does and how it works.
"""

from __future__ import annotations

import argparse
import sys
# Other imports as needed


def cli_entry() -> None:
    """
    Entry point for the command.

    This function is called by the central dispatcher.
    It should handle argument parsing and execute the command.
    """
    parser = argparse.ArgumentParser(description="Description of the command")
    # Add arguments

    args = parser.parse_args()
    # Execute the command


if __name__ == "__main__":
    cli_entry()
```

## Error Handling

The central dispatcher provides robust error handling:

1. If a command module cannot be loaded, an appropriate error message is
   displayed
2. If a command module does not have a `cli_entry()` function, an error message
   is displayed
3. If a command raises an exception, it is caught and a helpful error message is
   displayed

Command modules should use `argparse` for argument parsing, which will
automatically handle `--help` flags and invalid arguments.

## Testing

Each command module should have corresponding tests in the `tests/cli/`
directory. The tests should verify that:

1. The command module can be loaded
2. The `cli_entry()` function exists and is callable
3. The command executes correctly with various arguments
4. Error cases are handled appropriately

See `tests/cli/test_khive_cli.py` for examples of how to test the CLI dispatcher
and command modules.
