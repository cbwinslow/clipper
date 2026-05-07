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

import json
import subprocess
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from vaclip.logging.setup import get_logger
from vaclip.utils.exceptions import ExportError

if TYPE_CHECKING:
    from vaclip.models.media import ExportedClip, MediaAsset, ScoredSegment

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
    def build_filter(self, media: "MediaAsset") -> str:
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

    def build_filter(self, media: "MediaAsset") -> str:
        """Scale to 1920x1080, padding letterbox if needed."""
        return "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:-1:-1:color=black"


class VerticalFramingStrategy(FramingStrategy):
    """9:16 portrait framing - suitable for YouTube Shorts, TikTok, Instagram Reels."""

    name = "vertical"
    width = 1080
    height = 1920

    def build_filter(self, media: "MediaAsset") -> str:
        """Crop center column from landscape source, then scale to 1080x1920."""
        # Crop the center ih*9/16 width strip, then scale
        return "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920"


class SquareFramingStrategy(FramingStrategy):
    """1:1 square framing - suitable for Instagram feed posts."""

    name = "square"
    width = 1080
    height = 1080

    def build_filter(self, media: "MediaAsset") -> str:
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
        ExportError: If the strategy name is not recognized.
    """
    cls = FRAMING_STRATEGIES.get(name)
    if cls is None:
        raise ExportError(
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
        media: "MediaAsset",
        segments: list["ScoredSegment"],
        framing: str = "wide",
        max_clips: int = 10,
    ) -> list["ExportedClip"]:
        """Export top-N segments as clips with the given framing strategy.

        Args:
            media: Source MediaAsset with video path.
            segments: Scored and ranked segments (will take top max_clips).
            framing: Framing strategy name.
            max_clips: Maximum number of clips to export.

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

        clips: list["ExportedClip"] = []
        for seg in segments[:max_clips]:
            try:
                clip = self._export_one(media, seg, strategy, asset_output_dir)
                clips.append(clip)
            except ExportError as exc:
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
        media: "MediaAsset",
        seg: "ScoredSegment",
        strategy: FramingStrategy,
        output_dir: Path,
    ) -> "ExportedClip":
        """Export a single segment as a clip.

        Args:
            media: Source MediaAsset.
            seg: Scored segment to export.
            strategy: Framing strategy to apply.
            output_dir: Directory to write the output file.

        Returns:
            ExportedClip with metadata.

        Raises:
            ExportError: If FFmpeg fails.
        """
        from vaclip.models.media import ExportedClip

        start = seg.segment.start
        end = seg.segment.end
        duration = end - start
        filename = f"{seg.rank:03d}_{seg.profile}_{strategy.name}.mp4"
        output_path = output_dir / filename

        vf_filter = strategy.build_filter(media)

        # TODO: implement FFmpeg command and execute it
        # cmd = [
        #     self.ffmpeg_bin,
        #     "-ss", str(start),
        #     "-to", str(end),
        #     "-i", str(media.local_path),
        #     "-vf", vf_filter,
        #     "-c:v", self.VIDEO_CODEC,
        #     "-preset", self.VIDEO_PRESET,
        #     "-crf", str(self.VIDEO_CRF),
        #     "-c:a", self.AUDIO_CODEC,
        #     "-b:a", self.AUDIO_BITRATE,
        #     "-movflags", "+faststart",
        #     "-y",  # overwrite output (not source)
        #     str(output_path),
        # ]
        # log.info("export.ffmpeg_start", rank=seg.rank, output=filename)
        # result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        # if result.returncode != 0:
        #     raise ExportError(f"FFmpeg failed for clip {filename}: {result.stderr[-500:]}")
        #
        # file_size = output_path.stat().st_size
        # return ExportedClip(
        #     asset_id=str(media.id),
        #     segment_rank=seg.rank,
        #     start=start,
        #     end=end,
        #     duration=duration,
        #     output_path=output_path,
        #     framing=strategy.name,
        #     profile=seg.profile,
        #     width=strategy.width,
        #     height=strategy.height,
        #     file_size_bytes=file_size,
        #     created_at=datetime.now(timezone.utc),
        # )
        raise NotImplementedError("ClipExporter._export_one() not yet implemented")

    def _save_manifest(self, clips: list["ExportedClip"], output_dir: Path) -> None:
        """Save a JSON manifest of all exported clips.

        Args:
            clips: List of exported clips.
            output_dir: Directory to write clips.json.
        """
        manifest = [json.loads(clip.model_dump_json()) for clip in clips]
        dest = output_dir / "clips.json"
        dest.write_text(json.dumps(manifest, indent=2, default=str))
        log.info("export.manifest_saved", path=str(dest), count=len(clips))
