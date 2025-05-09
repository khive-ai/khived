"""Utility functions for loading khivemcp configurations."""

import functools
import importlib
import inspect
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

# Internal metadata attribute key
_KHIVEMCP_OP_META = "__khivemcp_op_meta__"


__all__ = (
    "GroupConfig",
    "ServiceConfig",
    "ServiceGroup",
    "load_config",
    "operation",
    "run_khivemcp_server",
)


class GroupConfig(BaseModel):
    """Configuration for a single service group instance."""

    name: str = Field(
        ...,
        description="Unique name for this specific group instance (used in MCP tool names like 'name.operation').",
    )
    class_path: str = Field(
        ...,
        description="Full Python import path to the ServiceGroup class (e.g., 'my_module.submodule:MyGroupClass').",
    )
    description: str | None = Field(
        None, description="Optional description of this group instance."
    )
    packages: list[str] = Field(
        default_factory=list,
        description="List of additional Python packages required specifically for this group.",
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Group-specific configuration dictionary passed to the group's __init__ if it accepts a 'config' argument.",
    )
    env_vars: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables specific to this group (currently informational, not automatically injected).",
    )

    @field_validator("class_path")
    def check_class_path_format(cls, v):
        if ":" not in v or v.startswith(".") or ":" not in v.split(".")[-1]:
            raise ValueError("class_path must be in the format 'module.path:ClassName'")
        return v


class ServiceConfig(BaseModel):
    """Configuration for a service containing multiple named group instances."""

    name: str = Field(..., description="Name of the overall service.")
    description: str | None = Field(
        None, description="Optional description of the service."
    )
    groups: dict[str, GroupConfig] = Field(
        ...,
        description="Dictionary of group configurations. The keys are logical identifiers for the instances within this service config.",
    )
    packages: list[str] = Field(
        default_factory=list,
        description="List of shared Python packages required across all groups in this service.",
    )
    env_vars: dict[str, str] = Field(
        default_factory=dict,
        description="Shared environment variables for all groups (currently informational, not automatically injected).",
    )


class ServiceGroup:
    def __init__(self, config: dict[str, Any] | None = None):
        self.group_config = config or {}


def validate_path(p: Path):
    if p.suffix.lower() not in [".yaml", ".yml", ".json"]:
        raise ValueError(
            f"Unsupported file format: {p.suffix}. Supported formats are .yaml, .yml, and .json."
        )


def print_to_stderr(message: str) -> None:
    """Prints a message to standard error output."""
    print(message, file=sys.stderr)


def load_config(path: Path) -> ServiceConfig | GroupConfig:
    """Load and validate configuration from a YAML or JSON file.

    Determines whether the file represents a ServiceConfig (multiple groups)
    or a GroupConfig (single group) based on structure.

    Args:
        path: Path to the configuration file.

    Returns:
        A validated ServiceConfig or GroupConfig object.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValueError: If the file format is unsupported, content is invalid,
            or required fields (like class_path for GroupConfig) are missing.
    """
    if not path.exists():
        error_msg = f"Configuration file not found: {path}"
        raise FileNotFoundError(error_msg)

    print(f"[Config Loader] Reading configuration from: {path}", file=sys.stderr)
    file_content = path.read_text(encoding="utf-8")

    def validate_yaml_or_json(d: dict, err_msg) -> None:
        if not isinstance(d, dict):
            raise TypeError(err_msg)
        if "class_path" not in data:
            error_msg = "Configuration appears to be GroupConfig but is missing the required 'class_path' field."
            raise ValueError(error_msg)

    try:
        data: dict
        validate_path(path)

        if path.suffix.lower() in [".yaml", ".yml"]:
            data = yaml.safe_load(file_content)
            validate_yaml_or_json(
                data, "YAML content does not resolve to a dictionary."
            )
            print_to_stderr(f"[Config Loader] Parsed YAML content from '{path.name}'")
        if path.suffix.lower() == ".json":
            data = json.loads(file_content)
            validate_yaml_or_json(
                data, "JSON content does not resolve to a dictionary."
            )
            print_to_stderr(f"[Config Loader] Parsed JSON content from '{path.name}'")

        if "groups" not in data:
            print_to_stderr(
                "[Config Loader] Assuming GroupConfig structure. Validating...",
            )
            config_obj = GroupConfig(**data)
            print_to_stderr(
                f"[Config Loader] GroupConfig '{config_obj.name}' validated successfully.",
            )
            return config_obj

        # Differentiate based on structure (presence of 'groups' dictionary)
        if isinstance(data.get("groups"), dict):
            print_to_stderr(
                "[Config Loader] Detected ServiceConfig structure. Validating...",
            )
            config_obj = ServiceConfig(**data)
            print_to_stderr(
                f"[Config Loader] ServiceConfig '{config_obj.name}' validated successfully.",
            )
            return config_obj

    except (json.JSONDecodeError, yaml.YAMLError) as e:
        error_msg = f"Invalid file format in '{path.name}'"
        raise ValueError(error_msg) from e
    except ValidationError as e:
        error_msg = f"Configuration validation failed for '{path.name}'"
        raise ValueError(error_msg) from e
    except Exception as e:
        error_msg = (
            f"Failed to load configuration from '{path.name}': {type(e).__name__}: {e}"
        )
        raise ValueError(error_msg) from e


