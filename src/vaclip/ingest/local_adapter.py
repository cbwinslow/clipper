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

import json
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any
from uuid import UUID

from vaclip.ingest.base import IngestAdapter
from vaclip.logging.setup import get_logger
from vaclip.models.media import MediaAsset
from vaclip.utils.exceptions import VaClipIngestError, VaClipUnsupportedSourceError

log = get_logger(__name__)


class LocalFileAdapter(IngestAdapter):
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

    def supports(self, source: str) -> bool:
        """Return True if the source is a local file with supported extension.

        Args:
            source: Source string to check.

        Returns:
            True if source is a local file with supported extension, False otherwise.
        """
        try:
            path = Path(source)
            # Must be an existing file with supported extension
            return path.is_file() and path.suffix.lower() in self.supported_extensions
        except Exception:
            # If path creation fails or any other error, it's not supported
            return False

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
            asset = self._build_asset(asset_id, source_path, local_path, audio_path, metadata, profile)
            self._save_asset(asset)

            log.info("ingest.complete", asset_id=asset_id, duration=asset.duration_seconds)
            return asset

        except VaClipIngestError:
            raise
        except Exception as exc:
            log.error("ingest.failed", source=str(source_path), asset_id=asset_id, error=str(exc))
            raise VaClipIngestError(f"Local ingest failed for {source_path}: {exc}") from exc

    def _validate(self, path: Path) -> None:
        """Validate that the file exists and has a supported extension.

        Args:
            path: Path to validate.

        Raises:
            VaClipUnsupportedSourceError: If the path doesn't exist or is unsupported.
        """
        if not path.exists():
            raise VaClipUnsupportedSourceError(f"File not found: {path}")
        if not path.is_file():
            raise VaClipUnsupportedSourceError(f"Not a file: {path}")
        if path.suffix.lower() not in self.supported_extensions:
            raise VaClipUnsupportedSourceError(
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
            VaClipIngestError: If ffprobe fails.
        """
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams", "-show_format",
            str(video_path),
        ]
        
        log.debug("ffprobe.metadata.start", cmd=" ".join(cmd), path=str(video_path))
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            log.error("ffprobe.metadata.failed", path=str(video_path), error=result.stderr, returncode=result.returncode)
            raise VaClipIngestError(f"ffprobe failed: {result.stderr}")
        
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            log.error("ffprobe.metadata.json_decode_failed", path=str(video_path), error=str(exc), stdout=result.stdout[:200])
            raise VaClipIngestError(f"Failed to parse ffprobe output: {exc}") from exc
        
        # Initialize default values
        duration = 0.0
        width = 0
        height = 0
        fps = 0.0
        codec = "unknown"
        format_name = "unknown"
        
        # Extract format information
        if "format" in data:
            format_info = data["format"]
            duration = float(format_info.get("duration", 0))
            format_name = format_info.get("format_name", "unknown")
        
        # Extract stream information
        if "streams" in data:
            for stream in data["streams"]:
                # Look for video stream first
                if stream.get("codec_type") == "video":
                    width = int(stream.get("width", 0))
                    height = int(stream.get("height", 0))
                    
                    # Parse frame rate (can be string like "30/0" or "30")
                    fps_str = stream.get("r_frame_rate", "0")
                    try:
                        if "/" in fps_str:
                            num, den = fps_str.split("/")
                            fps = float(num) / float(den) if float(den) != 0 else 0.0
                        else:
                            fps = float(fps_str)
                    except (ValueError, ZeroDivisionError):
                        fps = 0.0
                    
                    codec = stream.get("codec_name", "unknown")
                    break  # Use first video stream found
            
            # If no video stream found, look for audio stream for codec at least
            if width == 0 or height == 0:
                for stream in data["streams"]:
                    if stream.get("codec_type") == "audio" and codec == "unknown":
                        codec = stream.get("codec_name", "unknown")
                        break
        
        # Ensure we have reasonable defaults
        if duration <= 0:
            duration = 0.0
        if width <= 0:
            width = 1920  # Default to common HD width
        if height <= 0:
            height = 1080  # Default to common HD height
        if fps <= 0.0:
            fps = 30.0   # Default to common FPS
        if codec == "unknown":
            codec = "unknown"
        if format_name == "unknown":
            format_name = "unknown"
        
        metadata = {
            "duration": duration,
            "width": width,
            "height": height,
            "fps": fps,
            "codec": codec,
            "format": format_name,
        }
        
        log.info("ffprobe.metadata.complete", 
                path=str(video_path),
                duration=duration,
                width=width,
                height=height,
                fps=fps,
                codec=codec,
                format=format_name)
        
        return metadata

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
        from vaclip.ingest.audio_extractor import extract_audio
        
        audio_path = extract_audio(
            video_path=video_path,
            asset_id=asset_id,
            cache_dir=self.cache_dir,
            sample_rate=self.AUDIO_SAMPLE_RATE,
            channels=self.AUDIO_CHANNELS,
        )
        
        log.info("ffmpeg.extract.audio.complete", asset_id=asset_id, audio_path=str(audio_path))
        return audio_path

    def _build_asset(
        self,
        asset_id: str,
        source_path: Path,
        local_path: Path,
        audio_path: Path,
        metadata: dict[str, Any],
        profile: str,
    ) -> MediaAsset:
        """Construct a MediaAsset from metadata and paths.

        Args:
            asset_id: Unique identifier.
            source_path: Original source file path.
            local_path: Path to the local video file (staged in input directory).
            audio_path: Path to extracted WAV.
            metadata: ffprobe metadata dict.
            profile: Content profile.

        Returns:
            Populated MediaAsset instance.
        """
        # Extract title from metadata or use filename stem
        title = metadata.get("title") or local_path.stem
        
        asset = MediaAsset(
            id=UUID(asset_id),
            source_url=str(source_path),
            local_path=local_path,
            title=title,
            duration_seconds=metadata["duration"],
            width=metadata["width"],
            height=metadata["height"],
            fps=metadata["fps"],
            codec=metadata["codec"],
            audio_path=audio_path,
            format=metadata["format"],
            profile=profile,
        )
        
        log.info(
            "asset.build.complete",
            asset_id=asset_id,
            title=title,
            duration=metadata["duration"],
            width=metadata["width"],
            height=metadata["height"],
            fps=metadata["fps"],
            codec=metadata["codec"],
            format=metadata["format"]
        )
        
        return asset

    def _save_asset(self, asset: MediaAsset) -> None:
        """Save MediaAsset JSON to cache directory."""
        dest = self.cache_dir / str(asset.id) / "media_asset.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(asset.model_dump_json(indent=2))
        log.info("ingest.asset_saved", path=str(dest))
