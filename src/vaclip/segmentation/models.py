"""Segmentation models for VAClip.

Defines the ClipCandidate model representing a candidate video segment identified
by the segmentation stage.
"""

from __future__ import annotations

from pydantic import Field, model_validator

from vaclip.models.base import IdentifiedModel
from vaclip.models.schemas import FramingStrategy


class ClipCandidate(IdentifiedModel):
    """A candidate clip segment produced by the segmentation stage.

    Attributes:
        start: Start time in seconds (>= 0).
        end: End time in seconds (must be > start).
        framing: Desired output framing strategy.
        segment_id: Identifier linking back to the original transcript segment.
        start_word: Index of the first word in the clip (within transcript segment).
        end_word: Index of the last word in the clip (within transcript segment).
    """

    start: float = Field(..., ge=0, description="Clip start time in seconds")
    end: float = Field(..., ge=0, description="Clip end time in seconds")
    framing: FramingStrategy = Field(
        FramingStrategy.WIDE,
        description="Framing strategy for the exported clip",
    )
    segment_id: int = Field(..., description="ID of the source transcript segment")
    start_word: int = Field(..., ge=0, description="Index of first word in clip")
    end_word: int = Field(..., ge=0, description="Index of last word in clip")

    @model_validator(mode="after")
    def end_after_start(self) -> ClipCandidate:
        if self.end <= self.start:
            raise ValueError("ClipCandidate.end must be > ClipCandidate.start")
        return self

    @model_validator(mode="after")
    def word_indices_valid(self) -> ClipCandidate:
        if self.end_word < self.start_word:
            raise ValueError("ClipCandidate.end_word must be >= ClipCandidate.start_word")
        return self

    @classmethod
    def example(cls) -> ClipCandidate:
        """Return a fixture instance for tests."""
        return cls(
            start=12.5,
            end=45.0,
            framing=FramingStrategy.WIDE,
            segment_id=3,
            start_word=15,
            end_word=120,
        )