def operation(
    name: str | None = None,
    description: str | None = None,
    schema: type[BaseModel] | None = None,
):
    """
    Decorator to mark an async method in an khivemcp group class as an operation.

    This attaches metadata used by the khivemcp server during startup to register
    the method as an MCP tool.

    Args:
        name: The local name of the operation within the group. If None, the
            method's name is used. The final MCP tool name will be
            'group_config_name.local_name'.
        description: A description for the MCP tool. If None, the method's
            docstring is used.
    """
    if name is not None and not isinstance(name, str):
        error_msg = "operation 'name' must be a string or None."
        raise TypeError(error_msg)
    if description is not None and not isinstance(description, str):
        error_msg = "operation 'description' must be a string or None."
        raise TypeError(error_msg)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if not inspect.isfunction(func):
            # This might happen if applied to non-methods, although intended for methods
            error_msg = "@khivemcp.operation can only decorate functions/methods."
            raise TypeError(error_msg)
        if not inspect.iscoroutinefunction(func):
            error_msg = f"@khivemcp.operation requires an async function (`async def`), but got '{func.__name__}'."
            raise TypeError(error_msg)

        op_name = name or func.__name__
        op_desc = (
            description
            or inspect.getdoc(func)
            or f"Executes the '{op_name}' operation."
        )
        if schema is not None:
            # Ensure the schema is a valid BaseModel subclass
            op_desc += f"Input schema: {schema.model_json_schema()}."

        # Store metadata directly on the function object
        setattr(
            func,
            _KHIVEMCP_OP_META,
            {
                "local_name": op_name,
                "description": op_desc,
                "is_khivemcp_operation": True,  # Explicit marker
            },
        )

        # The wrapper primarily ensures metadata is attached.
        # The original function (`func`) is what gets inspected for signature/hints.
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # We don't need complex logic here anymore. The registration process
            # will call the original bound method.
            request = kwargs.get("request")
            if request and schema:
                if isinstance(request, dict):
                    request = schema.model_validate(request)
                if isinstance(request, str):
                    request = schema.model_validate_json(request)

            return await func(*args, request=request)

        # Copy metadata to the wrapper as well, just in case something inspects the wrapper directly
        # (though registration should ideally look at the original func via __wrapped__)
        # setattr(wrapper, _khivemcp_OP_META, getattr(func, _khivemcp_OP_META))
        # Update: functools.wraps should handle copying attributes like __doc__, __name__
        # Let's ensure our custom attribute is also copied if needed, though maybe redundant.
        if hasattr(func, _KHIVEMCP_OP_META):
            setattr(wrapper, _KHIVEMCP_OP_META, getattr(func, _KHIVEMCP_OP_META))

        wrapper.doc = func.__doc__
        return wrapper

    return decorator


