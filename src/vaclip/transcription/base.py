"""Abstract base class for all transcription backends.

Agent Notes:
- All ASR backends must inherit from TranscriptionBackend
- Default implementation: FasterWhisperBackend (GPU, large-v3)
- TranscriptResult is the output contract - do not change field names
- word_timestamps=True is required for accurate clip boundary alignment
- Backends must handle CUDA OOM gracefully and fall back to int8
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TranscriptWord:
    """A single word with timing from ASR output."""

    word: str
    start: float  # seconds
    end: float    # seconds
    probability: float = 0.0


@dataclass
class TranscriptSegment:
    """A sentence-level transcript segment with timing."""

    id: int
    text: str
    start: float  # seconds
    end: float    # seconds
    avg_logprob: float = 0.0
    no_speech_prob: float = 0.0
    words: list[TranscriptWord] = field(default_factory=list)

    @property
    def duration(self) -> float:
        """Segment duration in seconds."""
        return self.end - self.start

    @property
    def word_count(self) -> int:
        """Number of words in segment."""
        return len(self.text.split())

    @property
    def words_per_minute(self) -> float:
        """Speech rate in words per minute."""
        if self.duration <= 0:
            return 0.0
        return (self.word_count / self.duration) * 60.0


@dataclass
class TranscriptResult:
    """Full transcript result from an ASR backend.

    This is the output contract for all transcription backends.
    Downstream stages consume this to generate candidates.
    """

    run_id: str
    audio_path: str
    language: str
    segments: list[TranscriptSegment] = field(default_factory=list)
    duration_seconds: float = 0.0
    model_name: str = ""
    compute_type: str = ""

    @property
    def full_text(self) -> str:
        """Concatenated full transcript text."""
        return " ".join(s.text.strip() for s in self.segments)

    @property
    def segment_count(self) -> int:
        """Total number of transcript segments."""
        return len(self.segments)


class TranscriptionBackend(ABC):
    """Abstract base class for all VAClip transcription backends.

    Subclasses must implement: transcribe()
    Use FasterWhisperBackend as the reference implementation.
    """

    @abstractmethod
    def transcribe(self, audio_path: str, run_id: str, language: Optional[str] = None) -> TranscriptResult:
        """Transcribe audio file and return a TranscriptResult.

        Implementations must:
        1. Load or reuse the ASR model
        2. Run transcription with word timestamps
        3. Return a complete TranscriptResult
        4. Log model name, compute type, and duration
        5. Handle CUDA errors gracefully

        Args:
            audio_path: Path to the extracted audio file.
            run_id: Run identifier for artifact grouping.
            language: Optional ISO 639-1 language code (auto-detect if None).

        Returns:
            TranscriptResult with all segments populated.
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this backend's dependencies are installed and usable."""
        ...
