# VAClip - Project Roadmap

## Vision

VAClip will become a fully autonomous, local-first highlight extraction engine
that requires zero manual effort to produce platform-ready short clips from
long-form video or audio content.

---

## Phase 0 - Foundation (Current)

**Goal:** Establish repo structure, tooling, contracts, and documentation.

### Milestones
- [x] Repo scaffold with all directories
- [x] Pydantic data models (`MediaAsset`, `Transcript`, `ScoredSegment`)
- [x] Abstract base classes for all layers
- [x] Typer CLI skeleton with subcommand stubs
- [x] structlog logging setup
- [x] Custom exception hierarchy
- [x] Project docs (project_summary, architecture, rules, tasks, roadmap)
- [x] Agent handoff docs
- [x] configs/app.yaml
- [x] pyproject.toml with all dependencies declared
- [ ] tests/conftest.py with shared fixtures

---

## Phase 1 - Ingest (VACLIP-001 to VACLIP-004)

**Goal:** Download and normalize media from all supported sources.

### Tasks
- [ ] VACLIP-001: Implement `YtDlpAdapter` for YouTube/Rumble/Kick/Twitch
- [ ] VACLIP-002: Implement `LocalFileAdapter` for local video/audio files
- [ ] VACLIP-003: Audio extraction from video using FFmpeg
- [ ] VACLIP-004: `MediaAsset` serialization and caching

### Success Criteria
- `vaclip ingest <url>` downloads video and saves `MediaAsset` JSON
- `vaclip ingest --local <path>` validates and copies local file
- Audio track extracted to `cache/<id>/audio.wav`
- All metadata (duration, resolution, fps, codec) captured

---

## Phase 2 - Transcription (VACLIP-005 to VACLIP-007)

**Goal:** Produce accurate word-level transcripts with GPU acceleration.

### Tasks
- [ ] VACLIP-005: Implement `WhisperBackend` with faster-whisper + CUDA
- [ ] VACLIP-006: Implement `WhisperCPUBackend` as fallback
- [ ] VACLIP-007: Segment audio into speaker turns (pyannote or silero-vad)

### Success Criteria
- Transcription runs on RTX 3060 using CUDA
- Word-level timestamps accurate to <100ms
- `Transcript` JSON saved to `cache/transcripts/<id>.json`
- CPU fallback works when GPU unavailable

---

## Phase 3 - Scoring (VACLIP-008 to VACLIP-012)

**Goal:** Identify highlight-worthy segments using multi-signal analysis.

### Tasks
- [ ] VACLIP-008: Implement `TranscriptScorer` (keywords, sentiment, reactions)
- [ ] VACLIP-009: Implement `AudioEnergyScorer` (RMS, volume spikes, silence)
- [ ] VACLIP-010: Implement `VisualMotionScorer` (optical flow, scene change)
- [ ] VACLIP-011: Implement `CompositeScorer` with configurable weights
- [ ] VACLIP-012: Profile-based scoring presets (podcast, gaming, sports)

### Success Criteria
- Each scorer produces normalized 0.0-1.0 scores per segment
- `ScoredSegment` JSON saved to `cache/scores/<id>.json`
- Profile `podcast` emphasizes TranscriptScorer
- Profile `gaming` emphasizes AudioEnergy + VisualMotion

---

## Phase 4 - Export (VACLIP-013 to VACLIP-016)

**Goal:** Render final clips in platform-optimized formats.

### Tasks
- [ ] VACLIP-013: Implement `ClipExporter` using FFmpeg subprocess
- [ ] VACLIP-014: Implement `WideFramingStrategy` (16:9)
- [ ] VACLIP-015: Implement `VerticalFramingStrategy` (9:16 for Shorts)
- [ ] VACLIP-016: Implement `SquareFramingStrategy` (1:1 for Instagram)

### Success Criteria
- Clips exported under 60 seconds for Shorts profile
- Aspect ratio applied correctly per framing strategy
- Output files named `<id>_<rank>_<profile>.<ext>`
- All source artifacts preserved; nothing deleted

---

## Phase 5 - Pipeline Integration (VACLIP-017 to VACLIP-019)

**Goal:** Wire all layers into a single end-to-end pipeline.

### Tasks
- [ ] VACLIP-017: Implement `VAClipPipeline.run()` orchestrator
- [ ] VACLIP-018: Add checkpoint/resume logic (`--from-stage`)
- [ ] VACLIP-019: Add `--dry-run` mode that logs planned actions without executing

### Success Criteria
- `vaclip run <url> --profile podcast --framing vertical` produces clips end-to-end
- Interrupted pipeline can resume from last completed stage
- `--dry-run` prints plan without downloading or processing

---

## Phase 6 - Quality & Testing (VACLIP-020 to VACLIP-023)

**Goal:** Achieve 70%+ test coverage and validate output quality.

### Tasks
- [ ] VACLIP-020: Unit tests for all scorers
- [ ] VACLIP-021: Integration tests with sample media files
- [ ] VACLIP-022: Benchmarks for transcription speed (RTX 3060 vs CPU)
- [ ] VACLIP-023: Manual QA checklist for clip quality review

### Success Criteria
- `pytest tests/unit/` passes in < 30 seconds
- Coverage >= 70% for `src/vaclip/`
- Benchmark results documented in `docs/benchmarks.md`

---

## Phase 7 - Optional Enhancements (VACLIP-024+)

**Goal:** Add power features once core pipeline is stable.

### Candidates
- [ ] VACLIP-024: OpenRouter LLM reranker for top-N candidates
- [ ] VACLIP-025: Subtitle/caption burning onto clips
- [ ] VACLIP-026: RSS/podcast feed auto-monitor
- [ ] VACLIP-027: Batch processing mode (process entire channel)
- [ ] VACLIP-028: Web dashboard (FastAPI + minimal frontend)
- [ ] VACLIP-029: Webhook notifications when clips are ready
- [ ] VACLIP-030: Auto-upload to YouTube Shorts / TikTok via API

---

## Release Targets

| Version | Phases | Status |
|---------|--------|--------|
| v0.1.0 | 0 | In Progress |
| v0.2.0 | 0-1 | Planned |
| v0.3.0 | 0-2 | Planned |
| v0.4.0 | 0-3 | Planned |
| v0.5.0 | 0-4 | Planned |
| v1.0.0 | 0-5 | Planned |
| v1.x | 6-7 | Future |
