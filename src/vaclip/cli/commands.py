"""vaclip.cli.commands

Typer-based CLI entry points for the VAClip pipeline.
All commands delegate to VAClipPipeline and emit structured logs.

Usage:
    vaclip run   <source> [OPTIONS]
    vaclip plan  <source> [OPTIONS]
    vaclip info  <source>
    vaclip clean [OPTIONS]

Agent Instructions:
  - Add new sub-commands by defining a new @app.command() function
  - Use rich for pretty console output (progress bars, tables)
  - Keep command logic thin - delegate immediately to pipeline/services
  - All errors should propagate as typer.Exit(code=1) with a logged message
  - Add --version flag via version_callback pattern
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import structlog
import typer
from rich.console import Console
from rich.table import Table

from vaclip.config.settings import Settings, load_settings
from vaclip.models.schemas import FramingStrategy, Profile

log = structlog.get_logger(__name__)
console = Console()

# ---------------------------------------------------------------------------
# Typer application
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="vaclip",
    help="VAClip: AI-powered video highlight extractor.",
    add_completion=True,
    pretty_exceptions_show_locals=False,
)


def _version_callback(value: bool) -> None:  # noqa: FBT001
    if value:
        from vaclip import __version__

        typer.echo(f"vaclip {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(  # noqa: UP007
        None,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """VAClip root callback - handles global flags."""


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command("run")
def cmd_run(
    source: str = typer.Argument(..., help="URL or local path to media file."),
    profile: Profile = typer.Option(
        Profile.PODCAST, "--profile", "-p", help="Processing profile."
    ),
    framing: FramingStrategy = typer.Option(
        FramingStrategy.WIDE, "--framing", "-f", help="Output framing strategy."
    ),
    max_clips: int = typer.Option(10, "--max-clips", "-n", help="Maximum clips to export."),
    config: Optional[Path] = typer.Option(  # noqa: UP007
        None, "--config", "-c", help="Path to YAML config override."
    ),
    from_stage: str = typer.Option(
        "ingest", "--from-stage", help="Resume from pipeline stage."
    ),
) -> None:
    """Run the full VAClip pipeline on a media source.

    Downloads / ingests the source, transcribes audio, scores segments for
    highlight moments, and exports short clips to the output directory.

    Examples:
        vaclip run https://youtube.com/watch?v=XYZ --profile podcast
        vaclip run ./my_video.mp4 --framing vertical --max-clips 5
    """
    log.info(
        "cli.run",
        source=source,
        profile=profile.value,
        framing=framing.value,
        max_clips=max_clips,
    )

    settings: Settings = load_settings(config)

    # TODO: Instantiate VAClipPipeline and call .run()
    # from vaclip.pipeline.pipeline import VAClipPipeline, PipelineStage
    # pipeline = VAClipPipeline(settings=settings)
    # result = pipeline.run(
    #     source=source,
    #     profile=profile.value,
    #     framing=framing.value,
    #     from_stage=PipelineStage[from_stage.upper()],
    #     max_clips=max_clips,
    # )
    # console.print(f"[green]Done![/green] Exported {len(result.clips)} clips.")
    raise NotImplementedError("Pipeline execution not yet wired up")


@app.command("plan")
def cmd_plan(
    source: str = typer.Argument(..., help="URL or local path to media file."),
    profile: Profile = typer.Option(Profile.PODCAST, "--profile", "-p"),
    framing: FramingStrategy = typer.Option(FramingStrategy.WIDE, "--framing", "-f"),
    max_clips: int = typer.Option(10, "--max-clips", "-n"),
    config: Optional[Path] = typer.Option(None, "--config", "-c"),  # noqa: UP007
) -> None:
    """Dry-run: log pipeline plan without executing any stages.

    Useful for verifying settings and understanding what would happen
    without downloading or processing any media.
    """
    log.info("cli.plan", source=source, profile=profile.value)
    settings: Settings = load_settings(config)

    # TODO: call pipeline.run(dry_run=True)
    console.print("[yellow]Plan mode not yet implemented.[/yellow]")
    raise NotImplementedError


@app.command("info")
def cmd_info(
    source: str = typer.Argument(..., help="URL or local path to inspect."),
) -> None:
    """Print media metadata without running the full pipeline.

    Calls the ingest adapter to extract duration, resolution, fps, and title.
    """
    log.info("cli.info", source=source)

    # TODO: call YtDlpAdapter or LocalFileAdapter .probe()
    console.print("[yellow]Info command not yet implemented.[/yellow]")
    raise NotImplementedError


@app.command("clean")
def cmd_clean(
    cache: bool = typer.Option(True, "--cache/--no-cache", help="Remove cache directory."),
    logs: bool = typer.Option(False, "--logs/--no-logs", help="Remove log files."),
    output: bool = typer.Option(False, "--output/--no-output", help="Remove output clips."),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
) -> None:
    """Remove generated artifacts (cache, logs, output clips).

    By default only cache is cleaned.  Pass --yes to skip interactive prompt.
    """
    targets: list[str] = []
    if cache:
        targets.append("cache")
    if logs:
        targets.append("logs")
    if output:
        targets.append("output")

    if not targets:
        console.print("Nothing to clean.")
        return

    if not confirm:
        typer.confirm(
            f"This will delete: {', '.join(targets)}. Continue?",
            abort=True,
        )

    settings: Settings = load_settings()
    removed: list[str] = []

    # TODO: iterate targets and delete directories
    # for target in targets:
    #     path = getattr(settings.paths, f"{target}_dir")
    #     if path.exists():
    #         shutil.rmtree(path)
    #         removed.append(str(path))

    log.info("cli.clean", removed=removed)
    console.print(f"[green]Cleaned:[/green] {removed}")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def entrypoint() -> None:
    """Package entrypoint registered in pyproject.toml [project.scripts]."""
    try:
        app()
    except Exception as exc:  # noqa: BLE001
        log.exception("cli.fatal", error=str(exc))
        sys.exit(1)


if __name__ == "__main__":
    entrypoint()
