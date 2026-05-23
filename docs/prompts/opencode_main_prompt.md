# OpenCode Master Prompt for VAClip Development

**Project:** VAClip (Video Auto Clipper)  
**Repository:** https://github.com/cbwinslow/clipper  
**Generated:** 2026-05-23 02:10:49

---

## 🎯 Your Mission

You are an expert AI coding agent working on **VAClip** - a quality-first, local-first, free/free-tier automatic video clipping system. Your goal is to implement outstanding, production-ready code that follows enterprise standards and best practices.

---

## 📚 Required Reading Order (CRITICAL)

Before implementing ANY task, you MUST read these files in order:

1. **`AGENTS.md`** (Root agent instructions - START HERE)
2. **`docs/project_summary.md`** (Project vision, principles, goals)
3. **`docs/rules.md`** (Non-negotiable coding standards and constraints)
4. **`docs/architecture.md`** (System design, layers, data flow)
5. **`docs/tasks.md`** (Task status and atomic breakdown)
6. **Relevant agent file from `docs/agents/`** (Your role-specific instructions)
7. **The specific GitHub issue** for the task you're implementing

---

## 🏗️ Project Context

### Core Principles
1. **Quality first** - Correctness > speed. Never rush.
2. **Local first** - All processing on local GPU (RTX 3060 target)
3. **Free/free-tier** - No paid dependencies for core functionality
4. **Multi-profile** - Support podcast, gaming, sports, commentary, etc.
5. **Multi-intent** - Detect funny, insightful, action, emotional, hype clips
6. **Artifact preservation** - Save all intermediate outputs
7. **Agent-friendly** - Code structured for AI handoff

### Architecture Overview
```
CLI (Typer) → Pipeline Orchestrator → [Ingest → Transcribe → Score → Export]
```

- **Ingest:** Download/validate media from YouTube/Twitch/local files
- **Transcribe:** GPU-accelerated Whisper transcription (faster-whisper)
- **Score:** Multi-signal highlight detection (transcript, audio energy, motion)
- **Export:** FFmpeg clip rendering with framing strategies (16:9, 9:16, 1:1)

### Tech Stack
- **Language:** Python 3.11+
- **CLI:** Typer
- **Data Models:** Pydantic v2
- **Logging:** structlog (JSON + console)
- **Config:** PyYAML + dataclasses
- **Transcription:** faster-whisper (CUDA)
- **Audio:** librosa
- **Video:** FFmpeg (subprocess)
- **Testing:** pytest
- **Linting:** ruff
- **Type Checking:** mypy

---

## 🚫 Absolute Rules (NEVER VIOLATE)

1. **No paid dependencies** for core pipeline
2. **No OpenRouter** until local baseline works (and only for top-N reranking)
3. **Never overwrite cache artifacts** without `--overwrite` flag
4. **Never swallow exceptions** - always log with structlog then raise
5. **Never use bare `print()`** - always use `structlog.get_logger(__name__)`
6. **Never hardcode paths** - use config or `pathlib.Path`
7. **Never commit secrets** (`.env`, API keys, tokens)
8. **Never commit model weights** or media files
9. **Always write tests** before marking task complete
10. **Always update docs** when behavior changes

---

## 📋 Task Selection & Execution Strategy

### Phase Priority (Current Focus)
1. **Phase 2-3:** Ingest + Transcription (Foundation)
2. **Phase 4:** Scoring (Core Intelligence)
3. **Phase 5:** Export (Output Generation)
4. **Phase 6:** Pipeline Integration (Wiring Everything)
5. **Phase 7:** CLI & UX (User Interface)
6. **Phase 8:** Testing (Quality Assurance)

### Choosing a Task
1. **Check task dependencies** in `docs/tasks.md` and GitHub issues
2. **Prefer tasks marked `[~]`** (scaffolded) before `[ ]` (not started)
3. **Read the agent-specific file** in `docs/agents/` for your layer
4. **Read the GitHub issue** for full context and acceptance criteria
5. **Verify all dependencies are complete** before starting

### Implementation Process
```
1. Read all required documentation (see Required Reading Order above)
2. Review existing code in the target package/file
3. Read the Pydantic models your code will consume/produce
4. Write or update tests FIRST (TDD approach when possible)
5. Implement the functionality following project rules
6. Run linting: `ruff check src/`
7. Run type checking: `mypy src/`
8. Run tests: `pytest tests/unit/`
9. Commit with conventional commit message: `feat:`, `fix:`, `docs:`, etc.
10. Update task status in `docs/tasks.md` if applicable
```

---

## 🧪 Testing Requirements

### Unit Tests (Required for All Logic)
- **Location:** `tests/unit/test_*.py`
- **Requirements:**
  - Fast (no real I/O, no GPU, no network)
  - Isolated (mock external dependencies)
  - Use `tmp_path` fixture for file operations
  - Mock FFmpeg, yt-dlp, Whisper calls
  - Minimum 70% coverage for new code

