"""Unit tests for the pipeline module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vaclip.pipeline.pipeline import VAClipPipeline as Pipeline
from vaclip.utils.exceptions import VaClipError


def test_pipeline_init():
    """Test Pipeline initialization."""
    pipeline = Pipeline()
    assert pipeline.settings is not None


def test_pipeline_run_success(tmp_path):
    """Test successful pipeline run."""
    mock_media = MagicMock()
    mock_media.id = "test-id"
    mock_media.audio_path = Path("/dummy/audio.wav")
    mock_media.duration_seconds = 120.0
    mock_media.width = 1920
    mock_media.height = 1080
    mock_media.fps = 30.0
    mock_media.codec = "h264"
    mock_media.format = "mp4"

    mock_transcript = MagicMock()
    mock_transcript.segments = []

    mock_scored_segments = []

    with patch("vaclip.pipeline.checkpoint.load_checkpoint") as mock_load_ckpt, \
         patch("vaclip.pipeline.checkpoint.save_checkpoint") as mock_save_ckpt, \
         patch("vaclip.ingest.local_adapter.LocalFileAdapter") as mock_adapter_class, \
         patch("vaclip.transcription.whisper_backend.get_transcription_backend") as mock_backend_fn, \
         patch("vaclip.scoring.highlight_scorer.CompositeScorer") as mock_scorer_class, \
         patch("vaclip.export.clip_exporter.ClipExporter") as mock_exporter_class:

        mock_checkpoint = MagicMock()
        mock_checkpoint.is_stage_completed.return_value = False
        mock_load_ckpt.return_value = mock_checkpoint

        mock_adapter = MagicMock()
        mock_adapter.ingest.return_value = mock_media
        mock_adapter_class.return_value = mock_adapter

        mock_backend = MagicMock()
        mock_backend.transcribe.return_value = mock_transcript
        mock_backend_fn.return_value = mock_backend

        mock_scorer = MagicMock()
        mock_scorer.score_all.return_value = mock_scored_segments
        mock_scorer_class.return_value = mock_scorer

        mock_exporter = MagicMock()
        mock_exporter.export.return_value = []
        mock_exporter_class.return_value = mock_exporter

        pipeline = Pipeline()
        pipeline.settings.paths.output_dir = tmp_path / "output"

        result = pipeline.run(
            source="input.mp4",
            profile="podcast",
            framing="wide",
        )

        mock_adapter.ingest.assert_called_once()
        mock_backend.transcribe.assert_called_once()
        mock_scorer.score_all.assert_called_once()
        mock_exporter.export.assert_called_once()


def test_pipeline_run_ingest_failure(tmp_path):
    """Test pipeline run when ingest fails."""
    with patch("vaclip.pipeline.checkpoint.load_checkpoint") as mock_load_ckpt, \
         patch("vaclip.pipeline.checkpoint.save_checkpoint") as mock_save_ckpt, \
         patch("vaclip.ingest.local_adapter.LocalFileAdapter") as mock_adapter_class:

        mock_checkpoint = MagicMock()
        mock_checkpoint.is_stage_completed.return_value = False
        mock_load_ckpt.return_value = mock_checkpoint

        mock_adapter = MagicMock()
        mock_adapter.ingest.side_effect = Exception("Ingest failed")
        mock_adapter_class.return_value = mock_adapter

        pipeline = Pipeline()
        pipeline.settings.paths.output_dir = tmp_path / "output"

        with pytest.raises(Exception, match="Ingest failed"):
            pipeline.run(
                source="input.mp4",
                profile="podcast",
            )


def test_pipeline_run_missing_components():
    """Test pipeline run when components are not set."""
    pipeline = Pipeline()
    mock_media = MagicMock()
    mock_media.id = "test-id"
    mock_media.audio_path = None

    with patch("vaclip.pipeline.checkpoint.load_checkpoint") as mock_load_ckpt, \
         patch("vaclip.pipeline.checkpoint.save_checkpoint") as mock_save_ckpt, \
         patch("vaclip.ingest.local_adapter.LocalFileAdapter") as mock_adapter_class:

        mock_checkpoint = MagicMock()
        mock_checkpoint.is_stage_completed.return_value = False
        mock_load_ckpt.return_value = mock_checkpoint

        mock_adapter = MagicMock()
        mock_adapter.ingest.return_value = mock_media
        mock_adapter_class.return_value = mock_adapter

        with pytest.raises(Exception):
            pipeline.run(
                source="input.mp4",
                profile="podcast",
            )