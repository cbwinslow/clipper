"""vaclip.models.schemas

Pydantic v2 domain models shared across all pipeline stages.
These are the canonical data contracts for the VAClip system.

Agent Instructions:
  - All fields should have clear descriptions via Field(..., description=...)
  - Use model_validator for cross-field validation
  - Keep models immutable (frozen=True) where possible
  - Add example() class methods for test fixtures
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class MediaType(str, Enum):
    """Supported ingest media types."""

    VIDEO = "video"
    AUDIO = "audio"
    PODCAST = "podcast"


class HighlightType(str, Enum):
    """Category of detected highlight moment."""

    LAUGH = "laugh"
    APPLAUSE = "applause"
    PEAK_ENERGY = "peak_energy"
    KEY_QUOTE = "key_quote"
    TOPIC_SHIFT = "topic_shift"
    REACTION = "reaction"
    GOAL = "goal"
    KNOCKOUT = "knockout"
    GENERIC = "generic"


class FramingStrategy(str, Enum):
    """Video framing / aspect-ratio strategy for exported clips."""

    WIDE = "wide"        # 16:9  landscape
    VERTICAL = "vertical"  # 9:16  portrait (Shorts / TikTok)
    SQUARE = "square"    # 1:1   Instagram


class Profile(str, Enum):
    """Processing profile that tunes scorer weights."""

    PODCAST = "podcast"
    GAMING = "gaming"
    SPORTS = "sports"
    INTERVIEW = "interview"
    GENERAL = "general"


# ---------------------------------------------------------------------------
# Ingest models
# ---------------------------------------------------------------------------


class MediaMeta(BaseModel, frozen=True):
    """Metadata extracted from a media source before transcription."""

    source_url: str = Field(..., description="Original URL or file path")
    local_path: Path = Field(..., description="Resolved local file path after download")
    duration_sec: float = Field(..., ge=0, description="Duration in seconds")
    media_type: MediaType = Field(MediaType.VIDEO, description="Detected media type")
    title: str | None = Field(None, description="Title from metadata or filename")
    width: int | None = Field(None, description="Video width in pixels")
    height: int | None = Field(None, description="Video height in pixels")
    fps: float | None = Field(None, description="Frames per second")
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    extra: dict[str, Any] = Field(default_factory=dict, description="Provider-specific extras")

    @classmethod
    def example(cls) -> "MediaMeta":
        """Return a fixture instance for tests."""
        return cls(
            source_url="https://youtube.com/watch?v=example",
            local_path=Path("/tmp/example.mp4"),
            duration_sec=3600.0,
            media_type=MediaType.PODCAST,
            title="Example Podcast Episode",
            width=1920,
            height=1080,
            fps=30.0,
        )


# ---------------------------------------------------------------------------
# Transcription models
# ---------------------------------------------------------------------------


class Word(BaseModel, frozen=True):
    """A single word with timing and confidence from the ASR engine."""

    text: str = Field(..., description="Raw word text")
    start: float = Field(..., ge=0, description="Start time in seconds")
    end: float = Field(..., ge=0, description="End time in seconds")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="ASR confidence score")

    @model_validator(mode="after")
    def end_after_start(self) -> "Word":
        if self.end < self.start:
            raise ValueError("Word.end must be >= Word.start")
        return self


class Segment(BaseModel, frozen=True):
    """A contiguous speech segment (sentence / phrase) from the ASR engine."""

    id: int = Field(..., description="Segment index within the transcript")
    text: str = Field(..., description="Full segment text")
    start: float = Field(..., ge=0, description="Start time in seconds")
    end: float = Field(..., ge=0, description="End time in seconds")
    words: list[Word] = Field(default_factory=list, description="Word-level timestamps")
    speaker: str | None = Field(None, description="Speaker label from diarization")
    language: str = Field("en", description="ISO 639-1 language code")

    @property
    def duration(self) -> float:
        return self.end - self.start

    @classmethod
    def example(cls) -> "Segment":
        return cls(
            id=0,
            text="This is an example sentence.",
            start=0.0,
            end=3.5,
            words=[
                Word(text="This", start=0.0, end=0.4),
                Word(text="is", start=0.5, end=0.7),
                Word(text="an", start=0.8, end=1.0),
                Word(text="example", start=1.1, end=1.6),
                Word(text="sentence.", start=1.7, end=2.2),
            ],
        )


class Transcript(BaseModel, frozen=True):
    """Full transcript produced by the ASR backend."""

    segments: list[Segment] = Field(default_factory=list)
    language: str = Field("en")
    model_name: str = Field(..., description="ASR model identifier (e.g. 'large-v3')")
    duration_sec: float = Field(..., ge=0)
    transcribed_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def full_text(self) -> str:
        return " ".join(s.text for s in self.segments)


# ---------------------------------------------------------------------------
# Scoring models
# ---------------------------------------------------------------------------


class SignalScore(BaseModel, frozen=True):
    """Individual signal contribution to the overall highlight score."""

    name: str = Field(..., description="Signal identifier (e.g. 'energy', 'sentiment')")
    raw: float = Field(..., description="Raw signal value")
    normalized: float = Field(..., ge=0.0, le=1.0, description="0-1 normalized value")
    weight: float = Field(1.0, ge=0.0, description="Profile weight applied")

    @property
    def weighted(self) -> float:
        return self.normalized * self.weight


class ScoredSegment(BaseModel):
    """A transcript segment annotated with highlight scores."""

    segment: Segment
    highlight_type: HighlightType = HighlightType.GENERIC
    signals: list[SignalScore] = Field(default_factory=list)
    score: float = Field(0.0, ge=0.0, description="Composite highlight score (0-1)")
    rank: int | None = Field(None, description="Rank among all segments (1 = best)")

    def compute_score(self) -> float:
        """Recompute and store composite score from signal contributions."""
        total_weight = sum(s.weight for s in self.signals) or 1.0
        self.score = sum(s.weighted for s in self.signals) / total_weight
        return self.score


# ---------------------------------------------------------------------------
# Export models
# ---------------------------------------------------------------------------


class ClipBounds(BaseModel, frozen=True):
    """Temporal bounds for a video clip with optional padding."""

    start: float = Field(..., ge=0, description="Clip start in seconds")
    end: float = Field(..., ge=0, description="Clip end in seconds")
    pad_start: float = Field(0.5, ge=0, description="Pre-roll padding seconds")
    pad_end: float = Field(0.5, ge=0, description="Post-roll padding seconds")

    @property
    def padded_start(self) -> float:
        return max(0.0, self.start - self.pad_start)

    @property
    def padded_end(self) -> float:
        return self.end + self.pad_end

    @property
    def duration(self) -> float:
        return self.padded_end - self.padded_start

    @model_validator(mode="after")
    def end_after_start(self) -> "ClipBounds":
        if self.end <= self.start:
            raise ValueError("ClipBounds.end must be > ClipBounds.start")
        return self


class ExportedClip(BaseModel):
    """A finalized output clip ready for delivery."""

    clip_id: str = Field(..., description="Unique clip identifier (UUID)")
    source_path: Path = Field(..., description="Original media file")
    output_path: Path = Field(..., description="Rendered clip file")
    bounds: ClipBounds
    framing: FramingStrategy = FramingStrategy.WIDE
    scored_segment: ScoredSegment
    exported_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def duration(self) -> float:
        return self.bounds.duration

    @property
    def is_short(self) -> bool:
        """True when the clip qualifies as a Short / Reel (<= 60 s)."""
        return self.duration <= 60.0
