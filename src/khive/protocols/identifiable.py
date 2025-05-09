from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from ._utils import serialize_datetime, serialize_id, validate_datetime, validate_id


class Identifiable(BaseModel):
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
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp for the element.",
        frozen=True,
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last updated timestamp for the element.",
    )

    def update_timestamp(self) -> None:
        """Update the last updated timestamp to the current time."""
        self.updated_at = datetime.now(UTC)

    @field_serializer("id")
    def _serialize_ids(self, v: UUID) -> str:
        return serialize_id(v)

    @field_validator("id", mode="before")
    def _validate_ids(cls, v: str | UUID) -> UUID:
        return validate_id(v)

    @field_serializer("created_at", "updated_at")
    def _serialize_created_updated(self, v: datetime) -> str:
        return serialize_datetime(v)

    @field_validator("created_at", "updated_at", mode="before")
    def _validate_created_updated(cls, v: str | datetime) -> datetime:
        return validate_datetime(v)
