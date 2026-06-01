"""tests.unit.segmentation.test_models

Unit tests for vaclip.segmentation.models Pydantic domain models.
All tests should be fast and require no I/O or external dependencies.
"""

from __future__ import annotations

import pytest

from vaclip.segmentation.models import ClipCandidate
from vaclip.models.schemas import FramingStrategy


class TestClipCandidate:
    def test_valid_clip_candidate(self) -> None:
        """Test creation of a valid ClipCandidate with word alignment fields."""
        candidate = ClipCandidate(
            start=12.5,
            end=45.0,
            framing=FramingStrategy.WIDE,
            segment_id=3,
            start_word=15,
            end_word=120,
        )
        assert candidate.start == 12.5
        assert candidate.end == 45.0
        assert candidate.framing == FramingStrategy.WIDE
        assert candidate.segment_id == 3
        assert candidate.start_word == 15
        assert candidate.end_word == 120

    def test_end_before_start_raises(self) -> None:
        """Test that end time before start time raises ValueError."""
        with pytest.raises(ValueError, match="end must be"):
            ClipCandidate(
                start=45.0,
                end=12.5,
                framing=FramingStrategy.WIDE,
                segment_id=3,
                start_word=15,
                end_word=120,
            )

    def test_end_equal_start_raises(self) -> None:
        """Test that end time equal to start time raises ValueError."""
        with pytest.raises(ValueError, match="end must be"):
            ClipCandidate(
                start=12.5,
                end=12.5,
                framing=FramingStrategy.WIDE,
                segment_id=3,
                start_word=15,
                end_word=120,
            )

    def test_word_indices_invalid_raises(self) -> None:
        """Test that end_word < start_word raises ValueError."""
        with pytest.raises(ValueError, match="end_word must be"):
            ClipCandidate(
                start=12.5,
                end=45.0,
                framing=FramingStrategy.WIDE,
                segment_id=3,
                start_word=120,
                end_word=15,  # end_word < start_word
            )

    def test_word_indices_equal_valid(self) -> None:
        """Test that equal start_word and end_word is valid (single word clip)."""
        candidate = ClipCandidate(
            start=12.5,
            end=13.0,
            framing=FramingStrategy.WIDE,
            segment_id=3,
            start_word=15,
            end_word=15,  # Single word
        )
        assert candidate.start_word == candidate.end_word == 15

    def test_negative_word_indices_raises(self) -> None:
        """Test that negative word indices raise ValueError."""
        with pytest.raises(Exception):  # ValidationError from Pydantic
            ClipCandidate(
                start=12.5,
                end=45.0,
                framing=FramingStrategy.WIDE,
                segment_id=3,
                start_word=-1,  # Negative
                end_word=120,
            )

        with pytest.raises(Exception):  # ValidationError from Pydantic
            ClipCandidate(
                start=12.5,
                end=45.0,
                framing=FramingStrategy.WIDE,
                segment_id=3,
                start_word=15,
                end_word=-1,  # Negative
            )

    def test_example_fixture(self) -> None:
        """Test the example fixture method."""
        candidate = ClipCandidate.example()
        assert candidate.start == 12.5
        assert candidate.end == 45.0
        assert candidate.framing == FramingStrategy.WIDE
        assert candidate.segment_id == 3
        assert candidate.start_word == 15
        assert candidate.end_word == 120

    def test_serialization_deserialization(self) -> None:
        """Test that the model can be serialized to dict and deserialized."""
        original = ClipCandidate(
            start=12.5,
            end=45.0,
            framing=FramingStrategy.VERTICAL,
            segment_id=7,
            start_word=100,
            end_word=250,
        )
        
        # Serialize to dict
        data = original.to_dict()
        assert isinstance(data, dict)
        assert data["start"] == 12.5
        assert data["end"] == 45.0
        assert data["framing"] == "vertical"
        assert data["segment_id"] == 7
        assert data["start_word"] == 100
        assert data["end_word"] == 250
        
        # Deserialize from dict
        restored = ClipCandidate.from_dict(data)
        assert restored == original
