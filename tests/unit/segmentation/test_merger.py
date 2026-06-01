"""tests.unit.segmentation.test_merger

Unit tests for vaclip.segmentation.merger module.
"""

from __future__ import annotations

import pytest

from vaclip.models.schemas import Segment, Word
from vaclip.segmentation.merger import merge


class TestMerger:
    def test_merge_creates_candidates_with_word_indices(self) -> None:
        """Test that merge creates ClipCandidate objects with word alignment fields."""
        # Create test shot boundaries that overlap with transcript segments
        shots = [(2.0, 4.0), (6.0, 7.0)]  # Overlaps with both segments
        
        # Create test transcript segments with word-level timestamps
        words_seg1 = [
            Word(text="Hello", start=0.0, end=0.5, confidence=0.9),
            Word(text="world", start=0.6, end=1.2, confidence=0.8),
            Word(text="this", start=1.3, end=1.8, confidence=0.85),
            Word(text="is", start=1.9, end=2.2, confidence=0.9),
            Word(text="a", start=2.3, end=2.5, confidence=0.95),
            Word(text="test", start=2.6, end=3.2, confidence=0.9),
        ]
        words_seg2 = [
            Word(text="Another", start=5.0, end=5.8, confidence=0.85),
            Word(text="segment", start=5.9, end=6.6, confidence=0.9),
            Word(text="with", start=6.7, end=7.2, confidence=0.8),
            Word(text="words", start=7.3, end=8.0, confidence=0.85),
        ]
        
        transcript_segments = [
            Segment(id=0, text="Hello world this is a test", start=0.0, end=3.5, words=words_seg1),
            Segment(id=1, text="Another segment with words", start=5.0, end=8.5, words=words_seg2),
        ]
        
        # Run the merger
        candidates = merge(shots, transcript_segments, min_duration=1.0)
        
        # Verify we get candidates
        assert len(candidates) > 0
        
        # Check that each candidate has word alignment fields populated
        for candidate in candidates:
            assert hasattr(candidate, 'start_word')
            assert hasattr(candidate, 'end_word')
            assert isinstance(candidate.start_word, int)
            assert isinstance(candidate.end_word, int)
            assert candidate.start_word >= 0
            assert candidate.end_word >= 0
            assert candidate.end_word >= candidate.start_word  # end_word should be >= start_word
            
            # Verify the word indices make sense for the segment
            seg = transcript_segments[candidate.segment_id]
            assert candidate.start_word < len(seg.words)
            assert candidate.end_word < len(seg.words)
            
            # Verify that the word timing overlaps with the clip timing
            if candidate.start_word < len(seg.words):
                start_word = seg.words[candidate.start_word]
                # The start word should overlap with the clip start (word ends after clip starts)
                assert start_word.end >= candidate.start or abs(start_word.end - candidate.start) < 0.1
            
            if candidate.end_word < len(seg.words):
                end_word = seg.words[candidate.end_word]
                # The end word should overlap with the clip end (word starts before clip ends)
                assert end_word.start <= candidate.end or abs(end_word.start - candidate.end) < 0.1

    def test_merge_with_no_overlap_returns_empty(self) -> None:
        """Test that merge returns empty list when there's no overlap."""
        shots = [(0.0, 5.0)]
        words = [Word(text="test", start=10.0, end=10.5, confidence=0.9)]
        transcript_segments = [Segment(id=0, text="test", start=10.0, end=10.5, words=words)]
        
        candidates = merge(shots, transcript_segments, min_duration=5.0)
        assert len(candidates) == 0

    def test_merge_respects_min_duration(self) -> None:
        """Test that merge respects the minimum duration threshold."""
        shots = [(0.0, 3.0)]  # 3 second shot
        words = [Word(text="test", start=0.0, end=0.5, confidence=0.9)]
        transcript_segments = [Segment(id=0, text="test", start=0.0, end=0.5, words=words)]
        
        # With min_duration=5.0, should return empty since overlap is only 0.5 seconds
        candidates = merge(shots, transcript_segments, min_duration=5.0)
        assert len(candidates) == 0
        
        # With min_duration=0.1, should return candidate since overlap is 0.5 seconds
        candidates = merge(shots, transcript_segments, min_duration=0.1)
        assert len(candidates) == 1
        assert candidates[0].start == 0.0
        assert candidates[0].end == 0.5
        assert candidates[0].segment_id == 0
        assert candidates[0].start_word == 0
        assert candidates[0].end_word == 0

    def test_merge_handles_empty_inputs(self) -> None:
        """Test that merge handles empty shot or transcript lists."""
        # Empty shots
        candidates = merge([], [Segment(id=0, text="test", start=0.0, end=1.0, words=[])])
        assert len(candidates) == 0
        
        # Empty transcripts
        candidates = merge([(0.0, 5.0)], [])
        assert len(candidates) == 0
        
        # Both empty
        candidates = merge([], [])
        assert len(candidates) == 0
