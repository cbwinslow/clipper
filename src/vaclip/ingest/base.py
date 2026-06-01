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

import hashlib
import json
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from vaclip.config.settings import Settings
    from vaclip.models.media import MediaAsset


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
        on_progress: ProgressCallback | None = None,
        on_complete: Callable[[MediaAsset], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
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
    def ingest(self, source: str, profile: str = "generic") -> MediaAsset:
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

    def _emit_complete(self, result: MediaAsset | None) -> None:
        """Emit a completion event to the registered callback if any."""
        if self._on_complete and result is not None:
            self._on_complete(result)

    def _emit_error(self, exc: Exception) -> None:
        """Emit an error event to the registered callback if any."""
        if self._on_error:
            self._on_error(exc)

    def _get_settings(self) -> Settings:
        """Get the global settings object."""
        from vaclip.config.settings import get_settings
        return get_settings()

    def _get_cached_ffprobe_metadata(self, file_path: Path) -> dict[str, Any] | None:
        """Get ffprobe metadata from cache if available and not expired.
        
        Args:
            file_path: Path to the media file
            
        Returns:
            Cached metadata dict if available and not expired, None otherwise
        """
        try:
            settings = self._get_settings()
            cache_dir = settings.paths.cache_dir / "ffprobe"
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Compute file hash
            file_hash = self._compute_file_hash(file_path)
            cache_file = cache_dir / f"{file_hash}.json"

            # Check if cache file exists
            if not cache_file.exists():
                return None

            # Check if cache is expired (30 days)
            cache_age = time.time() - cache_file.stat().st_mtime
            if cache_age > (30 * 24 * 60 * 60):  # 30 days in seconds
                return None

            # Load cached metadata
            with open(cache_file) as f:
                cached_data = json.load(f)

            return cached_data
        except Exception:
            # If any error occurs, return None to fall back to fresh ffprobe call
            return None

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of a file.
        
        Args:
            file_path: Path to the file to hash
            
        Returns:
            Hexadecimal SHA256 hash string
        """
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _cache_ffprobe_metadata(self, file_path: Path, metadata: dict[str, Any]) -> None:
        """Cache ffprobe metadata using file hash as key.
        
        Args:
            file_path: Path to the media file
            metadata: Metadata dict to cache
        """
        try:
            settings = self._get_settings()
            cache_dir = settings.paths.cache_dir / "ffprobe"
            cache_dir.mkdir(parents=True, exist_ok=True)

            # Compute file hash
            file_hash = self._compute_file_hash(file_path)
            cache_file = cache_dir / f"{file_hash}.json"

            # Save metadata to cache
            with open(cache_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception:
            # Fail silently - caching is optional optimization
            pass
