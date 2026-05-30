# Testing Strategy

# VAClip Testing Strategy

This document outlines the comprehensive testing approach for VAClip, including test types, organization, coverage goals, and best practices.

## Table of Contents
1. [Test Philosophy](#test-philosophy)
2. [Test Types and Organization](#test-types-and-organization)
3. [Coverage Goals](#coverage-goals)
4. [Testing Pyramid](#testing-pyramid)
5. [Test Execution and CI](#test-execution-and-ci)
6. [Best Practices](#best-practices)
7. [Mocking and Test Doubles](#mocking-and-test-doubles)
8. [Test Data Management](#test-data-management)
9. [Performance Testing](#performance-testing)
10. [Security Testing](#security-testing)

---

## Test Philosophy

VAClip follows a **quality-first** approach to testing, emphasizing:

1. **Correctness over speed**: Tests must verify correct behavior before considering performance
2. **Determinism**: Tests should produce consistent results given the same inputs
3. **Isolation**: Unit tests should test components in isolation with proper mocking
4. **Maintainability**: Tests should be clear, readable, and easy to update
5. **Value-driven**: Focus testing efforts on areas that provide the highest confidence

## Test Types and Organization

### Unit Tests
- **Location**: `tests/unit/`
- **Purpose**: Test individual functions, methods, and classes in isolation
- **Dependencies**: Mock all external dependencies (filesystem, network, GPU, external APIs)
- **Speed Goal**: < 1 second per test
- **Framework**: pytest
- **Markers**: `@pytest.mark.unit`

### Integration Tests
- **Location**: `tests/integration/`
- **Purpose**: Test components working together, verify contracts between layers
- **Dependencies**: May use real filesystem, but mock external services (YouTube, APIs)
- **Speed Goal**: < 10 seconds per test
- **Framework**: pytest
- **Markers**: `@pytest.mark.integration`

### End-to-End Tests
- **Location**: `tests/integration/` (marked appropriately)
- **Purpose**: Test complete user workflows from ingest to export
- **Dependencies**: Use real fixture media files, test actual CLI commands
- **Speed Goal**: < 60 seconds per test
- **Framework**: pytest
- **Markers**: `@pytest.mark.integration`, `@pytest.mark.slow`

### Property-Based Tests
- **Location**: Within unit/ or integration/ as appropriate
- **Purpose**: Test properties that should hold across a range of inputs
- **Library**: hypothesis (when beneficial)
- **Markers**: `@pytest.mark.property`

## Coverage Goals

### Overall Coverage
- **Minimum Acceptable**: 70% line coverage
- **Target**: 80%+ line coverage
- **Critical Paths**: 90%+ coverage for main execution paths

### Per-Module Targets
- **Core Models** (`src/vaclip/models/`): 85%+
- **Configuration** (`src/vaclip/config/`): 80%+
- **Ingest Layer** (`src/vaclip/ingest/`): 80%+
- **Transcription Layer** (`src/vaclip/transcription/`): 80%+
- **Segmentation Layer** (`src/vaclip/segmentation/`): 80%+
- **Scoring Layer** (`src/vaclip/scoring/`): 80%+
- **Export Layer** (`src/vaclip/export/`): 80%+
- **Pipeline Layer** (`src/vaclip/pipeline/`): 85%+ (higher due to orchestration complexity)
- **CLI Layer** (`src/vaclip/cli/`): 75%+
- **Utils Layer** (`src/vaclip/utils/`): 80%+
- **Logging Layer** (`src/vaclip/logging/`): 75%

### Enforcement
- Coverage reports generated on every CI run
- Coverage thresholds enforced in CI (fail build if below minimum)
- Coverage reports uploaded as artifacts for review
- Gradual improvement expected - initial focus on critical paths

## Testing Pyramid

VAClip follows the classic testing pyramid with emphasis on unit tests:

```
                    E2E Tests (10%)
                         ▲
              Integration Tests (20%)
                         ▲
                    Unit Tests (70%)
```

### Unit Tests (70%)
- **Focus**: Individual components, functions, methods
- **Dependencies**: Fully mocked
- **Speed**: Very fast (<1s per test)
- **Frequency**: Run on every commit
- **Maintenance**: Low cost to maintain

### Integration Tests (20%)
- **Focus**: Component interactions, contract verification
- **Dependencies**: Real filesystem, mocked external services
- **Speed**: Moderate (<10s per test)
- **Frequency**: Run on every commit (may be skipped in resource-constrained CI)
- **Maintenance**: Moderate cost

### End-to-End Tests (10%)
- **Focus**: Complete user workflows
- **Dependencies**: Real fixture media, actual CLI invocation
- **Speed**: Slow (<60s per test)
- **Frequency**: Run on every commit (may run less frequently in CI)
- **Maintenance**: Higher cost but highest confidence

## Test Execution and CI

### Local Development
```bash
# Run all tests
pytest

# Run only unit tests (fastest feedback)
pytest -m "unit"

# Run only integration tests
pytest -m "integration"

# Run tests with coverage
pytest --cov=src/vaclip --cov-report=term-missing

# Run a specific test file
pytest tests/unit/test_models.py

# Run tests matching a keyword
pytest -k "transcript"
```

### Continuous Integration
CI pipeline executes the following:
1. **Linting**: `ruff check src/vaclip tests/`
2. **Type Checking**: `mypy src/vaclip`
3. **Unit Tests**: `pytest -m "unit" --cov=src/vaclip --cov-report=xml`
4. **Integration Tests**: `pytest -m "integration" --timeout=300`
5. **Coverage Report**: Upload coverage.xml to code coverage service
6. **Artifact Preservation**: Save test logs and coverage reports

### Test Timeout Settings
- Unit tests: 30 seconds default
- Integration tests: 5 minutes default (configurable via markers)
- E2E tests: 10 minutes default

## Best Practices

### Test Organization
1. **One assert per test** when possible (clear purpose)
2. **Descriptive test names**: `test_[what]_[when]_[expect]`
3. **Group related tests** in classes when using pytest classes
4. **Use fixtures** for common setup/teardown
5. **Keep tests independent** - no test should depend on another's state

### Writing Effective Tests
1. **Arrange-Act-Assert (AAA)** pattern:
   ```python
   def test_something():
       # Arrange: Set up preconditions and inputs
       # Act: Call the function/method under test
       # Assert: Verify the expected outcome
   ```
2. **Test boundary conditions** and edge cases
3. **Test error conditions** and exception handling
4. **Test the happy path** (normal operation)
5. **Avoid testing implementation details** - focus on behavior

### Test Naming Conventions
- **Test files**: `test_[module_name].py`
- **Test classes** (when used): `Test[ClassName]`
- **Test functions/methods**: `test_[description_of_behavior]`
- **Descriptive names** are preferred over cryptic abbreviations

### Documentation in Tests
1. **Docstrings** for complex test functions
2. **Comments** explaining non-obvious test logic
3. **Clear variable names** that indicate purpose
4. **Avoid magic numbers** - use named constants when meaningful

## Mocking and Test Doubles

### Mocking Framework
- Primary: `unittest.mock` (built into Python)
- Alternative: `pytest-mock` fixture when beneficial

### What to Mock
1. **External APIs and services** (YouTube, OpenRouter, etc.)
2. **File system operations** (when testing logic, not I/O)
3. **Hardware/GPU access** (torch.cuda, etc.)
4. **Subprocess calls** (FFmpeg, yt-dlp when not testing integration)
5. **Random number generation** (for deterministic tests)
6. **Time-dependent functions** (datetime.now(), time.time())

### What NOT to Mock
1. **Pure functions** (deterministic functions with no side effects)
2. **Simple data classes** (Pydantic models, dataclasses)
3. **Internal helper functions** (unless complex enough to warrant isolation)
4. **Constants and configuration values**

### Mocking Examples

#### Mocking External Libraries
```python
def test_ytdlp_download(mock_ytdl):
    # Arrange
    mock_instance = MagicMock()
    mock_ytdl.return_value = mock_instance
    mock_instance.download.return_value = None
    
    # Act
    result = ytdlp_adapter.ingest("https://youtube.com/watch?v=test")
    
    # Assert
    mock_ytdl.assert_called_once()
    mock_instance.download.assert_called_once()
```

#### Mocking Subprocess Calls
```python
def test_ffmpeg_extraction(mock_subprocess_run):
    # Arrange
    mock_subprocess_run.return_value = CompletedProcess(
        args=["ffmpeg", "-i", "input.mp4", "-f", "wav", "output.wav"],
        returncode=0,
        stdout=b"",
        stderr=b""
    )
    
    # Act
    audio_path = extract_audio(Path("input.mp4"))
    
    # Assert
    mock_subprocess_run.assert_called_once()
    assert audio_path == Path("output.wav")
```

#### Mocking File System Operations
```python
def test_file_exists(mock_path_exists):
    # Arrange
    mock_path_exists.return_value = True
    
    # Act
    result = file_exists(Path("/some/path"))
    
    # Assert
    assert result is True
    mock_path_exists.assert_called_once_with(Path("/some/path"))
```

## Test Data Management

### Fixture Strategy
1. **Built-in fixtures**: Small data generated in tests (ideal for unit tests)
2. **Fixture files**: Committed test media files (for integration tests)
3. **Temporary files**: Created in `tmp_path` fixture (isolated per test)
4. **External fixtures**: Downloaded/generated as needed (marked appropriately)

### Media Fixtures
VAClip maintains a set of small, committed media files for integration testing:
- `tests/fixtures/sample_podcast.mp3` (30s audio)
- `tests/fixtures/sample_video.mp4` (10s video)
- `tests/fixtures/sample_audio.wav` (5s audio for transcription tests)

These files are:
- Small (< 500KB each)
- Copyright-free or synthetic
- Generated using FFmpeg commands
- Regenerable if lost

### Sensitive Data
- **Never commit** API keys, tokens, or passwords
- Use environment variables for test configuration
- Mock external services that require authentication
- Use test-specific credentials that can be safely committed

## Performance Testing

### When to Performance Test
1. **After major algorithm changes**
2. **When optimizing critical paths**
3. **Before major releases**
4. **When addressing performance issues**

### Performance Test Guidelines
1. **Baseline first**: Measure performance before optimization
2. **Isolate variables**: Change one thing at a time
3. **Use realistic data**: Test with production-like data volumes
4. **Measure multiple runs**: Account for variability
5. **Report meaningfully**: Include mean, median, p95, etc.
6. **Check for regressions**: Compare against baseline

### Performance Test Locations
- **Location**: `tests/performance/` (when created)
- **Markers**: `@pytest.mark.performance`
- **Frequency**: Run less frequently (nightly, pre-release)
- **Reporting**: Generate performance reports and track trends

### Key Performance Metrics
1. **End-to-end latency**: Time from source to exported clips
2. **Stage latency**: Time spent in each pipeline stage
3. **Throughput**: Files processed per unit time
4. **Resource utilization**: CPU, GPU, memory, disk I/O
5. **Scalability**: Performance with increasing workloads

## Security Testing

### Security Test Scope
1. **Input validation**: Protection against injection attacks
2. **File path safety**: Prevention of directory traversal
3. **Command injection**: Safe subprocess usage
4. **Information disclosure**: Proper error handling
5. **Dependency vulnerabilities**: Regular dependency scanning

### Security Test Practices
1. **Use security scanning tools**:
   - `bandit` for Python security issues
   - `safety` for dependency vulnerabilities
   - `pip-audit` for known vulnerable packages
2. **Write security-focused tests**:
   - Test file path validation
   - Test command argument sanitization
   - Test error message information disclosure
3. **Regular dependency updates**:
   - Monitor for security advisories
   - Update dependencies promptly
4. **Secure defaults**:
   - Fail securely (deny by default)
   - Principle of least privilege
   - Defense in depth

### Security Test Locations
- **Location**: Integrated into unit/ and integration/ tests
- **Markers**: `@pytest.mark.security`
- **Examples**:
  - Testing that user input doesn't lead to path traversal
  - Verifying that shell commands are properly escaped
  - Checking that error messages don't leak sensitive information
  - Validating that file uploads are restricted to safe extensions

## Test Maintenance

### Regular Activities
1. **Review test failures** promptly
2. **Update tests** when interfaces change
3. **Remove obsolete tests** when features are removed
4. **Improve test coverage** for low-coverage areas
5. **Refactor messy tests** for better maintainability
6. **Update test fixtures** as needed

### Test Debt Reduction
1. **Identify slow tests** and optimize or mark appropriately
2. **Consolidate duplicate tests** into parameterized tests
3. **Replace brittle tests** with more robust versions
4. **Improve test isolation** to reduce inter-test dependencies
5. **Enhance test diagnostics** for faster failure investigation

## Definition of Done for Testing

A feature is considered adequately tested when:

1. **Unit tests exist** for all public functions and methods
2. **Unit test coverage** meets or exceeds module targets
3. **Integration tests exist** for cross-component interactions
4. **Edge cases and error conditions** are tested
5. **Tests are deterministic** and produce consistent results
6. **Tests are maintainable** and clear in intent
7. **Mocking is appropriate** and doesn't test implementation details
8. **Test names are descriptive** and follow conventions
9. **Tests pass consistently** in local and CI environments
10. **Coverage reports** show acceptable levels and trends

## References and Further Reading

1. **pytest documentation**: https://docs.pytest.org/
2. **hypothesis documentation**: https://hypothesis.works/
3. **Testing Pyramid**: Martin Fowler's article on the test pyramid
4. **Google Testing Blog**: Various articles on testing best practices
5. **Python Testing with pytest** by Brian Okken (book)
6. **Unit Testing Principles, Practices, and Patterns** by Vladimir Khorikov (book)

--- 

*This testing strategy should be reviewed and updated periodically as the project evolves and testing practices improve.*