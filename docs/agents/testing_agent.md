# Testing Agent Handoff

## Agent Role

You are the **Testing Agent**. Your sole responsibility is implementing and maintaining the
testing infrastructure for VAClip: writing unit and integration tests, establishing testing
patterns, ensuring test coverage, and validating that all components work correctly together.

## Tasks to Implement

- VACLIP-019: Establish testing patterns and conventions
- VACLIP-020: Write comprehensive unit test suite for all modules
- VACLIP-021: Write end-to-end integration test suite (M-36)
- VACLIP-022: Implement test fixtures and mocking strategies
- VACLIP-023: Set up coverage reporting and enforcement
- VACLIP-024: Configure continuous integration for testing
- VACLIP-025: Create testing documentation and guidelines

## Files You Own

```
tests/
    __init__.py          - export test utilities
    conftest.py          - shared pytest fixtures and configuration
    unit/                - unit tests for each module
        __init__.py
        test_ingest.py
        test_transcription.py
        test_segmentation.py
        test_scoring.py
        test_export.py
        test_pipeline.py
        test_models.py
        test_utils.py
        test_cli.py
    integration/         - end-to-end integration tests
        __init__.py
        test_pipeline_e2e.py
        test_cli_e2e.py
        test_fixtures/   - test media files and configs
            sample_podcast.mp3
            sample_video.mp4
            sample_config.yaml
    utils/               - testing helpers and mocks
        __init__.py
        mocks.py
        helpers.py
docs/
    testing_strategy.md  - comprehensive testing approach
    troubleshooting.md   - common testing issues and solutions
```

## Files You Must NOT Modify

- `src/` - production code (only modify to improve testability)
- `configs/` - configuration files (except for test-specific overrides)
- `AGENTS.md` - agent instructions (update references to testing docs)

## Contracts

### Test Organization

All tests should follow the AAA pattern: Arrange, Act, Assert.

Unit tests should:
- Test one component in isolation
- Use mocks for external dependencies
- Be fast and deterministic
- Focus on business logic and edge cases

Integration tests should:
- Test multiple components working together
- Use real files and services where appropriate
- Be marked with `@pytest.mark.integration`
- Use temporary directories for file I/O
- Be skipable in CI by default (marked as slow)

### Test Naming Conventions

- Test files: `test_[module_name].py`
- Test classes: `Test[ClassName]` (when using classes)
- Test functions: `test_[description_of_what_being_tested]`
- Test methods: `test_[description]` (within test classes)

### Fixture Usage

- Use `@pytest.fixture` for reusable test setup
- Scope fixtures appropriately (`function`, `class`, `module`, `session`)
- Place shared fixtures in `tests/conftest.py`
- Use descriptive fixture names that indicate purpose

## Implementation Guide

### Testing Pyramid

VAClip follows the classic testing pyramid:

```
          UI/E2E Tests
               ▲
          Integration Tests
               ▲
          Unit Tests (base)
```

#### Unit Tests (70% of tests)
- Test individual functions, methods, and classes
- Mock all external dependencies (filesystem, network, GPU)
- Run on every commit
- Target: 80%+ coverage

#### Integration Tests (20% of tests)
- Test combinations of components
- Use real filesystem, but mocked external services
- Run on every commit (marked fixtures may be skipped in CI)
- Target: 20%+ coverage

#### End-to-End Tests (10% of tests)
- Test complete user workflows
- Use real fixture media files
- Run in CI with `@pytest.mark.slow` and `@pytest.mark.integration`
- Target: 5+ critical user journeys

### Mocking Strategy

```python
# For external libraries
with patch('yt_dlp.YoutubeDL') as mock_ytdl:
    mock_instance = MagicMock()
    mock_ytdl.return_value = mock_instance
    mock_instance.download.return_value = None
    # Configure return values as needed

# For subprocess calls (FFmpeg, etc.)
with patch('subprocess.run') as mock_run:
    mock_run.return_value = CompletedProcess(args=[], returncode=0)
    # Configure stdout/stderr as needed

# For file system operations
with patch('pathlib.Path.exists') as mock_exists:
    mock_exists.return_value = True
```

### Test Data Strategies

1. **Synthetic Data**: Generated in tests (ideal for unit tests)
2. **Fixture Files**: Small, committed test files (for integration tests)
3. **Temporary Files**: Created in `tmp_path` (isolated per test)
4. **Mock Objects**: Using `unittest.mock` for complex dependencies

## Key Dependencies

```toml
pytest = ">=8.0.0"
pytest-asyncio = ">=0.23.0"
pytest-cov = ">=5.0.0"
```

## Testing Requirements

### Unit Test Requirements

1. **Isolation**: Each test should test only one unit of work
2. **Determinism**: Same input should always produce same output
3. **Speed**: Unit tests should complete in < 1 second each
4. **Coverage**: Target 80%+ line coverage for all modules
5. **Edge Cases**: Test boundary conditions, error conditions, invalid inputs
6. **Clear Assertions**: Each test should have one clear purpose

### Integration Test Requirements

1. **Realistic Scenarios**: Test realistic user workflows
2. **Fixture-Based**: Use committed small media files
3. **Isolated State**: Each test should clean up after itself
4. **Dependency Marking**: Use `@pytest.mark.integration` and `@pytest.mark.slow`
5. **Configuration Override**: Use test-specific settings to avoid side effects

### Coverage Requirements

- **Minimum**: 70% overall coverage
- **Target**: 80%+ coverage for all modules
- **Critical Paths**: 90%+ coverage for main execution paths
- **Enforcement**: Fail CI if coverage drops below threshold

## Logging in Tests

```python
# Capture logs for assertion
def test_something(caplog):
    # ... test code ...
    assert "expected message" in caplog.text
    assert "ERROR" not in caplog.text  # or check for expected errors

# Or check that specific logging occurred
def test_logging(caplog):
    # ... test code that should log ...
    assert any(
        record.levelno == logging.INFO and "expected message" in record.message
        for record in caplog.records
    )
```

## Error Handling in Tests

```python
# Test that exceptions are raised correctly
def test_raises_error():
    with pytest.raises(ValueError, match="expected error message"):
        # code that should raise ValueError
    
# Test that exceptions are logged and handled
def test_error_handling(caplog):
    # ... code that should handle an error gracefully ...
    assert "Handling error:" in caplog.text
    assert "traceback" not in caplog.text  # or check for expected traceback logging
```

## Definition of Done

- [ ] Testing strategy document created (`docs/testing_strategy.md`)
- [ ] Troubleshooting guide includes testing section (`docs/troubleshooting.md`)
- [ ] All existing modules have corresponding unit test files in `tests/unit/`
- [ ] Unit tests achieve 80%+ coverage for all modules
- [ ] Integration test suite for M-36 is complete and passes when dependencies are implemented
- [ ] CI pipeline runs tests on every commit and reports coverage
- [ ] `ruff check tests/` passes with 0 errors
- [ ] `mypy tests/` passes in strict mode
- [ ] Test fixtures are properly isolated and don't leak state between tests
- [ ] Clear documentation exists for how to write, run, and debug tests
- [ ] Contributing guidelines include testing requirements and expectations