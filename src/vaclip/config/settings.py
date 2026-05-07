"""VAClip configuration settings.

This module defines the hierarchical settings dataclass tree that maps
directly to configs/app.yaml. All settings are strongly typed and
validated at startup.

Agent Instructions:
    - Add new settings as dataclass fields with type hints and defaults
    - Keep settings grouped by layer (transcription, scoring, export, etc.)
    - Never hardcode paths - always use settings.paths.*
    - Load via Settings.from_yaml(path) or Settings.from_env()
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class PathSettings:
    """Filesystem path configuration for all VAClip directories."""

    input_dir: Path = Path("input")
    output_dir: Path = Path("output")
    cache_dir: Path = Path("cache")
    models_dir: Path = Path("models")
    logs_dir: Path = Path("logs")
    transcripts_dir: Path = Path("cache/transcripts")
    scores_dir: Path = Path("cache/scores")

    def ensure_all(self) -> None:
        """Create all configured directories if they do not exist."""
        for _name, value in self.__dict__.items():
            if isinstance(value, Path):
                value.mkdir(parents=True, exist_ok=True)


@dataclass
class TranscriptionSettings:
    """Settings for the Whisper transcription backend."""

    model_name: str = "large-v3"
    device: str = "cuda"          # "cuda" or "cpu" - auto-detected if not set
    compute_type: str = "float16"  # "float16" for CUDA, "int8" for CPU
    language: str | None = None    # None = auto-detect
    word_timestamps: bool = True
    vad_filter: bool = True        # voice activity detection to skip silence
    beam_size: int = 5             # higher = more accurate, slower
    best_of: int = 5


@dataclass
class ScoringSettings:
    """Settings for the multi-signal highlight scoring engine."""

    default_profile: str = "podcast"
    top_n: int = 10
    min_segment_duration: float = 5.0   # seconds
    max_segment_duration: float = 60.0  # seconds

    # Default weights (overridden by profile)
    transcript_weight: float = 0.5
    audio_weight: float = 0.3
    visual_weight: float = 0.2

    # LLM reranking (disabled by default)
    use_llm_reranker: bool = False
    llm_model: str = "openai/gpt-4o-mini"  # via OpenRouter
    llm_top_n_candidates: int = 20         # send top N to LLM for reranking


@dataclass
class ExportSettings:
    """Settings for clip rendering and export."""

    default_framing: str = "wide"         # "wide", "vertical", "square"
    max_clip_duration: float = 60.0       # seconds - enforced for Shorts
    video_codec: str = "libx264"
    video_preset: str = "slow"            # quality-first
    video_crf: int = 18                   # 0=lossless, 51=worst; 18=high quality
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    container: str = "mp4"
    # Framing dimensions
    wide_width: int = 1920
    wide_height: int = 1080
    vertical_width: int = 1080
    vertical_height: int = 1920
    square_size: int = 1080


@dataclass
class ArtifactSettings:
    """Controls for intermediate artifact preservation."""

    keep_audio_wav: bool = True       # keep extracted audio after transcription
    keep_transcripts: bool = True     # keep transcript JSON files
    keep_scores: bool = True          # keep scoring JSON files
    keep_source_video: bool = True    # never delete downloaded video
    overwrite: bool = False           # overwrite existing artifacts


@dataclass
class LoggingSettings:
    """Logging configuration."""

    level: str = "INFO"               # DEBUG, INFO, WARNING, ERROR
    format: str = "console"           # "console" or "json"
    log_file: Path | None = Path("logs/vaclip.log")
    rotation: str = "10 MB"
    retention: str = "7 days"


@dataclass
class Settings:
    """Root settings object. Load from YAML or environment variables."""

    paths: PathSettings = field(default_factory=PathSettings)
    transcription: TranscriptionSettings = field(default_factory=TranscriptionSettings)
    scoring: ScoringSettings = field(default_factory=ScoringSettings)
    export: ExportSettings = field(default_factory=ExportSettings)
    artifacts: ArtifactSettings = field(default_factory=ArtifactSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)

    @classmethod
    def from_yaml(cls, path: Path = Path("configs/app.yaml")) -> "Settings":
        """Load settings from a YAML file, merging with defaults."""
        # TODO: implement YAML loading and merge with dataclass defaults
        # Use dacite or manual dict-to-dataclass conversion
        if not path.exists():
            return cls()
        with open(path) as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
        return cls._from_dict(data)

    @classmethod
    def from_env(cls) -> "Settings":
        """Override settings from environment variables.

        Environment variable format: VACLIP__SECTION__KEY
        Example: VACLIP__TRANSCRIPTION__MODEL_NAME=base
        """
        # TODO: implement env var override logic
        settings = cls.from_yaml()
        return settings

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> "Settings":
        """Construct Settings from a nested dictionary (e.g., from YAML)."""
        # TODO: implement recursive dataclass construction from dict
        # Consider using dacite library for nested dataclass hydration
        return cls()

    def validate(self) -> None:
        """Run post-load validation checks.

        Raises:
            ValueError: if any required setting is invalid
        """
        # TODO: validate device is "cuda" or "cpu"
        # TODO: validate crf is 0-51
        # TODO: validate weight sum is approximately 1.0
        # TODO: warn if cuda requested but not available
        pass


# Module-level singleton - initialized lazily
_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the global Settings singleton, loading from YAML on first call."""
    global _settings  # noqa: PLW0603
    if _settings is None:
        _settings = Settings.from_env()
        _settings.validate()
    return _settings


def reset_settings() -> None:
    """Reset the settings singleton (primarily for testing)."""
    global _settings  # noqa: PLW0603
    _settings = None
