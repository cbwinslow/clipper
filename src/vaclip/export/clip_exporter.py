"""Clip export and framing strategies for VAClip.

Renders final video clips from scored segments using FFmpeg subprocess.
Supports wide (16:9), vertical (9:16), and square (1:1) framing.

Agent Instructions:
    - Implement the TODO sections in ClipExporter._export_one()
    - Build the FFmpeg command using strategy.build_filter()
    - Use subprocess.run with check=False, inspect returncode
    - Name output files: <rank>_<profile>_<framing>.mp4
    - Save ExportedClip JSON to output/<asset_id>/clips.json
    - Never delete or overwrite source files
    - See docs/agents/export_agent.md for full implementation guide
"""
from __future__ import annotations

import hashlib
import subprocess
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import orjson

from vaclip.export.subtitle import burn_subtitles
from vaclip.logging.setup import get_logger
from vaclip.models.media import ExportedClip
from vaclip.models.schemas import ClipBounds
from vaclip.models.schemas import FramingStrategy as FramingStrategyEnum
from vaclip.utils.exceptions import VaClipExportError

if TYPE_CHECKING:
    from vaclip.models.media import MediaAsset, ScoredSegment

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Framing Strategies
# ---------------------------------------------------------------------------

class FramingStrategy(ABC):
    """Abstract base class for video framing/cropping strategies.

    Subclasses define the output dimensions and FFmpeg filter string
    needed to transform the source video to the target aspect ratio.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy identifier (e.g., 'wide', 'vertical', 'square')."""
        ...

    @property
    @abstractmethod
    def width(self) -> int:
        """Output video width in pixels."""
        ...

    @property
    @abstractmethod
    def height(self) -> int:
        """Output video height in pixels."""
        ...

    @abstractmethod
    def build_filter(self, media: MediaAsset) -> str:
        """Build the FFmpeg -vf filter string for this framing.

        Args:
            media: The source MediaAsset (provides width/height for smart cropping).

        Returns:
            FFmpeg video filter string.
        """
        ...


class WideFramingStrategy(FramingStrategy):
    """16:9 landscape framing - suitable for YouTube and standard video."""

    name = "wide"
    width = 1920
    height = 1080

    def build_filter(self, media: MediaAsset) -> str:
        """Scale to 1920x1080, padding letterbox if needed."""
        return "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:-1:-1:color=black"


class VerticalFramingStrategy(FramingStrategy):
    """9:16 portrait framing - suitable for YouTube Shorts, TikTok, Instagram Reels."""

    name = "vertical"
    width = 1080
    height = 1920

    def build_filter(self, media: MediaAsset) -> str:
        """Crop center column from landscape source, then scale to 1080x1920."""
        # Crop the center ih*9/16 width strip, then scale
        return "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920"


class SquareFramingStrategy(FramingStrategy):
    """1:1 square framing - suitable for Instagram feed posts."""

    name = "square"
    width = 1080
    height = 1080

    def build_filter(self, media: MediaAsset) -> str:
        """Crop center square from source, then scale to 1080x1080."""
        return "crop=ih:ih:(iw-ih)/2:0,scale=1080:1080"


# Registry of all framing strategies
FRAMING_STRATEGIES: dict[str, type[FramingStrategy]] = {
    "wide": WideFramingStrategy,
    "vertical": VerticalFramingStrategy,
    "square": SquareFramingStrategy,
}


def get_framing_strategy(name: str) -> FramingStrategy:
    """Return a framing strategy by name.

    Args:
        name: Strategy name ("wide", "vertical", "square").

    Returns:
        Instantiated FramingStrategy.

    Raises:
        VaClipExportError: If the strategy name is not recognized.
    """
    cls = FRAMING_STRATEGIES.get(name)
    if cls is None:
        raise VaClipExportError(
            f"Unknown framing strategy '{name}'. "
            f"Available: {list(FRAMING_STRATEGIES)}"
        )
    return cls()


# ---------------------------------------------------------------------------
# Clip Exporter
# ---------------------------------------------------------------------------

