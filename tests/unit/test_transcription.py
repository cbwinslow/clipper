"""Unit tests for the transcription module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vaclip.transcription.whisper_backend import WhisperBackend
from vaclip.utils.exceptions import VaClipTranscriptionError


def test_whisper_backend_init():
    """Test WhisperBackend initialization."""
    backend = WhisperBackend()
    assert backend._model is None  # Model not loaded yet


@patch("faster_whisper.WhisperModel")
def test_whisper_backend_load_model(mock_whisper_model):
    """Test loading the Whisper model."""
    mock_model_instance = MagicMock()
    mock_whisper_model.return_value = mock_model_instance

    backend = WhisperBackend()
    backend._load_model()

    assert backend._model is mock_model_instance
    mock_whisper_model.assert_called_once_with(
        "large-v3", device="cuda", compute_type="float16", download_root="models"
    )


@patch("faster_whisper.WhisperModel")
def test_whisper_backend_transcribe_success(mock_whisper_model):
    """Test successful transcription."""
    # Create mock segments with direct attributes (matching actual code access pattern)
    mock_segment1 = MagicMock()
    mock_segment1.id = 0
    mock_segment1.text = "Hello world"
    mock_segment1.start = 0.0
    mock_segment1.end = 2.5
    mock_segment1.words = []  # empty words list to avoid inner loop

    mock_segment2 = MagicMock()
    mock_segment2.id = 1
    mock_segment2.text = "This is a test"
    mock_segment2.start = 2.5
    mock_segment2.end = 5.0
    mock_segment2.words = []

    mock_model_instance = MagicMock()
    mock_info = MagicMock()
    mock_info.language = "en"
    mock_info.duration = 5.0
    mock_model_instance.transcribe.return_value = (
        [mock_segment1, mock_segment2],
        mock_info,
    )
    mock_whisper_model.return_value = mock_model_instance

    backend = WhisperBackend()
    backend._load_model()

    # Create a dummy audio file
    audio_file = Path("dummy.wav")
    audio_file.touch()

    try:
        result = backend.transcribe(audio_file, "test123")
        assert len(result.segments) == 2
        assert result.segments[0].start == 0.0
        assert result.segments[0].end == 2.5
        assert result.segments[0].text == "Hello world"
        assert result.segments[1].start == 2.5
        assert result.segments[1].end == 5.0
        assert result.segments[1].text == "This is a test"
        assert result.language == "en"
    finally:
        audio_file.unlink(missing_ok=True)


@patch("faster_whisper.WhisperModel")
def test_whisper_backend_transcribe_failure(mock_whisper_model):
    """Test transcription failure."""
    mock_model_instance = MagicMock()
    mock_model_instance.transcribe.side_effect = Exception("Transcription failed")
    mock_whisper_model.return_value = mock_model_instance

    backend = WhisperBackend()
    backend._load_model()

    audio_file = Path("dummy.wav")
    audio_file.touch()

    try:
        with pytest.raises(VaClipTranscriptionError, match="Transcription failed"):
            backend.transcribe(audio_file, "test123")
    finally:
        audio_file.unlink(missing_ok=True)


def test_whisper_backend_transcribe_without_model():
    """Test transcribing without loading model first."""
    backend = WhisperBackend()
    audio_file = Path("dummy.wav")
    audio_file.touch()

    try:
        # Mock _load_model to raise the expected error
        with patch.object(backend, '_load_model', side_effect=VaClipTranscriptionError("Model not loaded. Call load_model() first.")):
            with pytest.raises(VaClipTranscriptionError):
                backend.transcribe(audio_file, "test123")
    finally:
        audio_file.unlink(missing_ok=True)