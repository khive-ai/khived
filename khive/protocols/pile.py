from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, ClassVar, Generic, Iterator, TypeVar
from uuid import UUID

from pydantic import Field, field_serializer, field_validator
from pydantic.fields import FieldInfo
from typing_extensions import Self

from khive._errors import ItemExistsError, ItemNotFoundError
from khive.adapters.types import Adaptable, AdapterRegistry, PileAdapterRegistry

from .element import Element

T = TypeVar("T", bound=Element)
D = TypeVar("D", bound=Any)


__all__ = ("Pile",)


class Pile(Element, Adaptable, Generic[T]):
    order: list[UUID] = Field(
        default_factory=list,
        description="List of UUIDs representing the order of items in the pile.",
    )
    collections: dict[UUID, T] = Field(default_factory=dict)

    _adapter_registry: ClassVar[AdapterRegistry] = PileAdapterRegistry

    def clear(self) -> None:
        self.order.clear()
        self.collections.clear()

    def __pydantic_extra__(self) -> dict[str, FieldInfo]:
        return {
            "_async_lock": Field(default_factory=asyncio.Lock),
        }

    def __pydantic_private__(self) -> dict[str, FieldInfo]:
        return self.__pydantic_extra__()

    @field_validator("collections", mode="before")
    def _validate_item(cls, data: dict):
        for k, v in data.items():
            if isinstance(v, dict):
                data[k] = Element.from_dict(v)
        return data

    @field_serializer("collections")
    def _serialize_collections(self, data: dict[UUID, T]):
        return {str(k): v.to_dict() for k, v in data.items()}

    def __getstate__(self):
        """Prepare for pickling."""
        state = self.__dict__.copy()
        state["_async_lock"] = None
        return state

    def __setstate__(self, state):
        """Restore after unpickling."""
        self.__dict__.update(state)
        self._async_lock = asyncio.Lock()

    @property
    def async_lock(self):
        """Async lock."""
        if not hasattr(self, "_async_lock") or self._async_lock is None:
            self._async_lock = asyncio.Lock()
        return self._async_lock

    async def __aenter__(self) -> Self:
        """Enter async context."""
        await self.async_lock.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context."""
        self.async_lock.release()

    class AsyncPileIterator:
        def __init__(self, pile: Pile):
            self.pile = pile
            self.index = 0

        def __aiter__(self) -> AsyncIterator[T]:
            return self

        async def __anext__(self) -> T:
            if self.index >= len(self.pile):
                raise StopAsyncIteration
            item = self.pile[self.index]
            self.index += 1
            await asyncio.sleep(0)  # Yield control to the event loop
            return item

    async def __aiter__(self) -> AsyncIterator[T]:
        """Async iterate over items."""
        async with self.async_lock:
            current_order = self.order[:]

        for key in current_order:
            yield self.collections[key]
            await asyncio.sleep(0)  # Yield control to the event loop

    async def __anext__(self) -> T:
        """Async get next item."""
        try:
            return await anext(self.AsyncPileIterator(self))
        except StopAsyncIteration:
            raise StopAsyncIteration("End of pile")

    def __iter__(self) -> Iterator[T]:
        """Iterate over items safely."""
        current_order = self.order[:]
        for key in current_order:
            yield self.collections[key]

    def __next__(self) -> T:
        """Get next item."""
        try:
            return next(iter(self))
        except StopIteration:
            raise StopIteration("End of pile")

    def __len__(self) -> int:
        """Get length of pile."""
        return len(self.collections)

    def __contains__(self, item: T) -> bool:
        """Check if item is in pile."""
        return item in self.collections.values() or item in self.collections

    def __setitem__(
        self,
        key: UUID | int,
        item: T,
    ) -> None:
        if not isinstance(item, Element):
            raise TypeError(
                f"Invalid item type: {type(item)}. Expected Element instances."
            )
        if isinstance(key, UUID):
            if item.id != key:
                raise ValueError(
                    f"Item ID {item.id} does not match key {key}. "
                    "Use the item ID as the key."
                )
            if item.id not in self.collections:
                self.order.append(item.id)
            self.collections[item.id] = item

        elif isinstance(key, int):
            try:
                order = self.order[:]
                order[key] = item.id
                self.order = order
                self.collections[item.id] = item
            except IndexError:
                raise IndexError(
                    f"Index {key} out of range. Pile length is {len(self.order)}."
                )
        else:
            raise TypeError(f"Invalid key type: {type(key)}. Expected UUID or int.")

    # private methods
    def __getitem__(self, key: int | slice | UUID) -> list[T] | T:
        if isinstance(key, (int, slice)):
            try:
                # Get the UUID(s) at the specified index/slice
                uuid_keys = self.order[key]

                # Handle both single UUID and list of UUIDs
                if isinstance(uuid_keys, list):
                    result = [self.collections[uuid_key] for uuid_key in uuid_keys]
                else:
                    return self.collections[uuid_keys]

                return result
            except Exception as e:
                raise ItemNotFoundError(f"index {key}. Error: {e}")

        if isinstance(key, str):
            try:
                id_ = UUID(key)
                return self.collections[id_]
            except Exception as e:
                raise ItemNotFoundError(f"key {key}. Error: {e}")

        if isinstance(key, UUID):
            try:
                return self.collections[key]
            except Exception as e:
                raise ItemNotFoundError(f"key {key}. Error: {e}")

        raise TypeError(
            f"Invalid key type: {type(key)}. Expected int, slice, str, or UUID."
        )

    def __list__(self) -> list[T]:
        return [self.collections[id] for id in self.order]

    def insert(self, index: int, item: T, /):
        """Insert an item at the specified index.

        Args:
            index: The position to insert the item
            item: The Element to insert

        Raises:
            TypeError: If index is not an integer or item is not an Element
            ItemExistsError: If the item already exists in the pile
        """
        if not isinstance(index, int):
            raise TypeError(
                "The index for inserting items into a pile must be an integer"
            )
        if not isinstance(item, Element):
            raise TypeError("The item in a pile must be an instance of Element")
        if item.id in self.collections:
            raise ItemExistsError(f"Item({str(item.id)[:5]}...) already")
        # Store UUID in order list, not the item itself
        # This prevents unhashable object issues and reduces memory usage
        self.order.insert(index, item.id)
        self.collections[item.id] = item

    def append(self, item: T, /):
        self.insert(len(self.order), item)

    def extend(self, items: list[T] | Pile[T], /):
        if isinstance(items, Pile):
            items = list(items)
        if not isinstance(items, list):
            raise TypeError("The items to extend must be a list or a Pile")

        # Check for duplicates more efficiently
        item_ids = [i.id for i in items]
        dup_ids = set(item_ids) & set(self.collections.keys())
        if dup_ids:
            raise ItemExistsError(
                f"Item(s) {', '.join(str(id)[:5]+'...' for id in dup_ids)}) already exist"
            )

        to_add = {i.id: i for i in items}
        self.collections.update(to_add)
        self.order.extend(item_ids)

    def get(self, key: T | UUID, default=..., /) -> T | D:
        """lookup via item or id"""
        v = None
        if isinstance(key, Element):
            v = self.collections.get(key.id)
        if isinstance(key, UUID):
            v = self.collections.get(key)
        if v is None:
            if default is not ...:
                return default
            return v

        raise TypeError(
            "The indexing key for a `Pile.get()` should be an element instance or a UUID, to get items via integer or slice indexing, use `pile[index]` directly"
        )

    def update(self, item: T | list | Pile, /):
        items: list[T] = (
            list(item)
            if isinstance(item, Pile)
            else (item if isinstance(item, list) else [item])
        )
        orders = self.order[:]
        for i in items:
            if i.id not in self.collections:
                orders.append(i.id)
        self.collections.update({i.id: i for i in items})
        self.order = orders

    def keys(self):
        return iter(self.order)

    def values(self):
        return iter(self.collections[id] for id in self.order)

    def pop(self, key: int | UUID | T, default=..., /):

        try:
            item = self[key] if isinstance(key, int) else self.get(key)
        except Exception as e:
            raise e

        if item is None:
            if default is ...:
                raise ItemNotFoundError(
                    f"Key({str(key)[:5]}...) does not exist in the pile"
                )
            return default

        self.order.remove(item.id)
        return self.collections.pop(item.id)

    @classmethod
    def adapt_from(cls, obj: Any, obj_key: str, many: bool = False, **kwargs: Any):
        """Create from another format."""
        dict_ = cls._get_adapter_registry().adapt_from(
            subj_cls=cls, obj=obj, obj_key=obj_key, many=many, **kwargs
        )
        if isinstance(dict_, list):
            dict_ = {"collections": dict_}
        return cls.from_dict(dict_)
