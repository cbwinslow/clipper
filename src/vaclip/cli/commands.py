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

import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import structlog
import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from vaclip.config.settings import Settings, load_settings
from vaclip.models.schemas import FramingStrategy, Profile
from vaclip.pipeline.pipeline import PipelineResult, PipelineStage, VAClipPipeline

if TYPE_CHECKING:
    pass

log = structlog.get_logger(__name__)
console = Console()

# Export command functions for use in main app
__all__ = ["cmd_run", "cmd_plan", "cmd_info", "cmd_clean"]

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
    version: bool | None = typer.Option(  # noqa: UP007
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
    source: str = typer.Option(..., "--source", "-s", help="URL or local path to media file."),
    profile: Profile = typer.Option(
        Profile.PODCAST, "--profile", "-p", help="Processing profile."
    ),
    framing: FramingStrategy = typer.Option(
        FramingStrategy.WIDE, "--framing", "-f", help="Output framing strategy."
    ),
    max_clips: int = typer.Option(10, "--max-clips", "-n", help="Maximum clips to export."),
    config: Path | None = typer.Option(  # noqa: UP007
        None, "--config", "-c", help="Path to YAML config override."
    ),
    from_stage: str = typer.Option(
        "ingest", "--from-stage", help="Resume from pipeline stage."
    ),
    output_dir: Path | None = typer.Option(  # noqa: UP007
        None, "--output-dir", "-o", help="Output directory for clips."
    ),
    dry_run: bool = typer.Option(  # noqa: UP007
        False, "--dry-run", help="Plan but do not execute."
    ),
) -> None:
    """Run the full VAClip pipeline on a media source.

    Downloads / ingests the source, transcribes audio, scores segments for
    highlight moments, and exports short clips to the output directory.

    Examples:
        vaclip run --source https://youtube.com/watch?v=XYZ --profile podcast
        vaclip run --source ./my_video.mp4 --framing vertical --max-clips 5
    """
    log.info(
        "cli.run",
        source=source,
        profile=profile.value,
        framing=framing.value,
        max_clips=max_clips,
    )

    settings: Settings = load_settings(config)
    if output_dir is not None:
        settings.paths.output_dir = output_dir
    from_stage_enum = PipelineStage[from_stage.upper()]

    # Calculate number of stages to run for progress bar
    stages_to_run = [s for s in PipelineStage if s.value >= from_stage_enum.value]
    num_stages = len(stages_to_run)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        overall_task = progress.add_task("[cyan]Running pipeline...", total=num_stages)

        def on_stage_start(stage: PipelineStage, result: PipelineResult) -> None:
            progress.update(overall_task, description=f"[cyan]Running {stage.name.lower()}...")

        def on_stage_complete(stage: PipelineStage, result: PipelineResult) -> None:
            elapsed = result.elapsed_seconds.get(stage.name, 0)
            progress.update(overall_task, advance=1)
            console.print(f"[green]✓[/green] {stage.name} completed in {elapsed:.1f}s")

        def on_stage_error(stage: PipelineStage, result: PipelineResult) -> None:
            console.print(f"[red]✗[/red] {stage.name} failed")
            # Don't advance on error since stage didn't complete successfully

        pipeline = VAClipPipeline(
            settings=settings,
            on_stage_start=on_stage_start,
            on_stage_complete=on_stage_complete,
            on_stage_error=on_stage_error,
        )
        try:
            result = pipeline.run(
                source=source,
                profile=profile.value,
                framing=framing.value,
                from_stage=from_stage_enum,
                max_clips=max_clips,
                dry_run=dry_run,
            )
            console.print(f"[green]Done![/green] Exported {len(result.clips)} clips.")
        except Exception as exc:
            log.exception("cli.run.failed", error=str(exc))
            console.print(f"[red]Pipeline failed:[/red] {exc}")
            raise typer.Exit(code=1)


@app.command("plan")
def cmd_plan(
    source: str = typer.Argument(..., help="URL or local path to media file."),
    profile: Profile = typer.Option(Profile.PODCAST, "--profile", "-p"),
    framing: FramingStrategy = typer.Option(FramingStrategy.WIDE, "--framing", "-f"),
    max_clips: int = typer.Option(10, "--max-clips", "-n"),
    config: Path | None = typer.Option(None, "--config", "-c"),  # noqa: UP007
    from_stage: str = typer.Option(
        "ingest", "--from-stage", help="Resume from pipeline stage."
    ),
) -> None:
    """Dry-run: log pipeline plan without executing any stages.

    Useful for verifying settings and understanding what would happen
    without downloading or processing any media.
    """
    log.info("cli.plan", source=source, profile=profile.value)
    settings: Settings = load_settings(config)

    from_stage_enum = PipelineStage[from_stage.upper()]
    pipeline = VAClipPipeline(settings=settings)
    pipeline.run(
        source=source,
        profile=profile.value,
        framing=framing.value,
        from_stage=from_stage_enum,
        max_clips=max_clips,
        dry_run=True,
    )

    console.print(f"[bold]Plan for:[/bold] {source}")
    console.print(f"  Profile: {profile.value}")
    console.print(f"  Framing: {framing.value}")
    console.print(f"  From stage: {from_stage_enum.name}")
    console.print(f"  Max clips: {max_clips}")
    console.print("\n[bold]Stages to run:[/bold]")
    for stage in PipelineStage:
        if stage.value >= from_stage_enum.value:
            console.print(f"  [green]{stage.name}[/green]")
        else:
            console.print(f"  [dim]{stage.name} (skipped)[/dim]")


@app.command("info")
def cmd_info(
    source: str = typer.Argument(..., help="URL or local path to inspect."),
) -> None:
    """Print media metadata without running the full pipeline.

    Calls the ingest adapter to extract duration, resolution, fps, and title.
    """
    log.info("cli.info", source=source)

    from vaclip.ingest.local_adapter import LocalFileAdapter

    if source.startswith("http"):
        console.print("[yellow]Info command for URLs requires full ingest flow.[/yellow]")
        console.print(f"Use: vaclip run --dry-run --source {source}")
    else:
        adapter = LocalFileAdapter()
        try:
            # Get basic info from ffprobe
            metadata = adapter._extract_metadata(Path(source))
            console.print(f"[bold]Source:[/bold] {source}")
            console.print(f"[bold]Duration:[/bold] {metadata['duration']:.1f}s")
            console.print(f"[bold]Resolution:[/bold] {metadata['width']}x{metadata['height']}")
            console.print(f"[bold]FPS:[/bold] {metadata['fps']}")
            console.print(f"[bold]Codec:[/bold] {metadata['codec']}")
            console.print(f"[bold]Format:[/bold] {metadata['format']}")
        except Exception as exc:
            console.print(f"[red]Error inspecting file:[/red] {exc}")
            raise typer.Exit(code=1)


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

    for target in targets:
        path = getattr(settings.paths, f"{target}_dir")
        if path.exists():
            shutil.rmtree(path)
            removed.append(str(path))

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
