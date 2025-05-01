"""
Utility functions for the protocols module.
"""

from datetime import datetime
from uuid import UUID


def serialize_id(value: UUID) -> str:
    """Serialize a UUID to a string."""
    return str(value)


def validate_id(value: str | UUID) -> UUID:
    """Validate and convert a string or UUID to a UUID."""
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except Exception:
        raise ValueError(
            "Input value for field <id> should be a `uuid.UUID` object or a valid `uuid` representation"
        )


def serialize_created_at(value: datetime) -> str:
    """Serialize a datetime to an ISO format string."""
    return value.isoformat()


def validate_created_at(value: str | datetime) -> datetime:
    """Validate and convert a string or datetime to a datetime."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except Exception:
            pass

    raise ValueError(
        "Input value for field <created_at> should be a `datetime.datetime` object or `isoformat` string"
    )
