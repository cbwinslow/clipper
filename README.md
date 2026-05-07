# Clipper - VAClip Video Auto-Clipper

A quality-first, local-first, free/free-tier automatic video clipping system with AI-powered highlight detection.

## Features

- Multi-source ingest (local files, YouTube, Twitch, Kick, Rumble, and more via yt-dlp)
- GPU-accelerated transcription via faster-whisper (RTX 3060 optimized)
- Shot boundary detection via TransNetV2
- Multi-profile scoring (podcast, gaming, reaction, sports, commentary)
- Multi-intent clip detection (funny, insightful, action, emotional, hype)
- Sub-60s shorts-optimized export with vertical/square framing options
- Full artifact retention for all intermediate pipeline stages
- Professional CLI via Typer
- Structured logging and error handling
- OpenRouter integration (optional, last-mile reranking only)

## Namespace

`vaclip` - Video Auto Clipper

## Requirements

- Python 3.11+
- FFmpeg (with NVENC support)
- CUDA-capable GPU (RTX 3060 recommended)
- yt-dlp
- See `pyproject.toml` for full dependency list

## Installation

```bash
git clone https://github.com/cbwinslow/clipper.git
cd clipper
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -e .
```

## Usage

```bash
vaclip ingest --source "https://youtube.com/watch?v=..." --output ./input
vaclip transcribe --input ./input/video.mp4
vaclip segment --input ./cache/transcript.json
vaclip score --profile podcast --intent funny
vaclip export --top 10 --format shorts
vaclip run pipeline --source "video.mp4" --profile podcast
```

## Project Structure

```
clipper/
  src/vaclip/         # Main package
  docs/               # Project documentation
  configs/            # YAML configuration files
  tests/              # Test suite
  input/              # Source media
  output/             # Final exported clips
  cache/              # Intermediate artifacts
  models/             # Downloaded ML models
  logs/               # Run logs
```

## Documentation

See `docs/` for full project documentation including:
- `project_summary.md`
- `architecture.md`
- `srs.md`
- `features.md`
- `tasks.md`
- `agents.md`
- `rules.md`
- `roadmap.md`

## License

MIT
