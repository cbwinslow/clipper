# VAClip Makefile
# Developer workflow shortcuts for installation, linting, testing, and running.
# All commands assume an activated Python 3.11+ virtual environment.
#
# Usage:
#   make install     Install project and dev dependencies
#   make lint        Run ruff linter
#   make format      Auto-format with ruff
#   make typecheck   Run mypy type checker
#   make test        Run pytest (all tests)
#   make test-unit   Run only unit tests
#   make test-int    Run only integration tests
#   make run         Run pipeline (example)
#   make clean       Remove generated artifacts
#   make clean-all   Remove everything including venv

.PHONY: install install-dev lint format typecheck test test-unit test-int \
        run clean clean-all check help

# -------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------

PYTHON      ?= python3
VENV        ?= .venv
PIP         := $(VENV)/bin/pip
PYTHON_BIN  := $(VENV)/bin/python
RUFF        := $(VENV)/bin/ruff
MYPY        := $(VENV)/bin/mypy
PYTEST      := $(VENV)/bin/pytest
VACLIP      := $(VENV)/bin/vaclip

SRC_DIR     := src
TESTS_DIR   := tests
DOCS_DIR    := docs

# -------------------------------------------------------------------------
# Installation
# -------------------------------------------------------------------------

$(VENV):  ## Create virtual environment
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip

install: $(VENV)  ## Install project in editable mode with all dependencies
	$(PIP) install -e ".[dev]"
	@echo "Installation complete. Activate with: source $(VENV)/bin/activate"

install-dev: install  ## Install additional development tools
	$(PIP) install pre-commit
	$(VENV)/bin/pre-commit install
	@echo "Dev tools installed and pre-commit hooks activated."

# -------------------------------------------------------------------------
# Code Quality
# -------------------------------------------------------------------------

lint:  ## Run ruff linter (no fixes)
	$(RUFF) check $(SRC_DIR) $(TESTS_DIR)

format:  ## Auto-fix style issues with ruff
	$(RUFF) check --fix $(SRC_DIR) $(TESTS_DIR)
	$(RUFF) format $(SRC_DIR) $(TESTS_DIR)

typecheck:  ## Run mypy type checker
	$(MYPY) $(SRC_DIR)/vaclip --ignore-missing-imports

check: lint typecheck  ## Run all code quality checks

# -------------------------------------------------------------------------
# Testing
# -------------------------------------------------------------------------

test:  ## Run all tests with coverage report
	$(PYTEST) $(TESTS_DIR) -v \
		--tb=short \
		--cov=$(SRC_DIR)/vaclip \
		--cov-report=term-missing \
		--cov-report=html:htmlcov

test-unit:  ## Run only unit tests (fast, no I/O)
	$(PYTEST) $(TESTS_DIR)/unit -v --tb=short

test-int:  ## Run only integration tests
	$(PYTEST) $(TESTS_DIR)/integration -v --tb=short

test-ci:  ## Run tests in CI mode (fail fast, no coverage HTML)
	$(PYTEST) $(TESTS_DIR) -v --tb=short -x \
		--cov=$(SRC_DIR)/vaclip \
		--cov-report=term-missing

# -------------------------------------------------------------------------
# Running the CLI
# -------------------------------------------------------------------------

run:  ## Quick run example (override SOURCE= and PROFILE= from command line)
	$(VACLIP) run $(SOURCE) --profile $(PROFILE) --max-clips 5

run-plan:  ## Dry-run plan (no downloads or processing)
	$(VACLIP) plan $(SOURCE) --profile podcast

run-info:  ## Print media info for a source
	$(VACLIP) info $(SOURCE)

# -------------------------------------------------------------------------
# Cleanup
# -------------------------------------------------------------------------

clean:  ## Remove cache, logs, output clips, build artifacts
	rm -rf cache/ logs/ output/ .pytest_cache/ htmlcov/ \
		.mypy_cache/ dist/ build/ \
		$(SRC_DIR)/vaclip.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Artifacts cleaned."

clean-all: clean  ## Remove everything including virtual environment
	rm -rf $(VENV)
	@echo "Virtual environment removed. Run 'make install' to start fresh."

# -------------------------------------------------------------------------
# Help
# -------------------------------------------------------------------------

help:  ## Show this help message
	@echo ""
	@echo "VAClip Developer Commands"
	@echo "========================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""

.DEFAULT_GOAL := help
