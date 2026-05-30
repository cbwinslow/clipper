"""yt-dlp ingest adapter for VAClip.

Downloads video/audio from YouTube, Rumble, Kick, Twitch, and 1000+
other sites supported by yt-dlp. Extracts audio and produces a MediaAsset.

Agent Instructions:
    - Implement the TODO sections below
    - Use yt_dlp.YoutubeDL context manager for downloads
    - Parse the .info.json file yt-dlp writes for metadata
    - Call _extract_audio() after successful download
    - Construct MediaAsset from metadata + paths
    - Save MediaAsset JSON to cache/<asset_id>/media_asset.json
    - See docs/agents/ingest_agent.md for full implementation guide
"""
from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path
from typing import Any
from uuid import UUID

from vaclip.ingest.base import IngestAdapter
from vaclip.logging.setup import get_logger
from vaclip.models.media import MediaAsset
from vaclip.utils.exceptions import VaClipIngestError

log = get_logger(__name__)


class YtDlpAdapter(IngestAdapter):
    """Ingest adapter that downloads media using yt-dlp.

    Supports YouTube, Rumble, Kick, Twitch, Vimeo, SoundCloud,
    and 1000+ other sites via yt-dlp's extractor ecosystem.

    Attributes:
        output_dir: Directory where downloaded files are stored.
        audio_sample_rate: Sample rate for extracted audio WAV.
        audio_channels: Number of audio channels (1=mono, 2=stereo).

    Example::

        adapter = YtDlpAdapter()
        asset = adapter.ingest("https://youtube.com/watch?v=dQw4w9WgXcQ", profile="generic")
        print(asset.local_path)
    """

    DEFAULT_FORMAT: str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
    AUDIO_SAMPLE_RATE: int = 16000  # Whisper requires 16kHz
    AUDIO_CHANNELS: int = 1         # mono

    def __init__(
        self,
        output_dir: Path = Path("input"),
        cache_dir: Path = Path("cache"),
    ) -> None:
        """Initialize the yt-dlp adapter.

        Args:
            output_dir: Where to store downloaded video files.
            cache_dir: Where to store intermediate artifacts (audio, metadata).
        """
        self.output_dir = output_dir
        self.cache_dir = cache_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)

    def supports(self, source: str) -> bool:
        """Return True if the source is a URL that yt-dlp can handle.

        Args:
            source: Source string to check.

        Returns:
            True if source looks like a URL, False for local file paths.
        """
        # yt-dlp can handle URLs; local paths are handled by LocalFileAdapter
        return source.startswith(("http://", "https://"))

    def ingest(self, source: str, profile: str = "generic") -> MediaAsset:
        """Download media from a URL and return a normalized MediaAsset.

        Args:
            source: URL of the video/audio to download.
            profile: Content profile hint ("podcast", "gaming", etc.).

        Returns:
            MediaAsset with all metadata and paths populated.

        Raises:
            IngestError: If the download fails for any reason.
        """
        log.info("ingest.start", source=source, adapter="YtDlpAdapter", profile=profile)

        asset_id = str(uuid.uuid4())
        asset_dir = self.output_dir / asset_id
        asset_dir.mkdir(parents=True, exist_ok=True)

        try:
            video_path, info = self._download(source, asset_dir, asset_id)
            audio_path = self._extract_audio(video_path, asset_id)
            asset = self._build_asset(asset_id, source, video_path, audio_path, info, profile)
            self._save_asset(asset)

            log.info(
                "ingest.complete",
                asset_id=asset_id,
                duration=asset.duration_seconds,
                title=asset.title,
            )
            return asset

        except VaClipIngestError:
            raise
        except Exception as exc:
            log.error("ingest.failed", source=source, asset_id=asset_id, error=str(exc))
            raise VaClipIngestError(f"Download failed for {source}: {exc}") from exc

    def _download(self, url: str, output_dir: Path, asset_id: str) -> tuple[Path, dict[str, Any]]:
        """Run yt-dlp to download the video and write an info JSON file.

        Args:
            url: The source URL.
            output_dir: Directory to write output files.
            asset_id: Unique ID used in output filenames.

        Returns:
            Tuple of (video_path, info_dict).

        Raises:
            IngestError: If yt-dlp reports a download error.
        """
        import yt_dlp
        
        ydl_opts = {
            "format": self.DEFAULT_FORMAT,
            "outtmpl": str(output_dir / f"{asset_id}.%(ext)s"),
            "writeinfojson": True,
            "quiet": True,
            "no_warnings": False,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_path = Path(ydl.prepare_filename(info))
                log.info("yt-dlp.download.complete", asset_id=asset_id, url=url, format=info.get("format"))
                return video_path, info
        except Exception as exc:
            log.error("yt-dlp.download.failed", asset_id=asset_id, url=url, error=str(exc))
            raise VaClipIngestError(f"yt-dlp download failed for {url}: {exc}") from exc

    def _extract_audio(self, video_path: Path, asset_id: str) -> Path:
        """Extract audio track from video as 16kHz mono WAV using FFmpeg.

        Args:
            video_path: Path to the downloaded video file.
            asset_id: Used to name the output WAV file.

        Returns:
            Path to the extracted WAV file.

        Raises:
            IngestError: If FFmpeg fails to extract audio.
        """
        audio_path = self.cache_dir / "audio" / f"{asset_id}.wav"
        audio_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vn",                        # no video
            "-acodec", "pcm_s16le",       # 16-bit PCM
            "-ar", str(self.AUDIO_SAMPLE_RATE),
            "-ac", str(self.AUDIO_CHANNELS),
            str(audio_path),
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                log.error("ffmpeg.extract.audio.failed", asset_id=asset_id, error=result.stderr, returncode=result.returncode)
                raise VaClipIngestError(f"FFmpeg audio extraction failed: {result.stderr}")
            
            log.info("ffmpeg.extract.audio.complete", asset_id=asset_id, audio_path=str(audio_path))
            return audio_path
        except Exception as exc:
            log.error("ffmpeg.extract.audio.exception", asset_id=asset_id, error=str(exc))
            raise VaClipIngestError(f"FFmpeg audio extraction failed for {video_path}: {exc}") from exc

    def _build_asset(
        self,
        asset_id: str,
        source_url: str,
        video_path: Path,
        audio_path: Path,
        info: dict[str, Any],
        profile: str,
    ) -> MediaAsset:
        """Construct a MediaAsset from yt-dlp info dict and file paths.

        Args:
            asset_id: Unique identifier.
            source_url: Original download URL.
            video_path: Path to downloaded video.
            audio_path: Path to extracted WAV.
            info: yt-dlp info dict (from writeinfojson or extract_info).
            profile: Content profile.

        Returns:
            Populated MediaAsset instance.
        """
        # Extract metadata from info dict with fallbacks
        title = info.get('title') or info.get('fulltitle') or video_path.stem
        duration_seconds = float(info.get('duration', 0))
        
        # Video properties - try to get from info dict first, then fall back to format info
        width = info.get('width') or 0
        height = info.get('height') or 0
        fps = info.get('fps') or 0.0
        
        # If we don't have width/height/fps directly, try to get from format
        if width == 0 or height == 0 or fps == 0.0:
            formats = info.get('formats', [])
            if formats:
                # Find the best format (usually the last one or the one with resolution)
                for fmt in formats:
                    if fmt.get('width') and fmt.get('height'):
                        width = width or fmt.get('width', 0)
                        height = height or fmt.get('height', 0)
                        fps = fps or fmt.get('fps', 0.0)
                        if width > 0 and height > 0:
                            break
        
        # Codec - try video codec first
        codec = info.get('vcodec') or info.get('video_codec') or 'unknown'
        if codec == 'none':
            codec = 'unknown'
            
        # Format/container
        format_name = info.get('format') or info.get('ext') or 'mp4'
        if format_name == 'none':
            format_name = 'mp4'
        
        # Ensure we have reasonable defaults
        if width <= 0:
            width = 1920  # Default to common HD width
        if height <= 0:
            height = 1080  # Default to common HD height
        if fps <= 0.0:
            fps = 30.0   # Default to common FPS
        if duration_seconds <= 0:
            duration_seconds = 0.0  # Will be corrected if possible
        
        asset = MediaAsset(
            id=UUID(asset_id),
            source_url=source_url,
            local_path=video_path,
            title=title,
            duration_seconds=duration_seconds,
            width=int(width),
            height=int(height),
            fps=float(fps),
            codec=codec,
            audio_path=audio_path,
            format=format_name,
            profile=profile,
        )
        
        log.info(
            "asset.build.complete",
            asset_id=asset_id,
            title=title,
            duration=duration_seconds,
            width=width,
            height=height,
            fps=fps,
            codec=codec,
            format=format_name
        )
        
        return asset

    def _save_asset(self, asset: MediaAsset) -> None:
        """Serialize the MediaAsset to JSON in the cache directory.

        Args:
            asset: The MediaAsset to serialize.
        """
        asset_cache = self.cache_dir / str(asset.id)
        asset_cache.mkdir(parents=True, exist_ok=True)
        dest = asset_cache / "media_asset.json"
        dest.write_text(asset.model_dump_json(indent=2))
        log.info("ingest.asset_saved", path=str(dest))
