"""Abstract base class for all ingest adapters.

All source adapters (local, yt-dlp, etc.) must inherit from IngestAdapter
and implement the abstract methods defined here.

Agent Notes:
- Use @abstractmethod for all required methods
- IngestAdapter.resolve() should determine SourceType from the source string
- IngestAdapter.download() should return a local staged file path
- IngestAdapter.supports() is the polymorphic dispatch method
- Event hooks: on_start, on_progress, on_complete, on_error
- Use tenacity for retry logic in subclasses
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from vaclip.models.media import MediaAsset

from vaclip.models.media import SourceRequest, SourceType

# Type alias for event hook callbacks
ProgressCallback = Callable[[float, str], None]  # (progress_pct, message)


class IngestAdapter(ABC):
    """Abstract base class for all VAClip ingest source adapters.

    Subclasses must implement: supports(), download()
    Subclasses should call super().__init__() and use self._hooks
    for event-driven progress reporting.

    Example subclasses:
    - LocalFileAdapter  (SourceType.LOCAL)
    - YtDlpAdapter      (SourceType.YOUTUBE, TWITCH, KICK, RUMBLE, GENERIC_URL)
    """

    def __init__(
        self,
        on_progress: Optional[ProgressCallback] = None,
        on_complete: Optional[Callable[["MediaAsset"], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> None:
        """Initialize the adapter with optional event hook callbacks."""
        self._on_progress = on_progress
        self._on_complete = on_complete
        self._on_error = on_error

    @abstractmethod
    def supports(self, source: str) -> bool:
        """Return True if this adapter can handle the given source string.

        Used for polymorphic adapter selection in IngestService.
        Adapters are tried in registration order; first match wins.

        Args:
            source: Local path or remote URL string.

        Returns:
            True if this adapter handles this source type.
        """
        ...

    @abstractmethod
    def ingest(self, source: str, profile: str = "generic") -> "MediaAsset":
        """Download/stage the source and return a MediaAsset.

        Implementations must:
        1. Stage the file to the configured input directory
        2. Call _emit_progress() during long operations
        3. Raise VaClipIngestError on unrecoverable failure
        4. Extract audio to cache directory if needed
        5. Return a complete MediaAsset with all metadata populated

        Args:
            source: URL or local path to the media to ingest.
            profile: Content profile hint for downstream processing.

        Returns:
            MediaAsset with staged_path, audio_path, and metadata populated.
        """
        ...

    def _emit_progress(self, pct: float, message: str) -> None:
        """Emit a progress event to the registered callback if any."""
        if self._on_progress:
            self._on_progress(pct, message)

    def _emit_complete(self, result: Optional["MediaAsset"]) -> None:
        """Emit a completion event to the registered callback if any."""
        if self._on_complete and result is not None:
            self._on_complete(result)

    def _emit_error(self, exc: Exception) -> None:
        """Emit an error event to the registered callback if any."""
        if self._on_error:
            self._on_error(exc)
