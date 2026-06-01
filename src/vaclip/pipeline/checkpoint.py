"""Checkpoint saving and loading for pipeline stages."""

from pathlib import Path

import orjson

from vaclip.config.settings import get_settings
from vaclip.models.pipeline import PipelineStage


class Checkpoint:
    """Manages checkpoint data for pipeline stage completion."""

    def __init__(self, completed_stages: set[PipelineStage] = None):
        self.completed_stages = completed_stages or set()

    def add_stage(self, stage: PipelineStage) -> None:
        """Mark a stage as completed."""
        self.completed_stages.add(stage)

    def is_stage_completed(self, stage: PipelineStage) -> bool:
        """Check if a stage has been completed."""
        return stage in self.completed_stages

    def to_dict(self) -> dict:
        """Convert checkpoint to dictionary for serialization."""
        return {
            "completed_stages": [stage.value for stage in self.completed_stages]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Checkpoint":
        """Create checkpoint from dictionary."""
        completed_stages = {
            PipelineStage(stage) for stage in data.get("completed_stages", [])
        }
        return cls(completed_stages=completed_stages)


def get_checkpoint_path() -> Path:
    """Get the path to the checkpoint file."""
    settings = get_settings()
    return settings.paths.cache_dir / "pipeline_checkpoint.json"


def save_checkpoint(checkpoint: Checkpoint) -> None:
    """Save checkpoint to disk."""
    checkpoint_path = get_checkpoint_path()
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    data = orjson.dumps(checkpoint.to_dict(), option=orjson.OPT_INDENT_2)
    checkpoint_path.write_bytes(data)


def load_checkpoint() -> Checkpoint:
    """Load checkpoint from disk, returning empty checkpoint if file doesn't exist."""
    checkpoint_path = get_checkpoint_path()
    if not checkpoint_path.exists():
        return Checkpoint()

    try:
        data = checkpoint_path.read_bytes()
        checkpoint_dict = orjson.loads(data)
        return Checkpoint.from_dict(checkpoint_dict)
    except Exception:
        # If checkpoint is corrupted, return empty checkpoint
        return Checkpoint()
