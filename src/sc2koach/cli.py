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
    output: Annotated[
        Path | None,
        typer.Option("-o", "--output", help="Report path (default: <replay stem>.md in cwd)"),
    ] = None,
    focus: Annotated[str | None, typer.Option("--focus", help="Focus player name")] = None,
    focus_id: Annotated[
        str | None, typer.Option("--focus-id", help="Focus player toon handle")
    ] = None,
    alias: Annotated[
        list[str] | None, typer.Option("--alias", help="Other name of the focus player")
    ] = None,
    pair: Annotated[
        list[str] | None,
        typer.Option("--pair", help="Manual counterpart pair 'nameA:nameB' (repeatable)"),
    ] = None,
    config_path: Annotated[
        Path | None, typer.Option("--config", help="Config file (replaces default lookup)")
    ] = None,
) -> None:
    """Analyze a replay and write <name>.md and <name>.findings.json."""
    from .config import load_config
    from .pipeline import analyze as run_analysis
    from .report import write_outputs

    cli = {"focus": {"name": focus, "toon_handle": focus_id, "aliases": alias or []}}
    try:
        config = load_config(cli=cli, explicit_path=config_path)
        result = run_analysis(replay, config, pairs=pair or [])
    except Sc2KoachError as err:
        _fail(err)
    md_path = output if output is not None else Path.cwd() / f"{replay.stem}.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md, js = write_outputs(result, md_path, top_n=config.report.top_n)
    for w in result.warnings:
        typer.echo(f"warning [{w.code}]: {w.message}", err=True)
    typer.echo(f"wrote {md}")
    typer.echo(f"wrote {js}")


@app.command()
def version() -> None:
    """Print the sc2Koach version."""
    typer.echo(__version__)


if __name__ == "__main__":
    app()
