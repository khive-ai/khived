# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
khive_mcp.py - MCP (Model Context Protocol) server management and interaction.

Features
========
* MCP server configuration management via .khive/mcps/config.json
* Proper MCP initialization handshake and communication
* JSON-RPC 2.0 over stdin/stdout transport
* Server lifecycle management (start, stop, status)
* Tool discovery and execution
* Persistent server connections

CLI
---
    khive mcp list                           # List configured servers
    khive mcp status [server]                # Show server status
    khive mcp start <server>                 # Start an MCP server
    khive mcp stop <server>                  # Stop an MCP server
    khive mcp tools <server>                 # List available tools
    khive mcp call <server> <tool> [args]    # Call a tool

Exit codes: 0 success · 1 failure · 2 warnings.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
    "C": "\033[36m" if sys.stdout.isatty() else "",
    "M": "\033[35m" if sys.stdout.isatty() else "",
    "N": "\033[0m" if sys.stdout.isatty() else "",
}
verbose_mode = False


def log_msg_mcp(msg: str, *, kind: str = "B") -> None:
    if verbose_mode:
        print(f"{ANSI[kind]}▶{ANSI['N']} {msg}")


def format_message_mcp(prefix: str, msg: str, color_code: str) -> str:
    return f"{color_code}{prefix}{ANSI['N']} {msg}"


def info_msg_mcp(msg: str, *, console: bool = True) -> str:
    output = format_message_mcp("✔", msg, ANSI["G"])
    if console:
        print(output)
    return output


def warn_msg_mcp(msg: str, *, console: bool = True) -> str:
    output = format_message_mcp("⚠", msg, ANSI["Y"])
    if console:
        print(output, file=sys.stderr)
    return output


def error_msg_mcp(msg: str, *, console: bool = True) -> str:
    output = format_message_mcp("✖", msg, ANSI["R"])
    if console:
        print(output, file=sys.stderr)
    return output


def die_mcp(
    msg: str, json_data: dict[str, Any] | None = None, json_output_flag: bool = False
) -> None:
    error_msg_mcp(msg, console=not json_output_flag)
    if json_output_flag:
        base_data = {"status": "failure", "message": msg}
        if json_data:
            base_data.update(json_data)
        print(json.dumps(base_data, indent=2))
    sys.exit(1)


# --- Configuration Data Classes ---
@dataclass
class MCPServerConfig:
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    always_allow: list[str] = field(default_factory=list)
    disabled: bool = False
    timeout: int = 30


@dataclass
class MCPConfig:
    project_root: Path
    servers: dict[str, MCPServerConfig] = field(default_factory=dict)

    # CLI args / internal state
    json_output: bool = False
    dry_run: bool = False
    verbose: bool = False

    @property
    def khive_config_dir(self) -> Path:
        return self.project_root / ".khive"

    @property
    def mcps_config_file(self) -> Path:
        return self.khive_config_dir / "mcps" / "config.json"

    @property
    def mcps_state_file(self) -> Path:
        return self.khive_config_dir / "mcps" / "state.json"


def load_mcp_config(
    project_r: Path, cli_args: argparse.Namespace | None = None
) -> MCPConfig:
    cfg = MCPConfig(project_root=project_r)

    # Load MCP server configurations
    if cfg.mcps_config_file.exists():
        log_msg_mcp(f"Loading MCP config from {cfg.mcps_config_file}")
        try:
            config_data = json.loads(cfg.mcps_config_file.read_text())
            mcp_servers = config_data.get("mcpServers", {})

            for server_name, server_config in mcp_servers.items():
                cfg.servers[server_name] = MCPServerConfig(
                    name=server_name,
                    command=server_config.get("command", ""),
                    args=server_config.get("args", []),
                    env=server_config.get("env", {}),
                    always_allow=server_config.get("alwaysAllow", []),
                    disabled=server_config.get("disabled", False),
                    timeout=server_config.get("timeout", 30),
                )
        except (json.JSONDecodeError, KeyError) as e:
            warn_msg_mcp(f"Could not parse MCP config: {e}. Using empty configuration.")

    # Apply CLI arguments
    if cli_args:
        cfg.json_output = cli_args.json_output
        cfg.dry_run = cli_args.dry_run
        cfg.verbose = cli_args.verbose

        global verbose_mode
        verbose_mode = cli_args.verbose

    return cfg