async def run_khivemcp_server(
    config: ServiceConfig | GroupConfig, transport: Literal["stdio", "sse"] = "sse"
) -> None:
    """Initializes and runs the FastMCP server based on loaded configuration."""

    from mcp.server.fastmcp import FastMCP  # type: ignore[import]

    server_name = config.name
    server_description = getattr(config, "description", None)

    # 1. Instantiate FastMCP Server
    mcp_server = FastMCP(name=server_name, instructions=server_description)
    print(f"[Server] Initializing FastMCP server: '{server_name}'", file=sys.stderr)

    # 2. Prepare List of Groups to Load
    groups_to_load: list[tuple[str, GroupConfig]] = []
    if isinstance(config, ServiceConfig):
        print_to_stderr(
            f"[Server] Loading groups from ServiceConfig '{config.name}'..."
        )
        group_names = set()
        for key, group_config in config.groups.items():
            if group_config.name in group_names:
                print(
                    f"[Error] Duplicate group name '{group_config.name}' in ServiceConfig key '{key}'. Group names must be unique.",
                    file=sys.stderr,
                )
                sys.exit(1)
            group_names.add(group_config.name)
            groups_to_load.append((group_config.class_path, group_config))
    elif isinstance(config, GroupConfig):
        print(
            f"[Server] Loading single group from GroupConfig '{config.name}'...",
            file=sys.stderr,
        )
        if not hasattr(config, "class_path") or not config.class_path:
            print_to_stderr(
                f"[Error] GroupConfig '{config.name}' needs 'class_path'.",
            )
            sys.exit(1)
        groups_to_load.append((config.class_path, config))
    else:
        print_to_stderr("[Error] Invalid config type.")
        sys.exit(1)

    print(
        f"[Server] Found {len(groups_to_load)} group configuration(s).", file=sys.stderr
    )

    # 3. Load Groups and Register Tools using khivemcp Decorator Info
    total_tools_registered = 0
    registered_tool_names = (
        set()
    )  # Track registered MCP tool names to prevent duplicates

    for class_path, group_config in groups_to_load:
        group_name_from_config = group_config.name
        print_to_stderr(
            f"  [Loader] Processing Group Instance: '{group_name_from_config}' (Class Path: {class_path})"
        )
        try:
            # Dynamic Import
            module_path, class_name = class_path.rsplit(":", 1)
            module = importlib.import_module(module_path)
            group_cls = getattr(module, class_name)
            print_to_stderr(
                f"    [Loader] Imported class '{class_name}' from module '{module_path}'"
            )

            # Instantiate Group - Pass config if __init__ accepts 'config'
            group_instance = None
            try:
                sig = inspect.signature(group_cls.__init__)
                if "config" in sig.parameters:
                    group_instance = group_cls(config=group_config.config)
                    print_to_stderr(
                        f"    [Loader] Instantiated '{group_name_from_config}' (passed config dict)"
                    )
                else:
                    group_instance = group_cls()
                    print_to_stderr(
                        f"    [Loader] Instantiated '{group_name_from_config}' (no config dict passed)"
                    )
            except Exception as init_e:
                print(
                    f"    [Error] Failed to instantiate group '{group_name_from_config}': {init_e}",
                    file=sys.stderr,
                )
                continue  # Skip this group if instantiation fails

            # Find and Register Tools based on @khivemcp.decorators.operation
            group_tools_registered = 0
            for member_name, member_value in inspect.getmembers(group_instance):
                # Check if it's an async method and has our decorator's metadata
                if inspect.iscoroutinefunction(member_value) and hasattr(
                    member_value, _KHIVEMCP_OP_META
                ):
                    # Verify it's the correct marker
                    op_meta = getattr(member_value, _KHIVEMCP_OP_META, {})
                    if op_meta.get("is_khivemcp_operation") is not True:
                        continue  # Not our decorator

                    local_op_name = op_meta.get("local_name")
                    op_description = op_meta.get("description")

                    if local_op_name:
                        # Construct the full MCP tool name
                        full_tool_name = f"{group_name_from_config}_{local_op_name}"

                        # Check for duplicate MCP tool names across all groups
                        if full_tool_name in registered_tool_names:
                            print_to_stderr(
                                f"      [Register] ERROR: Duplicate MCP tool name '{full_tool_name}' detected (from group '{group_name_from_config}', method '{member_name}'). Tool names must be unique across the entire service."
                            )
                            # Optionally exit or just skip registration
                            continue  # Skip this duplicate tool

                        # Register the BOUND instance method directly with FastMCP
                        print_to_stderr(
                            f"      [Register] Method '{member_name}' as MCP tool '{full_tool_name}'"
                        )
                        try:
                            # For methods that take a Context parameter, we need to adapt them to work with FastMCP
                            # FastMCP automatically creates a context object, we just need to make sure it's used
                            # method_sig = inspect.signature(member_value)
                            # params = list(method_sig.parameters.values())

                            # Register the tool directly - FastMCP will handle parameters appropriately
                            mcp_server.add_tool(
                                member_value,  # The bound method from the instance
                                name=full_tool_name,
                                description=op_description,
                            )
                            registered_tool_names.add(
                                full_tool_name
                            )  # Track registered name
                            group_tools_registered += 1
                        except Exception as reg_e:
                            print_to_stderr(
                                f"      [Error] Failed registering tool '{full_tool_name}': {reg_e}"
                            )
                            # Potentially log traceback here
                    else:
                        # This case should ideally not happen if decorator enforces name
                        print_to_stderr(
                            f"      [Register] WARNING: Method '{member_name}' in group '{group_name_from_config}' decorated but missing local name. Skipping."
                        )

            if group_tools_registered == 0:
                print_to_stderr(
                    f"    [Loader] INFO: No methods decorated with @khivemcp.operation found or registered for group '{group_name_from_config}'."
                )
            total_tools_registered += group_tools_registered

        except ModuleNotFoundError:
            print_to_stderr(
                f"  [Error] Module not found for group '{group_name_from_config}' at path '{module_path}'. Check config and PYTHONPATH."
            )
        except AttributeError:
            print_to_stderr(
                f"  [Error] Class '{class_name}' not found in module '{module_path}' for group '{group_name_from_config}'. Check config."
            )
        except Exception as e:
            print_to_stderr(
                f"  [Error] Failed during loading or registration for group '{group_name_from_config}': {type(e).__name__}: {e}"
            )

    if total_tools_registered == 0:
        print_to_stderr(
            "[Warning] No khivemcp operations were successfully registered. The server will run but offer no tools."
        )

    # 4. Start the FastMCP Server (using stdio transport by default)
    print_to_stderr(
        f"[Server] Tool registration complete ({total_tools_registered} tools registered). Starting server via stdio..."
    )
    try:
        # This is a blocking call
        if transport == "stdio":
            print_to_stderr("[Server] Running server with stdio transport...")
            await mcp_server.run_stdio_async()
        elif transport == "sse":
            print_to_stderr("[Server] Running server with SSE transport...")
            await mcp_server.run_sse_async()
        else:
            print_to_stderr(
                f"[Error] Unsupported transport '{transport}'. Supported transports are 'stdio' and 'sse'.",
            )
            sys.exit(1)
    except Exception as e:
        print_to_stderr(
            f"\n[Error] MCP server execution failed unexpectedly: {type(e).__name__}: {e}"
        )
        # Consider logging the full traceback here for debugging
        # import traceback
        # traceback.print_exc(file=sys.stderr)
        sys.exit(1)  # Exit with error code
    finally:
        # This might not be reached if run_xxx_async runs indefinitely until interrupted
        print("[Server] Server process finished.", file=sys.stderr)
