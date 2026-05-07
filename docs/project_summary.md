# VAClip - Project Summary

## Project Name
VAClip (Video Auto Clipper)

## Namespace
`vaclip`

## One-Line Description
A quality-first, local-first, free/free-tier automatic video clipping system with AI-powered multimodal highlight detection.

## Problem Statement
Manually reviewing long-form video content (podcasts, streams, gaming VODs, etc.) to find shareable clips is time-consuming. Existing paid tools lack control, quality, and privacy. VAClip automates the process locally on the user's own hardware using open-source AI models.

## Core Principles
1. **Quality first** - Slow and accurate beats fast and wrong
2. **Local first** - All core processing runs on local GPU (RTX 3060)
3. **Free/free-tier** - No paid dependencies for core pipeline
4. **Multi-profile** - Optimized modes per content type
5. **Multi-intent** - Detects funny, insightful, action, emotional, hype clips
6. **Artifact preservation** - All intermediate pipeline outputs are saved
7. **Agent-friendly** - Code is structured for AI agent handoff

## Target Hardware
- Windows 11
- NVIDIA RTX 3060 (12GB VRAM)
- CUDA-capable GPU required for GPU transcription path
- CPU fallback available but not recommended for large models

## Primary Use Cases (Phase 1)
1. Podcast/commentary highlight extraction (shorts, < 60s)
2. Multi-profile clip detection across content types
3. YouTube/Twitch/Kick/Rumble/local file ingest

## Content Profiles
- podcast, gaming, reaction, sports, commentary, interview, educational, generic

## Clip Intents
- funny, insightful, action, emotional, hype, highlight, educational, generic

## Free Tool Stack
| Layer | Tool |
|---|---|
| CLI | Typer |
| Config | Pydantic + YAML |
| Logging | structlog |
| Ingest | yt-dlp + local file |
| Media | FFmpeg + ffprobe |
| Transcription | faster-whisper (GPU) |
| Shot Detection | TransNetV2 (optional) |
| Embeddings | sentence-transformers |
| Reranking | OpenRouter (optional, last resort) |

## Repository
https://github.com/cbwinslow/clipper

## Documentation Index
- `docs/architecture.md` - System architecture
- `docs/features.md` - Feature list
- `docs/srs.md` - Software requirements
- `docs/tasks.md` - Atomic task breakdown
- `docs/rules.md` - Project rules and constraints
- `docs/roadmap.md` - Phase roadmap
- `docs/agents/` - Per-agent instruction files
- `AGENTS.md` - Root agent instruction file
