from .identifiable import Identifiable
from datetime import datetime, timezone
from pydantic import Field, field_serializer, field_validator


__all__ = (
    "Temporal",
)

class Temporal(Identifiable):
    """Allows for updating the last updated timestamp."""

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last updated timestamp for the element.",
    )

    def update_timestamp(self) -> None:
        """Update the last updated timestamp to the current time."""
        self.updated_at = datetime.now(timezone.utc)

    @field_serializer("updated_at")
    def _serialize_updated_at(self, v: datetime) -> str:
        return self._serialize_datetime_obj(v)

    @field_validator("updated_at", mode="before")
    def _validate_datetime_obj(cls, v: str | datetime) -> datetime:
        return super()._validate_datetime_obj(v)
