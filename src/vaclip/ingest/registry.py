"""Ingest adapter registry and factory for VAClip.

Provides polymorphic adapter selection based on source string.
"""
from __future__ import annotations

from vaclip.ingest.base import IngestAdapter
from vaclip.ingest.local_adapter import LocalFileAdapter
from vaclip.ingest.ytdlp_adapter import YtDlpAdapter


class IngestRegistry:
    """Registry for ingest adapters with polymorphic selection.
    
    Maintains a list of adapters and selects the first one that
    supports the given source string.
    """

    def __init__(self) -> None:
        """Initialize the registry with default adapters."""
        self._adapters: list[IngestAdapter] = [
            YtDlpAdapter(on_progress=None, on_complete=None, on_error=None),  # Try yt-dlp for URLs first
            LocalFileAdapter(on_progress=None, on_complete=None, on_error=None),   # Then try local files
        ]

    def register(self, adapter: IngestAdapter) -> None:
        """Register a new ingest adapter.
        
        Args:
            adapter: Adapter instance to register
        """
        self._adapters.append(adapter)

    def get_adapter(self, source: str | None) -> IngestAdapter:
        """Get the first adapter that supports the given source.

        Args:
            source: Source string (file path or URL)

        Returns:
            IngestAdapter that can handle the source

        Raises:
            ValueError: If no adapter supports the source
        """
        if source is None:
            raise ValueError("No ingest adapter found for source: None")
        for adapter in self._adapters:
            if adapter.supports(source):
                return adapter

        raise ValueError(f"No ingest adapter found for source: {source}")


# Global registry instance
_ingest_registry: IngestRegistry | None = None


def get_ingest_registry() -> IngestRegistry:
    """Get the global ingest registry instance.
    
    Returns:
        IngestRegistry singleton
    """
    global _ingest_registry
    if _ingest_registry is None:
        _ingest_registry = IngestRegistry()
    return _ingest_registry


def get_adapter(source: str) -> IngestAdapter:
    """Convenience function to get an adapter for a source.
    
    Args:
        source: Source string (file path or URL)
        
    Returns:
        IngestAdapter that can handle the source
    """
    return get_ingest_registry().get_adapter(source)
