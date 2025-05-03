from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, JsonValue, PrivateAttr

from .element import Element

logger = logging.getLogger(__name__)


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
    def create(cls, content: BaseModel | dict) -> Log:
        """
        Create a new Log from an Element, storing a dict snapshot
        of the element's data.
        """
        if isinstance(content, BaseModel):
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


ELEMENT_FIELDS = {"id", "created_at", "metadata"}
