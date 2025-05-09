from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class Identifiable(BaseModel):
    """Base class for objects with a unique identifier and timestamps."""

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=True,
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the element.",
        frozen=True,
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp for the element.",
        frozen=True,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last updated timestamp for the element.",
    )

    def update_timestamp(self) -> None:
        """Update the last updated timestamp to the current time."""
        self.updated_at = datetime.now(timezone.utc)

    @field_serializer("id")
    def _serialize_ids(self, v: UUID) -> str:
        return str(v)

    @field_validator("id", mode="before")
    def _validate_ids(cls, v: str | UUID) -> UUID:
        if isinstance(v, UUID):
            return v
        try:
            return UUID(str(v))
        except Exception as e:
            error_msg = "Input value for field <id> should be a `uuid.UUID` object or a valid `uuid` representation"
            raise ValueError(error_msg) from e

    @field_serializer("created_at", "updated_at")
    def _serialize_created_updated(self, v: datetime) -> str:
        return v.isoformat()

    @field_validator("created_at", "updated_at", mode="before")
    def _validate_created_updated(cls, v: str | datetime) -> datetime:
        """Validate and convert a string or datetime to a datetime."""
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v)
            except Exception:
                pass

        error_msg = "Input value for field <created_at> should be a `datetime.datetime` object or `isoformat` string"
        raise ValueError(error_msg)
