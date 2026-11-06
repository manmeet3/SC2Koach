"""Player identity: focus player, roster members and counterpart pairing
(design/DESIGN.md §5 "Players, teams, identity", §10).

Matching never guesses: an ambiguous match resolves to nothing.
"""

from __future__ import annotations

from collections.abc import Sequence

from sc2koach.config import FocusConfig, RosterMember
from sc2koach.models import AnalysisWarning, Player, Team


def _match(
    players: Sequence[Player],
    toon_handle: str | None,
    name: str | None,
    aliases: Sequence[str],
) -> tuple[str, list[int]]:
    """Match by toon handle → name → aliases. Returns (stage, matching player ids) for the
    first stage with at least one match, or ("", []) when nothing matches."""
    if toon_handle:
        ids = [p.id for p in players if p.toon_handle == toon_handle]
        if ids:
            return "toon handle", ids
    if name:
        key = name.casefold()
        ids = [p.id for p in players if p.name.casefold() == key]
        if ids:
            return "name", ids
    alias_keys = {a.casefold() for a in aliases if a}
    if alias_keys:
        ids = [p.id for p in players if p.name.casefold() in alias_keys]
        if ids:
            return "alias", ids
    return "", []


def resolve_focus(
    players: list[Player], focus: FocusConfig
) -> tuple[int | None, list[AnalysisWarning]]:
    """Resolve the configured focus identity to a player id, or None with a warning."""
    configured = bool(focus.toon_handle or focus.name or any(focus.aliases))
    if not configured:
        return None, []
    stage, ids = _match(players, focus.toon_handle, focus.name, focus.aliases)
    if len(ids) == 1:
        return ids[0], []
    if len(ids) > 1:
        names = ", ".join(p.name for p in players if p.id in ids)
        return None, [
            AnalysisWarning(
                code="focus_ambiguous",
                message=(
                    f"focus player is ambiguous: {len(ids)} players match by {stage} "
                    f"({names}); writing a neutral report"
                ),
            )
        ]
    wanted = [
        f"{label} {value!r}"
        for label, value in (
            ("toon handle", focus.toon_handle),
            ("name", focus.name),
            ("aliases", focus.aliases or None),
        )
        if value
    ]
    return None, [
        AnalysisWarning(
            code="focus_not_found",
            message=(
                f"focus player not found (looked for {', '.join(wanted)}); writing a neutral report"
            ),
        )
    ]


def resolve_roster(players: list[Player], roster: list[RosterMember]) -> dict[int, str]:
    """Map player id → roster member name. Ambiguous or unmatched members are skipped;
    a player already claimed by an earlier member is not reassigned."""
    out: dict[int, str] = {}
    for member in roster:
        _, ids = _match(players, member.toon_handle, member.name, member.aliases)
        if len(ids) == 1 and ids[0] not in out:
            out[ids[0]] = member.name
    return out


def apply_pairs(
    players: list[Player], teams: list[Team], pairs: list[str]
) -> tuple[list[Player], list[AnalysisWarning]]:
    """Apply `--pair nameA:nameB` overrides in order. Returns new Player objects."""
    by_id = {p.id: p.model_copy() for p in players}
    team_of = {pid: t.id for t in teams for pid in t.players}
    warnings: list[AnalysisWarning] = []

    def bad(pair: str, reason: str) -> None:
        warnings.append(
            AnalysisWarning(code="bad_pair", message=f"ignoring --pair {pair!r}: {reason}")
        )

    def lookup(name: str) -> tuple[int | None, str | None]:
        key = name.casefold()
        ids = [p.id for p in by_id.values() if p.name.casefold() == key]
        if not ids:
            return None, f"no player named {name!r}"
        if len(ids) > 1:
            return None, f"several players named {name!r}"
        return ids[0], None

    for pair in pairs:
        if ":" not in pair:
            bad(pair, "expected <nameA>:<nameB>")
            continue
        left, right = (s.strip() for s in pair.split(":", 1))
        if not left or not right:
            bad(pair, "expected <nameA>:<nameB>")
            continue
        a, err_a = lookup(left)
        b, err_b = lookup(right)
        if a is None or b is None:
            bad(pair, err_a or err_b or "unknown player")
            continue
        team_a = team_of.get(a, by_id[a].team)
        team_b = team_of.get(b, by_id[b].team)
        if team_a == team_b:
            bad(pair, "players are on the same team")
            continue
        for pid, p in by_id.items():
            if pid not in (a, b) and p.counterpart_id in (a, b):
                by_id[pid] = p.model_copy(
                    update={"counterpart_id": None, "counterpart_source": None}
                )
        by_id[a] = by_id[a].model_copy(update={"counterpart_id": b, "counterpart_source": "manual"})
        by_id[b] = by_id[b].model_copy(update={"counterpart_id": a, "counterpart_source": "manual"})

    return [by_id[p.id] for p in players], warnings


def default_counterparts(players: list[Player], teams: list[Team]) -> list[Player]:
    """Nominal pairing: the i-th player (by lobby slot, else player id) of the first team
    is the counterpart of the i-th player of the second. Returns new Player objects."""
    by_id = {
        p.id: p.model_copy(update={"counterpart_id": None, "counterpart_source": None})
        for p in players
    }
    ordered_teams = sorted(teams, key=lambda t: t.id)
    if len(ordered_teams) != 2:
        return [by_id[p.id] for p in players]

    members = [[by_id[pid] for pid in t.players if pid in by_id] for t in ordered_teams]
    use_slots = all(p.lobby_slot is not None for team in members for p in team)
    source = "slot" if use_slots else "player_id"

    def order(p: Player) -> tuple[int, int]:
        return (p.lobby_slot or 0, p.id) if use_slots else (p.id, 0)

    team1, team2 = (sorted(team, key=order) for team in members)
    for p1, p2 in zip(team1, team2, strict=False):
        by_id[p1.id] = p1.model_copy(update={"counterpart_id": p2.id, "counterpart_source": source})
        by_id[p2.id] = p2.model_copy(update={"counterpart_id": p1.id, "counterpart_source": source})
    return [by_id[p.id] for p in players]
