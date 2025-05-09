"""khivemcp Command Line Interface"""

import asyncio
import sys
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(
    name="khivemcp",
    help="khivemcp: Run configuration-driven MCP servers using FastMCP.",
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,  # Reduce noise on Typer errors
)


@app.command()
def run(
    config_file: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=False,
            writable=False,
            readable=True,
            resolve_path=True,
            help="Path to the service (YAML) or group (JSON/YAML) configuration file.",
        ),
    ],
    # Add other CLI options if needed, e.g., --transport=sse
) -> None:
    """Loads configuration and runs the khivemcp server using FastMCP."""
    from khive.connections.mcp_server import load_config, run_khivemcp_server

    try:
        config = load_config(config_file)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        raise typer.Exit(code=1) from e
    except Exception as e:
        print(
            f"An unexpected error occurred during configuration loading: {e}",
            file=sys.stderr,
        )
        raise typer.Exit(code=1) from e

    # Run the main async server function
    try:
        asyncio.run(run_khivemcp_server(config))
    except KeyboardInterrupt:
        print("\n[CLI] Server shutdown requested by user.", file=sys.stderr)
        # asyncio.run should handle cleanup, but add explicit cleanup if needed
    except Exception as e:
        # Catch errors from within run_khivemcp_server if they weren't handled there
        print(
            f"\n[Error] An unexpected error occurred during server execution: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        raise typer.Exit(code=1) from e
    finally:
        print("[CLI] khivemcp command finished.", file=sys.stderr)


def main():
    """CLI entry point function."""
    app()


# Make the script executable
if __name__ == "__main__":
    main()
