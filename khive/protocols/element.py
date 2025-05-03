from __future__ import annotations

import logging
from ast import TypeVar
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
)

from khive._class_registry import get_class
from khive.utils import import_module

from .utils import (
    serialize_created_at,
    serialize_id,
    sha256_of_dict,
    validate_created_at,
    validate_id,
)

logger = logging.getLogger(__name__)


__all__ = (
    "Metadata",
    "Element",
)


class Metadata:
    """Meta class for all elements in the system."""

    __slots__ = ("id", "created_at", "lion_class", "extra", "content_sha256")

    def __init__(
        self,
        id: UUID,
        created_at: datetime,
        lion_class: str,
        content_sha256: str | None = None,
        **kwargs,
    ):
        self.id = id
        self.created_at = created_at
        self.lion_class = lion_class
        self.content_sha256 = content_sha256
        if kwargs:
            self.extra = kwargs
        else:
            self.extra = {}

    @classmethod
    def create(cls, cls_type: type[Element], /, **kwargs) -> Metadata:
        """Create a new LionMeta with the current time and a new UUID."""
        return cls(
            id=uuid4(),
            created_at=datetime.now(UTC),
            lion_class=cls_type.class_name(full=True),
            **kwargs,
        )

    def to_dict(self, mode: Literal["json", "python"]) -> dict[str, Any]:
        """Convert this LionMeta to a dictionary."""
        return {
            "id": serialize_id(self.id) if mode == "json" else self.id,
            "created_at": (
                serialize_created_at(self.created_at)
                if mode == "json"
                else self.created_at
            ),
            "lion_class": self.lion_class,
            "content_sha256": self.content_sha256,
            **self.extra,
        }

    @classmethod
    def from_dict(cls, cls_type: type[Element], data: dict, /) -> Metadata:
        """Create a LionMeta from a dictionary.

        This method is used to restore a LionMeta from a dictionary
        previously produced by `to_dict`.
        """
        lion_class = data.get("lion_class")
        if lion_class != cls_type.class_name(full=True):
            raise ValueError(
                f"lion_class mismatch: {lion_class} != {cls_type.class_name(full=True)}"
            )
        data["id"] = validate_id(data.get("id"))
        data["created_at"] = validate_created_at(data.get("created_at"))
        return cls(**data)


class Element(BaseModel):
    """all elements in the system should inherit from this class. provides metadata, and polymorphic creation."""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=True,
        populate_by_name=True,
        extra="forbid",
    )

    metadata: Metadata = Field(
        default_factory=lambda: Metadata.create(Element),
        description="Meta class for Element.",
    )

    @field_serializer("metadata")
    def _serialize_metadata(self, v: Metadata) -> dict[str, Any]:
        self.get_content_sha256(update=True)
        return self.metadata.to_dict(mode="json")

    @field_validator("metadata", mode="before")
    def _validate_meta_before(cls, val: dict) -> Metadata:
        return Metadata.from_dict(cls, val)

    @field_validator("metadata", mode="after")
    def _validate_sha256(self, val: Metadata) -> Metadata:
        if val.content_sha256 is not None:
            if self.get_content_sha256(update=False) != val.content_sha256:
                raise ValueError(
                    f"Error in element instance re-creation: SHA256 mismatch"
                )
        return val

    def get_content_sha256(self, update=True) -> str:
        """Return the SHA256 hash of the content of this element.
        if update is True, update the content_sha256 in metadata.
        """
        dict_ = self.model_dump()
        dict_.pop("metadata")
        sha256 = sha256_of_dict(dict_)
        if update:
            self.metadata.content_sha256 = sha256
            return sha256

        if not self.metadata.content_sha256:
            self.metadata.content_sha256 = sha256
        return sha256

    @property
    def content_sha256(self) -> str:
        return self.metadata.content_sha256 or self.get_content_sha256()

    @property
    def id(self) -> UUID:
        """Return the unique identifier for this element."""
        return self.metadata.id

    @property
    def created_at(self) -> datetime:
        """Return the creation timestamp for this element."""
        return self.metadata.created_at

    @property
    def metaview(self):
        """Return an immutable view of metadata to prevent accidental side-effects."""
        return MappingProxyType(self.metadata.to_dict(mode="python"))

    @classmethod
    def class_name(cls, full: bool = False) -> str:
        """Returns this class's name. if full, returns the fully qualified name"""
        if full:
            return str(cls).split("'")[1]
        return cls.__name__

    def __hash__(self) -> int:
        """Make Element hashable based on its creation information."""
        return hash(self.id)

    def __bool__(self) -> bool:
        """Always True"""
        return True

    def __eq__(self, other) -> bool:
        if not isinstance(other, Element):
            return NotImplemented
        return self.id == other.id

    @classmethod
    def from_dict(cls, data: dict) -> Element:
        """Deserializes a json dictionary into an Element or subclass of Element.

        If `lion_class` in `metadata` refers to a subclass, this method
        attempts to create an instance of that subclass."""

        subcls: None | str = data.get("metadata", {}).get("lion_class")
        if subcls is not None and subcls != Element.class_name(True):
            try:
                subcls_type: type[Element] = get_class(subcls.split(".")[-1])
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


E = TypeVar("E", bound=Element)
