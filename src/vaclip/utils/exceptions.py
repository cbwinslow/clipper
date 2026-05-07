"""Custom exception hierarchy for VAClip.

All VAClip exceptions inherit from VaClipError.
Use specific subclasses to allow precise error handling.

Agent Notes:
- Always raise specific subclasses, never bare VaClipError
- Always log before raising using structlog
- Include context data in exception messages
- Use VaClipRetryableError for transient failures (network, etc.)
"""

from __future__ import annotations


class VaClipError(Exception):
    """Base exception for all VAClip errors."""


class VaClipConfigError(VaClipError):
    """Raised when configuration is invalid or missing."""


class VaClipIngestError(VaClipError):
    """Raised when ingest/download fails."""


class VaClipIngestRetryableError(VaClipIngestError):
    """Raised for transient ingest failures that can be retried."""


class VaClipUnsupportedSourceError(VaClipIngestError):
    """Raised when no adapter supports the given source."""


class VaClipMediaError(VaClipError):
    """Raised when media processing (ffprobe, ffmpeg) fails."""


class VaClipTranscriptionError(VaClipError):
    """Raised when transcription fails."""


class VaClipSegmentationError(VaClipError):
    """Raised when shot detection or candidate generation fails."""


class VaClipScoringError(VaClipError):
    """Raised when clip scoring fails."""


class VaClipExportError(VaClipError):
    """Raised when clip export/rendering fails."""


class VaClipArtifactError(VaClipError):
    """Raised when artifact read/write fails."""


class VaClipModelError(VaClipError):
    """Raised when ML model loading or inference fails."""


class VaClipOpenRouterError(VaClipError):
    """Raised when OpenRouter API call fails."""


class VaClipValidationError(VaClipError):
    """Raised when data validation fails outside of Pydantic."""


class VaClipPipelineError(VaClipError):
    """Raised when pipeline orchestration fails."""

    def __init__(self, stage: str, message: str, cause: Exception | None = None) -> None:
        """Initialize with stage name for better diagnostics."""
        super().__init__(f"[{stage}] {message}")
        self.stage = stage
        self.cause = cause