class ClipExporter:
    """Exports video clips from scored segments using FFmpeg.

    Slices the source video at segment start/end times, applies the
    configured framing strategy, and encodes to H.264/AAC MP4.
    All source artifacts are preserved - nothing is deleted.

    Example::

        exporter = ClipExporter()
        clips = exporter.export(
            media=media_asset,
            segments=scored_segments,
            framing="vertical",
            max_clips=5,
        )
    """

    # FFmpeg encoding settings (quality-first, matches user preference)
    VIDEO_CODEC: str = "libx264"
    VIDEO_PRESET: str = "slow"   # better quality, slower encoding
    VIDEO_CRF: int = 18          # 0=lossless, 51=worst; 18=high quality
    AUDIO_CODEC: str = "aac"
    AUDIO_BITRATE: str = "192k"

    def __init__(
        self,
        output_dir: Path = Path("output"),
        ffmpeg_bin: str = "ffmpeg",
    ) -> None:
        """Initialize the clip exporter.

        Args:
            output_dir: Root directory for exported clips.
            ffmpeg_bin: Path to the ffmpeg binary (default: system PATH).
        """
        self.output_dir = output_dir
        self.ffmpeg_bin = ffmpeg_bin

    def export(
        self,
        media: MediaAsset,
        segments: list[ScoredSegment],
        framing: str = "wide",
        max_clips: int = 10,
        caption: str | None = None,
    ) -> list[ExportedClip]:
        """Export top-N segments as clips with the given framing strategy.

        Args:
            media: Source MediaAsset with video path.
            segments: Scored and ranked segments (will take top max_clips).
            framing: Framing strategy name.
            max_clips: Maximum number of clips to export.
            caption: Optional text to burn as subtitles on all exported clips.

        Returns:
            List of ExportedClip objects with output paths and metadata.

        Raises:
            ExportError: If any clip export fails.
        """
        strategy = get_framing_strategy(framing)
        asset_output_dir = self.output_dir / str(media.id)
        asset_output_dir.mkdir(parents=True, exist_ok=True)

        log.info(
            "export.start",
            asset_id=str(media.id),
            framing=framing,
            segment_count=len(segments),
            max_clips=max_clips,
        )

        clips: list[ExportedClip] = []
        for seg in segments[:max_clips]:
            try:
                clip = self._export_one(media, seg, strategy, asset_output_dir, caption)
                clips.append(clip)
            except VaClipExportError as exc:
                log.error(
                    "export.clip_failed",
                    rank=seg.rank,
                    error=str(exc),
                    continue_on_error=True,
                )

        self._save_manifest(clips, asset_output_dir)
        log.info("export.complete", clips_exported=len(clips))
        return clips

    def _export_one(
        self,
        media: MediaAsset,
        seg: ScoredSegment,
        strategy: FramingStrategy,
        output_dir: Path,
        caption: str | None = None,
    ) -> ExportedClip:
        """Export a single segment as a clip.

        Args:
            media: Source MediaAsset.
            seg: Scored segment to export.
            strategy: Framing strategy to apply.
            output_dir: Directory to write the output file.
            caption: Optional text to burn as subtitles.

        Returns:
            ExportedClip with metadata.

        Raises:
            VaClipExportError: If FFmpeg fails.
        """
        from vaclip.models.media import ExportedClip

        start = seg.segment.start
        end = seg.segment.end
        filename = f"{seg.rank:03d}_{media.profile}_{strategy.name}.mp4"
        output_path = output_dir / filename

        vf_filter = strategy.build_filter(media)
        if caption:
            subtitle_filter = burn_subtitles(caption)
            if subtitle_filter:
                vf_filter = f"{vf_filter},{subtitle_filter}"
                log.info("export.subtitle_added", rank=seg.rank, caption_length=len(caption))

        cmd = [
            self.ffmpeg_bin,
            "-ss", str(start),
            "-to", str(end),
            "-i", str(media.local_path),
            "-vf", vf_filter,
            "-c:v", self.VIDEO_CODEC,
            "-preset", self.VIDEO_PRESET,
            "-crf", str(self.VIDEO_CRF),
            "-c:a", self.AUDIO_CODEC,
            "-b:a", self.AUDIO_BITRATE,
            "-movflags", "+faststart",
            "-y",
            str(output_path),
        ]
        log.info("export.ffmpeg_start", rank=seg.rank, output=filename)
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise VaClipExportError(f"FFmpeg failed for clip {filename}: {result.stderr[-500:]}")

        file_size = output_path.stat().st_size
        log.info("export.ffmpeg_success", rank=seg.rank, output=filename, bytes=file_size)
        return ExportedClip(
            clip_id=str(uuid.uuid4()),
            source_path=media.local_path,
            output_path=output_path,
            bounds=ClipBounds(start=start, end=end),
            profile=media.profile,
            width=strategy.width,
            height=strategy.height,
            framing=FramingStrategyEnum(strategy.name),
            scored_segment=seg,
            exported_at=datetime.now(UTC),
            metadata={},
            file_size_bytes=file_size,
        )

    def _save_manifest(self, clips: list[ExportedClip], output_dir: Path) -> None:
        """Save a JSON manifest of all exported clips.

        Args:
            clips: List of exported clips.
            output_dir: Directory to write clips.json.
        """
        if not clips:
            # If no clips, we still write a manifest with empty clips and no checksum
            manifest = {"input_checksum": None, "clips": []}
        else:
            # Compute SHA256 checksum of the source media (first clip's source path)
            source_path = clips[0].source_path
            if not source_path.exists():
                log.warning("export.manifest_source_missing", path=str(source_path))
                checksum = None
            else:
                hash_sha256 = hashlib.sha256()
                with open(source_path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_sha256.update(chunk)
                checksum = hash_sha256.hexdigest()

            # Convert each clip to a dictionary using model_dump_json and then parse to dict
            clip_dicts = [orjson.loads(clip.model_dump_json()) for clip in clips]
            manifest = {"input_checksum": checksum, "clips": clip_dicts}

        dest = output_dir / "clips.json"
        # Write with orjson, pretty printed with indent 2
        dest.write_bytes(orjson.dumps(manifest, option=orjson.OPT_INDENT_2))
        log.info("export.manifest_saved", path=str(dest), count=len(clips))
