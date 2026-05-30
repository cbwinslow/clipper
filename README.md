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
- **Graphical User Interface (GUI)** - Modern interface for visual feedback and enhanced user experience

## Namespace

`vaclip` - Video Auto Clipper

## Requirements

- Python 3.11+
- FFmpeg (with NVENC support)
- CUDA-capable GPU (RTX 3060 recommended)
- yt-dlp
- Node.js 18+ (for GUI development)
- See `backend/pyproject.toml` for backend dependency list
- See `frontend/package.json` for frontend dependency list

## Installation

```bash
git clone https://github.com/cbwinslow/clipper.git
cd clipper
# Backend setup (using uv)
cd backend
uv sync  # Installs dependencies from pyproject.toml
cd ..
# Frontend setup
cd frontend
npm install
cd ..
```

## Usage

### Command Line Interface (CLI)

```bash
vaclip ingest --source "https://youtube.com/watch?v=..." --output ./input
vaclip transcribe --input ./input/video.mp4
vaclip segment --input ./cache/transcript.json
vaclip score --profile podcast --intent funny
vaclip export --top 10 --format shorts
vaclip run pipeline --source "video.mp4" --profile podcast
```

### Graphical User Interface (GUI)

```bash
# Start backend server (from clipper root)
cd backend
uv run main.py  # Runs FastAPI server on http://localhost:8000

# In a new terminal, start frontend dev server (from clipper root)
cd frontend
npm run dev  # Runs Next.js dev server on http://localhost:3000
```

Then open your browser to http://localhost:3000 to access the VAClip GUI.

## Project Structure (Monorepo)

```
clipper/
  backend/              # FastAPI backend for GUI
    main.py             # Application entry point
    pyproject.toml      # Backend dependencies and project config
    /app                # API route modules (to be implemented)
  frontend/             # Next.js 14 frontend for GUI
    /app                # Next.js App Router pages and components
    /components         # Reusable UI components
    /lib                # Utility functions and API clients
    package.json        # Frontend dependencies and scripts
  src/vaclip/           # Main package (core VAClip functionality)
  docs/                 # Project documentation
  configs/              # YAML configuration files
  tests/                # Test suite
  input/                # Source media
  output/               # Final exported clips
  cache/                # Intermediate artifacts
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