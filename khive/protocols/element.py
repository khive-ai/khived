from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    PrivateAttr,
    field_serializer,
    field_validator,
)

from khive._class_registry import get_class
from khive.utils import import_module

from .utils import serialize_created_at, serialize_id, validate_created_at, validate_id

logger = logging.getLogger(__name__)


__all__ = (
    "ELEMENT_FIELDS",
    "Element",
    "Log",
)


class Element(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=True,
        populate_by_name=True,
        extra="forbid",
    )
    id: UUID = Field(
        default_factory=uuid4,
        title="ID",
        description="Unique identifier for this element.",
        frozen=True,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        title="Creation Timestamp",
        description="Timestamp of element creation.",
        frozen=True,
    )
    metadata: dict = Field(
        default_factory=dict,
        title="Metadata",
        description="Additional data for this element.",
    )

    @field_serializer("created_at")
    def _serialize_created_at(self, v: datetime):
        return serialize_created_at(v)

    @field_validator("created_at", mode="before")
    def _validate_created_at(cls, v: str | datetime):
        return validate_created_at(v)

    @field_serializer("id")
    def _serialize_id(self, v):
        return serialize_id(v)

    @field_validator("id", mode="before")
    def _validate_id(cls, v: str | UUID):
        return validate_id(v)

    @property
    def metaview(self):
        """Return an immutable view of metadata to prevent accidental side-effects."""
        return MappingProxyType(self.__dict__["metadata"])

    @field_validator("metadata", mode="before")
    def _validate_meta_integrity(cls, val: dict) -> dict:
        """Validates that `metadata` is a dictionary and checks class naming.

        If a `lion_class` field is present in `metadata`, it must match the
        fully qualified name of this class. Converts `metadata` to a dict
        if needed.
        """
        if not val:
            return {}
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except json.JSONDecodeError:
                pass
        if not isinstance(val, dict):
            raise ValueError("Invalid metadata.")

        if "lion_class" in val and val["lion_class"] != cls.class_name(full=True):
            raise ValueError("Metadata class mismatch.")
        # Check if lion_class key already exists and warn if it will be overwritten
        if "lion_class" in val and val["lion_class"] != cls.class_name(full=True):
            logger.warning(
                f"Overwriting existing lion_class key in metadata from {val['lion_class']} to {cls.class_name(full=True)}"
            )
        if not isinstance(val, dict):
            raise ValueError("Invalid metadata.")
        return val

    @classmethod
    def class_name(cls, full: bool = False) -> str:
        """Returns this class's name. full: True, returns the fully qualified class name; otherwise, returns only the class name."""
        if full:
            return str(cls).split("'")[1]
        return cls.__name__

    def __hash__(self) -> int:
        """Make Element hashable based on its ID.

        This allows Element objects to be used as dictionary keys and in sets.
        """
        return hash(self.id)

    def __eq__(self, other) -> bool:
        """Compare Elements based on their IDs.

        Two Elements are considered equal if they have the same ID.
        """
        if not isinstance(other, Element):
            return NotImplemented
        return self.id == other.id

    def to_dict(self) -> dict:
        """Converts this Element to a dictionary. Add lion_class to metadata"""
        dict_ = self.model_dump()
        # Make a copy of the metadata to avoid modifying the original
        metadata_copy = dict_.get("metadata", {}).copy()
        metadata_copy["lion_class"] = self.class_name(full=True)
        dict_["metadata"] = metadata_copy
        return dict_

    @classmethod
    def from_dict(cls, data: dict) -> Element:
        """Deserializes a dictionary into an Element or subclass of Element.

        If `lion_class` in `metadata` refers to a subclass, this method
        attempts to create an instance of that subclass."""

        subcls: None | str = data.get("metadata", {}).get("lion_class")
        if subcls is not None and subcls != Element.class_name(True):
            try:
                subcls_type: type = get_class(subcls.split(".")[-1])
            except Exception:
                try:
                    mod, imp = subcls.rsplit(".", 1)
                    subcls_type = import_module(mod, import_name=imp)
                except Exception:
                    pass

            if (
                hasattr(subcls_type, "from_dict")
                and subcls_type.from_dict.__func__ != cls.from_dict.__func__
            ):
                return subcls_type.from_dict(data)
        return cls.model_validate(data)


class Log(Element):
    """
    An immutable log entry that wraps a dictionary of content.

    Once created or restored from a dictionary, the log is marked
    as read-only.
    """

    content: dict[str, JsonValue]
    _immutable: bool = PrivateAttr(False)

    def __setattr__(self, name: str, value: Any) -> None:
        """Prevent mutation if log is immutable."""
        if getattr(self, "_immutable", False):
            raise AttributeError("This Log is immutable.")
        super().__setattr__(name, value)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Log:
        """
        Create a Log from a dictionary previously produced by `to_dict`.

        The dictionary must contain keys in `serialized_keys`.
        """
        self = cls.model_validate(data)
        self._immutable = True
        return self

    @classmethod
    def create(cls, content: Element | dict) -> Log:
        """
        Create a new Log from an Element, storing a dict snapshot
        of the element's data.
        """
        if hasattr(content, "to_dict"):
            content = content.to_dict()
        elif hasattr(content, "model_dump"):
            content = content.model_dump()

        if content == {}:
            logger.warning(
                "No content to log, or original data was of invalid type. Making an empty log..."
            )
            return cls(content={"error": "No content to log."})
        if not isinstance(content, dict):
            raise ValueError(
                "The input content for log creation should be of type `Element`, subclass of `pydantic.BaseModel` or a python dict"
            )

        return cls(content=content)


ELEMENT_FIELDS = {"id", "created_at", "metadata", "content", "embedding"}
