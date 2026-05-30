# CONTRIBUTING.md

# Contributing to VAClip

Thank you for considering contributing to VAClip! This document outlines our development process, coding standards, and how to contribute effectively.

## How to Contribute

1. **Fork the repository** on GitHub
2. **Create a feature branch** from `main`: `git checkout -b feature/your-feature-name`
3. **Make your changes** following our coding standards
4. **Write or update tests** for your changes
5. **Run the test suite** to ensure everything passes
6. **Commit your changes** with a descriptive commit message
7. **Push to your fork** and submit a pull request

## Development Setup

### Prerequisites

- Python 3.11+
- FFmpeg (with NVENC support for GPU acceleration)
- CUDA-capable GPU (RTX 3060 recommended) for GPU acceleration
- yt-dlp
- Git

### Local Development

```bash
# Clone the repository
git clone https://github.com/cbwinslow/clipper.git
cd clipper

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install development dependencies
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install
```

### Environment Configuration

Copy `.env.example` to `.env` and configure as needed:
```bash
cp .env.example .env
# Edit .env with your preferred settings
```

## Coding Standards

### Python Standards

- Python 3.11+ only
- Follow PEP 8 and Pythonic idioms
- Maximum line length: 100 characters
- Use type hints on all function signatures
- All public functions and classes must have docstrings
- Use structlog for all logging (never bare print)
- Use Pydantic v2 for all boundary/contract models
- Use Typer for all CLI patterns
- Abstract base classes for all adapters and services
- Polymorphism preferred over if/elif chains
- Use super() correctly in all subclasses
- Use lambdas for simple transforms only
- Use dataclasses for internal ephemeral objects

### Git Standards

- Write descriptive commit messages using conventional commits:
  - `feat:` for new features
  - `fix:` for bug fixes
  - `docs:` for documentation changes
  - `test:` for test additions/updates
  - `refactor:` for code refactoring
  - `chore:` for maintenance tasks
- Keep commits atomic and focused
- Never commit secrets or sensitive information
- Always pull before pushing to stay up-to-date

## Testing Standards

### Test Organization

- Unit tests: `tests/unit/` - test individual components in isolation
- Integration tests: `tests/integration/` - test components working together
- Use pytest as the testing framework
- Follow Arrange-Act-Assert (AAA) pattern in tests

### Test Requirements

- Write unit tests for all non-trivial logic
- Aim for 80%+ test coverage
- Mock external dependencies in unit tests
- Use test fixtures for common test data
- Mark integration tests with `@pytest.mark.integration`
- Mark slow tests with `@pytest.mark.slow`
- Tests must pass before submitting a pull request

### Running Tests

```bash
# Run all tests
pytest

# Run only unit tests
pytest -m "unit"

# Run only integration tests
pytest -m "integration"

# Run tests with coverage
pytest --cov=src/vaclip

# Run a specific test file
pytest tests/unit/test_models.py
```

## Code Review Process

1. **Pull Request Requirements**:
   - Clear title and description
   - Linked to relevant issue (if applicable)
   - Passes all CI checks (linting, type checking, tests)
   - Includes tests for new functionality
   - Follows coding standards

2. **Review Checklist**:
   - [ ] Code follows styling and formatting standards
   - [ ] Logic is correct and handles edge cases
   - [ ] Error handling is appropriate
   - [ ] Logging is used correctly (structlog, no bare print)
   - [ ] Tests are present and passing
   - [ ] Documentation is updated if needed
   - [ ] No secrets or sensitive information committed
   - [ ] Changes are minimal and focused

3. **Review Process**:
   - At least one approving review from maintainer
   - Address all review comments
   - Maintainer merges after approval

## Documentation

- Update documentation when code changes alter behavior
- Keep documentation in `docs/` directory
- Follow existing documentation style and structure
- Agent-specific documentation goes in `docs/agents/`
- Prompts and AI agent documentation goes in `docs/prompts/`

## AI Agent Guidelines

When working with AI agents (OpenCode, Cursor, etc.):

1. **Read documentation first**: Always consult `docs/prompts/opencode_main_prompt.md` and relevant agent files in `docs/agents/`
2. **Follow the quality checklist**: Use the predefined quality criteria before marking tasks complete
3. **Write tests early**: Practice test-driven development
4. **Log everything important**: Use structlog for all significant events
5. **Ask clarifying questions**: Better to ask than to implement incorrectly
6. **Review AI-generated code**: Trust but verify - always review generated code before submitting

## Reporting Issues

- Use the GitHub issue tracker
- Check if similar issues already exist
- Include relevant details:
  - VAClip version
  - Python version
  - Operating system
  - Steps to reproduce
  - Expected vs actual behavior
  - Logs and error messages (if applicable)
  - For GPU issues: GPU model, CUDA version, driver version

## License

By contributing to VAClip, you agree that your contributions will be licensed under the MIT License.

## Questions?

Feel free to ask questions in the GitHub discussions or by contacting the repository maintainer.

Happy contributing! 🎉