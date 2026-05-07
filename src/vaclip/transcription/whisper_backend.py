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

import pathlib
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from vaclip.logging.setup import get_logger
from vaclip.transcription.base import BaseTranscriptionBackend
from vaclip.utils.exceptions import TranscriptionError

if TYPE_CHECKING:
    from vaclip.config.settings import Settings

log = get_logger(__name__)


class WhisperBackend(BaseTranscriptionBackend):
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
        print(len(transcript.words))  # word-level tokens
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
            TranscriptionError: If the model fails to load.
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
            # TODO: implement model loading
            # from faster_whisper import WhisperModel
            # self._model = WhisperModel(
            #     self._model_name,
            #     device=self.DEVICE,
            #     compute_type=self.COMPUTE_TYPE,
            #     download_root=self.MODELS_DIR,
            # )
            raise NotImplementedError("WhisperBackend._load_model() not yet implemented")
        except Exception as exc:
            log.error("transcription.model_load_failed", model=self._model_name, error=str(exc))
            raise TranscriptionError(f"Failed to load Whisper model: {exc}") from exc

    def transcribe(
        self,
        audio_path: pathlib.Path,
        asset_id: str,
        language: str | None = None,
    ) -> "Transcript":  # type: ignore[name-defined]  # noqa: F821
        """Transcribe an audio file to a word-level timestamped Transcript.

        Args:
            audio_path: Path to 16kHz mono WAV file.
            asset_id: Used to name the output JSON file.
            language: Language code (e.g., "en"). None = auto-detect.

        Returns:
            Transcript with word-level tokens and metadata.

        Raises:
            TranscriptionError: If transcription fails.
        """
        from vaclip.models.media import Transcript, WordToken  # avoid circular

        log.info(
            "transcription.start",
            asset_id=asset_id,
            audio_path=str(audio_path),
            backend=self.DEVICE,
            model=self._model_name,
        )

        self._load_model()

        try:
            # TODO: implement transcription
            # segments, info = self._model.transcribe(
            #     str(audio_path),
            #     language=language,
            #     word_timestamps=True,
            #     vad_filter=True,
            #     beam_size=5,
            # )
            #
            # words: list[WordToken] = []
            # raw_segments: list[dict] = []
            # for segment in segments:
            #     raw_segments.append(segment._asdict())
            #     if segment.words:
            #         for w in segment.words:
            #             words.append(WordToken(
            #                 word=w.word.strip(),
            #                 start=w.start,
            #                 end=w.end,
            #                 confidence=w.probability,
            #             ))
            #
            # transcript = Transcript(
            #     asset_id=asset_id,
            #     language=info.language,
            #     words=words,
            #     segments=raw_segments,
            #     model_name=self._model_name,
            #     backend=f"whisper_{self.DEVICE}",
            #     duration_seconds=info.duration,
            #     created_at=datetime.now(timezone.utc),
            # )
            # self._save_transcript(transcript)
            #
            # log.info("transcription.complete", asset_id=asset_id, word_count=len(words))
            # return transcript
            raise NotImplementedError("WhisperBackend.transcribe() not yet implemented")

        except TranscriptionError:
            raise
        except Exception as exc:
            log.error("transcription.failed", asset_id=asset_id, error=str(exc))
            raise TranscriptionError(f"Transcription failed: {exc}") from exc

    def _save_transcript(self, transcript: "Transcript") -> None:  # type: ignore[name-defined]
        """Serialize transcript to JSON in the cache directory.

        Args:
            transcript: The Transcript to serialize.
        """
        from vaclip.config.settings import get_settings
        settings = get_settings()
        dest = settings.paths.transcripts_dir / f"{transcript.asset_id}.json"
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
    settings: "Settings | None" = None,
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
