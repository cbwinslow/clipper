"""VAClip pipeline CLI commands."""
from __future__ import annotations

# Import the Typer app with all pipeline commands from commands module
from vaclip.cli.commands import app

# Re-export for backwards compatibility if needed
__all__ = ["app"]
