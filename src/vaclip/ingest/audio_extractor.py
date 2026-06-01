"""Audio extraction utility for VAClip.

Provides a reusable function to extract audio from video files using FFmpeg.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from vaclip.utils.exceptions import VaClipIngestError as IngestError


def extract_audio(
    video_path: Path,
    asset_id: str,
    cache_dir: Path,
    sample_rate: int = 16000,
    channels: int = 1,
) -> Path:
    """Extract audio track from video as WAV using FFmpeg.

    Args:
        video_path: Path to the video file.
        asset_id: Unique ID used to name the output WAV file.
        cache_dir: Directory where the output WAV will be stored.
        sample_rate: Audio sample rate in Hz (default: 16000 for Whisper).
        channels: Number of audio channels (default: 1 for mono).

    Returns:
        Path to the extracted WAV file.

    Raises:
        IngestError: If FFmpeg fails to extract audio.
    """
    audio_path = cache_dir / "audio" / f"{asset_id}.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",                        # no video
        "-acodec", "pcm_s16le",       # 16-bit PCM
        "-ar", str(sample_rate),
        "-ac", str(channels),
        str(audio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise IngestError(f"FFmpeg audio extraction failed: {result.stderr}")
    return audio_path
