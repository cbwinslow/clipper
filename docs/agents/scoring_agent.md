# Scoring Agent Handoff

## Agent Role

You are the **Scoring Agent**. Your responsibility is implementing the
scoring layer: analyzing transcript, audio, and visual signals to identify
the most highlight-worthy segments of a video.

## Tasks to Implement

- VACLIP-008: `TranscriptScorer` - text-based signal analysis
- VACLIP-009: `AudioEnergyScorer` - audio amplitude/energy analysis
- VACLIP-010: `VisualMotionScorer` - frame motion and scene change analysis
- VACLIP-011: `CompositeScorer` - weighted combination of all scorers
- VACLIP-012: Profile-based scoring presets

## Files You Own

```
src/vaclip/scoring/
    __init__.py              - export public symbols
    base.py                  - BaseScorer (already scaffolded)
    transcript_scorer.py     - TODO: implement
    audio_energy_scorer.py   - TODO: implement
    visual_motion_scorer.py  - TODO: implement
    composite_scorer.py      - TODO: implement
    profiles.py              - TODO: preset configs per content type
src/vaclip/models/media.py   - ScoredSegment, Segment models (add here)
```

## Contracts

### Input

```python
class Segment(VaClipBaseModel):
    start: float  # seconds
    end: float    # seconds
    words: list[WordToken]  # from Transcript
    text: str     # joined word text
```

### Output: ScoredSegment

```python
class ScoredSegment(VaClipBaseModel):
    segment: Segment
    transcript_score: float    # 0.0-1.0
    audio_score: float         # 0.0-1.0
    visual_score: float        # 0.0-1.0
    composite_score: float     # weighted average
    rank: int                  # 1 = highest
    highlight_type: str        # "funny", "insightful", "hype", "action", etc.
    profile: str               # which scoring profile was used
```

Save as JSON: `cache/scores/<asset_id>.json`

## Implementation Guide

### TranscriptScorer

```python
class TranscriptScorer(BaseScorer):
    """Score segments based on transcript content signals."""

    # Keyword lists for different highlight types
    FUNNY_WORDS = {"laugh", "funny", "hilarious", "joke", "lol", "haha", ...}
    INSIGHTFUL_WORDS = {"important", "key", "critical", "basically", "essentially", ...}
    HYPE_WORDS = {"incredible", "amazing", "unbelievable", "crazy", "insane", ...}

    def score(self, segment: Segment, audio_path: pathlib.Path) -> float:
        """Score based on keyword density, sentiment, and reaction words."""
        # 1. Count keyword hits from FUNNY/INSIGHTFUL/HYPE word sets
        # 2. Run sentiment analysis (e.g., VADER, TextBlob - free)
        # 3. Measure words-per-second (pacing)
        # 4. Detect laughter, applause, reactions in text
        # 5. Normalize to 0.0-1.0
        ...
```

### AudioEnergyScorer

```python
class AudioEnergyScorer(BaseScorer):
    """Score segments based on audio energy and dynamics."""

    def score(self, segment: Segment, audio_path: pathlib.Path) -> float:
        """Score based on RMS energy, silence ratio, and volume spikes."""
        # 1. Load audio slice for segment using librosa
        # 2. Compute RMS energy per frame
        # 3. Detect silence ratio (low-energy frames)
        # 4. Detect sudden volume spikes
        # 5. Normalize to 0.0-1.0
        ...
```

### VisualMotionScorer

```python
class VisualMotionScorer(BaseScorer):
    """Score segments based on visual activity in video frames."""

    def score(self, segment: Segment, video_path: pathlib.Path) -> float:
        """Score based on optical flow and scene change detection."""
        # 1. Sample frames at 2fps for the segment duration
        # 2. Compute dense optical flow between consecutive frames (cv2.calcOpticalFlowFarneback)
        # 3. Detect scene cuts (histogram difference)
        # 4. Normalize to 0.0-1.0
        ...
```

### CompositeScorer

```python
class CompositeScorer:
    """Combines multiple scorers with configurable weights per profile."""

    def __init__(self, profile: ScoringProfile) -> None:
        self.profile = profile
        self.transcript_scorer = TranscriptScorer()
        self.audio_scorer = AudioEnergyScorer()
        self.visual_scorer = VisualMotionScorer()

    def score_all(
        self,
        segments: list[Segment],
        transcript: Transcript,
        media: MediaAsset,
    ) -> list[ScoredSegment]:
        """Score all segments and return ranked ScoredSegment list."""
        ...
```

### Profiles

```python
@dataclass
class ScoringProfile:
    name: str
    transcript_weight: float = 0.5
    audio_weight: float = 0.3
    visual_weight: float = 0.2
    min_duration: float = 5.0   # seconds
    max_duration: float = 60.0  # seconds
    top_n: int = 10

PROFILES = {
    "podcast": ScoringProfile("podcast", transcript_weight=0.7, audio_weight=0.2, visual_weight=0.1),
    "gaming": ScoringProfile("gaming", transcript_weight=0.2, audio_weight=0.4, visual_weight=0.4),
    "sports": ScoringProfile("sports", transcript_weight=0.1, audio_weight=0.3, visual_weight=0.6),
    "interview": ScoringProfile("interview", transcript_weight=0.6, audio_weight=0.3, visual_weight=0.1),
    "generic": ScoringProfile("generic"),
}
```

## Key Dependencies

```toml
librosa = ">=0.10.0"    # audio analysis
opencv-python = ">=4.8" # visual motion
vaderSentiment = ">=3.3" # free sentiment analysis
numpy = ">=1.24"
```

## Testing Requirements

- Unit tests: use synthetic segment and audio data (numpy arrays)
- Mock `librosa.load()` and `cv2.VideoCapture()`
- Test each scorer independently
- Test `CompositeScorer` with all three scorers mocked
- 70% coverage target

## Definition of Done

- [ ] All three scorers produce 0.0-1.0 normalized scores
- [ ] `CompositeScorer` ranks segments correctly by weighted sum
- [ ] Profile presets produce different rankings on the same input
- [ ] `ScoredSegment` list serialized to `cache/scores/<asset_id>.json`
- [ ] Unit tests pass for all scorers
- [ ] `ruff check src/vaclip/scoring/` passes with 0 errors
