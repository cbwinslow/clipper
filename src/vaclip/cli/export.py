"""vaclip.cli.export

Typer-based CLI command for exporting clips from cached scored segments.
"""

from __future__ import annotations

import json
from pathlib import Path

import structlog
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from vaclip.config.settings import Settings, load_settings
from vaclip.export.clip_exporter import ClipExporter
from vaclip.models.media import MediaAsset
from vaclip.models.schemas import FramingStrategy

# Create the Typer app for this command module
app = typer.Typer(help="Export top-ranked clips via FFmpeg.")
log = structlog.get_logger(__name__)
console = Console()


@app.command("export")
def cmd_export(
    source: str = typer.Argument(
        ..., help="URL or local path to media file (used to find cached assets)."
    ),
    max_clips: int = typer.Option(10, "--max-clips", "-n", help="Maximum clips to export."),
    framing: FramingStrategy = typer.Option(
        FramingStrategy.WIDE, "--framing", "-f", help="Output framing strategy."
    ),
    config: Path | None = typer.Option(
        None, "--config", "-c", help="Path to YAML config override."
    ),
) -> None:
    """Export clips from cached scored segments.

    Loads the MediaAsset and scored segments from cache for the given source,
    then exports the top-scoring segments as video clips.

    Examples:
        vaclip export ./my_video.mp4 --max-clips 5 --framing vertical
        vaclip export https://youtube.com/watch?v=XYZ --max-clips 3
    """
    log.info("cli.export", source=source, max_clips=max_clips, framing=framing.value)

    settings: Settings = load_settings(config)

    # Find the cached MediaAsset for this source
    media_asset = _find_media_asset(source, settings)
    if media_asset is None:
        console.print(f"[red]Error:[/red] No cached MediaAsset found for source: {source}")
        console.print(
            "Run the pipeline (or at least ingest and scoring stages) "
            "first to cache the assets."
        )
        raise typer.Exit(code=1)

    # Load scored segments from cache
    scored_segments = _load_scored_segments(media_asset, settings)
    if not scored_segments:
        console.print(f"[red]Error:[/red] No scored segments found for asset {media_asset.id}")
        console.print(
            "Run the scoring stage first to generate and cache scored segments."
        )
        raise typer.Exit(code=1)

    console.print(f"[blue]Found {len(scored_segments)} scored segments[/blue]")
    n_clips = min(max_clips, len(scored_segments))
    console.print(
        f"[blue]Exporting top {n_clips} clips with {framing.value} framing[/blue]"
    )

    # Export the clips
    exporter = ClipExporter(output_dir=settings.paths.output_dir)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=False,
    ) as progress:
        total_clips = min(max_clips, len(scored_segments))
        task = progress.add_task("[cyan]Exporting clips...", total=total_clips)

        def on_progress(current: int, total: int):
            progress.update(task, completed=current)

        clips = exporter.export(
            media=media_asset,
            segments=scored_segments,
            framing=framing.value,
            max_clips=max_clips,
        )

        progress.update(task, completed=len(clips))

    # Show summary
    if clips:
        _show_export_summary(clips, settings)
        out_dir = settings.paths.output_dir
        console.print(f"[green]Done![/green] Exported {len(clips)} clips to {out_dir}")
    else:
        console.print("[yellow]No clips were exported.[/yellow]")


def _find_media_asset(source: str, settings: Settings) -> MediaAsset | None:
    """Find the cached MediaAsset for the given source.

    Looks through cache/*/media_asset.json files to find one matching the source.
    """
    cache_dir = settings.paths.cache_dir

    if not cache_dir.exists():
        return None

    # Look for media_asset.json files in cache subdirectories
    for asset_dir in cache_dir.iterdir():
        if asset_dir.is_dir():
            media_asset_file = asset_dir / "media_asset.json"
            if media_asset_file.exists():
                try:
                    asset_data = json.loads(media_asset_file.read_text())
                    asset = MediaAsset.model_validate(asset_data)

                    # Check if this asset matches our source
                    if _sources_match(asset.source_url, source):
                        return asset
                except Exception as e:
                    log.debug(
                        "cli.export.skip_asset_file",
                        file=str(media_asset_file),
                        error=str(e),
                    )
                    continue

    return None


