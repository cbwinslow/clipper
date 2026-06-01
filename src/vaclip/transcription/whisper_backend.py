"""Whisper-based transcription backends for VAClip.

Provides GPU-accelerated (CUDA) and CPU fallback transcription backends
using the faster-whisper library. Produces word-level timestamped transcripts.

Agent Instructions:
    - Implement the TODO sections in WhisperBackend.transcribe()
    - Use faster_whisper.WhisperModel for inference
    - Build WordToken list from segment.words
    - Construct and save Transcript to cache/transcripts/<asset_id>.json
    - WhisperCPUBackend inherits from WhisperBackend, just overrides class vars
    - get_transcription_backend() auto-selects based on torch.cuda.is_available()
    - See docs/agents/transcription_agent.md for full implementation guide
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from vaclip.logging.setup import get_logger
from vaclip.utils.exceptions import VaClipTranscriptionError

if TYPE_CHECKING:

    from vaclip.config.settings import Settings
    from vaclip.models.schemas import Transcript

log = get_logger(__name__)


class WhisperBackend:
    """GPU-accelerated transcription backend using faster-whisper + CUDA.

    Targets RTX 3060 (12GB VRAM) with large-v3 model and float16 precision.
    Downloads model weights on first use to the configured models directory.

    Attributes:
        MODEL_NAME: Default Whisper model size.
        DEVICE: Compute device ("cuda" or "cpu").
        COMPUTE_TYPE: Quantization type for efficiency.

    Example::

        backend = WhisperBackend()
        transcript = backend.transcribe(Path("cache/audio/abc123.wav"), "abc123")
        print(len(transcript.segments))  # segment-level tokens
    """

    MODEL_NAME: str = "large-v3"
    DEVICE: str = "cuda"
    COMPUTE_TYPE: str = "float16"   # optimal for RTX 3060
    MODELS_DIR: str = "models"

    def __init__(self, model_name: str | None = None) -> None:
        """Load the Whisper model. Downloads to models/ on first use.

        Args:
            model_name: Override the default model size.
                        Options: "tiny", "base", "small", "medium", "large-v3"
        """
        self._model_name = model_name or self.MODEL_NAME
        self._model = None  # lazy-loaded on first transcribe call

    def _load_model(self) -> None:
        """Lazy-load the Whisper model to avoid startup delay.

        Raises:
            VaClipTranscriptionError: If the model fails to load.
        """
        if self._model is not None:
            return
        log.info(
            "transcription.model_loading",
            model=self._model_name,
            device=self.DEVICE,
            compute_type=self.COMPUTE_TYPE,
        )
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self._model_name,
                device=self.DEVICE,
                compute_type=self.COMPUTE_TYPE,
                download_root=self.MODELS_DIR,
            )
        except Exception as exc:
            log.error("transcription.model_load_failed", model=self._model_name, error=str(exc))
            raise VaClipTranscriptionError(f"Failed to load Whisper model: {exc}") from exc

    def transcribe(self, audio_path: str, run_id: str, language: str | None = None) -> Transcript:
        """Transcribe audio file and return a Transcript.

        Implementations must:
        1. Load or reuse the ASR model
        2. Run transcription with word timestamps
        3. Return a complete Transcript (Pydantic model)
        4. Log model name, compute type, and duration
        5. Handle CUDA errors gracefully

        Args:
            audio_path: Path to the extracted audio file.
            run_id: Run identifier for artifact grouping.
            language: Optional ISO 639-1 language code (auto-detect if None).

        Returns:
            Transcript with all segments populated.
        """
        from vaclip.config.settings import get_settings
        from vaclip.models.schemas import Segment, Transcript, Word

        log.info(
            "transcription.start",
            run_id=run_id,
            audio_path=audio_path,
            backend=self.DEVICE,
            model=self._model_name,
        )

        self._load_model()
        assert self._model is not None, "Model should be loaded by _load_model"

        try:
            # Import faster_whisper here to avoid slow startup if not used

            segments, info = self._model.transcribe(
                audio_path,
                language=language,
                word_timestamps=True,
                vad_filter=True,
                beam_size=5,
            )

            # Convert faster_whisper output to our Pydantic Transcript model
            transcript_segments: list[Segment] = []
            for segment in segments:
                # Convert words if present
                words: list[Word] = []
                if segment.words:
                    for w in segment.words:
                        word = Word(
                            text=w.word.strip(),
                            start=w.start,
                            end=w.end,
                            confidence=w.probability,
                        )
                        words.append(word)

                trans_segment = Segment(
                    id=segment.id,
                    text=segment.text,
                    start=segment.start,
                    end=segment.end,
                    words=words,
                )
                transcript_segments.append(trans_segment)

            # Build Transcript (Pydantic model)
            transcript = Transcript(
                segments=transcript_segments,
                language=info.language,
                model_name=self._model_name,
                duration_sec=info.duration,
            )

            # Save transcript to cache
            settings = get_settings()
            self._save_transcript(transcript, settings, run_id)

            log.info(
                "transcription.complete",
                run_id=run_id,
                word_count=sum(len(s.words) for s in transcript_segments),
                segment_count=len(transcript_segments),
            )
            return transcript

        except VaClipTranscriptionError:
            raise
        except Exception as exc:
            log.error("transcription.failed", run_id=run_id, error=str(exc))
            raise VaClipTranscriptionError(f"Transcription failed: {exc}") from exc

    def _save_transcript(self, transcript: Transcript, settings: Settings, run_id: str) -> None:
        """Serialize transcript to JSON in the cache directory.

        Args:
            transcript: The Transcript to serialize.
            settings: Settings object with paths configuration.
            run_id: Run identifier for the transcript filename.
        """
        dest = settings.paths.transcripts_dir / f"{run_id}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(transcript.model_dump_json(indent=2))
        log.info("transcription.saved", path=str(dest))


class WhisperCPUBackend(WhisperBackend):
    """CPU fallback transcription backend for systems without a CUDA GPU.

    Uses a smaller model and int8 quantization for reasonable CPU performance.
    Automatically selected by get_transcription_backend() when CUDA is unavailable.
    """

    MODEL_NAME: str = "base"     # smaller model for CPU speed
    DEVICE: str = "cpu"
    COMPUTE_TYPE: str = "int8"   # best CPU performance


def get_transcription_backend(
    settings: Settings | None = None,
) -> WhisperBackend:
    """Return the best available transcription backend for the current hardware.

    Auto-detects CUDA availability and returns WhisperBackend (GPU) or
    WhisperCPUBackend (CPU) accordingly.

    Args:
        settings: Optional settings object. Loads from config if None.

    Returns:
        An initialized transcription backend ready for use.
    """
    if settings is None:
        from vaclip.config.settings import get_settings
        settings = get_settings()

    try:
        import torch
        cuda_available = torch.cuda.is_available()
    except ImportError:
        cuda_available = False

    if cuda_available:
        log.info("transcription.backend_selected", backend="cuda", model=settings.transcription.model_name)
        return WhisperBackend(model_name=settings.transcription.model_name)

    log.warning(
        "transcription.cuda_unavailable",
        fallback="cpu",
        note="Install PyTorch with CUDA support for better performance",
    )
    return WhisperCPUBackend()