def save_mcp_state(config: MCPConfig, server_states: dict[str, dict[str, Any]]) -> None:
    """Save MCP server runtime state."""
    try:
        config.mcps_state_file.parent.mkdir(parents=True, exist_ok=True)
        config.mcps_state_file.write_text(json.dumps(server_states, indent=2))
    except OSError as e:
        warn_msg_mcp(f"Could not save MCP state: {e}")


def load_mcp_state(config: MCPConfig) -> dict[str, dict[str, Any]]:
    """Load MCP server runtime state."""
    if not config.mcps_state_file.exists():
        return {}

    try:
        return json.loads(config.mcps_state_file.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


# --- MCP Client Implementation ---
class MCPClient:
    """Proper MCP client that handles the full JSON-RPC 2.0 protocol."""

    def __init__(self, server_config: MCPServerConfig):
        self.server_config = server_config
        self.process: asyncio.subprocess.Process | None = None
        self.message_id = 0
        self.connected = False
        self.server_info: dict[str, Any] = {}
        self.tools: list[dict[str, Any]] = []

    async def connect(self) -> bool:
        """Connect to the MCP server and perform initialization handshake."""
        try:
            # Prepare environment
            env = os.environ.copy()
            env.update(self.server_config.env)

            # Start the MCP server process
            cmd = [self.server_config.command] + self.server_config.args
            log_msg_mcp(f"Starting MCP server: {' '.join(cmd)}")

            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            # Perform MCP initialization handshake
            await self._initialize()

            # List available tools
            await self._list_tools()

            self.connected = True
            return True

        except Exception as e:
            log_msg_mcp(f"Failed to connect: {e}")
            if self.process:
                self.process.terminate()
                await self.process.wait()
            return False

    async def _initialize(self):
        """Perform the MCP initialization handshake."""
        log_msg_mcp("Performing MCP initialization handshake")

        # Step 1: Send initialize request
        init_response = await self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                "clientInfo": {"name": "khive", "version": "1.0.0"},
            },
        )

        if "error" in init_response:
            raise Exception(f"Initialization failed: {init_response['error']}")

        # Store server info
        if "result" in init_response:
            self.server_info = init_response["result"]
            log_msg_mcp(
                f"Server: {self.server_info.get('serverInfo', {}).get('name', 'unknown')}"
            )

        # Step 3: Send initialized notification (Step 2 was receiving the response)
        await self._send_notification("notifications/initialized")
        log_msg_mcp("MCP initialization completed")

    async def _list_tools(self):
        """List available tools from the server."""
        tools_response = await self._send_request("tools/list")
        if "result" in tools_response and "tools" in tools_response["result"]:
            self.tools = tools_response["result"]["tools"]
            log_msg_mcp(f"Found {len(self.tools)} tools")

    async def _send_request(self, method: str, params: dict | None = None) -> dict:
        """Send a JSON-RPC request and wait for response."""
        if not self.process or not self.process.stdin:
            raise Exception("Not connected to MCP server")

        self.message_id += 1
        message = {"jsonrpc": "2.0", "id": self.message_id, "method": method}
        if params:
            message["params"] = params

        # Send message
        message_str = json.dumps(message) + "\n"
        log_msg_mcp(f"Sending: {method}")

        self.process.stdin.write(message_str.encode())
        await self.process.stdin.drain()

        # Read response
        try:
            response_line = await asyncio.wait_for(
                self.process.stdout.readline(), timeout=self.server_config.timeout
            )

            if not response_line:
                raise Exception("Server closed connection")

            response = json.loads(response_line.decode().strip())
            log_msg_mcp(f"Received response for: {method}")
            return response

        except asyncio.TimeoutError:
            raise Exception(f"Timeout waiting for response to {method}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {e}")

    async def _send_notification(self, method: str, params: dict | None = None):
        """Send a JSON-RPC notification (no response expected)."""
        if not self.process or not self.process.stdin:
            raise Exception("Not connected to MCP server")

        message = {"jsonrpc": "2.0", "method": method}
        if params:
            message["params"] = params

        message_str = json.dumps(message) + "\n"
        log_msg_mcp(f"Sending notification: {method}")

        self.process.stdin.write(message_str.encode())
        await self.process.stdin.drain()

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Call a specific tool on the MCP server."""
        if not self.connected:
            raise Exception("Not connected to MCP server")

        # Check if tool is allowed
        if (
            self.server_config.always_allow
            and tool_name not in self.server_config.always_allow
        ):
            raise Exception(f"Tool '{tool_name}' not in allowlist")

        # Check if tool exists
        tool_names = [tool.get("name") for tool in self.tools]
        if tool_name not in tool_names:
            raise Exception(f"Tool '{tool_name}' not found. Available: {tool_names}")

        log_msg_mcp(f"Calling tool: {tool_name}")
        response = await self._send_request(
            "tools/call", {"name": tool_name, "arguments": arguments}
        )

        if "error" in response:
            raise Exception(f"Tool call failed: {response['error']}")

        return response.get("result", {})

    async def list_tools(self) -> list[dict[str, Any]]:
        """Get list of available tools."""
        return self.tools

    async def disconnect(self):
        """Disconnect from the MCP server."""
        if self.process:
            try:
                # Send a graceful shutdown if possible
                if self.connected:
                    await self._send_notification("notifications/cancelled")
            except:
                pass  # Ignore errors during shutdown

            # Terminate the process
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()

            self.process = None
            self.connected = False


# --- Global MCP client registry ---
_mcp_clients: dict[str, MCPClient] = {}


async def get_mcp_client(server_config: MCPServerConfig) -> MCPClient:
    """Get or create an MCP client for a server."""
    if server_config.name not in _mcp_clients:
        client = MCPClient(server_config)
        if await client.connect():
            _mcp_clients[server_config.name] = client
        else:
            raise Exception(f"Failed to connect to MCP server '{server_config.name}'")

    return _mcp_clients[server_config.name]


async def disconnect_all_clients():
    """Disconnect all MCP clients."""
    for client in _mcp_clients.values():
        await client.disconnect()
    _mcp_clients.clear()


# --- Command Implementations ---
async def cmd_list_servers(config: MCPConfig) -> dict[str, Any]:
    """List all configured MCP servers."""
    servers_info = []

    for server_name, server_config in config.servers.items():
        server_info = {
            "name": server_name,
            "command": server_config.command,
            "disabled": server_config.disabled,
            "operations_count": len(server_config.always_allow),
            "status": "disconnected",
        }

        # Check if we have an active connection
        if server_name in _mcp_clients:
            client = _mcp_clients[server_name]
            if client.connected:
                server_info["status"] = "connected"
                server_info["tools_count"] = len(client.tools)

        servers_info.append(server_info)

    return {
        "status": "success",
        "message": f"Found {len(servers_info)} configured MCP servers",
        "servers": servers_info,
        "total_count": len(servers_info),
    }


async def cmd_server_status(
    config: MCPConfig, server_name: str | None = None
) -> dict[str, Any]:
    """Get status of one or all MCP servers."""
    if server_name:
        if server_name not in config.servers:
            return {
                "status": "failure",
                "message": f"Server '{server_name}' not found in configuration",
                "available_servers": list(config.servers.keys()),
            }

        server_config = config.servers[server_name]
        server_info = {
            "name": server_name,
            "command": server_config.command,
            "args": server_config.args,
            "disabled": server_config.disabled,
            "timeout": server_config.timeout,
            "allowed_operations": server_config.always_allow,
            "status": "disconnected",
        }

        # Check if we have an active connection
        if server_name in _mcp_clients:
            client = _mcp_clients[server_name]
            if client.connected:
                server_info["status"] = "connected"
                server_info["server_info"] = client.server_info
                server_info["tools"] = client.tools

        return {
            "status": "success",
            "message": f"Status for server '{server_name}'",
            "server": server_info,
        }
    else:
        # Return status for all servers
        return await cmd_list_servers(config)


async def cmd_list_tools(config: MCPConfig, server_name: str) -> dict[str, Any]:
    """List tools available on a specific server."""
    if server_name not in config.servers:
        return {
            "status": "failure",
            "message": f"Server '{server_name}' not found in configuration",
            "available_servers": list(config.servers.keys()),
        }

    if config.dry_run:
        return {
            "status": "dry_run",
            "message": f"Would list tools for server '{server_name}'",
            "server": server_name,
        }

    try:
        server_config = config.servers[server_name]
        client = await get_mcp_client(server_config)
        tools = await client.list_tools()

        return {
            "status": "success",
            "message": f"Found {len(tools)} tools on server '{server_name}'",
            "server": server_name,
            "tools": tools,
        }
    except Exception as e:
        return {
            "status": "failure",
            "message": f"Failed to list tools: {e}",
            "server": server_name,
        }


def parse_tool_arguments(args: argparse.Namespace) -> dict[str, Any]:
    """Parse tool arguments from CLI flags into a dictionary."""
    arguments = {}

    # Parse --var key=value arguments
    if hasattr(args, "var") and args.var:
        for var_arg in args.var:
            if "=" not in var_arg:
                raise ValueError(
                    f"Invalid --var format: '{var_arg}'. Expected format: key=value"
                )
            key, value = var_arg.split("=", 1)

            # Try to parse as JSON value for complex types
            try:
                parsed_value = json.loads(value)
                arguments[key] = parsed_value
            except json.JSONDecodeError:
                # If not valid JSON, treat as string
                arguments[key] = value

    # Parse individual flag arguments (--key value)
    # We'll collect these from unknown args that follow the pattern
    if hasattr(args, "tool_args") and args.tool_args:
        i = 0
        while i < len(args.tool_args):
            arg = args.tool_args[i]
            if arg.startswith("--"):
                key = arg[2:]  # Remove '--' prefix
                if i + 1 < len(args.tool_args) and not args.tool_args[i + 1].startswith(
                    "--"
                ):
                    value = args.tool_args[i + 1]
                    # Try to parse as JSON for complex types
                    try:
                        parsed_value = json.loads(value)
                        arguments[key] = parsed_value
                    except json.JSONDecodeError:
                        arguments[key] = value
                    i += 2
                else:
                    # Boolean flag (no value)
                    arguments[key] = True
                    i += 1
            else:
                i += 1

    # Fallback to JSON if provided
    if hasattr(args, "json_args") and args.json_args:
        try:
            json_arguments = json.loads(args.json_args)
            arguments.update(json_arguments)
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in --json argument: {args.json_args}")

    return arguments


async def cmd_call_tool(
    config: MCPConfig, server_name: str, tool_name: str, arguments: dict[str, Any]
) -> dict[str, Any]:
    """Call a tool on a specific server."""
    if server_name not in config.servers:
        return {
            "status": "failure",
            "message": f"Server '{server_name}' not found in configuration",
            "available_servers": list(config.servers.keys()),
        }

    if config.dry_run:
        return {
            "status": "dry_run",
            "message": f"Would call tool '{tool_name}' on server '{server_name}'",
            "server": server_name,
            "tool": tool_name,
            "arguments": arguments,
        }

    try:
        server_config = config.servers[server_name]
        client = await get_mcp_client(server_config)
        result = await client.call_tool(tool_name, arguments)

        return {
            "status": "success",
            "message": f"Tool '{tool_name}' executed successfully",
            "server": server_name,
            "tool": tool_name,
            "arguments": arguments,  # Include arguments in response for debugging
            "result": result,
        }
    except Exception as e:
        return {
            "status": "failure",
            "message": f"Failed to call tool: {e}",
            "server": server_name,
            "tool": tool_name,
            "arguments": arguments,
            "error": str(e),
        }


async def main_mcp_flow(args: argparse.Namespace, config: MCPConfig) -> dict[str, Any]:
    """Main MCP command flow."""
    try:
        # Dispatch to specific command handlers
        if args.command == "list":
            return await cmd_list_servers(config)

        elif args.command == "status":
            server_name = getattr(args, "server", None)
            return await cmd_server_status(config, server_name)

        elif args.command == "tools":
            server_name = args.server
            return await cmd_list_tools(config, server_name)

        elif args.command == "call":
            server_name = args.server
            tool_name = args.tool

            # Parse tool arguments from various CLI formats
            try:
                arguments = parse_tool_arguments(args)
            except ValueError as e:
                return {
                    "status": "failure",
                    "message": f"Argument parsing error: {e}",
                }

            return await cmd_call_tool(config, server_name, tool_name, arguments)

        else:
            return {
                "status": "failure",
                "message": f"Unknown command: {args.command}",
                "available_commands": ["list", "status", "tools", "call"],
            }

    finally:
        # Clean up connections on exit
        if not config.dry_run:
            await disconnect_all_clients()


# --- CLI Entry Point ---
def cli_entry_mcp() -> None:
    parser = argparse.ArgumentParser(description="khive MCP server management.")

    # Global arguments
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

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="MCP commands")

    # List command
    subparsers.add_parser("list", help="List configured MCP servers")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show server status")
    status_parser.add_argument("server", nargs="?", help="Specific server name")

    # Tools command
    tools_parser = subparsers.add_parser("tools", help="List available tools")
    tools_parser.add_argument("server", help="Server name")

    # Call command - Enhanced with natural argument parsing
    call_parser = subparsers.add_parser("call", help="Call a tool")
    call_parser.add_argument("server", help="Server name")
    call_parser.add_argument("tool", help="Tool name")

    # Support for --var key=value arguments
    call_parser.add_argument(
        "--var",
        action="append",
        help="Tool argument as key=value pair (can be repeated)",
    )

    # Support for JSON fallback
    call_parser.add_argument(
        "--json",
        dest="json_args",
        help="Tool arguments as JSON string (fallback for complex arguments)",
    )

    # Parse known args to allow unknown flags for tool arguments
    args, unknown = parser.parse_known_args()

    # If we're in call command, process unknown args as tool arguments
    if args.command == "call":
        args.tool_args = unknown

    if not args.command:
        parser.print_help()
        sys.exit(1)

    global verbose_mode
    verbose_mode = args.verbose

    if not args.project_root.is_dir():
        die_mcp(
            f"Project root not a directory: {args.project_root}",
            json_output_flag=args.json_output,
        )

    config = load_mcp_config(args.project_root, args)

    result = asyncio.run(main_mcp_flow(args, config))

    if config.json_output:
        print(json.dumps(result, indent=2))
    else:
        # Human-readable output
        status_icon = {
            "success": f"{ANSI['G']}✓{ANSI['N']}",
            "failure": f"{ANSI['R']}✗{ANSI['N']}",
            "dry_run": f"{ANSI['Y']}◦{ANSI['N']}",
            "skipped": f"{ANSI['Y']}-{ANSI['N']}",
        }.get(result.get("status", "unknown"), "?")

        print(f"{status_icon} {result.get('message', 'Operation completed')}")

        # Show additional details for specific commands
        if args.command == "list" and "servers" in result:
            print("\nConfigured MCP Servers:")
            for server in result["servers"]:
                status_color = {
                    "connected": ANSI["G"],
                    "disconnected": ANSI["Y"],
                }.get(server["status"], ANSI["R"])

                disabled_indicator = " (disabled)" if server["disabled"] else ""
                print(
                    f"  • {server['name']}: {status_color}{server['status']}{ANSI['N']}{disabled_indicator}"
                )
                print(f"    Command: {server['command']}")
                print(f"    Operations: {server['operations_count']}")
                if "tools_count" in server:
                    print(f"    Tools: {server['tools_count']}")

        elif args.command == "tools" and "tools" in result:
            print(f"\nAvailable Tools on {args.server}:")
            for tool in result["tools"]:
                print(f"  • {tool.get('name', 'unnamed')}")
                if "description" in tool:
                    print(f"    {tool['description']}")
                if "inputSchema" in tool and "properties" in tool["inputSchema"]:
                    params = list(tool["inputSchema"]["properties"].keys())
                    print(f"    Parameters: {', '.join(params)}")

        elif args.command == "call" and "result" in result:
            print("\nTool Result:")
            if "content" in result["result"]:
                for content in result["result"]["content"]:
                    if content.get("type") == "text":
                        print(content.get("text", ""))
            else:
                print(json.dumps(result["result"], indent=2))

            # Show the parsed arguments if verbose
            if verbose_mode and "arguments" in result:
                print("\nParsed Arguments:")
                print(json.dumps(result["arguments"], indent=2))

    # Exit with appropriate code
    if result.get("status") == "failure":
        sys.exit(1)
    elif result.get("status") in ["timeout", "forbidden"]:
        sys.exit(2)


def main(argv: list[str] | None = None) -> None:
    """Entry point for khive CLI integration."""
    # Save original args
    original_argv = sys.argv

    # Set new args if provided
    if argv is not None:
        sys.argv = [sys.argv[0], *argv]

    try:
        cli_entry_mcp()
    finally:
        # Restore original args
        sys.argv = original_argv


if __name__ == "__main__":
    cli_entry_mcp()
