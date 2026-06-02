"""yt-dlp ingest adapter for VAClip."""
from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path
from typing import Any

from vaclip.ingest.base import BaseIngestAdapter
from vaclip.logging.setup import get_logger
from vaclip.utils.exceptions import VaClipIngestError

log = get_logger(__name__)


class YtDlpAdapter(BaseIngestAdapter):
    """Ingest adapter that downloads media using yt-dlp.

    Supports YouTube, Rumble, Kick, Twitch, Vimeo, SoundCloud,
    and 1000+ other sites via yt-dlp's extractor ecosystem.

    Example::

        adapter = YtDlpAdapter()
        asset = adapter.ingest("https://youtube.com/watch?v=dQw4w9WgXcQ")
        print(asset.extra["audio_path"])
    """

    DEFAULT_FORMAT: str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_CHANNELS: int = 1

    def __init__(
        self,
        output_dir: Path = Path("input"),
        cache_dir: Path = Path("cache"),
        cookies_file: Path | None = None,
        rate_limit: str | None = None,
    ) -> None:
        self.output_dir = output_dir
        self.cache_dir = cache_dir
        self.cookies_file = cookies_file
        self.rate_limit = rate_limit
        output_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)

    def ingest(self, source: str, profile: str = "generic") -> Any:
        """Download media from a URL and return a normalized MediaAsset."""
        log.info("ingest.start", source=source, adapter="YtDlpAdapter")
        asset_id = str(uuid.uuid4())
        asset_dir = self.output_dir / asset_id
        asset_dir.mkdir(parents=True, exist_ok=True)

        try:
            info = self._download(source, asset_dir)
            video_path = self._find_video_file(asset_dir)
            audio_path = self._extract_audio(video_path, asset_id)
            asset = self._build_asset(asset_id, source, video_path, audio_path, info, profile)
            self._save_asset(asset, asset_id)
            log.info(
                "ingest.complete",
                asset_id=asset_id,
                title=info.get("title"),
                duration=info.get("duration"),
            )
            return asset
        except VaClipIngestError:
            raise
        except Exception as exc:
            log.error("ingest.failed", source=source, error=str(exc))
            raise VaClipIngestError(f"yt-dlp ingest failed for {source}: {exc}") from exc

    def _download(self, url: str, asset_dir: Path) -> dict[str, Any]:
        """Download media using yt-dlp and return extracted info dict."""
        try:
            import yt_dlp
        except ImportError as exc:
            raise VaClipIngestError(
                "yt-dlp is not installed. Run: pip install yt-dlp"
            ) from exc

        outtmpl = str(asset_dir / "%(title)s.%(ext)s")
        ydl_opts: dict[str, Any] = {
            "format": self.DEFAULT_FORMAT,
            "outtmpl": outtmpl,
            "writeinfojson": True,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
        }
        if self.cookies_file and self.cookies_file.exists():
            ydl_opts["cookiefile"] = str(self.cookies_file)
        if self.rate_limit:
            ydl_opts["ratelimit"] = self.rate_limit

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        return info or {}

    def _find_video_file(self, asset_dir: Path) -> Path:
        """Find the downloaded video file in the asset directory."""
        for ext in (".mp4", ".mkv", ".webm", ".mov"):
            matches = list(asset_dir.glob(f"*{ext}"))
            if matches:
                # Return the largest file (avoid tiny thumbnails)
                return max(matches, key=lambda p: p.stat().st_size)
        raise VaClipIngestError(
            f"No video file found in {asset_dir} after yt-dlp download."
        )

    def _extract_audio(self, video_path: Path, asset_id: str) -> Path:
        """Extract 16kHz mono WAV from the downloaded video."""
        audio_dir = self.cache_dir / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_path = audio_dir / f"{asset_id}.wav"
        if audio_path.exists():
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
        source_url: str,
        video_path: Path,
        audio_path: Path,
        info: dict[str, Any],
        profile: str,
    ) -> Any:
        from vaclip.models.schemas import MediaMeta, MediaType
        return MediaMeta(
            source_url=source_url,
            local_path=video_path,
            duration_sec=float(info.get("duration") or 0),
            media_type=MediaType.VIDEO,
            title=info.get("title") or video_path.stem,
            width=info.get("width"),
            height=info.get("height"),
            fps=float(info.get("fps") or 0) or None,
            extra={
                "asset_id": asset_id,
                "audio_path": str(audio_path),
                "uploader": info.get("uploader"),
                "upload_date": info.get("upload_date"),
                "view_count": info.get("view_count"),
                "like_count": info.get("like_count"),
                "description": (info.get("description") or "")[:500],
                "tags": info.get("tags") or [],
                "extractor": info.get("extractor"),
                "webpage_url": info.get("webpage_url") or source_url,
                "profile": profile,
            },
        )

    def _save_asset(self, asset: Any, asset_id: str) -> None:
        dest = self.cache_dir / asset_id / "media_asset.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(asset.model_dump_json(indent=2))
        log.debug("ingest.asset_saved", path=str(dest))
