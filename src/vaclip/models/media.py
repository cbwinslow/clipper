"""Media and source models for VAClip.

Defines the data contracts for source resolution, ingest staging,
and media metadata extraction stages.

Agent Notes:
- SourceType enum drives ingest adapter selection
- MediaMetadata is populated by ffprobe extraction
- IngestResult is the output contract from ingest stage
- Never add processing logic to these models
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field, field_validator

from vaclip.models.base import IdentifiedModel, VaClipBaseModel


class SourceType(str, Enum):
    """Supported ingest source types."""

    LOCAL = "local"
    YOUTUBE = "youtube"
    TWITCH = "twitch"
    KICK = "kick"
    RUMBLE = "rumble"
    GENERIC_URL = "generic_url"


class ContentProfile(str, Enum):
    """Content profile for scoring optimization."""

    PODCAST = "podcast"
    GAMING = "gaming"
    REACTION = "reaction"
    SPORTS = "sports"
    COMMENTARY = "commentary"
    INTERVIEW = "interview"
    EDUCATIONAL = "educational"
    GENERIC = "generic"


class ClipIntent(str, Enum):
    """Target clip detection intent."""

    FUNNY = "funny"
    INSIGHTFUL = "insightful"
    ACTION = "action"
    EMOTIONAL = "emotional"
    HYPE = "hype"
    HIGHLIGHT = "highlight"
    EDUCATIONAL = "educational"
    GENERIC = "generic"


class SourceRequest(VaClipBaseModel):
    """Input request for a source to be ingested.

    This is the entry point contract - everything starts here.
    """

    source: str = Field(description="Local file path or remote URL.")
    source_type: SourceType | None = Field(
        None, description="Force source type; auto-detected if None."
    )
    profile: ContentProfile = Field(
        ContentProfile.GENERIC, description="Content profile for scoring."
    )
    intent: ClipIntent = Field(ClipIntent.HIGHLIGHT, description="Target clip detection intent.")
    run_id: str | None = Field(None, description="Optional run ID for artifact grouping.")

    @field_validator("source")
    @classmethod
    def source_not_empty(cls, v: str) -> str:
        """Ensure source is not empty string."""
        if not v.strip():
            raise ValueError("source must not be empty")
        return v


class MediaMetadata(VaClipBaseModel):
    """Media file metadata extracted via ffprobe.

    Agent Notes:
    - Populated by FFprobeService.extract()
    - duration_seconds is the most critical field for segmentation
    - video_codec/audio_codec inform export decisions
    """

    file_path: str = Field(description="Absolute path to the media file.")
    duration_seconds: float = Field(description="Total duration in seconds.")
    width: int | None = Field(None, description="Video width in pixels.")
    height: int | None = Field(None, description="Video height in pixels.")
    fps: float | None = Field(None, description="Frames per second.")
    video_codec: str | None = Field(None, description="Video codec name.")
    audio_codec: str | None = Field(None, description="Audio codec name.")
    audio_sample_rate: int | None = Field(None, description="Audio sample rate in Hz.")
    audio_channels: int | None = Field(None, description="Number of audio channels.")
    file_size_bytes: int | None = Field(None, description="File size in bytes.")
    format_name: str | None = Field(None, description="Container format name.")
    bit_rate: int | None = Field(None, description="Overall bitrate in bits/s.")


class IngestResult(IdentifiedModel):
    """Output contract from the ingest stage.

    Agent Notes:
    - staged_path is where the local copy lives for downstream processing
    - audio_path is extracted audio for transcription (WAV/FLAC preferred)
    - metadata is populated after ffprobe extraction
    """

    source_request: SourceRequest
    staged_path: str = Field(description="Local path to staged media file.")
    audio_path: str | None = Field(None, description="Path to extracted audio file.")
    metadata: MediaMetadata | None = Field(None, description="ffprobe metadata.")
    run_id: str = Field(description="Unique run identifier for artifact grouping.")
