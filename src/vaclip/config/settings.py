"""VAClip configuration settings."""
from __future__ import annotations

import dataclasses
import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class PathSettings:
    input_dir: Path = field(default_factory=lambda: Path("input"))
    output_dir: Path = field(default_factory=lambda: Path("output"))
    cache_dir: Path = field(default_factory=lambda: Path("cache"))
    models_dir: Path = field(default_factory=lambda: Path("models"))
    logs_dir: Path = field(default_factory=lambda: Path("logs"))
    transcripts_dir: Path = field(default_factory=lambda: Path("cache/transcripts"))
    scores_dir: Path = field(default_factory=lambda: Path("cache/scores"))
    audio_dir: Path = field(default_factory=lambda: Path("cache/audio"))

    def ensure_all(self) -> None:
        for val in self.__dict__.values():
            if isinstance(val, Path):
                val.mkdir(parents=True, exist_ok=True)


@dataclass
class TranscriptionSettings:
    model_name: str = "large-v3"
    device: str = "auto"
    compute_type: str = "float16"
    language: str | None = None
    word_timestamps: bool = True
    vad_filter: bool = True
    beam_size: int = 5
    best_of: int = 5


@dataclass
class ScoringSettings:
    default_profile: str = "podcast"
    top_n: int = 10
    min_segment_duration: float = 5.0
    max_segment_duration: float = 60.0
    transcript_weight: float = 0.5
    audio_weight: float = 0.3
    visual_weight: float = 0.2


@dataclass
class ExportSettings:
    default_framing: str = "wide"
    max_clip_duration: float = 60.0
    video_codec: str = "libx264"
    video_preset: str = "slow"
    video_crf: int = 18
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"
    container: str = "mp4"


@dataclass
class ArtifactSettings:
    keep_audio_wav: bool = True
    keep_transcripts: bool = True
    keep_scores: bool = True
    keep_source_video: bool = True
    overwrite: bool = False


@dataclass
class LoggingSettings:
    level: str = "INFO"
    format: str = "console"
    log_file: Path | None = field(default_factory=lambda: Path("logs/vaclip.log"))


@dataclass
class Settings:
    paths: PathSettings = field(default_factory=PathSettings)
    transcription: TranscriptionSettings = field(default_factory=TranscriptionSettings)
    scoring: ScoringSettings = field(default_factory=ScoringSettings)
    export: ExportSettings = field(default_factory=ExportSettings)
    artifacts: ArtifactSettings = field(default_factory=ArtifactSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)

    @classmethod
    def from_yaml(cls, path: Path = Path("configs/app.yaml")) -> "Settings":
        if not path.exists():
            return cls()
        with open(path) as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
        return cls._from_dict(data)

    @classmethod
    def from_env(cls) -> "Settings":
        settings = cls.from_yaml()
        prefix = "VACLIP__"
        for key, val in os.environ.items():
            if not key.startswith(prefix):
                continue
            parts = key[len(prefix):].lower().split("__", 1)
            if len(parts) != 2:
                continue
            section, attr = parts
            section_obj = getattr(settings, section, None)
            if section_obj is None or not hasattr(section_obj, attr):
                continue
            current = getattr(section_obj, attr)
            try:
                if isinstance(current, bool):
                    setattr(section_obj, attr, val.lower() in ("1", "true", "yes"))
                elif isinstance(current, int):
                    setattr(section_obj, attr, int(val))
                elif isinstance(current, float):
                    setattr(section_obj, attr, float(val))
                elif isinstance(current, Path) or current is None:
                    setattr(section_obj, attr, Path(val))
                else:
                    setattr(section_obj, attr, val)
            except (ValueError, TypeError):
                pass
        return settings

    @classmethod
    def _from_dict(cls, data: dict[str, Any]) -> "Settings":
        section_types = {
            "paths": PathSettings,
            "transcription": TranscriptionSettings,
            "scoring": ScoringSettings,
            "export": ExportSettings,
            "artifacts": ArtifactSettings,
            "logging": LoggingSettings,
        }

        def hydrate(dc_cls, d):
            if not dataclasses.is_dataclass(dc_cls) or not isinstance(d, dict):
                return d
            flds = {f.name: f for f in dataclasses.fields(dc_cls)}
            kwargs: dict[str, Any] = {}
            for name, fld in flds.items():
                if fld.default is not dataclasses.MISSING:
                    default = fld.default
                elif fld.default_factory is not dataclasses.MISSING:
                    default = fld.default_factory()
                else:
                    default = None
                raw = d.get(name, default)
                if isinstance(default, Path) and raw is not None:
                    kwargs[name] = Path(raw)
                else:
                    kwargs[name] = raw
            return dc_cls(**kwargs)

        kwargs: dict[str, Any] = {}
        for sec, sec_cls in section_types.items():
            kwargs[sec] = hydrate(sec_cls, data.get(sec, {}))
        return cls(**kwargs)

    def validate(self) -> None:
        valid_devices = ("cuda", "cpu", "auto")
        if self.transcription.device not in valid_devices:
            raise ValueError(f"transcription.device must be one of {valid_devices}")
        if not 0 <= self.export.video_crf <= 51:
            raise ValueError("export.video_crf must be 0-51")
        w = (
            self.scoring.transcript_weight
            + self.scoring.audio_weight
            + self.scoring.visual_weight
        )
        if not 0.90 <= w <= 1.10:
            warnings.warn(
                f"Scoring weights sum to {w:.2f}; expected ~1.0", stacklevel=2
            )
        if self.transcription.device == "cuda":
            try:
                import torch
                if not torch.cuda.is_available():
                    warnings.warn(
                        "CUDA requested but not available; falling back to CPU.",
                        stacklevel=2,
                    )
            except ImportError:
                warnings.warn(
                    "torch not installed; cannot verify CUDA.", stacklevel=2
                )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
        _settings.validate()
    return _settings


def load_settings(config_path: Path | None = None) -> Settings:
    s = Settings.from_yaml(config_path) if config_path else Settings.from_env()
    s.validate()
    return s


def reset_settings() -> None:
    global _settings
    _settings = None
