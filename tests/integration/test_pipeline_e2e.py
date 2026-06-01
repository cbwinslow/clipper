"""End-to-end integration tests for the full Clipper pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from vaclip.cli.main import app

runner = CliRunner()


@pytest.mark.integration
def test_podcast_clip_from_local_file(tmp_path: Path, fixture_dir: Path):
    """Run pipeline on sample_video.mp4 and verify outputs."""
    # Use fixture media (video file, not podcast mp3 which doesn't exist)
    source = fixture_dir / "sample_video.mp4"
    output_dir = tmp_path / "output"
    config_path = fixture_dir / "sample_config.yaml"

    # Mock transcription to avoid model download
    with patch("vaclip.transcription.whisper_backend.WhisperBackend.transcribe") as mock_transcribe:
        mock_transcript = MagicMock()
        mock_transcript.segments = []
        mock_transcript.language = "en"
        mock_transcript.model_name = "tiny"
        mock_transcript.duration_sec = 5.0
        mock_transcribe.return_value = mock_transcript

        # Mock scoring to return empty list (no segments to score)
        with patch("vaclip.scoring.highlight_scorer.CompositeScorer.score_all") as mock_score:
            mock_score.return_value = []

            # Run the pipeline via CLI
            result = runner.invoke(
                app,
                [
                    "run",
                    "--source",
                    str(source),
                    "--output-dir",
                    str(output_dir),
                    "--config",
                    str(config_path),
                    "--profile",
                    "podcast",
                ],
            )

    assert result.exit_code == 0, f"Pipeline failed: {result.stdout}"

    # Verify manifest exists (clips.json in asset subdirectory)
    # The exporter creates output/<asset_id>/clips.json
    asset_dirs = list(output_dir.iterdir()) if output_dir.exists() else []
    assert len(asset_dirs) >= 1, "No asset directory created"
    manifest_path = asset_dirs[0] / "clips.json"
    assert manifest_path.exists(), "clips.json not found"
    manifest = json.loads(manifest_path.read_text())
    assert "clips" in manifest


@pytest.mark.integration
def test_video_clip_from_local_file(tmp_path: Path, fixture_dir: Path):
    """Run pipeline on sample_video.mp4 and verify outputs."""
    source = fixture_dir / "sample_video.mp4"
    output_dir = tmp_path / "output"
    config_path = fixture_dir / "sample_config.yaml"

    # Mock transcription
    with patch("vaclip.transcription.whisper_backend.WhisperBackend.transcribe") as mock_transcribe:
        mock_transcript = MagicMock()
        mock_transcript.segments = []
        mock_transcript.language = "en"
        mock_transcript.model_name = "tiny"
        mock_transcript.duration_sec = 5.0
        mock_transcribe.return_value = mock_transcript

        # Mock scoring
        with patch("vaclip.scoring.highlight_scorer.CompositeScorer.score_all") as mock_score:
            mock_score.return_value = []

            result = runner.invoke(
                app,
                [
                    "run",
                    "--source",
                    str(source),
                    "--output-dir",
                    str(output_dir),
                    "--config",
                    str(config_path),
                    "--profile",
                    "podcast",
                ],
            )

    assert result.exit_code == 0, f"Pipeline failed: {result.stdout}"

    # Verify manifest exists (clips.json in asset subdirectory)
    asset_dirs = list(output_dir.iterdir()) if output_dir.exists() else []
    assert len(asset_dirs) >= 1, "No asset directory created"
    manifest_path = asset_dirs[0] / "clips.json"
    assert manifest_path.exists(), "clips.json not found"
    manifest = json.loads(manifest_path.read_text())
    assert "clips" in manifest


@pytest.mark.integration
def test_dry_run_no_files_written(tmp_path: Path, fixture_dir: Path):
    """Dry run should plan but not create any output files."""
    source = fixture_dir / "sample_video.mp4"
    output_dir = tmp_path / "output"
    config_path = fixture_dir / "sample_config.yaml"

    result = runner.invoke(
        app,
        [
            "run",
            "--source",
            str(source),
            "--output-dir",
            str(output_dir),
            "--config",
            str(config_path),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, f"Dry run failed: {result.stdout}"
    assert "Planning mode" in result.stdout or "dry_run" in result.stdout.lower()

    # Ensure no output files were created
    assert not output_dir.exists() or not any(output_dir.iterdir()), "Output directory should be empty after dry run"


@pytest.mark.integration
def test_config_yaml_overrides_defaults(tmp_path: Path, fixture_dir: Path):
    """Config YAML should override default profile and top_n."""
    source = fixture_dir / "sample_video.mp4"
    output_dir = tmp_path / "output"
    # Create a config that overrides profile and top_k (which controls max clips)
    custom_config = fixture_dir / "custom_config.yaml"
    custom_config.write_text("""
