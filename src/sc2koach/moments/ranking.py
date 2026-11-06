"""Severity, deterministic IDs and per-player / per-team ranking (design/DESIGN.md §7)."""

from __future__ import annotations

from sc2koach.models import Finding


def _id_key(f: Finding) -> tuple:
    # (start, team, player, type) per §7; the rest only breaks exact ties deterministically.
    return (
        f.start,
        f.team,
        f.player or 0,
        f.type,
        f.end,
        f.evidence["est_cost"],
        sorted((k, str(v)) for k, v in f.evidence.items()),
    )


def finalize(findings: list[Finding]) -> list[Finding]:
    """Assign severity (est_cost / max est_cost) and IDs; return findings in ID order."""
    max_cost = max((int(f.evidence["est_cost"]) for f in findings), default=0)
    width = max(3, len(str(len(findings))))
    out = []
    for i, f in enumerate(sorted(findings, key=_id_key), start=1):
        cost = int(f.evidence["est_cost"])
        severity = round(cost / max_cost, 4) if max_cost > 0 else 0.0
        out.append(f.model_copy(update={"id": f"f-{i:0{width}d}", "severity": severity}))
    return out


def _by_cost(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: (-int(f.evidence["est_cost"]), f.id))


def rank_for_player(findings: list[Finding], player_id: int, n: int) -> list[Finding]:
    """Top `n` player-scope findings for `player_id`, by est_cost desc then id."""
    mine = [f for f in findings if f.scope == "player" and f.player == player_id]
    return _by_cost(mine)[: max(0, n)]


def rank_team(findings: list[Finding], team_id: int) -> list[Finding]:
    """Team-scope findings for `team_id`, by est_cost desc then id."""
    return _by_cost([f for f in findings if f.scope == "team" and f.team == team_id])
