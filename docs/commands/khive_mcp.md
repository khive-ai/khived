# khive mcp

**Purpose**: MCP (Model Context Protocol) server management and tool execution
interface.

## Synopsis

```bash
khive mcp list                           # List configured servers
khive mcp status [server]                # Show server status
khive mcp tools <server>                 # List available tools
khive mcp call <server> <tool> [args]    # Call a tool
```

## Key Features

- **MCP Protocol**: JSON-RPC 2.0 over stdin/stdout transport
- **Server Management**: Start, stop, and monitor MCP server lifecycle
- **Tool Discovery**: Automatically discover available server tools
- **Persistent Connections**: Maintain long-running server connections
- **Security Controls**: Tool allowlists and execution timeouts

## Command Options

| Option           | Type   | Default | Description                            |
| ---------------- | ------ | ------- | -------------------------------------- |
| `--project-root` | `path` | `cwd`   | Override project root directory        |
| `--json-output`  | `flag` | `false` | Output structured JSON results         |
| `--dry-run`      | `flag` | `false` | Show planned actions without execution |
| `--verbose`      | `flag` | `false` | Enable detailed output                 |

## Exit Codes

- `0`: Success
- `1`: Command failed or server error
- `2`: Timeout or permission denied

## Configuration

### Server Config (`.khive/mcps/config.json`)

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/path/to/allowed"
      ],
      "env": {
        "NODE_ENV": "development"
      },
      "alwaysAllow": ["read_file", "write_file", "list_directory"],
      "disabled": false,
      "timeout": 30
    },
    "database": {
      "command": "python",
      "args": ["-m", "mcp_server_sqlite", "--db-path", "data/app.db"],
      "alwaysAllow": ["query", "list_tables"],
      "timeout": 60
    }
  }
}
```

### Server Configuration Fields

| Field         | Type       | Required | Description                                 |
| ------------- | ---------- | -------- | ------------------------------------------- |
| `command`     | `string`   | Yes      | Executable command to start server          |
| `args`        | `string[]` | No       | Command line arguments                      |
| `env`         | `object`   | No       | Environment variables                       |
| `alwaysAllow` | `string[]` | No       | Auto-approved tool names                    |
| `disabled`    | `boolean`  | No       | Skip server during operations               |
| `timeout`     | `number`   | No       | Connection timeout in seconds (default: 30) |

## Tool Argument Formats

The `call` command supports multiple natural argument formats:

### Flag-based Arguments

```bash
# Simple values
khive mcp call server tool --key value --another_key "value with spaces"

# Boolean flags (no value = true)
khive mcp call server tool --enabled --verbose
```

### Key=Value Pairs

```bash
# Using --var syntax
khive mcp call server tool --var key=value --var path=/home/user

# JSON values in --var
khive mcp call server tool --var config='{"debug":true}' --var items='[1,2,3]'
```

### JSON Fallback

```bash
# For very complex nested structures
khive mcp call server tool --json '{"complex":{"nested":{"structure":"here"}}}'
```

### Mixed Usage

```bash
# Combine different formats
khive mcp call server tool --path file.txt --var mode=read --json '{"options":{"detailed":true}}'
```

### Type Handling

- String values: `--key value` or `--var key=value`
- JSON values: `--var key='{"json":"object"}'` (auto-parsed)
- Boolean flags: `--enabled` (becomes `{"enabled": true}`)
- Arrays: `--var items='[1,2,3]'` (auto-parsed)

## Commands

### list

List all configured MCP servers with status information.

```bash
khive mcp list [--json-output]
```

**Output**: Server names, status (connected/disconnected), tool counts

### status

Show detailed status for specific server or all servers.

```bash
khive mcp status [server] [--json-output]
```

**Output**: Connection state, server info, available tools, configuration

### tools

List all available tools on a specific MCP server.

```bash
khive mcp tools <server> [--json-output]
```

**Output**: Tool names, descriptions, parameter schemas

### call

Execute a tool on a specific MCP server.

```bash
khive mcp call <server> <tool> [--key value] [--var key=value] [--json args] [--json-output]
```

**Arguments**: Natural CLI flags, key=value pairs, or JSON fallback

## Output Formats

### JSON Output (`--json-output`)

#### List Command

```json
{
  "status": "success",
  "message": "Found 2 configured MCP servers",
  "servers": [
    {
      "name": "filesystem",
      "command": "npx",
      "disabled": false,
      "operations_count": 3,
      "status": "connected",
      "tools_count": 5
    }
  ],
  "total_count": 2
}
```

#### Status Command

```json
{
  "status": "success",
  "message": "Status for server 'filesystem'",
  "server": {
    "name": "filesystem",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem"],
    "status": "connected",
    "server_info": {
      "name": "filesystem-server",
      "version": "1.0.0"
    },
    "tools": [...]
  }
}
```

#### Tools Command

```json
{
  "status": "success",
  "message": "Found 5 tools on server 'filesystem'",
  "server": "filesystem",
  "tools": [
    {
      "name": "read_file",
      "description": "Read the complete contents of a file",
      "inputSchema": {
        "type": "object",
        "properties": {
          "path": { "type": "string", "description": "File path to read" }
        },
        "required": ["path"]
      }
    }
  ]
}
```

#### Call Command

```json
{
  "status": "success",
  "message": "Tool 'read_file' executed successfully",
  "server": "filesystem",
  "tool": "read_file",
  "arguments": {
    "path": "config.json",
    "encoding": "utf-8"
  },
  "result": {
    "content": [
      {
        "type": "text",
        "text": "File contents here..."
      }
    ]
  }
}
```

### Text Output (default)

```bash
# List output
✓ Found 2 configured MCP servers

