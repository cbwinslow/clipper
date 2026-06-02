"""Highlight scoring engine for VAClip.

Provides multi-signal scoring to identify the most interesting segments
of video content. Combines transcript, audio energy, and visual motion
signals via a configurable composite scorer.
"""
from __future__ import annotations

import pathlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from vaclip.logging.setup import get_logger

if TYPE_CHECKING:
    from vaclip.models.schemas import Segment, Transcript

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
    """Return a named ScoringProfile, falling back to 'generic'."""
    profile = PROFILES.get(name)
    if profile is None:
        log.warning("scoring.unknown_profile", name=name, fallback="generic")
        return PROFILES["generic"]
    return profile


# ---------------------------------------------------------------------------
# Individual Scorers
# ---------------------------------------------------------------------------

class TranscriptScorer:
    """Score segments based on transcript content signals."""

    FUNNY_WORDS: frozenset[str] = frozenset({
        "laugh", "funny", "hilarious", "joke", "lol", "haha", "prank",
        "comedy", "ridiculous", "absurd", "silly", "goofy", "humor",
    })
    INSIGHTFUL_WORDS: frozenset[str] = frozenset({
        "important", "key", "critical", "essentially", "basically",
        "the point is", "what matters", "the truth", "realize", "insight",
        "secret", "lesson", "mistake", "wrong", "actually", "discovered",
        "never", "always", "everyone", "nobody", "surprising", "unexpected",
    })
    HYPE_WORDS: frozenset[str] = frozenset({
        "incredible", "amazing", "unbelievable", "insane", "crazy",
        "wild", "epic", "legendary", "mind-blowing", "shocking", "wow",
        "omg", "no way", "what", "seriously", "literally", "absolutely",
    })
    EMOTIONAL_WORDS: frozenset[str] = frozenset({
        "love", "hate", "miss", "feel", "heart", "soul", "cry", "tears",
        "scared", "terrified", "excited", "proud", "ashamed", "grateful",
    })

    def score(self, segment: "Segment", audio_path: pathlib.Path | None = None) -> float:
        """Score segment by keyword density, pacing, and punctuation sentiment."""
        text = (segment.text or "").lower()
        words = text.split()
        if not words:
            return 0.0

        word_set = set(words)
        all_kw = self.FUNNY_WORDS | self.INSIGHTFUL_WORDS | self.HYPE_WORDS | self.EMOTIONAL_WORDS
        keyword_hits = len(word_set & all_kw)
        # weighted: funny/hype slightly higher than emotional
        weighted_hits = (
            len(word_set & self.FUNNY_WORDS) * 1.2
            + len(word_set & self.HYPE_WORDS) * 1.1
            + len(word_set & self.INSIGHTFUL_WORDS) * 1.0
            + len(word_set & self.EMOTIONAL_WORDS) * 0.9
        )
        density = min(weighted_hits / max(len(words), 1) * 5, 1.0)  # scale up small values

        # pacing: ~3 words/sec = fully engaging
        duration = max(segment.end - segment.start, 0.01)
        pacing = min(len(words) / duration / 3.0, 1.0)

        # punctuation as excitement proxy
        punct = min(
            (text.count("!") + text.count("?")) / max(len(words) / 8, 1),
            1.0,
        )

        score = density * 0.5 + pacing * 0.3 + punct * 0.2
        return float(min(max(score, 0.0), 1.0))


class AudioEnergyScorer:
    """Score segments based on audio energy and dynamics."""

    SILENCE_THRESHOLD_DB: float = -40.0

    def score(
        self,
        segment: "Segment",
        audio_path: pathlib.Path | None = None,
    ) -> float:
        """Score segment by RMS energy and silence ratio (requires librosa)."""
        if audio_path is None:
            log.warning("scoring.audio_path_missing", scorer="AudioEnergyScorer")
            return 0.0

        try:
            import librosa
            import numpy as np
        except ImportError:
            log.warning("scoring.librosa_missing", note="pip install librosa")
            return 0.0

        try:
            duration = max(segment.end - segment.start, 0.1)
            y, _sr = librosa.load(
                str(audio_path),
                sr=16000,
                offset=segment.start,
                duration=duration,
                mono=True,
            )
            if len(y) == 0:
                return 0.0

            rms = librosa.feature.rms(y=y)[0]
            rms_db = librosa.amplitude_to_db(rms, ref=float(np.max(rms)) if rms.max() > 0 else 1.0)
            silence_ratio = float(np.mean(rms_db < self.SILENCE_THRESHOLD_DB))
            mean_energy = float(np.mean(rms))

            # 0.1 RMS amplitude = loud/engaged speaker
            energy_score = float(np.clip(mean_energy / 0.1, 0.0, 1.0))
            activity_score = 1.0 - silence_ratio

            # detect energy spikes (sudden loud moments)
            if len(rms) > 2:
                spike_score = float(
                    np.clip(np.std(rms) / (mean_energy + 1e-8) / 2.0, 0.0, 1.0)
                )
            else:
                spike_score = 0.0

            score = energy_score * 0.5 + activity_score * 0.3 + spike_score * 0.2
            return float(np.clip(score, 0.0, 1.0))

        except Exception as exc:
            log.warning("scoring.audio_error", error=str(exc))
            return 0.0


