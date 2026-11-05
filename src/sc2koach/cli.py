"""Command-line interface (thin wrapper over the core library)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from . import __version__
from .errors import Sc2KoachError
from .gametime import fmt_mmss, loop_to_seconds
from .parser import load_replay

app = typer.Typer(add_completion=False, no_args_is_help=True, help="sc2Koach replay coach.")

ReplayArg = Annotated[Path, typer.Argument(help="Path to a .SC2Replay file")]


def _fail(err: Sc2KoachError) -> None:
    typer.echo(f"error: {err}", err=True)
    raise typer.Exit(err.exit_code)


@app.command()
def info(replay: ReplayArg) -> None:
    """Show teams, players, lobby slots and MMR for a replay."""
    try:
        r, mode = load_replay(replay)
    except Sc2KoachError as err:
        _fail(err)
    typer.echo(
        f"{r.map_name} | {mode.mode} | build {r.build} | {fmt_mmss(loop_to_seconds(r.frames))}"
    )
    for w in mode.warnings:
        typer.echo(f"warning: {w}", err=True)
    for team in r.teams:
        typer.echo(f"Team {team.number} ({team.result})")
        for p in sorted(team.players, key=lambda p: p.sid):
            rating = p.init_data.get("scaled_rating")
            mmr = rating if rating and rating > 0 else "n/a"
            typer.echo(
                f"  slot {p.sid}  {p.name:<20} {p.play_race:<8} MMR {mmr:<6} {p.toon_handle}"
            )


@app.command()
def analyze(
    replay: ReplayArg,
    output: Annotated[Path | None, typer.Option("-o", "--output", help="Report path")] = None,
) -> None:
    """Write a coaching report (not implemented yet; milestone M4)."""
    typer.echo("error: analyze is not implemented yet (milestone M4).", err=True)
    raise typer.Exit(1)


@app.command()
def version() -> None:
    """Print the sc2Koach version."""
    typer.echo(__version__)


if __name__ == "__main__":
    app()
