"""Pytest configuration and shared fixtures for VAClip tests.

Agent Notes:
- Add shared fixtures here that are used across multiple test modules
- Use tmp_path fixture for temporary file I/O in tests
- Use monkeypatch for environment variable overrides
- Mark slow tests with @pytest.mark.slow
- Mark GPU tests with @pytest.mark.gpu
- Fixtures follow the arrange-act-assert pattern
"""

from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest

# ============================================================
# Custom pytest marks
# ============================================================

def pytest_configure(config: pytest.Config) -> None:
    """Register custom pytest marks."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with -m 'not slow')")
    config.addinivalue_line("markers", "gpu: marks tests that require CUDA GPU")
    config.addinivalue_line("markers", "integration: marks integration tests requiring real files")
    config.addinivalue_line("markers", "unit: marks pure unit tests")


# ============================================================
# Path fixtures
# ============================================================

@pytest.fixture
def fixture_dir() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_audio_path(fixture_dir: Path) -> Path:
    """Return path to a short sample audio WAV file for transcription tests.

    Agent Notes:
    - Create tests/fixtures/sample_audio.wav for transcription tests
    - Should be a short (< 10s) spoken English audio clip
    - Do NOT commit large media files; use synthetic or generated audio
    """
    return fixture_dir / "sample_audio.wav"


@pytest.fixture
def sample_video_path(fixture_dir: Path) -> Path:
    """Return path to a short sample video file for ingest tests.

    Agent Notes:
    - Create tests/fixtures/sample_video.mp4 for ingest/export tests
    - Should be a very short (< 30s) video clip
    """
    return fixture_dir / "sample_video.mp4"


# ============================================================
# Config fixtures
# ============================================================

@pytest.fixture
def default_config_path() -> Path:
    """Return path to the default app config YAML."""
    return Path("configs/app.yaml")


# ============================================================
# Run ID fixtures
# ============================================================

@pytest.fixture
def test_run_id() -> str:
    """Return a stable test run ID for artifact naming."""
    return "test_run_00000000"


# ============================================================
# Sample data fixtures
# ============================================================

@pytest.fixture
def sample_transcript_segments() -> list[dict]:
    """Return a minimal list of transcript segment dicts for scorer tests.

    Agent Notes:
    - Expand this fixture as scorer tests require more signal diversity
    - Include funny, insightful, and neutral segments for testing
    """
    return [
        {"id": 0, "text": "Welcome to the podcast everyone.", "start": 0.0, "end": 3.5},
        {"id": 1, "text": "Today we have an incredible guest.", "start": 3.5, "end": 6.0},
        {"id": 2, "text": "That is literally the funniest thing I have ever heard.", "start": 45.0, "end": 49.0},
        {"id": 3, "text": "Wait wait wait, say that again.", "start": 49.0, "end": 51.5},
        {"id": 4, "text": "The key insight here is that nobody had thought of this before.", "start": 120.0, "end": 125.0},
    ]