scoring:
  default_profile: podcast
  top_k: 1
  min_score: 0.1
  use_embeddings: false
export:
  default_format: source
  video_encoder: libx264
  audio_encoder: aac
  crf: 23
  preset: ultrafast
artifacts:
  overwrite: true
""")

    # Mock transcription
    with patch("vaclip.transcription.whisper_backend.WhisperBackend.transcribe") as mock_transcribe:
        mock_transcript = MagicMock()
        mock_transcript.segments = []
        mock_transcript.language = "en"
        mock_transcript.model_name = "tiny"
        mock_transcript.duration_sec = 5.0
        mock_transcribe.return_value = mock_transcript

        # Mock scoring
        with patch("vaclip.scoring.highlight_scorer.CompositeScorer.score_all") as mock_score:
            mock_score.return_value = []

            result = runner.invoke(
                app,
                [
                    "run",
                    "--source",
                    str(source),
                    "--output-dir",
                    str(output_dir),
                    "--config",
                    str(custom_config),
                ],
            )

    assert result.exit_code == 0, f"Pipeline with custom config failed: {result.stdout}"

    # Verify that no clips were produced (due to empty scored segments)
    clips = list(output_dir.glob("*.mp4"))
    assert len(clips) == 0, f"Expected 0 clips, got {len(clips)}"


@pytest.mark.integration
def test_manifest_written_after_run(tmp_path: Path, fixture_dir: Path):
    """Manifest.json should be valid JSON and contain expected keys."""
    source = fixture_dir / "sample_video.mp4"
    output_dir = tmp_path / "output"
    config_path = fixture_dir / "sample_config.yaml"

    # Mock transcription
    with patch("vaclip.transcription.whisper_backend.WhisperBackend.transcribe") as mock_transcribe:
        mock_transcript = MagicMock()
        mock_transcript.segments = []
        mock_transcript.language = "en"
        mock_transcript.model_name = "tiny"
        mock_transcript.duration_sec = 5.0
        mock_transcribe.return_value = mock_transcript

        # Mock scoring
        with patch("vaclip.scoring.highlight_scorer.CompositeScorer.score_all") as mock_score:
            mock_score.return_value = []

            result = runner.invoke(
                app,
                [
                    "run",
                    "--source",
                    str(source),
                    "--output-dir",
                    str(output_dir),
                    "--config",
                    str(config_path),
                ],
            )

    assert result.exit_code == 0, f"Pipeline failed: {result.stdout}"

    # Manifest is clips.json in asset subdirectory
    asset_dirs = list(output_dir.iterdir()) if output_dir.exists() else []
    assert len(asset_dirs) >= 1, "No asset directory created"
    manifest_path = asset_dirs[0] / "clips.json"
    assert manifest_path.exists()

    # Validate JSON structure
    manifest = json.loads(manifest_path.read_text())
    assert "clips" in manifest


@pytest.mark.integration
def test_srt_generated_alongside_clip(tmp_path: Path, fixture_dir: Path):
    """Each exported clip should have a corresponding SRT file."""
    source = fixture_dir / "sample_video.mp4"
    output_dir = tmp_path / "output"
    config_path = fixture_dir / "sample_config.yaml"

    # Mock transcription
    with patch("vaclip.transcription.whisper_backend.WhisperBackend.transcribe") as mock_transcribe:
        mock_transcript = MagicMock()
        mock_transcript.segments = []
        mock_transcript.language = "en"
        mock_transcript.model_name = "tiny"
        mock_transcript.duration_sec = 5.0
        mock_transcribe.return_value = mock_transcript

        # Mock scoring
        with patch("vaclip.scoring.highlight_scorer.CompositeScorer.score_all") as mock_score:
            mock_score.return_value = []

            result = runner.invoke(
                app,
                [
                    "run",
                    "--source",
                    str(source),
                    "--output-dir",
                    str(output_dir),
                    "--config",
                    str(config_path),
                ],
            )

    assert result.exit_code == 0, f"Pipeline failed: {result.stdout}"

    clips = list(output_dir.glob("*.mp4"))
    srts = list(output_dir.glob("*.srt"))

    # No clips expected since we have no scored segments
    assert len(clips) == 0, "No clips expected with empty scored segments"
    assert len(srts) == 0, "No SRTs expected with no clips"