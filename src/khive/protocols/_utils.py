from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


def serialize_model_to_dict(m: BaseModel | dict | None, /, **kwargs) -> dict:
    """Serialize a Pydantic model to a dictionary. kwargs are passed to model_dump."""

    if isinstance(m, BaseModel):
        return m.model_dump(**kwargs)
    if m is None:
        return {}
    if isinstance(m, dict):
        return m

    error_msg = "Input value for field <model> should be a `pydantic.BaseModel` object or a `dict`"
    raise ValueError(error_msg)


def serialize_id(value: UUID) -> str:
    """Serialize a UUID to a string."""
    return str(value)


def validate_id(value: str | UUID) -> UUID:
    """Validate and convert a string or UUID to a UUID."""
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except Exception as e:
        error_msg = "Input value for field <id> should be a `uuid.UUID` object or a valid `uuid` representation"
        raise ValueError(error_msg) from e


def serialize_datetime(value: datetime) -> str:
    """Serialize a datetime to an ISO format string."""
    return value.isoformat()


def validate_datetime(value: str | datetime) -> datetime:
    """Validate and convert a string or datetime to a datetime."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except Exception:
            pass

    error_msg = "Input value for field <created_at> should be a `datetime.datetime` object or `isoformat` string"
    raise ValueError(error_msg)
