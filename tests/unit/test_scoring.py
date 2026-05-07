"""tests.unit.test_scoring

Unit tests for vaclip.scoring.highlight_scorer.
All tests are pure-Python with no GPU or model dependencies.

Agent Instructions:
  - Mock audio/visual feature extractors at the boundary
  - Test each scoring signal in isolation
  - Test profile weight application
  - Test rank assignment ordering (highest score = rank 1)
  - Run with: pytest tests/unit/test_scoring.py -v
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from vaclip.models.schemas import (
    HighlightType,
    Profile,
    Segment,
    SignalScore,
    ScoredSegment,
    Transcript,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_segment(id_: int, text: str, start: float, end: float) -> Segment:
    return Segment(id=id_, text=text, start=start, end=end)


def _make_transcript(*segments: Segment) -> Transcript:
    return Transcript(
        segments=list(segments),
        model_name="test-model",
        duration_sec=segments[-1].end if segments else 0.0,
    )


# ---------------------------------------------------------------------------
# ScoredSegment compute_score
# ---------------------------------------------------------------------------


class TestComputeScore:
    """Tests for ScoredSegment.compute_score()."""

    def test_single_signal_full_weight(self) -> None:
        scored = ScoredSegment(
            segment=_make_segment(0, "test", 0.0, 5.0),
            signals=[SignalScore(name="energy", raw=0.9, normalized=0.9, weight=1.0)],
        )
        assert scored.compute_score() == pytest.approx(0.9)

    def test_two_signals_equal_weight(self) -> None:
        scored = ScoredSegment(
            segment=_make_segment(0, "test", 0.0, 5.0),
            signals=[
                SignalScore(name="a", raw=0.0, normalized=0.0, weight=1.0),
                SignalScore(name="b", raw=1.0, normalized=1.0, weight=1.0),
            ],
        )
        assert scored.compute_score() == pytest.approx(0.5)

    def test_zero_weight_signals_no_division_error(self) -> None:
        """When all weights are 0 the scorer should avoid division by zero."""
        scored = ScoredSegment(
            segment=_make_segment(0, "test", 0.0, 5.0),
            signals=[
                SignalScore(name="a", raw=0.5, normalized=0.5, weight=0.0),
            ],
        )
        # Should not raise; result may be 0 due to guard in compute_score
        result = scored.compute_score()
        assert isinstance(result, float)

    def test_score_stored_on_instance(self) -> None:
        scored = ScoredSegment(
            segment=_make_segment(0, "test", 0.0, 5.0),
            signals=[SignalScore(name="s", raw=0.7, normalized=0.7, weight=1.0)],
        )
        scored.compute_score()
        assert scored.score == pytest.approx(0.7)


# ---------------------------------------------------------------------------
# HighlightScorer - placeholder tests
# (Implement these once HighlightScorer is wired up)
# ---------------------------------------------------------------------------


class TestHighlightScorerPlaceholder:
    """Placeholder tests for the HighlightScorer class.

    Agent Instructions:
      - Replace NotImplementedError markers with real assertions once
        vaclip.scoring.highlight_scorer.HighlightScorer is implemented
      - Import HighlightScorer at the top of this file when ready
      - Each test should mock external dependencies (librosa, transformers)
        using unittest.mock.patch or pytest-mock's mocker fixture
    """

    def test_scorer_returns_scored_segments_placeholder(self) -> None:
        """TODO: Instantiate HighlightScorer and call .score(transcript).

        Expected:
          - Returns list[ScoredSegment] with length == len(transcript.segments)
          - Each ScoredSegment has score in [0.0, 1.0]
          - Rank 1 segment has the highest score
        """
        pytest.skip("HighlightScorer not yet implemented - remove skip when ready")

    def test_podcast_profile_weights_speech_signals(self) -> None:
        """TODO: Verify that podcast profile up-weights sentiment/keyword signals.

        Expected:
          - Podcast profile boosts 'sentiment' and 'keyword_density' weights
          - Gaming profile boosts 'audio_energy' and 'reaction' weights
        """
        pytest.skip("Profile weight application not yet tested")

    def test_rank_assignment_highest_score_is_rank_1(self) -> None:
        """TODO: Verify rank ordering after .score() call.

        Expected:
          - The ScoredSegment with the highest .score gets rank=1
          - Ranks are contiguous integers starting at 1
        """
        pytest.skip("Rank assignment not yet implemented")

    def test_min_segment_duration_filter(self) -> None:
        """TODO: Very short segments (< min_duration setting) should be excluded.

        Expected:
          - Segments shorter than settings.scoring.min_segment_duration are dropped
        """
        pytest.skip("Segment duration filter not yet implemented")


# ---------------------------------------------------------------------------
# Signal normalisation helpers
# ---------------------------------------------------------------------------


class TestSignalNormalisation:
    """Tests for signal normalisation utility functions.

    Agent Instructions:
      - Import normalise_minmax and normalise_zscore from
        vaclip.scoring.highlight_scorer once implemented
      - These are pure functions with no side effects
    """

    def test_minmax_normalise_full_range(self) -> None:
        pytest.skip("normalise_minmax not yet implemented")

    def test_minmax_single_value_returns_zero(self) -> None:
        pytest.skip("normalise_minmax edge case not yet implemented")

    def test_zscore_normalise_zero_std_returns_zeros(self) -> None:
        pytest.skip("normalise_zscore edge case not yet implemented")
