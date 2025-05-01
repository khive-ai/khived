"""Utility functions for loading khivemcp configurations."""

import functools
import inspect
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

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
    def __init__(self, config: dict[str, Any] = None):
        self.group_config = config or {}


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
        raise FileNotFoundError(f"Configuration file not found: {path}")

    print(f"[Config Loader] Reading configuration from: {path}", file=sys.stderr)
    file_content = path.read_text(encoding="utf-8")

    try:
        data: dict
        if path.suffix.lower() in [".yaml", ".yml"]:
            data = yaml.safe_load(file_content)
            if not isinstance(data, dict):
                raise ValueError("YAML content does not resolve to a dictionary.")
            print(
                f"[Config Loader] Parsed YAML content from '{path.name}'",
                file=sys.stderr,
            )
        elif path.suffix.lower() == ".json":
            data = json.loads(file_content)
            if not isinstance(data, dict):
                raise ValueError("JSON content does not resolve to an object.")
            print(
                f"[Config Loader] Parsed JSON content from '{path.name}'",
                file=sys.stderr,
            )
        else:
            raise ValueError(f"Unsupported configuration file format: {path.suffix}")

        # Differentiate based on structure (presence of 'groups' dictionary)
        if "groups" in data and isinstance(data.get("groups"), dict):
            print(
                "[Config Loader] Detected ServiceConfig structure. Validating...",
                file=sys.stderr,
            )
            config_obj = ServiceConfig(**data)
            print(
                f"[Config Loader] ServiceConfig '{config_obj.name}' validated successfully.",
                file=sys.stderr,
            )
            return config_obj
        print(
            "[Config Loader] Assuming GroupConfig structure. Validating...",
            file=sys.stderr,
        )
        # GroupConfig requires 'class_path'
        if "class_path" not in data:
            raise ValueError(
                "Configuration appears to be GroupConfig but is missing the required 'class_path' field."
            )
        config_obj = GroupConfig(**data)
        print(
            f"[Config Loader] GroupConfig '{config_obj.name}' validated successfully.",
            file=sys.stderr,
        )
        return config_obj

    except (json.JSONDecodeError, yaml.YAMLError) as e:
        raise ValueError(f"Invalid file format in '{path.name}': {e}")
    except ValidationError as e:
        raise ValueError(f"Configuration validation failed for '{path.name}':\n{e}")
    except Exception as e:
        raise ValueError(
            f"Failed to load configuration from '{path.name}': {type(e).__name__}: {e}"
        )


def operation(
    name: str | None = None,
    description: str | None = None,
    schema: type[BaseModel] = None,
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
        raise TypeError("operation 'name' must be a string or None.")
    if description is not None and not isinstance(description, str):
        raise TypeError("operation 'description' must be a string or None.")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if not inspect.isfunction(func):
            # This might happen if applied to non-methods, although intended for methods
            raise TypeError("@khivemcp.operation can only decorate functions/methods.")
        if not inspect.iscoroutinefunction(func):
            raise TypeError(
                f"@khivemcp.operation requires an async function (`async def`), but got '{func.__name__}'."
            )

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
