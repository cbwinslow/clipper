# VAClip - Atomic Task Breakdown

All tasks are atomic, handoff-friendly, and follow the agent task template.
Each task has: ID, phase, objective, inputs, outputs, acceptance criteria.

## Task Template
```
Task ID: VACLIP-XXX
Phase: 0-5
Title: Short imperative title
Objective: One sentence description
Inputs: What files/data/state are required
Outputs: What files/data/state are produced
Acceptance Criteria:
  - [ ] Specific testable criteria
Dependencies: Other task IDs
Agent: Which agent role handles this
```

---

## Phase 0 - Foundation

### VACLIP-001: Project scaffold and environment
**Objective:** Set up Python project with venv, pyproject.toml, and verify GPU access.
**Inputs:** Empty repo
**Outputs:** Installable `vaclip` package, passing smoke tests
**Acceptance Criteria:**
- [ ] `pip install -e .` succeeds
- [ ] `vaclip --version` returns version string
- [ ] `import torch; torch.cuda.is_available()` returns True
- [ ] `ffmpeg -version` runs without error
**Agent:** setup_agent

### VACLIP-002: Logging and config loading
**Objective:** Implement structlog setup and YAML config loader with Pydantic validation.
**Inputs:** `configs/app.yaml`, `src/vaclip/logging/setup.py`
**Outputs:** Working `get_logger()`, working config load
**Acceptance Criteria:**
- [ ] `configure_logging(verbose=True)` produces colored output
- [ ] Config loads from `configs/app.yaml` without error
- [ ] Invalid config raises `VaClipConfigError`
**Agent:** config_agent

---

## Phase 1 - Ingest

### VACLIP-010: Local file ingest adapter
**Objective:** Implement LocalFileAdapter that stages local video files for processing.
**Inputs:** `src/vaclip/ingest/base.py`, local MP4/MKV file
**Outputs:** `IngestResult` with `staged_path` and `run_id`
**Acceptance Criteria:**
- [ ] Supports .mp4, .mkv, .webm, .avi, .mov
- [ ] Raises `VaClipIngestError` for missing files
- [ ] Emits progress callbacks
- [ ] Test: `test_local_file_adapter.py` passes
**Agent:** ingest_agent

### VACLIP-011: yt-dlp ingest adapter
**Objective:** Implement YtDlpAdapter for YouTube, Twitch, Kick, Rumble, generic URLs.
**Inputs:** `src/vaclip/ingest/base.py`, valid URL
**Outputs:** `IngestResult` with downloaded staged file
**Acceptance Criteria:**
- [ ] YouTube URL downloads successfully
- [ ] Unsupported URL raises `VaClipUnsupportedSourceError`
- [ ] Progress callback fires during download
- [ ] Test: `test_ytdlp_adapter.py` passes (mocked)
**Agent:** ingest_agent

### VACLIP-012: FFprobe metadata extraction
**Objective:** Implement FFprobeService to extract MediaMetadata from staged files.
**Inputs:** Staged video file path
**Outputs:** `MediaMetadata` with duration, codec, fps, etc.
**Acceptance Criteria:**
- [ ] Returns correct duration for test video
- [ ] Returns None gracefully for corrupt files
- [ ] Saves artifact to cache
**Agent:** ingest_agent

### VACLIP-013: Audio extraction
**Objective:** Implement audio extraction service using FFmpeg.
**Inputs:** Staged video file path
**Outputs:** Extracted WAV/FLAC audio file path
**Acceptance Criteria:**
- [ ] Produces 16kHz mono WAV by default
- [ ] Uses NVENC/GPU where available
- [ ] Saves audio path to IngestResult
**Agent:** ingest_agent

---

## Phase 2 - Transcription

### VACLIP-020: FasterWhisper backend implementation
**Objective:** Implement FasterWhisperBackend using large-v3 on CUDA.
**Inputs:** `src/vaclip/transcription/base.py`, extracted audio WAV
**Outputs:** `TranscriptResult` with segments and word timestamps
**Acceptance Criteria:**
- [ ] Runs on CUDA with float16
- [ ] Falls back to int8_float16 on OOM
- [ ] word_timestamps=True produces per-word timing
- [ ] Saves transcript artifact to cache
- [ ] Test: `test_faster_whisper_backend.py` passes
**Agent:** transcription_agent

---

## Phase 3 - Segmentation

### VACLIP-030: Transcript-window candidate generator
**Objective:** Generate candidate clip windows from TranscriptResult.
**Inputs:** `TranscriptResult`, config (min/max duration, step)
**Outputs:** List of `CandidateClip` objects
**Acceptance Criteria:**
- [ ] All candidates within min/max duration bounds
- [ ] Candidate text preserves segment boundaries
- [ ] Overlap suppression removes near-duplicate windows
- [ ] Saves candidates artifact to cache
**Agent:** segmentation_agent

---

## Phase 4 - Scoring

### VACLIP-040: Podcast/commentary heuristic scorer
**Objective:** Implement PodcastHighlightScorer with multi-signal heuristics.
**Inputs:** `CandidateClip` list
**Outputs:** `ScoredClip` list ranked by score
**Acceptance Criteria:**
- [ ] Scores between 0.0-1.0
- [ ] score_breakdown populated with individual signals
- [ ] reasoning string is non-empty
- [ ] Test with fixture transcript produces reasonable rankings
**Agent:** scoring_agent

---

## Phase 5 - Export

### VACLIP-050: FFmpeg clip exporter
**Objective:** Export top-ranked clips to output directory using FFmpeg.
**Inputs:** `ScoredClip` list, source video path, export config
**Outputs:** MP4 clip files in output directory
**Acceptance Criteria:**
- [ ] Clips start/end at correct timestamps
- [ ] Quality settings from config are applied
- [ ] Vertical/square framing options work
- [ ] Export manifest JSON saved to cache
**Agent:** export_agent

---

## Phase 5 - Pipeline

### VACLIP-060: End-to-end pipeline command
**Objective:** Wire all stages into `vaclip run pipeline` command.
**Inputs:** Source URL or file path, profile, intent
**Outputs:** Exported clips, full artifact trail
**Acceptance Criteria:**
- [ ] `vaclip run pipeline --source video.mp4 --profile podcast` completes
- [ ] All intermediate artifacts present in cache
- [ ] Top clips present in output
- [ ] Errors at any stage log clearly and exit cleanly
**Agent:** pipeline_agent
