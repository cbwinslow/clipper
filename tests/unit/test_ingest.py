"""Unit tests for the ingest module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vaclip.ingest.base import IngestAdapter
from vaclip.ingest.local_adapter import LocalFileAdapter
from vaclip.ingest.registry import IngestRegistry
from vaclip.ingest.ytdlp_adapter import YtDlpAdapter
from vaclip.utils.exceptions import VaClipIngestError, VaClipUnsupportedSourceError


def test_base_adapter_abstract():
    """Test that IngestAdapter cannot be instantiated directly."""
    with pytest.raises(TypeError):
        IngestAdapter()


def test_local_adapter_can_handle(tmp_path):
    """Test LocalFileAdapter supports method."""
    adapter = LocalFileAdapter()
    # Create temporary files for testing
    video_file = tmp_path / "video.mp4"
    video_file.write_text("fake video")
    mkv_file = tmp_path / "video.mkv"
    mkv_file.write_text("fake video")
    avi_file = tmp_path / "video.avi"
    avi_file.write_text("fake video")

    # Should handle local files with video extensions
    assert adapter.supports(str(video_file)) is True
    assert adapter.supports(str(mkv_file)) is True
    assert adapter.supports(str(avi_file)) is True
    # Should not handle URLs or non-video files
    assert adapter.supports("https://www.youtube.com/watch?v=test") is False
    assert adapter.supports("/path/to/document.pdf") is False
    assert adapter.supports("") is False


    def test_local_adapter_ingest(tmp_path):
        """Test LocalFileAdapter ingest method."""
        # Create a temporary file
        test_file = tmp_path / "test_video.mp4"
        test_file.write_text("fake video content")

        with patch("subprocess.run") as mock_ffprobe, \
             patch("vaclip.ingest.audio_extractor.extract_audio") as mock_extract_audio:

            mock_ffprobe.return_value.returncode = 0
            mock_ffprobe.return_value.stdout = '{"streams": [{"codec_type": "video", "width": 1920, "height": 1080, "r_frame_rate": "30/0", "codec_name": "h264"}], "format": {"duration": "120.0", "format_name": "mp4"}}'
            mock_ffprobe.return_value.stderr = ""

            mock_extract_audio.return_value = Path("/dummy/audio/path.wav")

            adapter = LocalFileAdapter()
            result = adapter.ingest(str(test_file))

            # The file gets copied to input directory, so source_url is original, local_path is copied
            assert result.source_url == str(test_file)
            assert result.local_path.startswith("input/")
            assert result.local_path.endswith("/test_video.mp4")
            assert result.audio_path == str(Path("/dummy/audio/path.wav"))
            assert result.duration_seconds == 120.0
            assert result.profile == "generic"


def test_local_adapter_ingest_nonexistent():
    """Test LocalFileAdapter ingest with nonexistent file."""
    adapter = LocalFileAdapter()
    with pytest.raises(VaClipUnsupportedSourceError, match="File not found"):
        adapter.ingest(Path("/nonexistent/file.mp4"))


def test_ytdlp_adapter_can_handle():
    """Test YtDlpAdapter supports method."""
    adapter = YtDlpAdapter()
    # Should handle URLs
    assert adapter.supports("https://www.youtube.com/watch?v=test") is True
    assert adapter.supports("https://youtu.be/test") is True
    assert adapter.supports("http://example.com/video.mp4") is True
    # Should not handle local file paths
    assert adapter.supports("/path/to/video.mp4") is False


@patch("yt_dlp.YoutubeDL")
def test_ytdlp_adapter_ingest_success(mock_ytdlp):
    """Test YtDlpAdapter ingest with successful extraction."""
    mock_instance = MagicMock()
    mock_instance.extract_info.return_value = {
        "id": "test123",
        "title": "Test Video",
        "duration": 120,
        "formats": [{"url": "http://example.com/video.mp4", "ext": "mp4"}],
    }
    mock_instance.prepare_filename.return_value = "/tmp/test_video.mp4"
    mock_ytdlp.return_value.__enter__.return_value = mock_instance

    adapter = YtDlpAdapter()
    with patch.object(adapter, '_extract_audio', return_value=Path("/dummy/audio/path.wav")):
        result = adapter.ingest("https://www.youtube.com/watch?v=test123")

    assert result.source_url == "https://www.youtube.com/watch?v=test123"
    assert result.title == "Test Video"
    assert result.duration_seconds == 120
    assert result.audio_path == Path("/dummy/audio/path.wav")


@patch("yt_dlp.YoutubeDL")
def test_ytdlp_adapter_ingest_failure(mock_ytdlp):
    """Test YtDlpAdapter ingest with yt-dlp failure."""
    mock_ytdlp.side_effect = Exception("Download failed")

    adapter = YtDlpAdapter()
    with pytest.raises(VaClipIngestError, match="yt-dlp download failed"):
        adapter.ingest("https://www.youtube.com/watch?v=test123")


def test_registry_get_adapter(tmp_path):
    """Test IngestRegistry returns correct adapter."""
    registry = IngestRegistry()

    # Create a temporary file for local file test
    video_file = tmp_path / "video.mp4"
    video_file.write_text("fake video")

    # Test YouTube URL
    adapter = registry.get_adapter("https://youtube.com/watch?v=test")
    assert isinstance(adapter, YtDlpAdapter)

    # Test direct video URL
    adapter = registry.get_adapter("https://example.com/video.mp4")
    assert isinstance(adapter, YtDlpAdapter)

    # Test local file
    adapter = registry.get_adapter(str(video_file))
    assert isinstance(adapter, LocalFileAdapter)

    # Test unsupported URL (should still use YtDlpAdapter as fallback for any URL)
    adapter = registry.get_adapter("https://example.com/not_video.txt")
    assert isinstance(adapter, YtDlpAdapter)


def test_registry_get_adapter_unsupported():
    """Test IngestRegistry with unsupported input."""
    registry = IngestRegistry()
    
    # Test empty string
    with pytest.raises(ValueError, match="No ingest adapter found for source:"):
        registry.get_adapter("")
    
    # Test None
    with pytest.raises(ValueError, match="No ingest adapter found for source:"):
        registry.get_adapter(None)