def _sources_match(source1: str, source2: str) -> bool:
    """Check if two source strings refer to the same media.

    Handles comparison of URLs vs local paths, normalization, etc.
    """
    # Normalize both sources for comparison
    norm1 = _normalize_source(source1)
    norm2 = _normalize_source(source2)
    return norm1 == norm2


def _normalize_source(source: str) -> str:
    """Normalize a source string for comparison.

    Converts to absolute path for local files, leaves URLs as-is.
    """
    try:
        path = Path(source)
        if path.is_absolute() or path.exists():
            # It's a local file path
            return str(path.resolve())
    except Exception:
        pass

    # Treat as URL or non-existent path
    return source


def _load_scored_segments(media_asset: MediaAsset, settings: Settings) -> list:
    """Load scored segments from cache for the given media asset."""
    # Use the media asset ID to find the scored segments file
    asset_id_str = str(media_asset.id)
    score_file = settings.paths.scores_dir / f"{asset_id_str}.json"

    if not score_file.exists():
        # Try alternative: use the file stem (as done in scoring)
        alt_score_file = settings.paths.scores_dir / f"{media_asset.local_path.stem}.json"
        if alt_score_file.exists():
            score_file = alt_score_file
        else:
            return []

    try:
        # Load the scored segments data
        score_data = json.loads(score_file.read_text())

        # Convert back to ScoredSegment objects
        from vaclip.models.media import ScoredSegment
        from vaclip.models.schemas import HighlightType, Segment, SignalScore

        scored_segments = []
        for item in score_data:
            # Reconstruct Segment
            segment_data = item["segment"]
            segment = Segment(
                id=segment_data["id"],
                text=segment_data["text"],
                start=segment_data["start"],
                end=segment_data["end"],
                words=[],  # Words not saved in the simplified score format
            )

            # Reconstruct SignalScores
            signals = []
            for signal_data in item.get("signals", []):
                signal = SignalScore(
                    name=signal_data["name"],
                    raw=signal_data["raw"],
                    normalized=signal_data["normalized"],
                    weight=signal_data["weight"],
                )
                signals.append(signal)

            # Create ScoredSegment
            scored_segment = ScoredSegment(
                segment=segment,
                highlight_type=HighlightType(item["highlight_type"]),
                signals=signals,
                score=item["score"],
                rank=item["rank"],
            )
            scored_segments.append(scored_segment)

        return scored_segments
    except Exception as e:
        log.error("cli.export.load_scored_failed", error=str(e), score_file=str(score_file))
        return []


def _show_export_summary(clips: list, settings: Settings) -> None:
    """Show a summary of exported clips."""
    table = Table(title="Exported Clips")
    table.add_column("Rank", style="cyan", justify="right")
    table.add_column("Start", style="green")
    table.add_column("End", style="green")
    table.add_column("Score", style="magenta", justify="right")
    table.add_column("Output File", style="blue")

    for clip in clips:
        table.add_row(
            str(clip.scored_segment.rank),
            f"{clip.bounds.start:.2f}s",
            f"{clip.bounds.end:.2f}s",
            f"{clip.scored_segment.score:.3f}",
            clip.output_path.name,
        )

    console.print(table)

    # Show total output directory size
    total_size = sum(clip.file_size_bytes or 0 for clip in clips)
    console.print(f"\n[blue]Total output size:[/blue] {total_size / (1024*1024):.2f} MB")
    console.print(f"[blue]Output directory:[/blue] {settings.paths.output_dir}")


# Entrypoint for when this module is run directly
if __name__ == "__main__":
    app()
