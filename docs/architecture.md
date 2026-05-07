# VAClip - System Architecture

## Overview

VAClip is a local-first, GPU-accelerated video highlight extraction pipeline.
All processing runs on-device. External APIs are optional and disabled by default.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        CLI (Typer)                       │
│              vaclip ingest | run | export                │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    Pipeline Orchestrator                  │
│              vaclip.pipeline.VACLipPipeline              │
└──┬──────────────┬──────────────┬───────────┬────────────┘
   │              │              │           │
   ▼              ▼              ▼           ▼
┌──────┐   ┌──────────┐  ┌──────────┐  ┌────────┐
│Ingest│   │Transcribe│  │  Score   │  │ Export │
│Layer │   │  Layer   │  │  Layer   │  │ Layer  │
└──────┘   └──────────┘  └──────────┘  └────────┘
```

## Layers

### 1. Ingest Layer (`src/vaclip/ingest/`)

Responsible for acquiring media from various sources.

- **BaseIngestAdapter** (abstract) - defines `ingest(source) -> MediaAsset`
- **YtDlpAdapter** - downloads from YouTube, Rumble, Kick, Twitch, etc.
- **LocalFileAdapter** - copies/validates local video files
- **RSSFeedAdapter** (future) - monitors RSS/podcast feeds for new episodes

Outputs: `MediaAsset` Pydantic model saved to `input/` directory.

### 2. Transcription Layer (`src/vaclip/transcription/`)

Converts audio to word-level timestamped transcripts.

- **BaseTranscriptionBackend** (abstract) - defines `transcribe(audio_path) -> Transcript`
- **WhisperBackend** - uses faster-whisper with CUDA/GPU acceleration
- **WhisperCPUBackend** - CPU fallback for systems without GPU

Outputs: `Transcript` Pydantic model with word-level timestamps, saved to `cache/transcripts/`.

### 3. Scoring Layer (`src/vaclip/scoring/`)

Identifies highlight-worthy segments using multi-signal analysis.

- **BaseScorer** (abstract) - defines `score(segment) -> float`
- **TranscriptScorer** - keyword density, sentiment, laughter/reaction words
- **AudioEnergyScorer** - RMS energy, silence detection, volume spikes
- **VisualMotionScorer** - frame optical flow, scene change detection
- **LLMReranker** - optional OpenRouter reranker for top-N candidates
- **CompositeScorer** - weighted aggregation of all scorers

Outputs: `ScoredSegment` list, saved to `cache/scores/`.

### 4. Export Layer (`src/vaclip/export/`)

Renders final clips and applies formatting for target platform.

- **ClipExporter** - slices source video using FFmpeg
- **FramingStrategy** (abstract) - defines output aspect ratio logic
  - **WideFramingStrategy** - 16:9 landscape (YouTube)
  - **VerticalFramingStrategy** - 9:16 portrait (Shorts/TikTok)
  - **SquareFramingStrategy** - 1:1 (Instagram)
- **SubtitleBurner** (future) - burns transcript captions onto clips

Outputs: Final clip files in `output/` directory.

## Data Flow

```
Source URL / Local Path
        │
        ▼
  MediaAsset (input/)
        │
        ▼
  Transcript (cache/transcripts/)
        │
        ▼
  Segments → ScoredSegments (cache/scores/)
        │
        ▼
  TopSegments → Clips (output/)
```

## Key Design Decisions

### Local-First
All models and processing run locally. No data leaves the machine by default.
External API calls (OpenRouter) require explicit `--use-llm` flag.

### Artifact Preservation
Every intermediate output is written to disk before the next stage begins.
The pipeline can be resumed from any checkpoint using `--from-stage`.

### GPU Acceleration
Whisper and vision models use CUDA when available (RTX 3060 target).
Falls back to CPU automatically with a warning log.

### Pydantic Contracts
All inter-layer data is typed via Pydantic v2 models.
This ensures agents can read/write data without ambiguity.

### Pluggable Adapters
All layers use abstract base classes. New backends (sources, models, exporters)
can be added without modifying existing code (Open/Closed Principle).

## Directory Structure

```
clipper/
├── src/vaclip/          # Main Python package
│   ├── cli/             # Typer CLI entry points
│   ├── config/          # Settings and configuration
│   ├── ingest/          # Source adapters
│   ├── transcription/   # Speech-to-text backends
│   ├── scoring/         # Highlight scoring engines
│   ├── export/          # Clip rendering and framing
│   ├── pipeline/        # Orchestration logic
│   ├── models/          # Pydantic data contracts
│   ├── logging/         # structlog setup
│   └── utils/           # Shared utilities
├── configs/             # YAML configuration files
├── docs/                # Project documentation
│   └── agents/          # Per-agent handoff docs
├── tests/               # Test suite
│   ├── unit/            # Fast, no I/O tests
│   └── integration/     # Real-file tests
├── input/               # Downloaded/copied source media
├── output/              # Final rendered clips
├── cache/               # Intermediate artifacts
│   ├── transcripts/     # Whisper outputs
│   └── scores/          # Segment score files
├── models/              # Downloaded model weights (gitignored)
└── logs/                # Runtime log files
```

## Technology Stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| Language | Python 3.11+ | Type hints, match statements |
| CLI | Typer | Auto-generates --help |
| Data contracts | Pydantic v2 | Strict validation |
| Logging | structlog | JSON + console |
| Config | PyYAML + dataclasses | Hierarchical settings |
| Download | yt-dlp | Multi-platform |
| Transcription | faster-whisper | GPU-accelerated |
| Audio analysis | librosa | Feature extraction |
| Vision | OpenCV | Frame analysis |
| Video editing | FFmpeg (subprocess) | Clip extraction |
| Testing | pytest | Unit + integration |
| Linting | ruff | Fast, comprehensive |
| Type checking | mypy | Strict mode |
