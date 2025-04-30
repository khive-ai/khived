from __future__ import annotations

import json
from typing import Any, ClassVar

from pydantic import Field, field_validator

from khive._class_registry import LION_CLASS_REGISTRY
from khive.adapters.types import Adaptable, AdapterRegistry, NodeAdapterRegistry

from .element import Element

__all__ = ("Node",)


class Node(Element, Adaptable):
    """
    A base class for all Nodes in a graph, storing:
      - Arbitrary content
      - Metadata as a dict
      - An optional numeric embedding (list of floats)
      - Automatic subclass registration
    """

    _adapter_registry: ClassVar[AdapterRegistry] = NodeAdapterRegistry

    content: Any = None
    embedding: list[float] | None = Field(
        default_factory=list,
        description="Optional numeric embedding vector. Empty list or None are both valid.",
    )

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        """Initialize and register subclasses in the global class registry."""
        super().__pydantic_init_subclass__(**kwargs)
        LION_CLASS_REGISTRY[cls.class_name(full=True)] = cls

    @field_validator("embedding", mode="before")
    def _parse_embedding(cls, value: list[float] | str | None) -> list[float] | None:
        if value is None:
            return None
        if isinstance(value, str):
            if value == "":
                return None  # Empty string is treated as None
            try:
                loaded = json.loads(value)
                if not isinstance(loaded, list):
                    raise ValueError
                return [float(x) for x in loaded]
            except Exception as e:
                raise ValueError("Invalid embedding string.") from e
        if isinstance(value, list):
            try:
                return [float(x) for x in value]
            except Exception as e:
                raise ValueError("Invalid embedding list.") from e
        raise ValueError("Invalid embedding type; must be list or JSON-encoded string.")

    @classmethod
    def adapt_from(
        cls, obj: Any, obj_key: str, many: bool = False, **kwargs: Any
    ) -> Node:
        """
        Construct a Node from an external format using a registered adapter.
        If the adapter returns a dictionary with 'lion_class', we can
        auto-delegate to the correct subclass via from_dict.
        """
        result = cls._get_adapter_registry().adapt_from(
            cls, obj, obj_key, many=many, **kwargs
        )
        # If adapter returned multiple items, choose the first or handle as needed.
        if isinstance(result, list):
            result = result[0]
        return cls.from_dict(result)


# File: lionagi/protocols/graph/node.py
