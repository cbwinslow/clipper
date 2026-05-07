"""Local file ingest adapter for VAClip.

Ingests local video and audio files, validates format, extracts audio,
and produces a MediaAsset without any network calls.

Agent Instructions:
    - Implement the TODO sections below
    - Use ffprobe to extract video metadata (duration, resolution, fps, codec)
    - Copy the file to input/<asset_id>/ if it's not already there
    - Extract audio using FFmpeg (same as YtDlpAdapter._extract_audio)
    - Construct and return MediaAsset
    - See docs/agents/ingest_agent.md for full implementation guide
"""
from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

from vaclip.ingest.base import BaseIngestAdapter
from vaclip.logging.setup import get_logger
from vaclip.models.media import MediaAsset
from vaclip.utils.exceptions import IngestError, UnsupportedSourceError

log = get_logger(__name__)


class LocalFileAdapter(BaseIngestAdapter):
    """Ingest adapter for local video and audio files.

    Validates the file format, optionally copies it to the input directory,
    extracts metadata via ffprobe, and produces a MediaAsset.

    Supported formats:
        Video: .mp4, .mkv, .mov, .avi, .webm, .flv
        Audio: .mp3, .wav, .m4a, .aac, .ogg, .flac

    Example::

        adapter = LocalFileAdapter()
        asset = adapter.ingest("/path/to/myvideo.mp4", profile="podcast")
        print(asset.duration_seconds)
    """

    SUPPORTED_VIDEO_EXTENSIONS: frozenset[str] = frozenset(
        {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv"}
    )
    SUPPORTED_AUDIO_EXTENSIONS: frozenset[str] = frozenset(
        {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
    )
    AUDIO_SAMPLE_RATE: int = 16000  # Whisper requires 16kHz
    AUDIO_CHANNELS: int = 1         # mono

    @property
    def supported_extensions(self) -> frozenset[str]:
        """Return all supported file extensions."""
        return self.SUPPORTED_VIDEO_EXTENSIONS | self.SUPPORTED_AUDIO_EXTENSIONS

    def __init__(
        self,
        input_dir: Path = Path("input"),
        cache_dir: Path = Path("cache"),
        copy_files: bool = True,
    ) -> None:
        """Initialize the local file adapter.

        Args:
            input_dir: Destination directory for ingested media.
            cache_dir: Directory for intermediate artifacts.
            copy_files: If True, copy source files to input_dir.
                        If False, reference them in-place (use with caution).
        """
        self.input_dir = input_dir
        self.cache_dir = cache_dir
        self.copy_files = copy_files
        input_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)

    def ingest(self, source: str, profile: str = "generic") -> MediaAsset:
        """Ingest a local file and return a normalized MediaAsset.

        Args:
            source: Path to the local file (string or stringified Path).
            profile: Content profile hint ("podcast", "gaming", etc.).

        Returns:
            MediaAsset with all metadata and paths populated.

        Raises:
            UnsupportedSourceError: If the file extension is not supported.
            IngestError: If metadata extraction or audio extraction fails.
        """
        source_path = Path(source)
        log.info("ingest.start", source=str(source_path), adapter="LocalFileAdapter")

        self._validate(source_path)

        asset_id = str(uuid.uuid4())

        try:
            local_path = self._copy_or_link(source_path, asset_id)
            metadata = self._extract_metadata(local_path)
            audio_path = self._extract_audio(local_path, asset_id)
            asset = self._build_asset(asset_id, local_path, audio_path, metadata, profile)
            self._save_asset(asset)

            log.info("ingest.complete", asset_id=asset_id, duration=asset.duration_seconds)
            return asset

        except (UnsupportedSourceError, IngestError):
            raise
        except Exception as exc:
            log.error("ingest.failed", source=str(source_path), asset_id=asset_id, error=str(exc))
            raise IngestError(f"Local ingest failed for {source_path}: {exc}") from exc

    def _validate(self, path: Path) -> None:
        """Validate that the file exists and has a supported extension.

        Args:
            path: Path to validate.

        Raises:
            UnsupportedSourceError: If the path doesn't exist or is unsupported.
        """
        if not path.exists():
            raise UnsupportedSourceError(f"File not found: {path}")
        if not path.is_file():
            raise UnsupportedSourceError(f"Not a file: {path}")
        if path.suffix.lower() not in self.supported_extensions:
            raise UnsupportedSourceError(
                f"Unsupported extension '{path.suffix}'. "
                f"Supported: {sorted(self.supported_extensions)}"
            )

    def _copy_or_link(self, source: Path, asset_id: str) -> Path:
        """Copy source file to input directory or return in-place path.

        Args:
            source: Source file path.
            asset_id: Unique ID for naming the destination.

        Returns:
            Path to the file in the input directory.
        """
        if not self.copy_files:
            return source
        dest_dir = self.input_dir / asset_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / source.name
        if not dest.exists():
            shutil.copy2(source, dest)
            log.info("ingest.file_copied", src=str(source), dest=str(dest))
        return dest

    def _extract_metadata(self, video_path: Path) -> dict[str, Any]:
        """Use ffprobe to extract video metadata.

        Args:
            video_path: Path to the video file.

        Returns:
            Dictionary with keys: duration, width, height, fps, codec, format.

        Raises:
            IngestError: If ffprobe fails.
        """
        # TODO: implement ffprobe metadata extraction
        # cmd = [
        #     "ffprobe", "-v", "quiet",
        #     "-print_format", "json",
        #     "-show_streams", "-show_format",
        #     str(video_path),
        # ]
        # result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        # if result.returncode != 0:
        #     raise IngestError(f"ffprobe failed: {result.stderr}")
        # data = json.loads(result.stdout)
        # Parse streams and format to extract duration, width, height, fps, codec
        raise NotImplementedError("LocalFileAdapter._extract_metadata() not yet implemented")

    def _extract_audio(self, video_path: Path, asset_id: str) -> Path:
        """Extract audio track as 16kHz mono WAV using FFmpeg.

        Args:
            video_path: Path to the video or audio file.
            asset_id: Used to name the output WAV file.

        Returns:
            Path to the extracted WAV file.

        Raises:
            IngestError: If FFmpeg fails.
        """
        audio_path = self.cache_dir / "audio" / f"{asset_id}.wav"
        audio_path.parent.mkdir(parents=True, exist_ok=True)

        # TODO: implement FFmpeg audio extraction (same as YtDlpAdapter._extract_audio)
        raise NotImplementedError("LocalFileAdapter._extract_audio() not yet implemented")

    def _build_asset(
        self,
        asset_id: str,
        local_path: Path,
        audio_path: Path,
        metadata: dict[str, Any],
        profile: str,
    ) -> MediaAsset:
        """Construct a MediaAsset from metadata and paths.

        Args:
            asset_id: Unique identifier.
            local_path: Path to the local video file.
            audio_path: Path to extracted WAV.
            metadata: ffprobe metadata dict.
            profile: Content profile.

        Returns:
            Populated MediaAsset instance.
        """
        # TODO: construct MediaAsset from metadata
        raise NotImplementedError("LocalFileAdapter._build_asset() not yet implemented")

    def _save_asset(self, asset: MediaAsset) -> None:
        """Save MediaAsset JSON to cache directory."""
        dest = self.cache_dir / str(asset.id) / "media_asset.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(asset.model_dump_json(indent=2))
        log.info("ingest.asset_saved", path=str(dest))
