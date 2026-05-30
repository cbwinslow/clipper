"""Unit tests for the export module."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch
import uuid
import subprocess

import pytest

from vaclip.export.clip_exporter import ClipExporter, get_framing_strategy
from vaclip.models.media import MediaAsset
from vaclip.models.schemas import Segment, ScoredSegment, ClipBounds, ExportedClip, FramingStrategy
from vaclip.utils.exceptions import VaClipExportError


def test_clip_exporter_init():
    exporter = ClipExporter()
    assert exporter.output_dir == Path("output")
    assert exporter.ffmpeg_bin == "ffmpeg"


def test_clip_exporter_custom_init():
    exporter = ClipExporter(output_dir=Path("custom/output"), ffmpeg_bin="/path/to/ffmpeg")
    assert exporter.output_dir == Path("custom/output")
    assert exporter.ffmpeg_bin == "/path/to/ffmpeg"


@patch("vaclip.export.clip_exporter.subprocess.run")
def test_clip_exporter_export_success(mock_subprocess_run, tmp_path):
    # Mock subprocess.run to create the output file and return success
    def mock_run(*args, **kwargs):
        # args[0] is the list of command and arguments
        # The last element is the output file path
        output_path = Path(args[0][-1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("dummycontent")  # 12 bytes exactly
        return subprocess.CompletedProcess(args[0], 0, stdout="", stderr="")

    mock_subprocess_run.side_effect = mock_run

    output_dir = tmp_path / "output"
    exporter = ClipExporter(output_dir=output_dir)

    input_file = tmp_path / "input.mp4"
    input_file.touch()
    media = MediaAsset(
        id=uuid.uuid4(),
        source_url=str(input_file),
        local_path=str(input_file),
        title="test",
        duration_seconds=30.0,
        width=1920,
        height=1080,
        fps=30.0,
        codec="h264",
        format="mp4",
        profile="default",
        video_id=None,
        is_url=False,
    )
    clip_segment = ScoredSegment(
        segment=Segment(
            id=1,
            text="test segment",
            start=10.0,
            end=20.0,
            words=[],
            speaker=None,
            language="en",
        ),
        score=0.8,
        highlights=["test"],
        rank=1,
    )

    clips = exporter.export(media, [clip_segment], framing="wide", max_clips=1)
    mock_subprocess_run.assert_called_once()
    args, kwargs = mock_subprocess_run.call_args
    assert "ffmpeg" in args[0]
    assert "-i" in args[0]
    assert str(input_file) in args[0]
    assert "-ss" in args[0]
    assert "10.0" in args[0]
    assert "-to" in args[0]
    assert "20.0" in args[0]
    # Build expected ExportedClip to compare with
    expected_clip = ExportedClip(
        clip_id=str(uuid.uuid4()),
        source_path=Path(input_file),
        output_path=output_dir / str(media.id) / "001_default_wide.mp4",
        bounds=ClipBounds(start=10.0, end=20.0),
        profile="default",
        width=1920,
        height=1080,
        framing=FramingStrategy.WIDE,
        scored_segment=clip_segment,
        exported_at=datetime.now(timezone.utc),
        metadata={},
        file_size_bytes=12,
    )
    assert len(clips) == 1
    # Check that key fields match (ignoring auto-generated fields like clip_id and exported_at)
    assert clips[0].source_path == expected_clip.source_path
    assert clips[0].output_path == expected_clip.output_path
    assert clips[0].bounds == expected_clip.bounds
    assert clips[0].profile == expected_clip.profile
    assert clips[0].width == expected_clip.width
    assert clips[0].height == expected_clip.height
    assert clips[0].framing == expected_clip.framing
    assert clips[0].scored_segment == expected_clip.scored_segment
    assert clips[0].file_size_bytes == expected_clip.file_size_bytes


@patch("vaclip.export.clip_exporter.subprocess.run")
def test_clip_exporter_export_failure(mock_subprocess_run, tmp_path):
    # Mock subprocess.run to return failure
    mock_subprocess_run.return_value.returncode = 1
    mock_subprocess_run.return_value.stdout = ""
    mock_subprocess_run.return_value.stderr = "FFmpeg error"

    output_dir = tmp_path / "output"
    exporter = ClipExporter(output_dir=output_dir)

    input_file = tmp_path / "input.mp4"
    input_file.touch()
    media = MediaAsset(
        id=uuid.uuid4(),
        source_url=str(input_file),
        local_path=str(input_file),
        title="test",
        duration_seconds=30.0,
        width=1920,
        height=1080,
        fps=30.0,
        codec="h264",
        format="mp4",
        profile="default",
        video_id=None,
        is_url=False,
    )
    clip_segment = ScoredSegment(
        segment=Segment(
            id=1,
            text="test segment",
            start=10.0,
            end=20.0,
        ),
        score=0.8,
        highlights=["test"],
        rank=1,
    )

    # export() catches individual failures and continues - returns empty list
    clips = exporter.export(media, [clip_segment], framing="wide", max_clips=1)
    assert len(clips) == 0


@patch("vaclip.export.clip_exporter.subprocess.run")
def test_clip_exporter_export_one_raises_on_failure(mock_subprocess_run, tmp_path):
    mock_subprocess_run.return_value.returncode = 1
    mock_subprocess_run.return_value.stdout = ""
    mock_subprocess_run.return_value.stderr = "FFmpeg error"

    output_dir = tmp_path / "output"
    exporter = ClipExporter(output_dir=output_dir)

    input_file = tmp_path / "input.mp4"
    input_file.touch()
    media = MediaAsset(
        id=uuid.uuid4(),
        source_url=str(input_file),
        local_path=str(input_file),
        title="test",
        duration_seconds=30.0,
        width=1920,
        height=1080,
        fps=30.0,
        codec="h264",
        format="mp4",
        profile="default",
        video_id=None,
        is_url=False,
    )
    clip_segment = ScoredSegment(
        segment=Segment(
            id=1,
            text="test segment",
            start=10.0,
            end=20.0,
        ),
        score=0.8,
        highlights=["test"],
        rank=1,
    )

    with pytest.raises(VaClipExportError, match="FFmpeg failed"):
        exporter._export_one(media, clip_segment, get_framing_strategy("wide"), output_dir)
