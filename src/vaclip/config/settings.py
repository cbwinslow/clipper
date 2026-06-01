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
    def from_yaml(cls, path: Path = Path("configs/app.yaml")) -> Settings:
        """Load settings from a YAML file, merging with defaults."""
        if not path.exists():
            return cls()
        with open(path) as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
        return cls._from_dict(data)

    @classmethod
    def from_env(cls) -> Settings:
        """Override settings from environment variables.

        Environment variable format: VACLIP__SECTION__KEY
        Example: VACLIP__TRANSCRIPTION__MODEL_NAME=base
        """
        settings = cls.from_yaml()
        settings = cls._apply_env_overrides(settings)
        return settings

    @classmethod
    def _apply_env_overrides(cls, settings: Settings) -> Settings:
        """Apply environment variable overrides to settings."""
        prefix = "VACLIP__"
        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue
            path = key[len(prefix):].lower().split("__")
            if len(path) != 2:
                continue

            section, field = path
            value = cls._convert_env_value(value)

            if section == "paths":
                if hasattr(settings.paths, field):
                    setattr(settings.paths, field, Path(value) if field.endswith("_dir") else value)
            elif section == "transcription":
                if hasattr(settings.transcription, field):
                    setattr(settings.transcription, field, value)
            elif section == "scoring":
                if hasattr(settings.scoring, field):
                    setattr(settings.scoring, field, value)
            elif section == "export":
                if hasattr(settings.export, field):
                    setattr(settings.export, field, value)
            elif section == "artifacts":
                if hasattr(settings.artifacts, field):
                    setattr(settings.artifacts, field, value)
            elif section == "logging":
                if hasattr(settings.logging, field):
                    setattr(settings.logging, field, value)

        return settings

    @staticmethod
    def _convert_env_value(value: str) -> Any:
        """Convert environment variable string to appropriate type."""
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            pass
        return value

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> Settings:
        """Construct Settings from a nested dictionary (e.g., from YAML)."""
        settings = cls()

        if "paths" in data:
            for key, value in data["paths"].items():
                if hasattr(settings.paths, key):
                    setattr(settings.paths, key, Path(value) if isinstance(value, str) else value)

        if "transcription" in data:
            for key, value in data["transcription"].items():
                if hasattr(settings.transcription, key):
                    setattr(settings.transcription, key, value)

        if "scoring" in data:
            for key, value in data["scoring"].items():
                if hasattr(settings.scoring, key):
                    setattr(settings.scoring, key, value)

        if "export" in data:
            for key, value in data["export"].items():
                if hasattr(settings.export, key):
                    setattr(settings.export, key, value)

        if "artifacts" in data:
            for key, value in data["artifacts"].items():
                if hasattr(settings.artifacts, key):
                    setattr(settings.artifacts, key, value)

        if "logging" in data:
            for key, value in data["logging"].items():
                if hasattr(settings.logging, key):
                    path_value = Path(value) if key == "log_file" and value else value
                    setattr(settings.logging, key, path_value)

        return settings

    def validate(self) -> None:
        """Run post-load validation checks.

        Raises:
            ValueError: if any required setting is invalid
        """
        if self.transcription.device not in ("cuda", "cpu"):
            raise ValueError(
                f"Invalid device: {self.transcription.device}. Must be 'cuda' or 'cpu'."
            )

        if not 0 <= self.export.video_crf <= 51:
            raise ValueError(f"Invalid CRF value: {self.export.video_crf}. Must be 0-51.")

        weight_sum = (
            self.scoring.transcript_weight
            + self.scoring.audio_weight
            + self.scoring.visual_weight
        )
        if abs(weight_sum - 1.0) > 0.01:
            raise ValueError(f"Scoring weights must sum to 1.0, got {weight_sum}")

        try:
            import torch
            if self.transcription.device == "cuda" and not torch.cuda.is_available():
                import warnings
                warnings.warn(
                    "CUDA requested but not available. Falling back to CPU.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                self.transcription.device = "cpu"
                self.transcription.compute_type = "int8"
        except ImportError:
            pass


# Module-level singleton - initialized lazily
_settings: Settings | None = None


def load_settings(config_path: Path | None = None) -> Settings:
    """Load Settings, optionally overriding with a specific config file.

    Args:
        config_path: Path to a YAML config file. If None, defaults to the
            standard config location used by Settings.from_yaml().
    """
    if config_path is not None:
        return Settings.from_yaml(config_path)
    return Settings.from_env()


def get_settings() -> Settings:
    """Return the global Settings singleton, loading from YAML on first call."""
    global _settings  # noqa: PLW0603
    if _settings is None:
        _settings = load_settings()
        _settings.validate()
    return _settings


def reset_settings() -> None:
    """Reset the global settings singleton. Useful for testing."""
    global _settings  # noqa: PLW0603
    _settings = None
