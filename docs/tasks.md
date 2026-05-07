# VAClip — Atomic Task Backlog

This document tracks all granular implementation tasks for the VAClip project.
Each task is self-contained and suitable for hand-off to an AI coding agent.

> **Legend**
> - `[ ]` Not started
> - `[~]` In progress / scaffold exists — agent must fill implementation
> - `[x]` Complete

---

## Phase 0 — Project Scaffolding

| ID | Status | File | Description |
|----|--------|------|-------------|
| S-01 | `[x]` | `pyproject.toml` | Project metadata, dependencies, scripts |
| S-02 | `[x]` | `AGENTS.md` | Root agent instructions |
| S-03 | `[x]` | `README.md` | Project overview |
| S-04 | `[x]` | `.env.example` | Environment variable template |
| S-05 | `[x]` | `.gitignore` | Git ignore rules |
| S-06 | `[x]` | `docs/rules.md` | Coding standards |
| S-07 | `[x]` | `docs/architecture.md` | System architecture |
| S-08 | `[x]` | `docs/roadmap.md` | Project milestones |
| S-09 | `[x]` | `docs/tasks.md` | This file |
| S-10 | `[x]` | `Makefile` | Developer workflow shortcuts |

---

## Phase 1 — Core Models & Config

| ID | Status | File | Description |
|----|--------|------|-------------|
| M-01 | `[x]` | `src/vaclip/models/schemas.py` | Full Pydantic v2 domain schemas |
| M-02 | `[x]` | `src/vaclip/models/base.py` | Shared base model helpers |
| M-03 | `[x]` | `src/vaclip/models/media.py` | SourceType, MediaMetadata, IngestResult |
| M-04 | `[x]` | `src/vaclip/config/settings.py` | Settings dataclass + YAML loader |
| M-05 | `[ ]` | `src/vaclip/config/logging.py` | structlog configuration with JSON/dev renderers |
| M-06 | `[ ]` | `src/vaclip/exceptions.py` | Custom exception hierarchy |

**Task M-05 — Logging config**
- Objective: Configure structlog for JSON output in production, coloured dev output locally
- Output: `configure_logging(level, json_logs)` function called at startup
- Requirements: Use `structlog.configure()`, support `LOG_LEVEL` env var, include timestamp + caller
- Agent hint: See structlog docs for `ProcessorFormatter` with rich console renderer

**Task M-06 — Exception hierarchy**
- Objective: Define typed exceptions for each failure mode
- Output: `VAClipError`, `IngestError`, `TranscriptionError`, `ScoringError`, `ExportError`
- Requirements: Each carries structured context (source, stage, cause)
- Agent hint: Inherit from `Exception` with `__init__(self, message, **context)` pattern

---

## Phase 2 — Ingest

| ID | Status | File | Description |
|----|--------|------|-------------|
| I-01 | `[~]` | `src/vaclip/ingest/ytdlp_adapter.py` | yt-dlp download + probe |
| I-02 | `[~]` | `src/vaclip/ingest/local_adapter.py` | Local file adapter with ffprobe |
| I-03 | `[ ]` | `src/vaclip/ingest/base.py` | Abstract BaseIngestAdapter |
| I-04 | `[ ]` | `src/vaclip/ingest/registry.py` | Auto-detect adapter from URL/path |
| I-05 | `[ ]` | `src/vaclip/ingest/audio_extractor.py` | Extract WAV audio track from video |

**Task I-01 — YtDlpAdapter (fill scaffold)**
- Objective: Implement `download()` and `probe()` using `yt_dlp.YoutubeDL`
- Inputs: `source_url: str`, `output_dir: Path`, `ydl_opts: dict`
- Outputs: `MediaMeta` with local_path, duration_sec, title, width, height, fps
- Requirements: Respect `settings.ingest.cookies_file`; log via structlog; raise `IngestError` on failure
- Agent hint: Use `YoutubeDL.extract_info(url, download=True)` then map info dict to `MediaMeta`

**Task I-02 — LocalFileAdapter (fill scaffold)**
- Objective: Implement `probe()` using `ffprobe` subprocess call
- Inputs: `file_path: Path`
- Outputs: `MediaMeta` from ffprobe JSON output
- Requirements: Parse `ffprobe -v quiet -print_format json -show_streams -show_format`; raise `IngestError` on missing file

**Task I-03 — BaseIngestAdapter**
- Objective: Abstract base class with `download()`, `probe()`, `supports(url)` methods
- Requirements: Use `abc.ABC` and `@abstractmethod`; include type hints and docstrings

**Task I-04 — Adapter Registry**
- Objective: `get_adapter(source: str, settings) -> BaseIngestAdapter` factory
- Logic: file path -> LocalFileAdapter; URL -> YtDlpAdapter

**Task I-05 — Audio Extractor**
- Objective: Extract mono 16kHz WAV from video using ffmpeg
- Requirements: Use subprocess, check returncode, log stderr

---

## Phase 3 — Transcription

| ID | Status | File | Description |
|----|--------|------|-------------|
| T-01 | `[~]` | `src/vaclip/transcription/whisper_backend.py` | faster-whisper GPU/CPU backend |
| T-02 | `[ ]` | `src/vaclip/transcription/base.py` | Abstract BaseTranscriber |
| T-03 | `[ ]` | `src/vaclip/transcription/diarizer.py` | Speaker diarization with pyannote |
| T-04 | `[ ]` | `src/vaclip/transcription/cache.py` | Transcript caching (JSON) |

