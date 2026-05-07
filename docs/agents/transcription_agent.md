# Transcription Agent Handoff

## Agent Role

You are the **Transcription Agent**. Your responsibility is implementing the
transcription layer of VAClip: converting audio tracks into accurate,
word-level timestamped transcripts using GPU-accelerated Whisper models.

## Tasks to Implement

- VACLIP-005: `WhisperBackend` with faster-whisper + CUDA
- VACLIP-006: `WhisperCPUBackend` as automatic CPU fallback
- VACLIP-007: Speaker diarization / VAD segmentation

## Files You Own

```
src/vaclip/transcription/
    __init__.py           - export public symbols
    base.py               - BaseTranscriptionBackend (already scaffolded)
    whisper_backend.py    - TODO: GPU Whisper implementation
    whisper_cpu_backend.py - TODO: CPU fallback
    diarization.py        - TODO: speaker turn segmentation
src/vaclip/models/media.py  - Transcript, WordToken models (add here)
```

## Files You Must NOT Modify

- `src/vaclip/ingest/` - upstream layer
- `src/vaclip/scoring/` - downstream layer
- `src/vaclip/models/base.py` - shared contracts

## Contracts

### Input

```python
audio_path: pathlib.Path  # WAV file, 16kHz mono (from MediaAsset.audio_path)
asset_id: str             # for naming output files
```

### Output: Transcript

```python
class WordToken(VaClipBaseModel):
    word: str
    start: float   # seconds
    end: float     # seconds
    confidence: float  # 0.0-1.0

class Transcript(IdentifiedModel):
    asset_id: str
    language: str          # detected language code, e.g. "en"
    words: list[WordToken]
    segments: list[dict]   # raw Whisper segments
    model_name: str        # e.g. "large-v3"
    backend: str           # "whisper_cuda" or "whisper_cpu"
    duration_seconds: float
    created_at: datetime
```

Save as JSON: `cache/transcripts/<asset_id>.json`

## Implementation Guide

### WhisperBackend (CUDA)

```python
from faster_whisper import WhisperModel
from vaclip.transcription.base import BaseTranscriptionBackend
from vaclip.models.media import Transcript, WordToken

class WhisperBackend(BaseTranscriptionBackend):
    """GPU-accelerated Whisper transcription using faster-whisper + CUDA."""

    MODEL_NAME: str = "large-v3"  # best accuracy for RTX 3060
    DEVICE: str = "cuda"
    COMPUTE_TYPE: str = "float16"  # optimal for RTX 3060

    def __init__(self, model_name: str = MODEL_NAME) -> None:
        """Load the Whisper model. Downloads on first use to models/ dir."""
        # self._model = WhisperModel(model_name, device=self.DEVICE,
        #     compute_type=self.COMPUTE_TYPE, download_root="models/")
        ...

    def transcribe(self, audio_path: pathlib.Path, asset_id: str) -> Transcript:
        """Transcribe audio and return word-level timestamped Transcript."""
        # 1. Call self._model.transcribe(str(audio_path), word_timestamps=True)
        # 2. Iterate segments and words to build WordToken list
        # 3. Construct Transcript object
        # 4. Save to cache/transcripts/<asset_id>.json
        # 5. Return Transcript
        ...
```

### WhisperCPUBackend

```python
class WhisperCPUBackend(WhisperBackend):
    """CPU fallback when CUDA is unavailable."""

    DEVICE: str = "cpu"
    COMPUTE_TYPE: str = "int8"  # best CPU performance
    MODEL_NAME: str = "base"    # smaller model for CPU speed
```

### Auto-selection

```python
def get_transcription_backend(settings: Settings) -> BaseTranscriptionBackend:
    """Return the best available backend based on hardware."""
    import torch
    if torch.cuda.is_available():
        log.info("transcription.backend", backend="cuda")
        return WhisperBackend(model_name=settings.transcription.model_name)
    log.warning("transcription.cuda_unavailable", fallback="cpu")
    return WhisperCPUBackend()
```

## Model Selection Guide

| Model | VRAM | Speed | Accuracy | Recommended For |
|-------|------|-------|----------|-----------------|
| tiny | <1GB | Very fast | Low | Testing only |
| base | 1GB | Fast | OK | CPU fallback |
| small | 2GB | Medium | Good | Light GPU |
| medium | 5GB | Slower | Very good | RTX 3060 |
| large-v3 | 10GB | Slow | Best | RTX 3060 (default) |

RTX 3060 has 12GB VRAM, so `large-v3` is the default target.

## Key Dependencies

```toml
faster-whisper = ">=1.0.0"
torch = ">=2.0.0"   # with CUDA 11.8 or 12.x
```

Install PyTorch with CUDA support:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

## Testing Requirements

- Unit tests: mock `WhisperModel`, provide a tiny WAV fixture
- Integration tests: marked `@pytest.mark.integration` + `@pytest.mark.gpu`
- Fixture: `tests/fixtures/sample_audio.wav` (5 seconds, 16kHz mono)
- 70% coverage target for this module

## Logging

```python
log.info("transcription.start", asset_id=asset_id, backend=self.DEVICE)
log.info("transcription.complete", asset_id=asset_id,
         word_count=len(transcript.words), duration=transcript.duration_seconds)
log.warning("transcription.low_confidence", asset_id=asset_id, min_conf=min_confidence)
log.error("transcription.failed", asset_id=asset_id, error=str(e))
```

## Error Handling

```python
from vaclip.utils.exceptions import TranscriptionError

# Raise TranscriptionError for model load failures or transcription errors
# Log CUDA OOM separately with fallback suggestion
# Never swallow exceptions silently
```

## Definition of Done

- [ ] `WhisperBackend.transcribe()` produces word-level timestamps on CUDA
- [ ] `WhisperCPUBackend` works on CPU-only machines
- [ ] Auto-selection detects GPU availability correctly
- [ ] `Transcript` JSON serialized to `cache/transcripts/<asset_id>.json`
- [ ] Unit tests pass with mocked model
- [ ] `ruff check src/vaclip/transcription/` passes with 0 errors
- [ ] `mypy src/vaclip/transcription/` passes in strict mode
