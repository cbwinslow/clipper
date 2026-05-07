"""VAClip main pipeline orchestrator.

Coordinates all pipeline stages: ingest, transcription, scoring, and export.
Supports checkpoint/resume and dry-run mode.

Agent Instructions:
    - Implement VAClipPipeline.run() by calling each stage in order
    - Check for existing artifacts before running each stage (resume support)
    - Use settings.artifacts.overwrite to decide whether to re-run stages
    - Emit pipeline events via on_stage_start/on_stage_complete hooks
    - Log stage timing for benchmarking
    - See docs/agents/ingest_agent.md etc. for each stage's contract
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Callable, TYPE_CHECKING

from vaclip.logging.setup import get_logger
from vaclip.utils.exceptions import VaClipError

if TYPE_CHECKING:
    from vaclip.config.settings import Settings
    from vaclip.models.media import ExportedClip, MediaAsset, ScoredSegment, Transcript

log = get_logger(__name__)


class PipelineStage(Enum):
    """Enumeration of all pipeline stages in execution order."""

    INGEST = auto()
    TRANSCRIPTION = auto()
    SCORING = auto()
    EXPORT = auto()


@dataclass
class PipelineResult:
    """Container for all outputs produced by a pipeline run.

    Attributes:
        media: The ingested MediaAsset.
        transcript: The transcription output.
        scored_segments: Ranked list of ScoredSegments.
        clips: List of exported clip files.
        elapsed_seconds: Wall-clock time for each stage.
        completed_stages: Set of stages that ran successfully.
    """

    media: "MediaAsset | None" = None
    transcript: "Transcript | None" = None
    scored_segments: "list[ScoredSegment]" = field(default_factory=list)
    clips: "list[ExportedClip]" = field(default_factory=list)
    elapsed_seconds: dict[str, float] = field(default_factory=dict)
    completed_stages: set[PipelineStage] = field(default_factory=set)


# Type alias for stage event callbacks
StageCallback = Callable[[PipelineStage, PipelineResult], None]


class VAClipPipeline:
    """Main pipeline orchestrator for VAClip.

    Chains the ingest, transcription, scoring, and export stages together.
    Supports checkpoint resumption (skip stages already completed) and
    dry-run mode (plan but do not execute).

    Event Hooks:
        on_stage_start: Called before each stage begins.
        on_stage_complete: Called after each stage completes successfully.
        on_stage_error: Called if a stage raises an exception.

    Example::

        pipeline = VAClipPipeline(settings)
        result = pipeline.run(
            source="https://youtube.com/watch?v=...",
            profile="podcast",
            framing="vertical",
        )
        print(f"Exported {len(result.clips)} clips")
    """

    def __init__(
        self,
        settings: "Settings | None" = None,
        on_stage_start: StageCallback | None = None,
        on_stage_complete: StageCallback | None = None,
        on_stage_error: StageCallback | None = None,
    ) -> None:
        """Initialize the pipeline.

        Args:
            settings: Configuration settings. Loads from YAML if None.
            on_stage_start: Optional callback fired before each stage.
            on_stage_complete: Optional callback fired after each stage.
            on_stage_error: Optional callback fired on stage failure.
        """
        if settings is None:
            from vaclip.config.settings import get_settings
            settings = get_settings()
        self.settings = settings
        self.on_stage_start: StageCallback = on_stage_start or (lambda s, r: None)
        self.on_stage_complete: StageCallback = on_stage_complete or (lambda s, r: None)
        self.on_stage_error: StageCallback = on_stage_error or (lambda s, r: None)

    def run(
        self,
        source: str,
        profile: str | None = None,
        framing: str | None = None,
        from_stage: PipelineStage = PipelineStage.INGEST,
        dry_run: bool = False,
        max_clips: int = 10,
    ) -> PipelineResult:
        """Execute the full pipeline from ingest to export.

        Args:
            source: URL or local path to the media source.
            profile: Scoring profile name. Uses settings default if None.
            framing: Export framing strategy. Uses settings default if None.
            from_stage: Resume from this stage (skip earlier stages).
            dry_run: If True, log planned actions but do not execute.
            max_clips: Maximum number of clips to export.

        Returns:
            PipelineResult containing all stage outputs.

        Raises:
            VaClipError: If any non-recoverable pipeline error occurs.
        """
        result = PipelineResult()
        _profile = profile or self.settings.scoring.default_profile
        _framing = framing or self.settings.export.default_framing

        log.info(
            "pipeline.start",
            source=source,
            profile=_profile,
            framing=_framing,
            from_stage=from_stage.name,
            dry_run=dry_run,
        )

        if dry_run:
            log.info("pipeline.dry_run", note="Planning mode - no files will be created")
            self._log_plan(source, _profile, _framing, from_stage, max_clips)
            return result

        # TODO: implement stage execution
        # Stage 1: Ingest
        # if from_stage.value <= PipelineStage.INGEST.value:
        #     result = self._run_stage(PipelineStage.INGEST, result, lambda: self._ingest(source, _profile))
        #
        # Stage 2: Transcription
        # if from_stage.value <= PipelineStage.TRANSCRIPTION.value:
        #     result = self._run_stage(PipelineStage.TRANSCRIPTION, result,
        #         lambda: self._transcribe(result.media))
        #
        # Stage 3: Scoring
        # if from_stage.value <= PipelineStage.SCORING.value:
        #     result = self._run_stage(PipelineStage.SCORING, result,
        #         lambda: self._score(result.media, result.transcript, _profile))
        #
        # Stage 4: Export
        # if from_stage.value <= PipelineStage.EXPORT.value:
        #     result = self._run_stage(PipelineStage.EXPORT, result,
        #         lambda: self._export(result.media, result.scored_segments, _framing, max_clips))

        raise NotImplementedError("VAClipPipeline.run() not yet implemented")

    def _run_stage(
        self,
        stage: PipelineStage,
        result: PipelineResult,
        fn: Callable[[], None],
    ) -> PipelineResult:
        """Execute a single pipeline stage with timing and event hooks.

        Args:
            stage: The stage being executed.
            result: Current pipeline result (mutated in place).
            fn: Callable that executes the stage logic.

        Returns:
            Updated PipelineResult.
        """
        self.on_stage_start(stage, result)
        log.info("pipeline.stage_start", stage=stage.name)
        t0 = time.perf_counter()
        try:
            fn()
            elapsed = time.perf_counter() - t0
            result.elapsed_seconds[stage.name] = elapsed
            result.completed_stages.add(stage)
            log.info("pipeline.stage_complete", stage=stage.name, elapsed_s=round(elapsed, 2))
            self.on_stage_complete(stage, result)
        except Exception as exc:
            elapsed = time.perf_counter() - t0
            log.error("pipeline.stage_failed", stage=stage.name, elapsed_s=round(elapsed, 2), error=str(exc))
            self.on_stage_error(stage, result)
            raise
        return result

    def _ingest(self, source: str, profile: str) -> "MediaAsset":
        """Run the ingest stage.

        Args:
            source: URL or local path.
            profile: Content profile.

        Returns:
            Ingested MediaAsset.
        """
        # TODO: select adapter based on source type (URL vs local path)
        # from vaclip.ingest.ytdlp_adapter import YtDlpAdapter
        # from vaclip.ingest.local_adapter import LocalFileAdapter
        # adapter = YtDlpAdapter() if source.startswith("http") else LocalFileAdapter()
        # return adapter.ingest(source, profile=profile)
        raise NotImplementedError()

    def _transcribe(self, media: "MediaAsset") -> "Transcript":
        """Run the transcription stage.

        Args:
            media: Ingested MediaAsset with audio_path set.

        Returns:
            Word-level Transcript.
        """
        # TODO: get backend and transcribe
        # from vaclip.transcription.whisper_backend import get_transcription_backend
        # backend = get_transcription_backend(self.settings)
        # return backend.transcribe(media.audio_path, str(media.id))
        raise NotImplementedError()

    def _score(
        self,
        media: "MediaAsset",
        transcript: "Transcript",
        profile: str,
    ) -> "list[ScoredSegment]":
        """Run the scoring stage.

        Args:
            media: MediaAsset for audio/video paths.
            transcript: Transcript for segment text.
            profile: Scoring profile name.

        Returns:
            Ranked list of ScoredSegments.
        """
        # TODO: build segments from transcript and score
        # from vaclip.scoring.highlight_scorer import CompositeScorer, get_profile
        # scorer = CompositeScorer(profile=get_profile(profile))
        # segments = self._build_segments(transcript)
        # return scorer.score_all(segments, transcript, media)
        raise NotImplementedError()

    def _export(
        self,
        media: "MediaAsset",
        segments: "list[ScoredSegment]",
        framing: str,
        max_clips: int,
    ) -> "list[ExportedClip]":
        """Run the export stage.

        Args:
            media: Source MediaAsset.
            segments: Ranked scored segments.
            framing: Export framing strategy.
            max_clips: Maximum clips to produce.

        Returns:
            List of ExportedClip objects.
        """
        # TODO: run clip exporter
        # from vaclip.export.clip_exporter import ClipExporter
        # exporter = ClipExporter(output_dir=self.settings.paths.output_dir)
        # return exporter.export(media, segments, framing=framing, max_clips=max_clips)
        raise NotImplementedError()

    def _log_plan(
        self,
        source: str,
        profile: str,
        framing: str,
        from_stage: PipelineStage,
        max_clips: int,
    ) -> None:
        """Log the planned pipeline actions without executing them."""
        log.info("pipeline.plan", source=source, profile=profile, framing=framing,
                 from_stage=from_stage.name, max_clips=max_clips)
        for stage in PipelineStage:
            if stage.value >= from_stage.value:
                log.info("pipeline.plan.stage", stage=stage.name, status="would_run")
            else:
                log.info("pipeline.plan.stage", stage=stage.name, status="skipped")