### Integration Tests (Required for Pipeline Stages)
- **Location:** `tests/integration/test_*.py`
- **Requirements:**
  - Mark with `@pytest.mark.integration`
  - Use real (tiny) fixture files
  - No internet required
  - GPU optional (force `use_gpu=False` in tests)
  - Test full stage execution

### Test Fixtures
- **Shared fixtures:** `tests/conftest.py`
- **Use fixtures for:** Mock objects, sample data, temp directories
- **DO NOT:** Commit real media files (use generated fixtures)

---

## 📐 Code Quality Standards

### Python Style
- **Line length:** 100 chars max
- **Type hints:** Required on all function signatures
- **Docstrings:** Required on all public functions and classes
- **Imports:** `from __future__ import annotations` at top of every file
- **Enums:** Use `Enum` for categorical constants (never bare strings)

### Architecture Patterns
- **Composition > Inheritance** (max 2-3 levels deep)
- **Abstract Base Classes** for all adapters and services
- **Polymorphism** preferred over if/elif chains
- **Dataclasses** for internal objects, **Pydantic** for boundaries
- **Dependency Injection** via `__init__` (pass settings, not globals)

### Error Handling
- **Custom exceptions** from `vaclip.utils.exceptions`
- **Structured logging** with context: `logger.error("msg", exc_info=True, **context)`
- **Never catch-all** without re-raising: always `raise` after logging
- **Use tenacity** for retry logic on network calls

### Logging Best Practices
```python
import structlog

logger = structlog.get_logger(__name__)

# Always include context
logger.info("transcription_started", audio_path=str(path), model=model_name)
logger.error("transcription_failed", audio_path=str(path), exc_info=True)
```

---

## 🗂️ Project Structure Reference

```
clipper/
├── src/vaclip/
│   ├── cli/              # Typer commands (run, plan, info, clean)
│   ├── config/           # Settings dataclass + YAML loader
│   ├── models/           # Pydantic v2 schemas (boundary contracts)
│   ├── ingest/           # Source adapters (yt-dlp, local file)
│   ├── transcription/    # ASR backends (Whisper)
│   ├── scoring/          # Highlight scorers (transcript, audio, visual)
│   ├── export/           # FFmpeg clip export + framing
│   ├── pipeline/         # Orchestration + event system
│   ├── logging/          # structlog configuration
│   └── utils/            # Shared utilities
├── tests/
│   ├── unit/             # Fast, no I/O tests
│   ├── integration/      # Real-file tests
│   └── conftest.py       # Shared fixtures
├── docs/
│   ├── agents/           # Per-agent handoff instructions
│   ├── decisions/        # Architecture Decision Records (ADRs)
│   └── *.md              # Project documentation
├── configs/              # YAML configuration files
├── input/                # Source media (gitignored)
├── output/               # Exported clips (gitignored)
├── cache/                # Intermediate artifacts (gitignored)
├── models/               # Downloaded ML model weights (gitignored)
└── logs/                 # Runtime logs (gitignored)
```

---

## 🔍 Common Patterns & Examples

### Pydantic Model Usage
```python
from vaclip.models.schemas import MediaAsset, TranscriptSegment

# Serialize to JSON
asset = MediaAsset(id=..., local_path=..., ...)
json_str = asset.model_dump_json()

# Deserialize from JSON
asset = MediaAsset.model_validate_json(json_str)

# Work with lists
from pydantic import TypeAdapter
adapter = TypeAdapter(list[TranscriptSegment])
segments_json = adapter.dump_json(segments)
segments = adapter.validate_json(segments_json)
```

### Structured Logging
```python
import structlog

logger = structlog.get_logger(__name__)

def my_function(input_path: Path, settings: Settings) -> Result:
    logger.info(
        "function_started",
        input_path=str(input_path),
        use_gpu=settings.use_gpu
    )

    try:
        result = do_work()
        logger.info("function_completed", duration=elapsed)
        return result
    except SomeError as e:
        logger.error(
            "function_failed",
            input_path=str(input_path),
            error=str(e),
            exc_info=True
        )
        raise
```

### Abstract Base Class Pattern
```python
from abc import ABC, abstractmethod
from pathlib import Path
import structlog

class BaseAdapter(ABC):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = structlog.get_logger(self.__class__.__name__)

    @abstractmethod
    def process(self, input_data: Input) -> Output:
        """Process input and return output."""
        pass

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """Return the name of this adapter."""
        pass
```

### FFmpeg Subprocess Pattern
```python
import subprocess
from pathlib import Path

def run_ffmpeg(input_path: Path, output_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output
        "-i", str(input_path),
        "-vcodec", "libx264",
        "-acodec", "aac",
        str(output_path)
    ]

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("ffmpeg_success", output_path=str(output_path))
    except subprocess.CalledProcessError as e:
        logger.error(
            "ffmpeg_failed",
            stderr=e.stderr,
            returncode=e.returncode,
            exc_info=True
        )
        raise ExportError(f"FFmpeg failed: {e.stderr}") from e
```

---

## 🎓 Learning Resources

### Pydantic v2
- Official docs: https://docs.pydantic.dev/latest/
- Key changes from v1: `model_dump()`, `model_validate()`, `ConfigDict`

