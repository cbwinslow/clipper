# VAClip - Project Rules

These rules apply to all contributors, agents, and AI coding assistants.
Violating these rules requires a documented justification in an ADR.

## Absolute Rules (Never Break)

1. **No paid dependencies** for core pipeline functionality
2. **No OpenRouter until local baseline works** and only for top-N reranking
3. **Never overwrite existing cache artifacts** unless `--overwrite` flag is set
4. **Never swallow exceptions silently** - always log with structlog before raising
5. **Never use bare `print()`** - always use `get_logger(__name__)`
6. **Never hardcode paths** - always use config or `pathlib.Path`
7. **Never commit `.env`** - only `.env.example`
8. **Never commit model weights** - add to `.gitignore`
9. **Never commit media files** - input/output/cache are gitignored
10. **Always write tests** for non-trivial logic before marking a task complete

## Code Quality Rules

- Python 3.11+ only, no compatibility shims for older versions
- All public functions and classes must have docstrings
- All function signatures must have complete type hints
- Line length: 100 characters max (enforced by ruff)
- Use `from __future__ import annotations` in all source files
- Prefer composition over deep inheritance (max 2-3 levels deep)
- Use `@abstractmethod` for all required interface methods
- Use `super().__init__()` in all subclass `__init__` methods
- Use `Enum` for all categorical constants (never bare strings)
- Use `dataclass` for internal ephemeral objects, `Pydantic` for boundary contracts

## Architecture Rules

- Each pipeline stage must be independently runnable via CLI
- Stages communicate only through well-defined Pydantic models
- No circular imports between packages
- `models/` package must not import from any other vaclip package
- `utils/` package must not import from domain packages
- `logging/` package must not import from domain packages
- Adapters must implement the abstract base from `base.py` in their package
- New source adapters go in `ingest/`, new ASR backends in `transcription/`
- New scorers go in `scoring/` and must inherit `ClipScorer`

## Artifact Rules

- All intermediate artifacts saved to `cache/{run_id}/` by default
- Artifact filenames: `{run_id}_{stage}_{type}.json`
- Use `orjson` for all JSON serialization/deserialization
- Artifacts must be valid JSON (not JSONL, not pickle)
- Never delete artifacts automatically; require explicit cleanup command

## Git Rules

- Commit messages use conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`
- One logical change per commit
- Never force-push to `main`
- PR description must reference task ID (e.g., `VACLIP-010`)

## Testing Rules

- Unit tests: fast, no external I/O, no GPU, no network
- Integration tests: marked `@pytest.mark.integration`, require real files
- GPU tests: marked `@pytest.mark.gpu`, skipped in CI without GPU
- Slow tests: marked `@pytest.mark.slow`, excluded from default test run
- Minimum coverage target: 70% for new code
- Use `tmp_path` fixture for all file I/O in tests
- Mock external calls (yt-dlp, ffmpeg) in unit tests

## Agent Handoff Rules

- Read `AGENTS.md` and relevant `docs/agents/*.md` before starting
- Read existing code in the target package before writing new code
- Never rename existing public symbols without updating all consumers
- Always run `ruff check src/` before marking a task complete
- Always run `pytest tests/unit/` before marking a task complete
- Document any deviation from these rules in `docs/decisions/`
