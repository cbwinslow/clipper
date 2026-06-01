"""Abstract base class for all clip scorers.

Agent Notes:
- All scorers must inherit from BaseScorer
- Scorers receive Segment and media path and return float score
- Use profile + intent to select the right scorer class
- Scorers should return normalized scores between 0.0 and 1.0
"""

from __future__ import annotations

import pathlib
from abc import ABC, abstractmethod

from vaclip.models.media import Segment


class BaseScorer(ABC):
    """Abstract base class for all VAClip clip scorers.

    Subclasses implement specific scoring logic for transcript, audio, or visual signals.
    Examples:
    - TranscriptScorer
    - AudioEnergyScorer
    - VisualMotionScorer
    """

    @abstractmethod
    def score(self, segment: Segment, media_path: pathlib.Path | None = None) -> float:
        """Score a segment and return a float score.

        Implementations must:
        1. Extract relevant features from segment and media_path
        2. Compute a normalized score between 0.0 and 1.0
        3. Never mutate the input segment

        Args:
            segment: The segment to score.
            media_path: Path to media file (audio for audio scorers, video for visual scorers,
                       unused for transcript scorers).

        Returns:
            Score in range [0.0, 1.0].
        """
        ...
