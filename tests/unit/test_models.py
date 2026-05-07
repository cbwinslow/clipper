"""tests.unit.test_models

Unit tests for vaclip.models.schemas Pydantic domain models.
All tests should be fast and require no I/O or external dependencies.

Agent Instructions:
  - Keep tests isolated and deterministic
  - Use pytest parametrize for edge cases
  - Each test class maps to one schema model
  - Use Model.example() fixtures where available
  - Run with: pytest tests/unit/test_models.py -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vaclip.models.schemas import (
    ClipBounds,
    ExportedClip,
    FramingStrategy,
    HighlightType,
    MediaMeta,
    MediaType,
    Profile,
    ScoredSegment,
    Segment,
    SignalScore,
    Transcript,
    Word,
)


# ---------------------------------------------------------------------------
# Word
# ---------------------------------------------------------------------------


class TestWord:
    def test_valid_word(self) -> None:
        word = Word(text="hello", start=0.0, end=0.5)
        assert word.text == "hello"
        assert word.confidence == 1.0

    def test_end_before_start_raises(self) -> None:
        with pytest.raises(ValueError, match="end must be"):
            Word(text="bad", start=1.0, end=0.5)

    def test_confidence_bounds(self) -> None:
        with pytest.raises(Exception):  # noqa: PT011
            Word(text="x", start=0.0, end=0.1, confidence=1.5)


# ---------------------------------------------------------------------------
# Segment
# ---------------------------------------------------------------------------


class TestSegment:
    def test_example_fixture(self) -> None:
        seg = Segment.example()
        assert seg.id == 0
        assert seg.duration == pytest.approx(3.5)
        assert len(seg.words) == 5

    def test_duration_property(self) -> None:
        seg = Segment(id=1, text="hi", start=2.0, end=5.0)
        assert seg.duration == pytest.approx(3.0)

    def test_speaker_defaults_none(self) -> None:
        seg = Segment(id=0, text="test", start=0.0, end=1.0)
        assert seg.speaker is None


# ---------------------------------------------------------------------------
# Transcript
# ---------------------------------------------------------------------------


class TestTranscript:
    def test_full_text_joins_segments(self) -> None:
        segments = [
            Segment(id=0, text="Hello", start=0.0, end=1.0),
            Segment(id=1, text="world", start=1.0, end=2.0),
        ]
        t = Transcript(segments=segments, model_name="large-v3", duration_sec=2.0)
        assert t.full_text == "Hello world"

    def test_empty_transcript(self) -> None:
        t = Transcript(model_name="tiny", duration_sec=0.0)
        assert t.full_text == ""
        assert t.segments == []


# ---------------------------------------------------------------------------
# MediaMeta
# ---------------------------------------------------------------------------


class TestMediaMeta:
    def test_example_fixture(self) -> None:
        meta = MediaMeta.example()
        assert meta.media_type == MediaType.PODCAST
        assert meta.duration_sec == pytest.approx(3600.0)

    def test_immutable(self) -> None:
        meta = MediaMeta.example()
        with pytest.raises(Exception):  # noqa: PT011
            meta.title = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ClipBounds
# ---------------------------------------------------------------------------


class TestClipBounds:
    def test_padded_start_floored_at_zero(self) -> None:
        bounds = ClipBounds(start=0.2, end=5.0, pad_start=1.0)
        assert bounds.padded_start == 0.0

    def test_padded_end(self) -> None:
        bounds = ClipBounds(start=1.0, end=5.0, pad_end=0.5)
        assert bounds.padded_end == pytest.approx(5.5)

    def test_duration(self) -> None:
        bounds = ClipBounds(start=1.0, end=4.0, pad_start=0.5, pad_end=0.5)
        assert bounds.duration == pytest.approx(4.0)  # 0.5..4.5

    def test_end_before_start_raises(self) -> None:
        with pytest.raises(ValueError, match="end must be"):
            ClipBounds(start=5.0, end=1.0)

    @pytest.mark.parametrize(
        "start,end,expected_is_short",
        [
            (0.0, 30.0, True),
            (0.0, 60.0, True),   # exactly 60 s -> short
            (0.0, 61.0, False),
        ],
    )
    def test_is_short_boundary(
        self, start: float, end: float, expected_is_short: bool
    ) -> None:
        # ExportedClip.is_short delegates to bounds.duration
        bounds = ClipBounds(start=start, end=end, pad_start=0.0, pad_end=0.0)
        assert bounds.duration <= 60.0 if expected_is_short else bounds.duration > 60.0


# ---------------------------------------------------------------------------
# SignalScore / ScoredSegment
# ---------------------------------------------------------------------------


class TestSignalScore:
    def test_weighted_property(self) -> None:
        sig = SignalScore(name="energy", raw=0.8, normalized=0.8, weight=2.0)
        assert sig.weighted == pytest.approx(1.6)

    def test_normalized_bounds(self) -> None:
        with pytest.raises(Exception):  # noqa: PT011
            SignalScore(name="x", raw=1.0, normalized=1.5, weight=1.0)


class TestScoredSegment:
    def test_compute_score_weighted_average(self) -> None:
        seg = Segment.example()
        scored = ScoredSegment(
            segment=seg,
            signals=[
                SignalScore(name="a", raw=1.0, normalized=0.6, weight=1.0),
                SignalScore(name="b", raw=1.0, normalized=1.0, weight=3.0),
            ],
        )
        score = scored.compute_score()
        # (0.6*1 + 1.0*3) / (1+3) = 3.6 / 4 = 0.9
        assert score == pytest.approx(0.9)

    def test_empty_signals_returns_zero(self) -> None:
        scored = ScoredSegment(segment=Segment.example())
        score = scored.compute_score()
        assert score == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Enum smoke tests
# ---------------------------------------------------------------------------


def test_profile_values() -> None:
    assert Profile.PODCAST.value == "podcast"
    assert Profile.GAMING.value == "gaming"


def test_framing_strategy_values() -> None:
    assert FramingStrategy.WIDE.value == "wide"
    assert FramingStrategy.VERTICAL.value == "vertical"
    assert FramingStrategy.SQUARE.value == "square"


def test_highlight_type_generic_default() -> None:
    scored = ScoredSegment(segment=Segment.example())
    assert scored.highlight_type == HighlightType.GENERIC
