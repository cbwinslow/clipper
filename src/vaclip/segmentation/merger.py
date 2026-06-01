"""Segment merger for VAClip.

Combines shot boundaries with transcript segments to create ClipCandidate objects.
"""

from __future__ import annotations

import orjson

from vaclip.config.settings import get_settings
from vaclip.logging.setup import get_logger
from vaclip.models.schemas import FramingStrategy, Segment
from vaclip.segmentation.models import ClipCandidate

log = get_logger(__name__)


def merge(
    shots: list[tuple[float, float]],
    transcript_segments: list[Segment],
    min_duration: float = 5.0,
) -> list[ClipCandidate]:
    """Merge shot boundaries with transcript segments to create clip candidates.

    Args:
        shots: List of (start, end) tuples representing shot boundaries in seconds.
        transcript_segments: List of transcript segments from ASR.
        min_duration: Minimum clip duration in seconds (default: 5.0).

    Returns:
        List of ClipCandidate objects representing overlapping regions that meet
        the minimum duration threshold.
    """
    candidates: list[ClipCandidate] = []

    for shot_start, shot_end in shots:
        for seg in transcript_segments:
            # Calculate overlap between shot and transcript segment
            overlap_start = max(shot_start, seg.start)
            overlap_end = min(shot_end, seg.end)
            overlap_duration = overlap_end - overlap_start

            if overlap_duration >= min_duration:
                # Find word indices within the overlapping region
                start_word_idx = 0
                end_word_idx = len(seg.words) - 1

                # Find first word that ends at or after overlap_start
                for i, word in enumerate(seg.words):
                    if word.end >= overlap_start:  # Word ends after or at overlap start
                        start_word_idx = i
                        break

                # Find last word that starts at or before overlap_end
                for i in range(len(seg.words) - 1, -1, -1):
                    if seg.words[i].start <= overlap_end:  # Word starts before or at overlap end
                        end_word_idx = i
                        break

                candidate = ClipCandidate(
                    start=overlap_start,
                    end=overlap_end,
                    framing=FramingStrategy.WIDE,
                    segment_id=seg.id,
                    start_word=start_word_idx,
                    end_word=end_word_idx,
                )
                candidates.append(candidate)

    return candidates


def save_segmentation_artifacts(
    run_id: str,
    shots: list[tuple[float, float]],
    candidates: list[ClipCandidate],
) -> None:
    """Save segmentation artifacts to cache/<run_id>/candidates.json.

    Args:
        run_id: Unique identifier for the pipeline run.
        shots: List of (start, end) tuples representing shot boundaries in seconds.
        candidates: List of ClipCandidate objects representing merged segments.
    """
    try:
        settings = get_settings()
        cache_dir = settings.paths.cache_dir / run_id
        cache_dir.mkdir(parents=True, exist_ok=True)

        artifact_data = {
            "shot_boundaries": shots,
            "candidates": [candidate.model_dump() for candidate in candidates],
        }

        artifact_file = cache_dir / "candidates.json"
        artifact_file.write_bytes(
            orjson.dumps(artifact_data, option=orjson.OPT_INDENT_2)
        )

        log.info(
            "segmentation.artifacts_saved",
            run_id=run_id,
            shot_count=len(shots),
            candidate_count=len(candidates),
            path=str(artifact_file),
        )
    except Exception as e:
        log.error(
            "segmentation.artifacts_save_failed",
            run_id=run_id,
            error=str(e),
            exc_info=True,
        )
        raise
