"""Error classes for the khive library."""


class ItemExistsError(Exception):
    """Raised when attempting to add an item that already exists in a collection."""


class ItemNotFoundError(Exception):
    """Raised when attempting to access an item that doesn't exist in a collection."""


class MissingAdapterError(Exception):
    """Raised when an adapter is not found for a given type."""


class ClassNotFoundError(Exception):
    """Raised when a class cannot be found by name in the registry or dynamically."""
