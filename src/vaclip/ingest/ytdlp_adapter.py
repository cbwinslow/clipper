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

from vaclip.ingest.base import BaseIngestAdapter
from vaclip.logging.setup import get_logger
from vaclip.models.media import MediaAsset
from vaclip.utils.exceptions import IngestError

log = get_logger(__name__)


class YtDlpAdapter(BaseIngestAdapter):
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

        except IngestError:
            raise
        except Exception as exc:
            log.error("ingest.failed", source=source, asset_id=asset_id, error=str(exc))
            raise IngestError(f"Download failed for {source}: {exc}") from exc

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
        # TODO: implement yt-dlp download
        # import yt_dlp
        # ydl_opts = {
        #     "format": self.DEFAULT_FORMAT,
        #     "outtmpl": str(output_dir / f"{asset_id}.%(ext)s"),
        #     "writeinfojson": True,
        #     "quiet": True,
        #     "no_warnings": False,
        # }
        # with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        #     info = ydl.extract_info(url, download=True)
        #     video_path = Path(ydl.prepare_filename(info))
        # return video_path, info
        raise NotImplementedError("YtDlpAdapter._download() not yet implemented")

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

        # TODO: implement FFmpeg audio extraction
        # cmd = [
        #     "ffmpeg", "-y",
        #     "-i", str(video_path),
        #     "-vn",                        # no video
        #     "-acodec", "pcm_s16le",       # 16-bit PCM
        #     "-ar", str(self.AUDIO_SAMPLE_RATE),
        #     "-ac", str(self.AUDIO_CHANNELS),
        #     str(audio_path),
        # ]
        # result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        # if result.returncode != 0:
        #     raise IngestError(f"FFmpeg audio extraction failed: {result.stderr}")
        raise NotImplementedError("YtDlpAdapter._extract_audio() not yet implemented")

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
        # TODO: extract metadata from info dict and construct MediaAsset
        # Fields to populate: title, duration_seconds, width, height, fps, codec, format
        raise NotImplementedError("YtDlpAdapter._build_asset() not yet implemented")

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
