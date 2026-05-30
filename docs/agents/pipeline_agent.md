# Pipeline Agent Handoff

## Agent Role

You are the **Pipeline Agent**. Your sole responsibility is implementing the
pipeline orchestration layer of VAClip: coordinating all stages (ingest,
transcription, segmentation, scoring, export) and managing checkpoint/resume
and dry-run functionality.

## Tasks to Implement

- VACLIP-010: `VAClipPipeline.run()` method - main pipeline execution
- VACLIP-011: Stage execution helpers (_ingest, _transcribe, _score, _export)
- VACLIP-012: Checkpoint/resume functionality (skip completed stages)
- VACLIP-013: Dry-run mode (plan but don't execute)
- VACLIP-014: Pipeline event hooks (on_stage_start/on_stage_complete/on_stage_error)
- VACLIP-015: Stage timing and performance benchmarking
- VACLIP-016: `PipelineResult` container for all stage outputs
- VACLIP-017: Error handling and propagation with proper context
- VACLIP-018: Pipeline configuration integration

## Files You Own

```
src/vaclip/pipeline/
    __init__.py          - export public symbols
    pipeline.py          - VAClipPipeline class (TODO: implement run() and helpers)
    base.py              - PipelineStage enum, PipelineResult dataclass (already scaffolded)
src/vaclip/models/media.py  - All media models used by pipeline (already scaffolded)
src/vaclip/config/settings.py  - Settings model (already scaffolded)
```

## Files You Must NOT Modify

- `src/vaclip/ingest/` - not your layer
- `src/vaclip/transcription/` - not your layer
- `src/vaclip/segmentation/` - not your layer
- `src/vaclip/scoring/` - not your layer
- `src/vaclip/export/` - not your layer
- `src/vaclip/models/base.py` - shared base contracts, discuss before changing

## Contracts

### Input

```python
# Pipeline initialization
settings: Settings  # Loaded from YAML or environment
source: str         # URL or local path to media file
profile: str        # Content profile name (from settings or override)
framing: str        # Export framing strategy (from settings or override)
from_stage: PipelineStage  # Resume point (INGEST, TRANSCRIPTION, SCORING, EXPORT)
dry_run: bool       # If True, only log planned actions
max_clips: int      # Maximum number of clips to export
```

### Output: PipelineResult

```python
@dataclass
class PipelineResult:
    media: "MediaAsset | None" = None              # From ingest stage
    transcript: "Transcript | None" = None         # From transcription stage
    scored_segments: "list[ScoredSegment]" = field(default_factory=list)  # From scoring
    clips: "list[ExportedClip]" = field(default_factory=list)  # From export
    elapsed_seconds: dict[str, float] = field(default_factory=dict)  # Wall-clock time per stage
    completed_stages: set[PipelineStage] = field(default_factory=set)  # Stages that ran successfully
```

## Implementation Guide

### VAClipPipeline Class Structure

```python
class VAClipPipeline:
    """Main pipeline orchestrator for VAClip.
    
    Chains the ingest, transcription, scoring, and export stages together.
    Supports checkpoint resumption (skip stages already completed) and
    dry-run mode (plan but do not execute).
    """
    
    def __init__(
        self,
        settings: "Settings | None" = None,
        on_stage_start: StageCallback | None = None,
        on_stage_complete: StageCallback | None = None,
        on_stage_error: StageCallback | None = None,
    ) -> None:
        """Initialize the pipeline with settings and optional callbacks."""
        # Load settings if not provided
        # Store callbacks for stage events
        pass
    
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
        
        This is the main entry point that coordinates all stages.
        """
        # 1. Determine effective profile and framing from settings/overrides
        # 2. Log pipeline start with parameters
        # 3. Handle dry_run mode (log plan, return empty result)
        # 4. Execute stages in order with checkpoint/resume logic:
        #    - INGEST: if from_stage <= INGEST
        #    - TRANSCRIPTION: if from_stage <= TRANSCRIPTION
        #    - SCORING: if from_stage <= SCORING
        #    - EXPORT: if from_stage <= EXPORT
        # 5. For each stage:
        #    - Call on_stage_start callback
        #    - Execute stage logic via helper method
        #    - Measure execution time
        #    - Update PipelineResult with stage outputs
        #    - Call on_stage_complete callback
        #    - Handle exceptions with on_stage_error callback
        # 6. Return populated PipelineResult
        pass
    
    # Stage helper methods - each calls the appropriate adapter/backend
    def _ingest(self, source: str, profile: str) -> "MediaAsset":
        """Run the ingest stage.
        
        Selects adapter based on source type (URL vs local path)
        and returns normalized MediaAsset.
        """
        # TODO: Implement adapter selection and execution
        pass
    
    def _transcribe(self, media: "MediaAsset") -> "Transcript":
        """Run the transcription stage.
        
        Gets backend from settings and transcribes media.audio_path.
        """
        # TODO: Implement transcription backend selection and execution
        pass
    
    def _score(
        self,
        media: "MediaAsset",
        transcript: "Transcript",
        profile: str,
    ) -> "list[ScoredSegment]":
        """Run the scoring stage.
        
        Builds segments from transcript and scores them using
        the segmentation layer.
        """
        # TODO: Implement segment building and scoring execution
        pass
    
    def _export(
        self,
        media: "MediaAsset",
        segments: "list[ScoredSegment]",
        framing: str,
        max_clips: int,
    ) -> "list[ExportedClip]":
        """Run the export stage.
        
        Uses clip exporter to render top segments to video files.
        """
        # TODO: Implement export execution
        pass
    
    def _run_stage(
        self,
        stage: PipelineStage,
        result: PipelineResult,
        fn: Callable[[], None],
    ) -> PipelineResult:
        """Execute a single pipeline stage with timing and event hooks.
        
        This is a helper method that handles:
        - Stage start callback
        - Execution timing
        - Error handling and error callback
        - Stage completion callback
        - Updating result with timing and completion status
        """
        # TODO: Implement stage execution wrapper with error handling
        pass
    
    def _log_plan(
        self,
        source: str,
        profile: str,
        framing: str,
        from_stage: PipelineStage,
        max_clips: int,
    ) -> None:
        """Log the planned pipeline actions without executing them."""
        # TODO: Implement dry-run planning logging
        pass
```

### Stage Execution Details

#### Ingest Stage Helper
```python
def _ingest(self, source: str, profile: str) -> "MediaAsset":
    # Determine if source is URL or local path
    if source.startswith(("http://", "https://")):
        adapter = YtDlpAdapter()
    else:
        adapter = LocalFileAdapter()
    
    return adapter.ingest(source, profile=profile)
```

#### Transcription Stage Helper
```python
def _transcribe(self, media: "MediaAsset") -> "Transcript":
    from vaclip.transcription.whisper_backend import get_transcription_backend
    
    backend = get_transcription_backend(self.settings)
    return backend.transcribe(media.audio_path, str(media.id))
```

#### Scoring Stage Helper
```python
def _score(
    self,
    media: "MediaAsset",
    transcript: "Transcript",
    profile: str,
) -> "list[ScoredSegment]":
    from vaclip.segmentation.window_generator import WindowGenerator
    from vaclip.scoring.highlight_scorer import CompositeScorer, get_profile
    
    # 1. Generate windows from transcript
    window_generator = WindowGenerator(
        window_size=self.settings.segmentation.window_step,
        step_size=self.settings.segmentation.window_step
    )
    windows = window_generator.generate_windows(transcript)
    
    # 2. Convert windows to format expected by scorers
    # (This would be implemented based on scorer interfaces)
    
    # 3. Get scorer and score segments
    scorer = CompositeScorer(profile=get_profile(profile))
    # TODO: Call scorer with appropriate data
    
    return scored_segments
```

#### Export Stage Helper
```python
def _export(
    self,
    media: "MediaAsset",
    segments: "list[ScoredSegment]",
    framing: str,
    max_clips: int,
) -> "list[ExportedClip]":
    from vaclip.export.clip_exporter import ClipExporter
    
    exporter = ClipExporter(output_dir=self.settings.paths.output_dir)
    return exporter.export(
        media=media,
        segments=segments,
        framing=framing,
        max_clips=max_clips
    )
```

## Key Dependencies

All dependencies are inherited from the individual layers:
- Ingest: yt-dlp, ffmpeg-python
- Transcription: faster-whisper, torch
- Segmentation: sentence-transformers, torch
- Scoring: sentence-transformers, torch
- Export: ffmpeg-python

## Testing Requirements

- Unit tests: Test pipeline orchestration logic with mocked stages
- Integration tests: Test full pipeline with real small fixture files
- Test coverage: 80% target for pipeline module (higher due to orchestration complexity)
- Test scenarios:
  - Normal full pipeline execution
  - Checkpoint/resume from each stage
  - Dry-run mode
  - Error handling and propagation
  - Stage timing measurement

## Logging

```python
from vaclip.logging.setup import get_logger
log = get_logger(__name__)

# Pipeline level logging
log.info("pipeline.start", source=source, profile=profile, framing=framing)
log.info("pipeline.stage_start", stage=stage.name)
log.info("pipeline.stage_complete", stage=stage.name, elapsed_s=round(elapsed, 2))
log.info("pipeline.stage_failed", stage=stage.name, elapsed_s=round(elapsed, 2), error=str(exc))
log.info("pipeline.dry_run", note="Planning mode - no files will be created")
log.info("pipeline.plan", source=source, profile=profile, framing=framing, from_stage=from_stage.name, max_clips=max_clips)
```

## Error Handling

```python
from vaclip.utils.exceptions import VaClipError

# All stage exceptions should be caught in _run_stage and re-raised as VaClipError
# with additional context if needed
# Never swallow exceptions silently
# Always include original exception as __cause__ when re-raising
```

## Definition of Done

- [ ] `VAClipPipeline.run()` executes all four stages in order when from_stage=INGEST
- [ ] Checkpoint/resume works correctly from each stage (INGEST, TRANSCRIPTION, SCORING)
- [ ] Dry-run mode logs planned actions but doesn't execute any stages
- [ ] Pipeline event hooks are called at appropriate times
- [ ] Stage timing is accurately measured and stored in PipelineResult
- [ ] PipelineResult contains all expected outputs from executed stages
- [ ] Error handling properly propagates exceptions with context
- [ ] Settings are properly integrated and used throughout pipeline
- [ ] Unit tests pass with mocks for all stage dependencies
- [ ] Integration test marked and skipped in CI by default
- [ ] `ruff check src/vaclip/pipeline/` passes with 0 errors
- [ ] `mypy src/vaclip/pipeline/` passes in strict mode