**Task T-01 — WhisperBackend (fill scaffold)**
- Objective: Implement `transcribe(audio_path)` returning `Transcript`
- Requirements: Use `faster_whisper.WhisperModel`; auto-select CUDA if available; map word timestamps to `Word` models
- Agent hint: Iterate `model.transcribe()` generator; collect segments and words

**Task T-03 — Speaker Diarization**
- Objective: Assign speaker labels to Segment objects post-transcription
- Requirements: Use `pyannote.audio` Pipeline; map diarization windows to nearest segments

**Task T-04 — Transcript Cache**
- Objective: Save/load `Transcript` to disk to skip re-transcription
- Key: SHA-256 of audio file path + model name
- Format: JSON via `transcript.model_dump_json()`

---

## Phase 4 — Scoring

| ID | Status | File | Description |
|----|--------|------|-------------|
| SC-01 | `[~]` | `src/vaclip/scoring/highlight_scorer.py` | Multi-signal scorer with profiles |
| SC-02 | `[ ]` | `src/vaclip/scoring/signals/audio_energy.py` | RMS energy signal |
| SC-03 | `[ ]` | `src/vaclip/scoring/signals/sentiment.py` | Sentiment signal (transformers) |
| SC-04 | `[ ]` | `src/vaclip/scoring/signals/keyword.py` | Keyword density signal |
| SC-05 | `[ ]` | `src/vaclip/scoring/signals/laughter.py` | Laughter/audience detection |
| SC-06 | `[ ]` | `src/vaclip/scoring/profiles.py` | Profile weight configs |

**Task SC-01 — HighlightScorer (fill scaffold)**
- Objective: Implement `score(transcript, media_meta) -> list[ScoredSegment]`
- Requirements: Load signals per profile; compute SignalScore per segment; assign rank; filter by `min_segment_duration`

**Task SC-02 — AudioEnergySignal**
- Objective: Compute RMS energy per segment window from WAV file
- Requirements: Use `librosa.feature.rms()`; normalise min-max across all segments

**Task SC-03 — SentimentSignal**
- Objective: Run sentiment analysis on segment text
- Requirements: Use `transformers.pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")`

**Task SC-06 — Profiles**
- Example: `PODCAST = {"sentiment": 2.0, "keyword_density": 1.5, "audio_energy": 0.5}`

---

## Phase 5 — Export

| ID | Status | File | Description |
|----|--------|------|-------------|
| E-01 | `[~]` | `src/vaclip/export/clip_exporter.py` | FFmpeg clip renderer |
| E-02 | `[ ]` | `src/vaclip/export/framing.py` | Crop/pad framing strategies |
| E-03 | `[ ]` | `src/vaclip/export/subtitle.py` | Burn-in subtitle generator |
| E-04 | `[ ]` | `src/vaclip/export/manifest.py` | Export manifest JSON writer |

**Task E-01 — ClipExporter (fill scaffold)**
- Objective: Implement `export(media, segments, framing, max_clips) -> list[ExportedClip]`
- Requirements: Call ffmpeg with `-ss`, `-to`, `-vf` crop filter; log each clip; raise `ExportError` on failure

**Task E-02 — Framing Strategies**
- WIDE: passthrough | VERTICAL: `crop=ih*9/16:ih,scale=1080:1920` | SQUARE: `crop=ih:ih,scale=1080:1080`

---

## Phase 6 — Pipeline Integration

| ID | Status | File | Description |
|----|--------|------|-------------|
| P-01 | `[~]` | `src/vaclip/pipeline/pipeline.py` | Main orchestrator |
| P-02 | `[ ]` | `src/vaclip/pipeline/checkpoint.py` | Stage checkpoint save/load |

**Task P-01 — VAClipPipeline.run() (fill scaffold)**
- Objective: Wire ingest -> extract audio -> transcribe -> score -> export
- Requirements: Honour `from_stage` to resume; call stage hooks; persist checkpoints; catch and re-raise as typed errors

---

## Phase 7 — CLI & UX

| ID | Status | File | Description |
|----|--------|------|-------------|
| C-01 | `[~]` | `src/vaclip/cli/commands.py` | Typer CLI commands |
| C-02 | `[ ]` | `src/vaclip/cli/progress.py` | Rich progress bar helpers |
| C-03 | `[ ]` | `src/vaclip/cli/output.py` | Rich table/panel output formatters |

**Task C-01 — Wire CLI to Pipeline**
- Objective: Replace `NotImplementedError` stubs in `cmd_run` and `cmd_plan`
- Requirements: Instantiate `VAClipPipeline`; call `run()` or `run(dry_run=True)`; handle errors with rich panel + exit(1)

---

## Phase 8 — Testing

| ID | Status | File | Description |
|----|--------|------|-------------|
| TS-01 | `[x]` | `tests/unit/test_models.py` | Domain schema unit tests |
| TS-02 | `[x]` | `tests/unit/test_scoring.py` | Scoring unit tests |
| TS-03 | `[ ]` | `tests/unit/test_config.py` | Settings loader tests |
| TS-04 | `[ ]` | `tests/integration/test_ingest.py` | Ingest adapter integration tests |
| TS-05 | `[ ]` | `tests/integration/test_pipeline.py` | End-to-end pipeline smoke test |
| TS-06 | `[ ]` | `tests/conftest.py` | Shared pytest fixtures |

---

## Conventions

- Tasks labelled `[~]` have a scaffold with `# TODO` comments and `NotImplementedError` - agent must implement each TODO.
- All new functions must have docstrings, type hints, and structlog calls.
- All external I/O must be wrapped in try/except raising the appropriate typed error.
- Tests must be added or updated alongside every implementation task.
