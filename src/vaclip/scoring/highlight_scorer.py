"""Highlight scoring engine for VAClip.

Provides multi-signal scoring to identify the most interesting segments
of video content. Combines transcript, audio energy, and visual motion
signals via a configurable composite scorer.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from vaclip.logging.setup import get_logger
from vaclip.models.schemas import HighlightType
from vaclip.scoring.base import BaseScorer

if TYPE_CHECKING:
    from vaclip.models.media import MediaAsset, ScoredSegment, Segment, Transcript

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Scoring Profiles
# ---------------------------------------------------------------------------

@dataclass
class ScoringProfile:
    """Configures weights and thresholds for a specific content type."""

    name: str
    transcript_weight: float = 0.5
    audio_weight: float = 0.3
    visual_weight: float = 0.2
    min_duration: float = 5.0
    max_duration: float = 60.0
    top_n: int = 10


PROFILES: dict[str, ScoringProfile] = {
    "podcast": ScoringProfile(
        "podcast",
        transcript_weight=0.7,
        audio_weight=0.2,
        visual_weight=0.1,
    ),
    "gaming": ScoringProfile(
        "gaming",
        transcript_weight=0.2,
        audio_weight=0.4,
        visual_weight=0.4,
    ),
    "sports": ScoringProfile(
        "sports",
        transcript_weight=0.1,
        audio_weight=0.3,
        visual_weight=0.6,
    ),
    "interview": ScoringProfile(
        "interview",
        transcript_weight=0.6,
        audio_weight=0.3,
        visual_weight=0.1,
    ),
    "music": ScoringProfile(
        "music",
        transcript_weight=0.1,
        audio_weight=0.6,
        visual_weight=0.3,
    ),
    "generic": ScoringProfile("generic"),
}


def get_profile(name: str) -> ScoringProfile:
    """Return a named ScoringProfile, falling back to 'generic' if not found."""
    profile = PROFILES.get(name)
    if profile is None:
        log.warning("scoring.unknown_profile", name=name, fallback="generic")
        return PROFILES["generic"]
    return profile


# ---------------------------------------------------------------------------
# Individual Scorers
# ---------------------------------------------------------------------------

class TranscriptScorer(BaseScorer):
    """Score segments based on transcript content signals.

    Analyzes keyword density, sentiment, pacing, and reaction words
    to identify verbally engaging or emotionally resonant moments.
    """

    FUNNY_WORDS: frozenset[str] = frozenset({
        "laugh", "funny", "hilarious", "joke", "lol", "haha", "prank",
        "comedy", "ridiculous", "absurd", "silly", "goofy",
    })
    INSIGHTFUL_WORDS: frozenset[str] = frozenset({
        "important", "key", "critical", "essentially", "basically",
        "the point is", "what matters", "the truth", "realize", "insight",
        "secret", "lesson", "mistake", "wrong", "actually",
    })
    HYPE_WORDS: frozenset[str] = frozenset({
        "incredible", "amazing", "unbelievable", "insane", "crazy",
        "wild", "epic", "legendary", "mind-blowing", "shocking", "wow",
        "omg", "no way", "what",
    })

    def score(self, segment: Segment, media_path: Path | None = None) -> float:
        """Score a segment based on transcript text signals."""
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

        words = segment.text.split()
        word_count = len(words)

        if word_count == 0:
            log.warning("scoring.empty_segment", segment_id=segment.id)
            return 0.0

        funny_hits = sum(1 for word in words if word.lower() in self.FUNNY_WORDS)
        insightful_hits = sum(1 for word in words if word.lower() in self.INSIGHTFUL_WORDS)
        hype_hits = sum(1 for word in words if word.lower() in self.HYPE_WORDS)
        total_hits = funny_hits + insightful_hits + hype_hits

        keyword_density = total_hits / word_count if word_count > 0 else 0.0

        duration = segment.end - segment.start
        words_per_second = word_count / duration if duration > 0 else 0.0
        if words_per_second >= 2.0:
            pacing_score = min(words_per_second / 5.0, 1.0)
        else:
            pacing_score = words_per_second / 2.0
        pacing_score = max(0.0, min(pacing_score, 1.0))

        analyzer = SentimentIntensityAnalyzer()
        sentiment_scores = analyzer.polarity_scores(segment.text)
        sentiment_score = (sentiment_scores["compound"] + 1) / 2

        weighted_sum = (keyword_density * 0.4) + (pacing_score * 0.3) + (sentiment_score * 0.3)
        final_score = max(0.0, min(weighted_sum, 1.0))

        log.debug(
            "scoring.transcript_score",
            segment_id=segment.id,
            keyword_density=keyword_density,
            pacing_score=pacing_score,
            sentiment_score=sentiment_score,
            final_score=final_score,
        )

        return final_score


class AudioEnergyScorer(BaseScorer):
    """Score segments based on audio energy and dynamics.

    Uses librosa to analyze the audio track and identify segments with
    high energy, volume spikes, or low silence ratios.
    """

    SILENCE_THRESHOLD_DB: float = -40.0

    def score(self, segment: Segment, media_path: Path | None = None) -> float:
        """Score a segment based on audio energy features."""
        if media_path is None:
            log.warning("scoring.audio_path_missing", scorer="AudioEnergyScorer")
            return 0.0

        try:
            import librosa
            import numpy as np

            duration = segment.end - segment.start
            y, _ = librosa.load(
                media_path,
                sr=16000,
                offset=segment.start,
                duration=duration
            )

            if len(y) == 0:
                log.warning("scoring.empty_audio_slice", segment_id=segment.id)
                return 0.0

            hop_length = 512
            rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]

            rms_db = librosa.amplitude_to_db(rms, ref=np.max)
            silence_frames = rms_db < self.SILENCE_THRESHOLD_DB
            silence_ratio = np.mean(silence_frames) if len(silence_frames) > 0 else 0.0

            rms_diff = np.diff(rms)
            spike_threshold = np.mean(rms_diff) + 2 * np.std(rms_diff)
            spikes = rms_diff > spike_threshold
            spike_ratio = np.mean(spikes) if len(spikes) > 0 else 0.0

            energy_score = np.mean(rms) / (np.max(rms) + 1e-8)
            energy_score = min(energy_score, 1.0)

            silence_score = 1.0 - silence_ratio

            if spike_ratio <= 0.15:
                spike_score = spike_ratio / 0.15
            else:
                spike_score = max(0.0, 1.0 - (spike_ratio - 0.15) * 2)

            final_score = (energy_score * 0.4) + (silence_score * 0.3) + (spike_score * 0.3)
            final_score = max(0.0, min(final_score, 1.0))

            log.debug(
                "scoring.audio_energy_score",
                segment_id=segment.id,
                energy_score=energy_score,
                silence_score=silence_score,
                spike_score=spike_score,
                final_score=final_score,
            )

            return final_score

        except Exception as e:
            log.error(
                "scoring.audio_error",
                error=str(e),
                scorer="AudioEnergyScorer",
                segment_id=segment.id,
            )
            return 0.0


class VisualMotionScorer(BaseScorer):
    """Score segments based on visual activity in video frames.

    Samples frames from the video and computes frame differences to quantify
    motion intensity, then normalizes to a 0-1 score.
    """

    SAMPLE_FPS: float = 2.0

    def score(self, segment: Segment, media_path: Path | None = None) -> float:
        """Score a segment based on visual motion and scene changes."""
        if media_path is None:
            log.warning("scoring.video_path_missing", scorer="VisualMotionScorer")
            return 0.0

        try:
            import cv2
            import numpy as np

            duration = segment.end - segment.start
            if duration <= 0:
                return 0.0

            cap = cv2.VideoCapture(str(media_path))
            if not cap.isOpened():
                log.error("scoring.visual_video_open_failed", path=str(media_path))
                return 0.0

            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0

            # Calculate frame indices to sample
            start_frame = int(segment.start * fps)
            end_frame = int(segment.end * fps)
            sample_interval = max(1, int(fps / self.SAMPLE_FPS))

            motion_scores = []
            prev_frame = None

            for frame_idx in range(start_frame, min(end_frame, total_frames), sample_interval):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret:
                    continue

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                if prev_frame is not None:
                    diff = cv2.absdiff(gray, prev_frame)
                    motion = np.mean(diff) / 255.0
                    motion_scores.append(motion)

                prev_frame = gray

            cap.release()

            if not motion_scores:
                return 0.0

            # Average motion intensity, then normalize to 0-1
            avg_motion = float(np.mean(motion_scores))
            # Boost contrast: typical motion values are 0.01-0.1, scale up
            score = min(avg_motion * 5.0, 1.0)

            log.debug(
                "scoring.visual_motion_score",
                segment_id=segment.id,
                frame_count=len(motion_scores),
                avg_motion=avg_motion,
                final_score=score,
            )

            return score

        except ImportError:
            log.warning("scoring.opencv_not_installed")
            return 0.0
        except Exception as e:
            log.error("scoring.visual_error", error=str(e), segment_id=segment.id)
            return 0.0


# ---------------------------------------------------------------------------
# Composite Scorer
# ---------------------------------------------------------------------------

class CompositeScorer:
    """Combines all scorers with profile-defined weights to rank segments.

    This is the main entry point for the scoring layer. It runs all
    individual scorers and produces a ranked list of ScoredSegments.
    """

    def __init__(self, profile: ScoringProfile) -> None:
        """Initialize with a scoring profile."""
        self.profile = profile
        self.transcript_scorer = TranscriptScorer()
        self.audio_scorer = AudioEnergyScorer()
        self.visual_scorer = VisualMotionScorer()

    def score_all(
        self,
        segments: list[Segment],
        transcript: Transcript,  # noqa: F841 - kept for future extensibility
        media: MediaAsset,
    ) -> list[ScoredSegment]:
        """Score all segments and return them ranked by composite score."""
        from vaclip.models.media import ScoredSegment, SignalScore

        log.info(
            "scoring.start",
            profile=self.profile.name,
            transcript_id=getattr(transcript, "id", None),
            segment_count=len(segments),
        )

        scored: list[ScoredSegment] = []
        for segment in segments:
            duration = segment.end - segment.start
            if duration < self.profile.min_duration or duration > self.profile.max_duration:
                continue

            t_score = self.transcript_scorer.score(segment, media_path=None)
            a_score = self.audio_scorer.score(segment, media_path=media.audio_path)
            v_score = self.visual_scorer.score(segment, media_path=media.local_path)

            transcript_signal = SignalScore(
                name="transcript",
                raw=t_score,
                normalized=t_score,
                weight=self.profile.transcript_weight,
            )
            audio_signal = SignalScore(
                name="audio",
                raw=a_score,
                normalized=a_score,
                weight=self.profile.audio_weight,
            )
            visual_signal = SignalScore(
                name="visual",
                raw=v_score,
                normalized=v_score,
                weight=self.profile.visual_weight,
            )

            scored_segment = ScoredSegment(
                segment=segment,
                highlight_type=self._classify(segment, t_score, a_score, v_score),
                signals=[transcript_signal, audio_signal, visual_signal],
            )

            scored_segment.compute_score()
            scored.append(scored_segment)

        scored.sort(key=lambda s: s.score, reverse=True)

        for rank, s in enumerate(scored, start=1):
            s.rank = rank

        try:
            asset_id = media.local_path.stem
            cache_dir = Path("cache/scores")
            cache_dir.mkdir(parents=True, exist_ok=True)
            score_file = cache_dir / f"{asset_id}.json"

            score_data = []
            for s in scored:
                score_data.append({
                    "segment": {
                        "id": s.segment.id,
                        "text": s.segment.text,
                        "start": s.segment.start,
                        "end": s.segment.end,
                    },
                    "highlight_type": s.highlight_type.value,
                    "score": s.score,
                    "rank": s.rank,
                    "signals": [
                        {
                            "name": sig.name,
                            "raw": sig.raw,
                            "normalized": sig.normalized,
                            "weight": sig.weight,
                            "weighted": sig.weighted
                        }
                        for sig in s.signals
                    ]
                })

            with open(score_file, "w") as f:
                json.dump(score_data, f, indent=2)

            log.info("scores.saved", file=str(score_file), count=len(scored))
        except Exception as e:
            log.error("scores.save_failed", error=str(e))

        log.info(
            "scoring.complete",
            scored=len(scored),
            top_score=scored[0].score if scored else 0,
        )
        return scored

    def _classify(
        self,
        segment: Segment,
        transcript_score: float,
        audio_score: float,
        visual_score: float,
    ) -> HighlightType:
        """Classify the highlight type based on which signal dominated."""
        scores = {
            "transcript": transcript_score,
            "audio": audio_score,
            "visual": visual_score
        }
        dominant_signal = max(scores.items(), key=lambda x: x[1])[0]

        if dominant_signal == "transcript":
            text_lower = segment.text.lower()
            words = text_lower.split()

            funny_hits = sum(1 for word in words if word in TranscriptScorer.FUNNY_WORDS)
            if funny_hits > 0:
                return HighlightType.LAUGH

            insightful_hits = sum(1 for word in words if word in TranscriptScorer.INSIGHTFUL_WORDS)
            if insightful_hits > 0:
                return HighlightType.KEY_QUOTE

            hype_hits = sum(1 for word in words if word in TranscriptScorer.HYPE_WORDS)
            if hype_hits > 0:
                return HighlightType.REACTION

        if dominant_signal == "audio":
            return HighlightType.PEAK_ENERGY

        if dominant_signal == "visual":
            return HighlightType.PEAK_ENERGY

        return HighlightType.GENERIC


# ---------------------------------------------------------------------------
# Signal Normalisation Helpers
# ---------------------------------------------------------------------------


def normalise_minmax(values: list[float]) -> list[float]:
    """Normalize values to 0-1 range using min-max scaling.

    Args:
        values: List of raw scores to normalize.

    Returns:
        List of normalized scores in [0.0, 1.0] range.
        Returns zeros if all values are identical or list is empty.
    """
    if not values:
        return []

    min_val = min(values)
    max_val = max(values)

    if max_val == min_val:
        return [0.0] * len(values)

    return [(v - min_val) / (max_val - min_val) for v in values]


def normalise_zscore(values: list[float]) -> list[float]:
    """Normalize values using z-score (mean=0.5, std=0.2) scaling.

    Args:
        values: List of raw scores to normalize.

    Returns:
        List of normalized scores. Values beyond ±2σ are clamped to [0.0, 1.0].
        Returns zeros if std is zero or list is empty.
    """
    import numpy as np

    if not values:
        return []

    arr = np.array(values, dtype=np.float64)
    mean = np.mean(arr)
    std = np.std(arr)

    if std == 0:
        return [0.0] * len(values)

    normalized = (arr - mean) / std
    # Scale to mean=0.5, std=0.2, then clamp
    result = (normalized / 2.0) + 0.5
    return [float(max(0.0, min(1.0, v))) for v in result]
