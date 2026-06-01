"""End-to-end integration tests for the CLI `clip` command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from vaclip.cli.main import app

runner = CliRunner()


@pytest.mark.integration
def test_clip_command_runs_successfully(tmp_path: Path, fixture_dir: Path):
    """The `run` command should run successfully on fixture media."""
    source = fixture_dir / "sample_video.mp4"
    output_dir = tmp_path / "output"

    # Mock transcription to avoid model download
    with patch("vaclip.transcription.whisper_backend.WhisperBackend.transcribe") as mock_transcribe:
        mock_transcript = MagicMock()
        mock_transcript.segments = []
        mock_transcript.language = "en"
        mock_transcript.model_name = "tiny"
        mock_transcript.duration_sec = 5.0
        mock_transcribe.return_value = mock_transcript

        # Mock scoring to return empty list
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
                    "--profile",
                    "podcast",
                ],
            )

    assert result.exit_code == 0, f"CLI run failed: {result.stdout}"

    # Verify asset directory was created (even with no clips)
    assert output_dir.exists(), "Output directory should be created"


@pytest.mark.integration
def test_clip_command_dry_run(tmp_path: Path, fixture_dir: Path):
    """`run --dry-run` should plan but not create output files."""
    source = fixture_dir / "sample_video.mp4"
    output_dir = tmp_path / "output"

    result = runner.invoke(
        app,
        [
            "run",
            "--source",
            str(source),
            "--output-dir",
            str(output_dir),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, f"Dry run failed: {result.stdout}"
    assert "Planning mode" in result.stdout or "dry_run" in result.stdout.lower()

    # Ensure no output files were created
    assert not output_dir.exists() or not any(output_dir.iterdir()), "Output directory should be empty after dry run"


@pytest.mark.integration
def test_clip_command_invalid_source_exits_1():
    """`run` with a nonexistent source should exit with code 1."""
    result = runner.invoke(app, ["run", "--source", "/nonexistent/path/to/video.mp4"])
    assert result.exit_code == 1, "Expected exit code 1 for invalid source"
    assert "Error" in result.stdout or "error" in result.stdout.lower()