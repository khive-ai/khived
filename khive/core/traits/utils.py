import hashlib
from datetime import datetime
from uuid import UUID

from openai import BaseModel
import orjson


def sha256_of_dict(obj: dict) -> str:
    """Deterministic SHA-256 of an arbitrary mapping."""
    payload: bytes = orjson.dumps(
        obj,
        option=(
            orjson.OPT_SORT_KEYS  # canonical ordering
            | orjson.OPT_NON_STR_KEYS  # allow int / enum keys if you need them
        ),
    )
    return hashlib.sha256(memoryview(payload)).hexdigest()


def serialize_model_to_dict(m: BaseModel | dict | None, /, **kwargs) -> dict:
    """Serialize a Pydantic model to a dictionary. kwargs are passed to model_dump."""

    if isinstance(m, BaseModel):
        return m.model_dump(**kwargs)
    if m is None:
        return {}
    if isinstance(m, dict):
        return m

    raise ValueError(
        "Input value for field <model> should be a `pydantic.BaseModel` object or a `dict`"
    )


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
