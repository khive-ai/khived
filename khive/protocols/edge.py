from abc import abstractmethod
from typing import Any
from uuid import UUID

from pydantic import Field, field_serializer, field_validator

from .element import ELEMENT_FIELDS, Element
from .node import Node

__all__ = (
    "EdgeCondition",
    "Edge",
)


class EdgeCondition:

    def __init__(self, source: Any = None):
        self.source = source

    @abstractmethod
    async def applies(self, *args, **kwargs) -> bool:
        pass


class Edge(Element):
    """
    An edge in a graph, connecting a head Node to a tail Node. Optional
    EdgeCondition can control traversal. Additional properties like labels,
    metadata, etc., may be stored in `properties`.
    """

    head: UUID
    tail: UUID
    properties: dict[str, Any] = Field(
        default_factory=dict,
        title="Properties",
        description="Custom properties associated with this edge.",
    )

    def __init__(
        self,
        head: Node,
        tail: Node,
        condition: EdgeCondition | None = None,
        label: list[str] | None = None,
        **kwargs,
    ):
        """
        Initialize an Edge.

        This constructor sets up an edge by linking a head node to a tail node,
        with optional conditions and labels. Additional properties can also be
        provided via keyword arguments.
        """
        if condition:
            if not isinstance(condition, EdgeCondition):
                raise ValueError("Condition must be an instance of EdgeCondition.")
            kwargs["condition"] = condition

        if label:
            label = [label] if not isinstance(label, list) else label
            if all(isinstance(i, str) for i in label):
                kwargs["label"] = label
            else:
                raise ValueError("Label must be a string or a list of strings.")

        if head.id == tail.id:
            raise ValueError("Head and tail nodes cannot be the same.")

        if not isinstance(head, Node):
            raise ValueError("Head must be an instance of Node.")

        if not isinstance(tail, Node):
            raise ValueError("Tail must be an instance of Node.")

        _kwargs = {}
        for key in ELEMENT_FIELDS:
            if (v := kwargs.pop(key, None)) is not None:
                _kwargs[key] = v

        super().__init__(head=head.id, tail=tail.id, properties=kwargs, **_kwargs)

    @field_serializer("head", "tail")
    def _serialize_head_tail(self, value: UUID) -> str:
        return self._serialize_id(value)

    @field_validator("head", "tail", mode="before")
    def _validate_head_tail(cls, value: UUID) -> UUID:
        return cls._validate_id(value)

    @property
    def label(self) -> list[str] | None:
        return self.properties.get("label")

    @property
    def condition(self) -> EdgeCondition | None:
        return self.properties.get("condition")

    @condition.setter
    def condition(self, value: EdgeCondition | None) -> None:
        if not isinstance(value, EdgeCondition):
            raise ValueError("Condition must be an instance of EdgeCondition.")
        self.properties["condition"] = value

    @label.setter
    def label(self, value: list[str] | None) -> None:
        if not value:
            self.properties["label"] = []
            return
        if isinstance(value, str):
            self.properties["label"] = [value]
            return
        if isinstance(value, list) and all(isinstance(i, str) for i in value):
            self.properties["label"] = value
            return
        raise ValueError("Label must be a string or a list of strings.")

    async def check_condition(self, *args, **kwargs) -> bool:
        """
        Check if this edge can be traversed, by evaluating any assigned condition.

        Returns:
            bool: True if condition is met or if no condition exists.
        """
        if self.condition:
            return await self.condition.applies(*args, **kwargs)
        return True
