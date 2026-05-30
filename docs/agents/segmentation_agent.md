# Segmentation Agent Handoff

## Agent Role

You are the **Segmentation Agent**. Your sole responsibility is implementing the
segmentation layer of VAClip: detecting shots and generating candidate clip
segments from transcribed audio.

## Tasks to Implement

- VACLIP-005: `BaseScorer` interface and `ScoredSegment` model
- VACLIP-006: Shot boundary detection using TransNetV2 (optional)
- VACLIP-007: Sliding window segment generation from transcript
- VACLIP-008: `HighlightMerger` for combining multi-scorer results
- VACLIP-009: `ContentProfileManager` for profile-based scoring weights

## Files You Own

```
src/vaclip/segmentation/
    __init__.py          - export public symbols
    base.py              - BaseSegmenter, ShotDetector (already scaffolded)
    shot_detector.py     - TODO: TransNetV2 implementation
    window_generator.py  - TODO: sliding window from transcript
    merger.py            - TODO: HighlightMerger implementation
    profile_manager.py   - TODO: ContentProfileManager
src/vaclip/models/media.py  - ScoredSegment, ClipCandidate models (already scaffolded)
```

## Files You Must NOT Modify

- `src/vaclip/ingest/` - not your layer
- `src/vaclip/transcription/` - not your layer
- `src/vaclip/scoring/` - not your layer (but you'll work closely with it)
- `src/vaclip/export/` - not your layer
- `src/vaclip/models/base.py` - shared contracts, discuss before changing

## Contracts

### Input

```python
# From transcription stage
transcript: Transcript  # Word-level transcript with timestamps
media: MediaAsset       # For duration, audio path if needed
profile: str            # Content profile name (podcast, gaming, etc.)
```

### Output: ScoredSegment List

```python
class ScoredSegment(BaseModel):
    start: float          # Start time in seconds
    end: float            # End time in seconds
    text: str             # Segment transcript text
    score: float          # Raw score from individual scorer (0-1)
    scorer: str           # Which scorer produced this (transcript, audio, etc.)
    metadata: dict[str, Any] = {}  # Scorer-specific metadata
```

### Output: ClipCandidate List (after merging)

```python
class ClipCandidate(BaseModel):
    start: float              # Start time in seconds
    end: float                # End time in seconds
    score: float              # Final merged score (0-1)
    profile: str              # Content profile used
    sources: list[str]        # List of scorer names that contributed
    text: str                 # Concatenated transcript text
```

Save as JSON: `cache/<run_id>/scores_<profile>.json`

## Implementation Guide

### BaseScorer Interface

```python
from abc import ABC, abstractmethod
from vaclip.models.media import ScoredSegment, Transcript
from vaclip.utils.exceptions import ScoringError

class BaseScorer(ABC):
    """Abstract base class for all signal scorers."""
    
    def __init__(self, weight: float = 1.0):
        self.weight = weight
    
    @abstractmethod
    def score(self, transcript: Transcript, media: MediaAsset) -> list[ScoredSegment]:
        """Score transcript and return list of ScoredSegments."""
        ...
    
    def validate_segments(self, segments: list[ScoredSegment]) -> list[ScoredSegment]:
        """Filter and validate segments (duration, bounds, etc.)."""
        # Default implementation: filter by duration, clip to media bounds
        ...
```

### Sliding Window Generator

```python
class WindowGenerator:
    """Generate overlapping windows from transcript for scoring."""
    
    def __init__(self, window_size: float = 10.0, step_size: float = 5.0):
        self.window_size = window_size
        self.step_size = step_size
    
    def generate_windows(self, transcript: Transcript) -> list[dict]:
        """Generate windows with start/end times and contained words."""
        windows = []
        current_time = 0.0
        
        while current_time < transcript.duration:
            window_end = min(current_time + self.window_size, transcript.duration)
            # Get words within window
            window_words = [
                w for w in transcript.words 
                if current_time <= w.start < window_end
            ]
            
            if window_words:
                windows.append({
                    'start': current_time,
                    'end': window_end,
                    'words': window_words,
                    'text': ' '.join(w.text for w in window_words)
                })
            
            current_time += self.step_size
            
        return windows
```

### HighlightMerger

```python
class HighlightMerger:
    """Merge scored segments from multiple scorers using profile weights."""
    
    def __init__(self, profile_manager: ContentProfileManager):
        self.profile_manager = profile_manager
    
    def merge(
        self, 
        scored_segments: dict[str, list[ScoredSegment]], 
        profile_name: str
    ) -> list[ClipCandidate]:
        """Merge segments from multiple scorers.
        
        Args:
            scored_segments: Dict of scorer_name -> list of ScoredSegments
            profile_name: Content profile to use for weights
            
        Returns:
            List of ClipCandidate objects, sorted by score descending
        """
        # 1. Apply profile weights to each scorer's segments
        weighted_segments = self._apply_weights(scored_segments, profile_name)
        
        # 2. Group segments by time proximity and merge overlapping
        grouped = self._group_by_time(weighted_segments)
        
        # 3. Create ClipCandidates from merged groups
        candidates = self._create_candidates(grouped, profile_name)
        
        # 4. Apply duration limits and trim if necessary
        candidates = self._apply_duration_limits(candidates, profile_name)
        
        # 5. Sort by score descending
        return sorted(candidates, key=lambda x: x.score, reverse=True)
```

### ContentProfileManager

```python
class ContentProfileManager:
    """Manage scoring profiles and their weights."""
    
    def __init__(self):
        self.profiles: dict[str, ContentProfile] = {}
        self._load_default_profiles()
    
    def get_profile(self, name: str) -> ContentProfile:
        """Get profile by name, fallback to generic."""
        return self.profiles.get(name, self.profiles["generic"])
    
    def get_scorer_weights(self, profile_name: str) -> dict[str, float]:
        """Get weight for each scorer type in the profile."""
        profile = self.get_profile(profile_name)
        return {
            "transcript": profile.transcript_weight,
            "audio": profile.audio_weight,
            "visual": profile.visual_weight,
            "embedding": profile.embedding_weight
        }
```

## Key Dependencies

```toml
sentence-transformers = ">=3.0.0"
torch = ">=2.0.0"
opencv-python = ">=4.0.0"  # For TransNetV2 if used
```

## Testing Requirements

- Unit tests: Mock transcript/media objects, test edge cases
- Integration tests: Use real small transcript fixtures
- Test coverage: 70% target for segmentation module
- Property-based testing: Test merging logic with overlapping segments

## Logging

```python
from vaclip.logging.setup import get_logger
log = get_logger(__name__)

log.info("segmentation.start", num_windows=len(windows))
log.info("segmentation.scoring_complete", 
         scorer="transcript", 
         num_segments=len(segments))
log.debug("segmentation.merging", 
          num_scorers=len(scored_segments),
          total_segments=sum(len(segs) for segs in scored_segments.values()))
```

## Error Handling

```python
from vaclip.utils.exceptions import SegmentationError, ScoringError

# Raise SegmentationError for window generation failures
# Raise ScoringError for individual scorer failures
# Always log before raising
# Never swallow exceptions silently
```

## Definition of Done

- [ ] `WindowGenerator.generate_windows()` creates proper overlapping windows
- [ ] At least one scorer implementation (transcript-based) works end-to-end
- [ ] `HighlightMerger.merge()` correctly applies weights and deduplicates
- [ ] `ContentProfileManager` loads and returns correct weights for profiles
- [ ] Unit tests pass with mocks
- [ ] Integration test marked and skipped in CI by default
- [ ] `ruff check src/vaclip/segmentation/` passes with 0 errors
- [ ] `mypy src/vaclip/segmentation/` passes in strict mode