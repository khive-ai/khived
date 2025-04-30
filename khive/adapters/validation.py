"""
Validation utilities for adapters.

This module provides validation functions that can be used by adapters
to validate data against schemas.
"""

from typing import Any, Optional, Type, TypeVar, cast

T = TypeVar("T")


def _validate(data: Any, schema: Type[T]) -> T:
    """
    Validate data against a schema using Pydantic.

    Parameters
    ----------
    data : Any
        The data to validate. If the data has a to_dict method, it will be called.
    schema : Type[T]
        The Pydantic model class to validate against.

    Returns
    -------
    T
        The validated data as an instance of the schema.

    Raises
    ------
    ImportError
        If Pydantic is not installed.
    ValidationError
        If the data does not match the schema.
    """
    try:
        from pydantic import TypeAdapter
    except ImportError:
        raise ImportError(
            "Package `pydantic` is needed for validation, please install via `pip install pydantic>=2.0.0`"
        )

    # Convert to dict if the object has a to_dict method
    if hasattr(data, "to_dict") and callable(getattr(data, "to_dict")):
        data = data.to_dict()

    # Use TypeAdapter for efficient validation
    adapter = TypeAdapter(schema)
    return cast(T, adapter.validate_python(data))


def validate_data(data: Any, schema: Optional[Type[T]] = None) -> Any:
    """
    Validate data against a schema if provided.

    This is a convenience function that can be used by adapters to validate
    data before returning it. If no schema is provided, the data is returned
    as-is.

    Parameters
    ----------
    data : Any
        The data to validate. If the data has a to_dict method, it will be called.
    schema : Optional[Type[T]]
        The Pydantic model class to validate against, or None to skip validation.

    Returns
    -------
    Any
        The validated data, or the original data if no schema was provided.
    """
    if schema is None:
        return data

    if isinstance(data, list):
        return [_validate(item, schema) for item in data]

    return _validate(data, schema)
