from __future__ import annotations

import logging
from abc import ABC
from ast import TypeVar
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any, Literal
from uuid import UUID, uuid4

from ..core.traits.utils import (
    serialize_created_at,
    serialize_id,
    validate_created_at,
    validate_id,
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
    def create(cls, cls_type: type[Identifiable], /, **kwargs) -> Metadata:
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
    def from_dict(cls, cls_type: type[Identifiable], data: dict, /) -> Metadata:
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

    @property
    def view(self) -> MappingProxyType:
        """Return an immutable view of metadata to prevent accidental side-effects."""
        return MappingProxyType(self.to_dict(mode="python"))
