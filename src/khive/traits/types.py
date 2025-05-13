# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from enum import Enum

from pydantic import BaseModel, field_validator

from khive.utils import validate_model_to_dict

__all__ = ("Embedding", "ExecutionStatus", "Execution", "Metadata")


Embedding = list[float]
Metadata = dict


class ExecutionStatus(str, Enum):
    """Status states for tracking action execution progress."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Execution(BaseModel):
    """Represents the execution state of an event."""

    duration: float | None = None
    response: dict | None = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    error: str | None = None

    @field_validator("response", mode="before")
    def _validate_response(cls, v: BaseModel | dict | None):
        return validate_model_to_dict(v)