Configured MCP Servers:
  • filesystem: connected
    Command: npx
    Operations: 3
    Tools: 5
  • database: disconnected (disabled)
    Command: python
    Operations: 2

# Tools output
✓ Found 5 tools on filesystem

Available Tools on filesystem:
  • read_file
    Read the complete contents of a file
    Parameters: path
  • write_file
    Write content to a file
    Parameters: path, content
```

## Usage Examples

```bash
# List all configured servers
khive mcp list

# Check status of specific server
khive mcp status filesystem

# List tools available on a server
khive mcp tools filesystem

# Call tools with natural CLI arguments
khive mcp call filesystem read_file --path config.json
khive mcp call filesystem write_file --path test.txt --content "Hello world"
khive mcp call database query --sql "SELECT * FROM users LIMIT 10"

# Use --var syntax for key=value pairs
khive mcp call filesystem read_file --var path=config.json
khive mcp call filesystem write_file --var path=test.txt --var content="Hello world"

# Boolean flags
khive mcp call filesystem list_directory --recursive --show_hidden

# Complex arguments with JSON values
khive mcp call api request --var method=POST --var headers='{"Content-Type":"application/json"}'

# Mixed usage
khive mcp call filesystem read_file --path config.json --var encoding=utf-8

# JSON fallback for very complex cases
khive mcp call complex_tool action --json '{"nested":{"deeply":{"complex":"structure"}}}'

# JSON output for automation
khive mcp list --json-output

# Dry run to see what would happen
khive mcp call filesystem write_file --path test.txt --content "hello" --dry-run
```

## MCP Protocol Details

### Initialization Sequence

1. Start server process with stdin/stdout pipes
2. Send `initialize` request with protocol version and capabilities
3. Receive server info and capabilities
4. Send `notifications/initialized` to complete handshake
5. Send `tools/list` to discover available tools

### Tool Execution

1. Validate tool exists and is allowed
2. Send `tools/call` request with tool name and arguments
3. Receive tool result or error response
4. Parse and return structured result

### Connection Management

- Maintains persistent connections to servers
- Automatic reconnection on connection loss
- Graceful shutdown with `notifications/cancelled`
- Process cleanup on timeout or error

## Security Considerations

### Tool Allowlists

- `alwaysAllow`: Tools that execute without confirmation
- Unlisted tools require explicit approval
- Empty allowlist blocks all tool execution

### Timeouts

- Connection timeout prevents hanging on server start
- Request timeout prevents indefinite waits
- Configurable per server

### Process Security

- Servers run as separate processes
- Environment isolation through custom env vars
- Automatic process cleanup on exit

## Error Handling

### Common Error Conditions

- Server not found in configuration
- Server process failed to start
- Tool not found on server
- Tool execution failed
- Connection timeout
- Invalid JSON arguments

### Status Values

- `success`: Operation completed successfully
- `failure`: Operation failed with error
- `dry_run`: Dry run mode, no execution
- `timeout`: Operation timed out
- `forbidden`: Tool not allowed

## Integration Notes

- **Protocol Standard**: Implements MCP specification JSON-RPC 2.0
- **State Persistence**: Maintains server connections across commands
- **Configuration**: Uses standard `.khive/mcps/config.json` format
- **Server Discovery**: Automatic tool discovery via `tools/list`
- **Error Recovery**: Automatic reconnection and process cleanup
- **Security**: Tool allowlists and execution timeouts
