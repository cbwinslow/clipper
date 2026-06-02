"""Local file ingest adapter for VAClip."""
from __future__ import annotations

import json
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any

from vaclip.ingest.base import BaseIngestAdapter
from vaclip.logging.setup import get_logger
from vaclip.utils.exceptions import VaClipIngestError, VaClipUnsupportedSourceError

log = get_logger(__name__)


class LocalFileAdapter(BaseIngestAdapter):
    """Ingest adapter for local video and audio files.

    Validates the file format, copies it to the input directory,
    extracts metadata via ffprobe, extracts audio via FFmpeg,
    and produces a normalized MediaAsset.

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
        return self.SUPPORTED_VIDEO_EXTENSIONS | self.SUPPORTED_AUDIO_EXTENSIONS

    def __init__(
        self,
        input_dir: Path = Path("input"),
        cache_dir: Path = Path("cache"),
        copy_files: bool = True,
    ) -> None:
        self.input_dir = input_dir
        self.cache_dir = cache_dir
        self.copy_files = copy_files
        input_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)

    def ingest(self, source: str, profile: str = "generic") -> Any:
        """Ingest a local file and return a normalized MediaAsset."""
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
            log.info("ingest.complete", asset_id=asset_id, duration=metadata.get("duration_seconds", 0))
            return asset
        except (VaClipUnsupportedSourceError, VaClipIngestError):
            raise
        except Exception as exc:
            log.error("ingest.failed", source=str(source_path), error=str(exc))
            raise VaClipIngestError(f"Local ingest failed for {source_path}: {exc}") from exc

    def _validate(self, path: Path) -> None:
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
        """Use ffprobe to extract video/audio metadata."""
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams", "-show_format",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise VaClipIngestError(
                f"ffprobe failed on {video_path}: {result.stderr[:500]}"
            )
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        fmt = data.get("format", {})

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        # duration: prefer format-level, fall back to video stream
        duration = float(fmt.get("duration") or 0)
        if not duration and video_stream:
            duration = float(video_stream.get("duration") or 0)

        # fps calculation
        fps = None
        if video_stream:
            r = video_stream.get("r_frame_rate", "0/1")
            try:
                num, den = r.split("/")
                fps = round(int(num) / max(int(den), 1), 3)
            except Exception:
                fps = None

        return {
            "duration_seconds": duration,
            "width": int(video_stream["width"]) if video_stream else None,
            "height": int(video_stream["height"]) if video_stream else None,
            "fps": fps,
            "video_codec": video_stream.get("codec_name") if video_stream else None,
            "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
            "audio_sample_rate": (
                int(audio_stream["sample_rate"]) if audio_stream else None
            ),
            "audio_channels": (
                int(audio_stream.get("channels", 0)) if audio_stream else None
            ),
            "file_size_bytes": int(fmt.get("size") or 0) or None,
            "format_name": fmt.get("format_name"),
            "bit_rate": int(fmt.get("bit_rate") or 0) or None,
            "title": fmt.get("tags", {}).get("title") or video_path.stem,
        }

    def _extract_audio(self, video_path: Path, asset_id: str) -> Path:
        """Extract audio track as 16kHz mono WAV using FFmpeg."""
        audio_dir = self.cache_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = audio_dir / f"{asset_id}.wav"
        if audio_path.exists():
            log.debug("ingest.audio_cached", path=str(audio_path))
            return audio_path
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", str(self.AUDIO_SAMPLE_RATE),
            "-ac", str(self.AUDIO_CHANNELS),
            str(audio_path),
        ]
        log.info("ingest.audio_extract", asset_id=asset_id, output=str(audio_path))
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise VaClipIngestError(
                f"FFmpeg audio extraction failed: {result.stderr[-500:]}"
            )
        return audio_path

    def _build_asset(  # type: ignore[return]
        self,
        asset_id: str,
        local_path: Path,
        audio_path: Path,
        metadata: dict[str, Any],
        profile: str,
    ) -> Any:
        """Construct a MediaAsset from extracted metadata and paths."""
        from vaclip.models.schemas import MediaMeta, MediaType
        return MediaMeta(
            source_url=str(local_path),
            local_path=local_path,
            duration_sec=metadata.get("duration_seconds", 0.0),
            media_type=MediaType.VIDEO
            if local_path.suffix.lower() in self.SUPPORTED_VIDEO_EXTENSIONS
            else MediaType.AUDIO,
            title=metadata.get("title") or local_path.stem,
            width=metadata.get("width"),
            height=metadata.get("height"),
            fps=metadata.get("fps"),
            extra={
                "asset_id": asset_id,
                "audio_path": str(audio_path),
                "video_codec": metadata.get("video_codec"),
                "audio_codec": metadata.get("audio_codec"),
                "audio_sample_rate": metadata.get("audio_sample_rate"),
                "audio_channels": metadata.get("audio_channels"),
                "file_size_bytes": metadata.get("file_size_bytes"),
                "format_name": metadata.get("format_name"),
                "bit_rate": metadata.get("bit_rate"),
                "profile": profile,
            },
        )

    def _save_asset(self, asset: Any) -> None:
        cache_dir = self.cache_dir / asset.extra.get("asset_id", "unknown")
        cache_dir.mkdir(parents=True, exist_ok=True)
        dest = cache_dir / "media_asset.json"
        dest.write_text(asset.model_dump_json(indent=2))
        log.debug("ingest.asset_saved", path=str(dest))
