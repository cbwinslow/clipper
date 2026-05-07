"""Base Pydantic models for VAClip boundary contracts.

All shared/inherited model base classes live here.
Do NOT put domain-specific models here - use dedicated model files.

Agent Notes:
- All models use Pydantic v2 syntax
- Use model_config = ConfigDict(...) for configuration
- Prefer frozen=True for immutable value objects
- Use field validators with @field_validator for complex validation
- Add examples to Field() for documentation
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class VaClipBaseModel(BaseModel):
    """Base model for all VAClip Pydantic models.

    Provides common configuration and utility methods.
    All domain models should inherit from this class.
    """

    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize model to dict for artifact persistence."""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VaClipBaseModel":
        """Deserialize model from dict (e.g., from JSON artifact)."""
        return cls.model_validate(data)


class TimestampedModel(VaClipBaseModel):
    """Base model for entities with creation/update timestamps."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class IdentifiedModel(TimestampedModel):
    """Base model for entities with a unique run/artifact ID."""

    id: UUID = Field(default_factory=uuid4, description="Unique identifier for this entity.")
