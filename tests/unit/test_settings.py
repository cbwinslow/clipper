"""Unit tests for settings module."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from vaclip.config.settings import (
    Settings,
    get_settings,
    reset_settings,
    PathSettings,
    TranscriptionSettings,
    ScoringSettings,
    ExportSettings,
    ArtifactSettings,
    LoggingSettings
)


def test_settings_defaults():
    """Test that default settings are loaded correctly."""
    settings = Settings()
    assert isinstance(settings.paths, PathSettings)
    assert isinstance(settings.transcription, TranscriptionSettings)
    assert isinstance(settings.scoring, ScoringSettings)
    assert isinstance(settings.export, ExportSettings)
    assert isinstance(settings.artifacts, ArtifactSettings)
    assert isinstance(settings.logging, LoggingSettings)


def test_settings_from_yaml(tmp_path):
    """Test loading settings from a YAML file."""
    yaml_content = """
    paths:
      input_dir: "test_input"
      output_dir: "test_output"
    transcription:
      model_name: "small"
      device: "cpu"
    scoring:
      transcript_weight: 0.6
      audio_weight: 0.3
      visual_weight: 0.1
    """
    yaml_file = tmp_path / "test_config.yaml"
    yaml_file.write_text(yaml_content)

    settings = Settings.from_yaml(yaml_file)
    assert settings.paths.input_dir == Path("test_input")
    assert settings.paths.output_dir == Path("test_output")
    assert settings.transcription.model_name == "small"
    assert settings.transcription.device == "cpu"
    assert settings.scoring.transcript_weight == 0.6
    assert settings.scoring.audio_weight == 0.3
    assert settings.scoring.visual_weight == 0.1


def test_settings_from_env(monkeypatch):
    """Test loading settings from environment variables."""
    monkeypatch.setenv("VACLIP__TRANSCRIPTION__MODEL_NAME", "medium")
    monkeypatch.setenv("VACLIP__TRANSCRIPTION__DEVICE", "cuda")
    monkeypatch.setenv("VACLIP__SCORING__TRANSCRIPT_WEIGHT", "0.7")
    monkeypatch.setenv("VACLIP__EXPORT__VIDEO_CRF", "20")

    settings = Settings.from_env()

    assert settings.transcription.model_name == "medium"
    assert settings.transcription.device == "cuda"
    assert settings.scoring.transcript_weight == 0.7
    assert settings.export.video_crf == 20


def test_settings_from_env_nested(monkeypatch):
    """Test loading nested settings from environment variables."""
    monkeypatch.setenv("VACLIP__PATHS__INPUT_DIR", "/custom/input")
    monkeypatch.setenv("VACLIP__PATHS__OUTPUT_DIR", "/custom/output")

    settings = Settings.from_env()
    assert settings.paths.input_dir == Path("/custom/input")
    assert settings.paths.output_dir == Path("/custom/output")


def test_settings_from_env_type_conversion(monkeypatch):
    """Test that environment variables are converted to correct types."""
    monkeypatch.setenv("VACLIP__TRANSCRIPTION__BEST_OF", "10")
    monkeypatch.setenv("VACLIP__SCORING__TOP_N", "5")
    monkeypatch.setenv("VACLIP__EXPORT__VERTICAL_WIDTH", "1280")
    monkeypatch.setenv("VACLIP__LOGGING__LEVEL", "DEBUG")

    settings = Settings.from_env()
    assert settings.transcription.best_of == 10
    assert settings.scoring.top_n == 5
    assert settings.export.vertical_width == 1280
    assert settings.logging.level == "DEBUG"


def test_settings_from_env_bool(monkeypatch):
    """Test boolean environment variable conversion."""
    monkeypatch.setenv("VACLIP__TRANSCRIPTION__WORD_TIMESTAMPS", "false")
    monkeypatch.setenv("VACLIP__ARTIFACTS__OVERWRITE", "true")

    settings = Settings.from_env()
    assert settings.transcription.word_timestamps is False
    assert settings.artifacts.overwrite is True


def test_settings_validation():
    """Test settings validation."""
    settings = Settings()
    settings.validate()  # Should not raise

    # Test invalid device
    settings.transcription.device = "invalid"
    with pytest.raises(ValueError, match="Invalid device"):
        settings.validate()

    # Reset and test invalid CRF
    settings.transcription.device = "cuda"
    settings.export.video_crf = 52
    with pytest.raises(ValueError, match="Invalid CRF value"):
        settings.validate()

    # Reset and test invalid weight sum
    settings.export.video_crf = 18
    settings.scoring.transcript_weight = 0.5
    settings.scoring.audio_weight = 0.3
    settings.scoring.visual_weight = 0.3  # Sum = 1.1
    with pytest.raises(ValueError, match="Scoring weights must sum to 1.0"):
        settings.validate()

    # Reset and test valid weight sum (with floating point tolerance)
    settings.scoring.transcript_weight = 0.333
    settings.scoring.audio_weight = 0.333
    settings.scoring.visual_weight = 0.334  # Sum = 1.0
    settings.validate()  # Should not raise


def test_settings_cuda_warning(monkeypatch):
    """Test warning when CUDA is requested but not available."""
    # Mock torch to simulate CUDA not available
    class MockTorch:
        class cuda:
            @staticmethod
            def is_available():
                return False

    # We need to patch where it's used, which is in the validate method
    with patch.dict('sys.modules', {'torch': MockTorch}):
        monkeypatch.setenv("VACLIP__TRANSCRIPTION__DEVICE", "cuda")

        settings = Settings.from_env()
        # Validate to trigger CUDA warning logic
        settings.validate()
        # After validation, device should be switched to cpu and compute_type to int8
        assert settings.transcription.device == "cpu"
        assert settings.transcription.compute_type == "int8"


def test_settings_singleton():
    """Test that get_settings returns a singleton."""
    reset_settings()
    settings1 = get_settings()
    settings2 = get_settings()
    assert settings1 is settings2

    # After reset, we should get a new instance
    reset_settings()
    settings3 = get_settings()
    assert settings3 is not settings1