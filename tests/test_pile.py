import asyncio

import pytest

from khive.protocols.node import Node
from khive.protocols.pile import Pile


def test_clear_resets_lock():
    """Test that clear() resets the async lock."""
    pile = Pile()

    # Add some items
    nodes = [Node() for _ in range(3)]
    for node in nodes:
        pile.append(node)

    # Get the original lock
    original_lock = pile.async_lock

    # Clear the pile
    pile.clear()

    # Verify the lock was reset
    assert pile.async_lock is not original_lock
    assert isinstance(pile.async_lock, asyncio.Lock)

    # Verify the pile is empty
    assert len(pile) == 0
    assert len(pile.order) == 0
    assert len(pile.collections) == 0


@pytest.mark.asyncio
async def test_async_lock_after_clear():
    """Test that the async lock works correctly after clearing."""
    pile = Pile()

    # Add some items
    nodes = [Node() for _ in range(3)]
    for node in nodes:
        pile.append(node)

    # Clear the pile
    pile.clear()

    # Test that the lock works in async context
    async with pile:
        # We should be able to acquire the lock
        assert pile.async_lock.locked()

    # After exiting the context, the lock should be released
    assert not pile.async_lock.locked()
