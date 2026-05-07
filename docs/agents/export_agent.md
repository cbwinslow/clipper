# Export Agent Handoff

## Agent Role

You are the **Export Agent**. Your responsibility is implementing the
export layer of VAClip: rendering final video clips from scored segments
using FFmpeg, with support for multiple aspect ratio framing strategies.

## Tasks to Implement

- VACLIP-013: `ClipExporter` using FFmpeg subprocess
- VACLIP-014: `WideFramingStrategy` (16:9 landscape)
- VACLIP-015: `VerticalFramingStrategy` (9:16 portrait for Shorts/TikTok)
- VACLIP-016: `SquareFramingStrategy` (1:1 for Instagram)

## Files You Own

```
src/vaclip/export/
    __init__.py               - export public symbols
    clip_exporter.py          - TODO: main exporter
    framing/
        __init__.py           - export framing strategies
        base.py               - FramingStrategy (abstract)
        wide.py               - TODO: 16:9 strategy
        vertical.py           - TODO: 9:16 strategy
        square.py             - TODO: 1:1 strategy
src/vaclip/models/media.py    - ExportedClip model (add here)
```

## Contracts

### Input

```python
segments: list[ScoredSegment]  # from scoring layer
media: MediaAsset              # original video path
profile: str                   # "podcast", "gaming", etc.
framing: str                   # "wide", "vertical", "square"
output_dir: pathlib.Path       # where to write clips
```

### Output: ExportedClip

```python
class ExportedClip(IdentifiedModel):
    asset_id: str
    segment_rank: int
    start: float              # seconds
    end: float                # seconds
    duration: float           # seconds
    output_path: pathlib.Path
    framing: str              # "wide", "vertical", "square"
    profile: str
    width: int
    height: int
    file_size_bytes: int
    created_at: datetime
```

Output file naming: `output/<asset_id>/<rank>_<profile>_<framing>.mp4`

## Implementation Guide

### ClipExporter

```python
class ClipExporter:
    """Exports video clips using FFmpeg. Preserves all source artifacts."""

    def export(
        self,
        media: MediaAsset,
        segments: list[ScoredSegment],
        framing: str = "wide",
        output_dir: pathlib.Path = pathlib.Path("output"),
        max_clips: int = 10,
    ) -> list[ExportedClip]:
        """Export top N segments as clips with the given framing strategy."""
        strategy = self._get_strategy(framing)
        clips = []
        for rank, seg in enumerate(segments[:max_clips], start=1):
            clip = self._export_one(media, seg, strategy, rank, output_dir)
            clips.append(clip)
        return clips

    def _export_one(
        self,
        media: MediaAsset,
        seg: ScoredSegment,
        strategy: FramingStrategy,
        rank: int,
        output_dir: pathlib.Path,
    ) -> ExportedClip:
        """Run FFmpeg to cut and frame one clip."""
        # Build FFmpeg command using strategy.build_filter(media)
        # ffmpeg -ss start -to end -i input -vf filter -c:v libx264 -c:a aac output
        ...

    def _get_strategy(self, framing: str) -> FramingStrategy:
        strategies = {"wide": WideFramingStrategy, "vertical": VerticalFramingStrategy,
                      "square": SquareFramingStrategy}
        cls = strategies.get(framing)
        if cls is None:
            raise ExportError(f"Unknown framing: {framing}")
        return cls()
```

### FramingStrategy (base)

```python
class FramingStrategy(ABC):
    """Abstract base for video framing/cropping strategies."""

    @property
    @abstractmethod
    def width(self) -> int: ...

    @property
    @abstractmethod
    def height(self) -> int: ...

    @abstractmethod
    def build_filter(self, media: MediaAsset) -> str:
        """Return FFmpeg -vf filter string for this framing."""
        ...
```

### WideFramingStrategy (16:9)

```python
class WideFramingStrategy(FramingStrategy):
    """16:9 landscape - suitable for YouTube full video or standard clips."""
    width = 1920
    height = 1080

    def build_filter(self, media: MediaAsset) -> str:
        # Scale to 1920x1080, pad if needed
        return "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:-1:-1"
```

### VerticalFramingStrategy (9:16)

```python
class VerticalFramingStrategy(FramingStrategy):
    """9:16 portrait - suitable for YouTube Shorts, TikTok, Instagram Reels."""
    width = 1080
    height = 1920

    def build_filter(self, media: MediaAsset) -> str:
        # Crop center column from landscape video
        # crop=ih*9/16:ih:(iw-ih*9/16)/2:0, scale=1080:1920
        return "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920"
```

### SquareFramingStrategy (1:1)

```python
class SquareFramingStrategy(FramingStrategy):
    """1:1 square - suitable for Instagram feed posts."""
    width = 1080
    height = 1080

    def build_filter(self, media: MediaAsset) -> str:
        return "crop=ih:ih:(iw-ih)/2:0,scale=1080:1080"
```

## FFmpeg Command Template

```bash
ffmpeg \
  -ss {start} \
  -to {end} \
  -i "{input_path}" \
  -vf "{filter_string}" \
  -c:v libx264 -preset slow -crf 18 \
  -c:a aac -b:a 192k \
  -movflags +faststart \
  -y \
  "{output_path}"
```

Use `-preset slow -crf 18` for quality-first encoding (aligns with user preference).

## Key Dependencies

FFmpeg must be installed on the system. No Python library needed - use `subprocess.run`.

```python
import subprocess
result = subprocess.run(cmd, capture_output=True, text=True, check=False)
if result.returncode != 0:
    raise ExportError(f"FFmpeg failed: {result.stderr}")
```

## Testing Requirements

- Unit tests: mock `subprocess.run` to verify FFmpeg command construction
- Test each framing strategy's `build_filter()` output
- Integration tests: use a real 10-second sample video
- Never delete test outputs - store in `tests/fixtures/output/`

## Definition of Done

- [ ] `ClipExporter.export()` produces MP4 files for top N segments
- [ ] All three framing strategies produce correct aspect ratios
- [ ] Output files named `<rank>_<profile>_<framing>.mp4`
- [ ] `ExportedClip` JSON saved to `output/<asset_id>/clips.json`
- [ ] Unit tests pass with mocked subprocess
- [ ] Source video is never modified or deleted
- [ ] `ruff check src/vaclip/export/` passes with 0 errors
