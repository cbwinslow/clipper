# Ingest Agent Handoff

## Agent Role

You are the **Ingest Agent**. Your sole responsibility is implementing the
ingest layer of VAClip: acquiring media from external sources and local files,
normalizing it into a `MediaAsset`, and persisting it for downstream stages.

## Tasks to Implement

- VACLIP-001: `YtDlpAdapter` - download via yt-dlp
- VACLIP-002: `LocalFileAdapter` - copy/validate local files
- VACLIP-003: Audio extraction using FFmpeg
- VACLIP-004: `MediaAsset` serialization and caching

## Files You Own

```
src/vaclip/ingest/
    __init__.py          - export public symbols
    base.py              - BaseIngestAdapter (already scaffolded)
    ytdlp_adapter.py     - TODO: implement
    local_adapter.py     - TODO: implement
    registry.py          - TODO: adapter registry by URL pattern
src/vaclip/models/media.py  - MediaAsset model (already scaffolded)
```

## Files You Must NOT Modify

- `src/vaclip/transcription/` - not your layer
- `src/vaclip/scoring/` - not your layer
- `src/vaclip/export/` - not your layer
- `src/vaclip/models/base.py` - shared contracts, discuss before changing

## Contracts

### Input

```python
# URL download
source: str  # e.g., "https://youtube.com/watch?v=..."

# Local file
path: pathlib.Path  # e.g., Path("input/myvideo.mp4")
```

### Output: MediaAsset

```python
class MediaAsset(IdentifiedModel):
    source_url: str | None
    local_path: pathlib.Path
    title: str
    duration_seconds: float
    width: int
    height: int
    fps: float
    codec: str
    audio_path: pathlib.Path | None  # extracted audio WAV
    format: str  # "mp4", "mkv", "mp3", etc.
    profile: str  # "podcast", "gaming", "sports", "generic"
    created_at: datetime
```

Save as JSON: `cache/<asset_id>/media_asset.json`

## Implementation Guide

### YtDlpAdapter

```python
import yt_dlp
from vaclip.ingest.base import BaseIngestAdapter
from vaclip.models.media import MediaAsset

class YtDlpAdapter(BaseIngestAdapter):
    """Downloads media from YouTube, Rumble, Kick, Twitch, and 1000+ other sites."""

    def ingest(self, source: str, profile: str = "generic") -> MediaAsset:
        """Download source URL and return a MediaAsset."""
        # 1. Configure yt_dlp options (output template, format, write-info-json)
        # 2. Call yt_dlp.YoutubeDL(opts).download([source])
        # 3. Parse yt-dlp info JSON to extract metadata
        # 4. Call self._extract_audio(video_path) -> audio_path
        # 5. Construct and return MediaAsset
        ...

    def _extract_audio(self, video_path: pathlib.Path) -> pathlib.Path:
        """Extract audio track to WAV using FFmpeg subprocess."""
        # ffmpeg -i video_path -vn -acodec pcm_s16le -ar 16000 -ac 1 audio.wav
        ...
```

### LocalFileAdapter

```python
class LocalFileAdapter(BaseIngestAdapter):
    """Ingests a local video or audio file."""

    SUPPORTED_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".mp3", ".wav", ".m4a"}

    def ingest(self, source: str, profile: str = "generic") -> MediaAsset:
        """Validate and copy local file, extract audio, return MediaAsset."""
        # 1. Validate path exists and extension is supported
        # 2. Copy to input/<asset_id>/ if not already there
        # 3. Use ffprobe to extract metadata (duration, width, height, fps, codec)
        # 4. Extract audio
        # 5. Construct and return MediaAsset
        ...
```

## Key Dependencies

```toml
yt-dlp = ">=2024.1.1"
ffmpeg-python = ">=0.2.0"  # or use subprocess directly
```

FFmpeg binary must be installed on the system and available in PATH.

## Testing Requirements

- Unit tests: mock `yt_dlp.YoutubeDL`, mock `subprocess.run` for FFmpeg
- Integration tests: marked `@pytest.mark.integration`, use real small test file
- Test file location: `tests/fixtures/sample_short.mp4` (10 second clip)
- 70% coverage target for this module

## Logging

```python
from vaclip.logging.setup import get_logger
log = get_logger(__name__)

log.info("ingest.start", source=source, adapter=self.__class__.__name__)
log.info("ingest.download_complete", asset_id=asset.id, duration=asset.duration_seconds)
log.error("ingest.failed", source=source, error=str(e))
```

## Error Handling

```python
from vaclip.utils.exceptions import IngestError, UnsupportedSourceError

# Raise IngestError for download failures
# Raise UnsupportedSourceError for unrecognized URL patterns or file types
# Always log before raising
# Never swallow exceptions silently
```

## Definition of Done

- [ ] `YtDlpAdapter.ingest()` downloads a YouTube URL end-to-end
- [ ] `LocalFileAdapter.ingest()` processes a local MP4 file
- [ ] `MediaAsset` JSON serialized to `cache/<id>/media_asset.json`
- [ ] Audio WAV extracted and path stored in `MediaAsset.audio_path`
- [ ] Unit tests pass with mocks
- [ ] Integration test marked and skipped in CI by default
- [ ] `ruff check src/vaclip/ingest/` passes with 0 errors
- [ ] `mypy src/vaclip/ingest/` passes in strict mode
