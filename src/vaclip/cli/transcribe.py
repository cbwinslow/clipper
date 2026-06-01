"""Placeholder for ${mod} CLI commands."""
from __future__ import annotations

import typer

app = typer.Typer(help="Placeholder for ${mod}.")

@app.command()
def placeholder():
    """Placeholder command."""
    typer.echo("This is a placeholder for ${mod} commands.")
