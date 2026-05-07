# AGENTS.md - VAClip Agent Instructions

This is the root agent instruction file. Read this first before loading any task-specific guidance.

## Mission

Build VAClip: a quality-first, local-first, free/free-tier automatic video clipping system.
Optimize for correctness, maintainability, and professional engineering standards.

## Required Reading Order

1. `AGENTS.md` (this file)
2. `docs/project_summary.md`
3. `docs/rules.md`
4. `docs/architecture.md`
5. `docs/tasks.md`
6. Relevant file in `docs/agents/`

## Non-Negotiables

1. No paid dependencies for core functionality
2. Prefer local GPU processing over hosted APIs
3. Optimize for correctness and traceability over speed
4. Update docs when code changes alter behavior
5. Respect package boundaries and shared Pydantic contracts
6. Use clear, simple naming conventions
7. No silent coupling, brittle scripts, or cheap workarounds
8. Write tests for all non-trivial logic
9. Ask when requirements are ambiguous - never guess
10. Keep tasks atomic and handoff-friendly
11. Always use structured logging via structlog
12. Always include stack traces in error handling
13. Preserve all intermediate artifacts

## Coding Standards

- Python 3.11+ only
- Typer for all CLI patterns
- Pydantic v2 for all boundary/contract models
- structlog for all logging (never bare print)
- Abstract base classes for all adapters and services
- Polymorphism preferred over if/elif chains
- Use super() correctly in all subclasses
- Use lambdas for simple transforms only
- Use dataclasses for internal ephemeral objects
- All public functions must have docstrings
- All classes must have docstrings
- Type hints required on all function signatures
- Line length: 100 chars max
- Follow PEP 8 and Pythonic idioms always

## Package Structure

```
src/vaclip/
  cli/          # Typer CLI commands
  config/       # Settings and config loading
  models/       # Pydantic boundary models
  ingest/       # Source adapters (local, yt-dlp, etc.)
  transcription/ # ASR backends
  segmentation/ # Shot detection and candidate generation
  scoring/      # Profile-based scoring engines
  export/       # FFmpeg clip export
  utils/        # Shared utilities
  logging/      # Structured logging setup
  pipeline/     # Orchestration layer
```

## Task Handoff Rules

- Every task must have: objective, inputs, outputs, acceptance criteria
- Never start coding without reading the relevant contract models in `src/vaclip/models/`
- Never break existing Pydantic model contracts without updating all consumers
- Write or update tests before marking a task complete
- Commit with descriptive messages: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`

## OpenRouter Policy

- Do NOT use OpenRouter unless explicitly instructed
- If used, limit to reranking top-20 candidates only
- Never send raw media or large transcripts to hosted APIs
- Always implement a local fallback path

## Error Handling Policy

- Use custom exception classes from `vaclip.utils.exceptions`
- Always log exceptions with structlog including stack traces
- Never swallow exceptions silently
- Use tenacity for retry logic on network operations
- Emit warnings via Python warnings module for non-fatal issues

## Artifact Policy

- Save ALL intermediate artifacts to `cache/` by default
- Use orjson for JSON serialization
- Artifact filenames must include run ID and stage name
- Never overwrite artifacts without explicit flag

## Agent Task Files

See `docs/agents/` for specific agent role definitions:
- `docs/agents/ingest_agent.md`
- `docs/agents/transcription_agent.md`
- `docs/agents/segmentation_agent.md`
- `docs/agents/scoring_agent.md`
- `docs/agents/export_agent.md`
- `docs/agents/pipeline_agent.md`
- `docs/agents/testing_agent.md`