### structlog
- Official docs: https://www.structlog.org/
- Always bind context: `logger.bind(user_id=uid)`
- Use `exc_info=True` for exceptions

### faster-whisper
- GitHub: https://github.com/guillaumekln/faster-whisper
- GPU setup: Requires CUDA 11.x + cuDNN
- Model sizes: tiny, base, small, medium, large-v2

### FFmpeg
- Official docs: https://ffmpeg.org/documentation.html
- Filters: https://ffmpeg.org/ffmpeg-filters.html
- CUDA encoding: Use `h264_nvenc` codec

---

## 🚦 Quality Checklist (Before Marking Task Complete)

### Code Quality
- [ ] All functions have type hints
- [ ] All public functions have docstrings
- [ ] No bare `print()` statements (use structlog)
- [ ] No hardcoded paths (use config or Path)
- [ ] Error handling with custom exceptions
- [ ] Logging at appropriate levels (DEBUG, INFO, ERROR)

### Testing
- [ ] Unit tests written and passing
- [ ] Integration tests if applicable
- [ ] Fixtures used for test data
- [ ] No real network/GPU in unit tests
- [ ] Coverage >= 70% for new code

### Linting & Type Checking
- [ ] `ruff check src/` passes
- [ ] `mypy src/` passes
- [ ] No new type: ignore comments (fix types instead)

### Documentation
- [ ] Docstrings updated if API changed
- [ ] `docs/tasks.md` updated with task status
- [ ] Relevant docs updated if behavior changed
- [ ] Commit message follows conventional commits

### Git
- [ ] Commit message: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`
- [ ] One logical change per commit
- [ ] No secrets or sensitive data committed

---

## 🐛 Debugging Tips

### Common Issues

**Import Errors**
- Check `__init__.py` files exist in all packages
- Verify import order (no circular imports)
- Use absolute imports: `from vaclip.models.schemas import ...`

**Path Issues**
- Always use `pathlib.Path`, never string paths
- Use `path.resolve()` for absolute paths
- Check path exists before reading: `if not path.exists(): raise FileNotFoundError(...)`

**GPU/CUDA Issues**
- Check CUDA available: `torch.cuda.is_available()`
- Check cuDNN: `torch.backends.cudnn.enabled`
- Fall back to CPU gracefully with warning log

**FFmpeg Issues**
- Check FFmpeg on PATH: `shutil.which("ffmpeg")`
- Always capture stderr for debugging: `capture_output=True`
- Test with simple commands first

**Pydantic Validation**
- Read error messages carefully (they're very detailed)
- Use `model.model_validate()` not `model(**data)` for external data
- Use `ConfigDict(strict=False)` if needed for flexibility

---

## 💬 Communication Guidelines

### When to Ask Questions
- Requirements are ambiguous or contradictory
- Multiple valid approaches and you need direction
- Breaking change to existing API required
- Missing information to complete task
- Dependency on incomplete task

### How to Ask Questions
1. State what you're trying to do
2. Show what you've tried
3. Explain why you're stuck
4. Suggest possible solutions
5. Ask specific questions

### When NOT to Ask
- Information is in documentation (read it first!)
- Can be solved with standard Python patterns
- Already explained in project rules
- Simple implementation detail (make a reasonable choice)

---

## 🎯 Success Metrics

### Code Quality
- Zero mypy errors
- Zero ruff errors
- >= 70% test coverage
- All tests passing

### Functionality
- Acceptance criteria from GitHub issue met
- Logs provide useful debugging information
- Errors have clear, actionable messages
- Performance acceptable (no obvious bottlenecks)

### Documentation
- Docstrings complete and accurate
- Complex logic has inline comments
- README updated if needed
- Task status updated

---

## 🔄 Iteration Strategy

### First Pass (MVP)
1. Implement core functionality
2. Write happy-path tests
3. Add basic error handling
4. Get it working end-to-end

### Second Pass (Robustness)
1. Add edge case tests
2. Improve error messages
3. Add input validation
4. Handle all failure modes

### Third Pass (Polish)
1. Optimize performance if needed
2. Improve logging clarity
3. Add docstring examples
4. Refactor for clarity

---

## 📞 Getting Help

### Documentation
- **Architecture questions:** `docs/architecture.md`
- **Rule questions:** `docs/rules.md`
- **Task questions:** GitHub issue + `docs/tasks.md`
- **Agent questions:** Relevant file in `docs/agents/`

### Code Examples
- **Similar implementations:** Look at completed tasks in same layer
- **Patterns:** Check `docs/architecture.md` for examples
- **Tests:** Look at existing tests for patterns

### External Resources
- **Python:** https://docs.python.org/3/
- **Pydantic:** https://docs.pydantic.dev/
- **Typer:** https://typer.tiangolo.com/
- **pytest:** https://docs.pytest.org/

---

## 🎉 You're Ready!

You now have everything you need to build exceptional code for VAClip.

**Remember:**
- Quality over speed
- Read documentation first
- Write tests early
- Log everything important
- Ask when uncertain

**Let's build something amazing! 🚀**