class VisualMotionScorer:
    """Score segments based on visual activity and optical flow."""

    SAMPLE_FPS: float = 2.0

    def score(
        self,
        segment: "Segment",
        video_path: pathlib.Path | None = None,
    ) -> float:
        """Score segment by optical flow magnitude (requires opencv-python)."""
        if video_path is None:
            log.warning("scoring.video_path_missing", scorer="VisualMotionScorer")
            return 0.0

        try:
            import cv2
            import numpy as np
        except ImportError:
            log.warning("scoring.cv2_missing", note="pip install opencv-python")
            return 0.0

        try:
            cap = cv2.VideoCapture(str(video_path))
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            step = max(1, int(fps / self.SAMPLE_FPS))
            start_frame = int(segment.start * fps)
            end_frame = int(segment.end * fps)

            frames: list[Any] = []
            for frame_idx in range(start_frame, end_frame, step):
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if not ret:
                    break
                frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
            cap.release()

            if len(frames) < 2:
                return 0.0

            flow_magnitudes: list[float] = []
            for prev_f, curr_f in zip(frames[:-1], frames[1:]):
                flow = cv2.calcOpticalFlowFarneback(
                    prev_f, curr_f, None,
                    pyr_scale=0.5, levels=3, winsize=15,
                    iterations=3, poly_n=5, poly_sigma=1.2, flags=0,
                )
                mag = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
                flow_magnitudes.append(float(np.mean(mag)))

            mean_motion = float(np.mean(flow_magnitudes))
            # 10 pixels/frame avg = high-motion content
            score = float(np.clip(mean_motion / 10.0, 0.0, 1.0))
            return score

        except Exception as exc:
            log.warning("scoring.visual_error", error=str(exc))
            return 0.0


# ---------------------------------------------------------------------------
# Composite Scorer
# ---------------------------------------------------------------------------

class CompositeScorer:
    """Combines all scorers with profile-defined weights to rank segments."""

    def __init__(self, profile: ScoringProfile) -> None:
        self.profile = profile
        self.transcript_scorer = TranscriptScorer()
        self.audio_scorer = AudioEnergyScorer()
        self.visual_scorer = VisualMotionScorer()

    def score_all(
        self,
        segments: list["Segment"],
        transcript: Any,
        media: Any,
    ) -> list[Any]:
        """Score all segments and return them ranked by composite score."""
        from vaclip.models.schemas import ScoredSegment, SignalScore, HighlightType

        audio_path = (
            pathlib.Path(media.extra["audio_path"])
            if hasattr(media, "extra") and media.extra.get("audio_path")
            else None
        )
        video_path = (
            pathlib.Path(str(media.local_path))
            if hasattr(media, "local_path") and media.local_path
            else None
        )

        log.info(
            "scoring.start",
            profile=self.profile.name,
            segment_count=len(segments),
        )

        scored: list[Any] = []
        for segment in segments:
            duration = segment.end - segment.start
            if not (self.profile.min_duration <= duration <= self.profile.max_duration):
                continue

            t_score = self.transcript_scorer.score(segment)
            a_score = self.audio_scorer.score(segment, audio_path=audio_path)
            v_score = self.visual_scorer.score(segment, video_path=video_path)

            composite = (
                t_score * self.profile.transcript_weight
                + a_score * self.profile.audio_weight
                + v_score * self.profile.visual_weight
            )

            scored.append(ScoredSegment(
                segment=segment,
                score=composite,
                signals=[
                    SignalScore(
                        name="transcript",
                        raw=t_score,
                        normalized=t_score,
                        weight=self.profile.transcript_weight,
                    ),
                    SignalScore(
                        name="audio",
                        raw=a_score,
                        normalized=a_score,
                        weight=self.profile.audio_weight,
                    ),
                    SignalScore(
                        name="visual",
                        raw=v_score,
                        normalized=v_score,
                        weight=self.profile.visual_weight,
                    ),
                ],
                highlight_type=self._classify(segment, t_score, a_score, v_score),
            ))

        scored.sort(key=lambda s: s.score, reverse=True)
        for rank, s in enumerate(scored, start=1):
            s.rank = rank

        log.info(
            "scoring.complete",
            profile=self.profile.name,
            scored=len(scored),
            top_score=round(scored[0].score, 4) if scored else 0,
        )
        return scored[: self.profile.top_n]

    def _classify(
        self,
        segment: "Segment",
        transcript_score: float,
        audio_score: float,
        visual_score: float,
    ) -> Any:
        """Classify highlight type based on dominant signal."""
        from vaclip.models.schemas import HighlightType

        text = (segment.text or "").lower()
        word_set = set(text.split())

        # Keyword-based overrides first
        if word_set & TranscriptScorer.FUNNY_WORDS:
            return HighlightType.LAUGH
        if word_set & {"applause", "clap", "crowd"}:
            return HighlightType.APPLAUSE

        # Signal dominance
        scores = {
            "transcript": transcript_score * self.profile.transcript_weight,
            "audio": audio_score * self.profile.audio_weight,
            "visual": visual_score * self.profile.visual_weight,
        }
        dominant = max(scores, key=lambda k: scores[k])

        if dominant == "transcript":
            if word_set & TranscriptScorer.INSIGHTFUL_WORDS:
                return HighlightType.KEY_QUOTE
            return HighlightType.GENERIC
        if dominant == "audio":
            return HighlightType.PEAK_ENERGY
        if dominant == "visual":
            return HighlightType.REACTION
        return HighlightType.GENERIC
