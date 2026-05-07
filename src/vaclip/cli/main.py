"""VAClip CLI - main entry point.

All CLI commands are registered here via Typer.
Use `vaclip --help` to see available commands.

Agent Notes:
- Add new command groups by importing and adding sub-apps
- Each command module lives in src/vaclip/cli/commands/
- Use @app.callback() for global options (verbosity, config path)
- Always use structured logging, never bare print()
"""

from __future__ import annotations

import typer
from rich.console import Console

from vaclip.__version__ import __version__
from vaclip.cli.commands import (
    export,
    ingest,
    pipeline,
    score,
    segment,
    transcribe,
)
from vaclip.logging.setup import configure_logging

app = typer.Typer(
    name="vaclip",
    help="VAClip - Automatic video clipping powered by local AI.",
    add_completion=True,
    rich_markup_mode="rich",
    no_args_is_help=True,
)

console = Console()

# Register sub-command groups
app.add_typer(ingest.app, name="ingest", help="Ingest media from local files or remote sources.")
app.add_typer(transcribe.app, name="transcribe", help="Transcribe audio using faster-whisper.")
app.add_typer(segment.app, name="segment", help="Detect shots and generate candidate clips.")
app.add_typer(score.app, name="score", help="Score candidate clips by profile and intent.")
app.add_typer(export.app, name="export", help="Export top-ranked clips via FFmpeg.")
app.add_typer(pipeline.app, name="run", help="Run full pipeline end-to-end.")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Show version and exit."),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose/debug logging."),
    config: str = typer.Option(None, "--config", "-c", help="Path to config YAML file."),
) -> None:
    """VAClip - Quality-first automatic video clipping.

    Run `vaclip COMMAND --help` for details on each command.
    """
    if version:
        console.print(f"[bold green]vaclip[/bold green] v{__version__}")
        raise typer.Exit()

    configure_logging(verbose=verbose)

    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())


if __name__ == "__main__":
    app()
