"""Faster-Whisper ASR backend for VAClip."""
from __future__ import annotations

import json
import pathlib
from datetime import datetime, timezone
from typing import Any

from vaclip.logging.setup import get_logger
from vaclip.utils.exceptions import VaClipTranscriptionError

log = get_logger(__name__)


class WhisperBackend:
    """Transcription backend powered by faster-whisper."""

    def __init__(
        self,
        model_name: str = "large-v3",
        device: str = "auto",
        compute_type: str = "float16",
        models_dir: pathlib.Path | None = None,
        transcripts_dir: pathlib.Path | None = None,
        beam_size: int = 5,
        vad_filter: bool = True,
    ) -> None:
        self._model_name = model_name
        self._device = device if device != "auto" else self._detect_device()
        self._compute_type = self._resolve_compute_type(compute_type, self._device)
        self._models_dir = models_dir or pathlib.Path("models")
        self._transcripts_dir = transcripts_dir or pathlib.Path("cache/transcripts")
        self._beam_size = beam_size
        self._vad_filter = vad_filter
        self._model: Any = None

    def transcribe(
        self,
        audio_path: pathlib.Path,
        asset_id: str,
        language: str | None = None,
        initial_prompt: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Transcribe audio. Caches result to disk keyed by asset_id."""
        if not force:
            cached = self._load_cached(asset_id)
            if cached:
                log.info("transcription.cache_hit", asset_id=asset_id)
                return cached

        log.info(
            "transcription.start",
            asset_id=asset_id,
            model=self._model_name,
            device=self._device,
        )
        self._load_model()

        try:
            segments_gen, info = self._model.transcribe(
                str(audio_path),
                language=language,
                initial_prompt=initial_prompt,
                word_timestamps=True,
                vad_filter=self._vad_filter,
                beam_size=self._beam_size,
            )

            segments: list[dict] = []
            for i, seg in enumerate(segments_gen):
                words = []
                if seg.words:
                    for w in seg.words:
                        words.append({
                            "text": w.word.strip(),
                            "start": round(w.start, 3),
                            "end": round(w.end, 3),
                            "confidence": round(w.probability, 4),
                        })
                segments.append({
                    "id": i,
                    "text": seg.text.strip(),
                    "start": round(seg.start, 3),
                    "end": round(seg.end, 3),
                    "words": words,
                    "avg_logprob": round(seg.avg_logprob, 4),
                    "no_speech_prob": round(seg.no_speech_prob, 4),
                })

            transcript = {
                "asset_id": asset_id,
                "language": info.language,
                "model_name": self._model_name,
                "duration_sec": round(info.duration, 3),
                "segments": segments,
                "transcribed_at": datetime.now(timezone.utc).isoformat(),
                "word_count": sum(len(s["words"]) for s in segments),
            }
            self._save_transcript(asset_id, transcript)
            log.info(
                "transcription.complete",
                asset_id=asset_id,
                segments=len(segments),
                words=transcript["word_count"],
                duration=transcript["duration_sec"],
            )
            return transcript

        except VaClipTranscriptionError:
            raise
        except Exception as exc:
            log.error("transcription.failed", asset_id=asset_id, error=str(exc))
            raise VaClipTranscriptionError(f"Transcription failed: {exc}") from exc

    def unload(self) -> None:
        """Release the model from memory."""
        self._model = None

    def _load_model(self) -> None:
        if self._model is not None:
            return
        log.info(
            "transcription.model_loading",
            model=self._model_name,
            device=self._device,
            compute_type=self._compute_type,
        )
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise VaClipTranscriptionError(
                "faster-whisper is not installed. Run: pip install faster-whisper"
            ) from exc
        self._models_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._model = WhisperModel(
                self._model_name,
                device=self._device,
                compute_type=self._compute_type,
                download_root=str(self._models_dir),
            )
            log.info("transcription.model_loaded", model=self._model_name)
        except Exception as exc:
            raise VaClipTranscriptionError(
                f"Failed to load Whisper model '{self._model_name}': {exc}"
            ) from exc

    def _save_transcript(self, asset_id: str, data: dict) -> None:
        self._transcripts_dir.mkdir(parents=True, exist_ok=True)
        out = self._transcripts_dir / f"{asset_id}.json"
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        log.debug("transcription.saved", path=str(out))

    def _load_cached(self, asset_id: str) -> dict | None:
        path = self._transcripts_dir / f"{asset_id}.json"
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                pass
        return None

    @staticmethod
    def _detect_device() -> str:
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    @staticmethod
    def _resolve_compute_type(compute_type: str, device: str) -> str:
        if device == "cpu" and compute_type == "float16":
            return "int8"
        return compute_type


def get_transcription_backend(settings: Any) -> WhisperBackend:
    """Construct a WhisperBackend from Settings."""
    t = settings.transcription
    p = settings.paths
    return WhisperBackend(
        model_name=t.model_name,
        device=t.device,
        compute_type=t.compute_type,
        models_dir=p.models_dir,
        transcripts_dir=p.transcripts_dir,
        beam_size=t.beam_size,
        vad_filter=t.vad_filter,
    )
