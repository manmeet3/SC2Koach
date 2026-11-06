"""Per-finding-type sentence templates and shared number/time formatting.

Findings carry no prose; text is rendered here from `Finding.evidence`. Second person is
used only for the focus player. Missing or None evidence values are omitted, never fatal.
"""

from __future__ import annotations

from collections.abc import Callable

from sc2koach.gametime import fmt_mmss
from sc2koach.models import AnalysisResult, Finding

NA = "n/a"

_BASE_ORDINALS = {1: "main", 2: "second", 3: "third", 4: "fourth", 5: "fifth"}


# --------------------------------------------------------------------------- formatting


def _num(value: object) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def fmt_int(value: object, default: str = NA) -> str:
    """Integer with thousands separators, e.g. 1640 -> "1,640"."""
    v = _num(value)
    return default if v is None else f"{round(v):,}"


def fmt_dec(value: object, default: str = NA) -> str:
    """One decimal place with thousands separators, e.g. 24.5."""
    v = _num(value)
    return default if v is None else f"{v:,.1f}"


def fmt_time(value: object, default: str = NA) -> str:
    v = _num(value)
    return default if v is None else fmt_mmss(v)


def fmt_secs(value: object, default: str = NA) -> str:
    v = _num(value)
    return default if v is None else f"{round(v):,}s"


def fmt_pct(ratio: object, default: str = NA) -> str:
    v = _num(ratio)
    return default if v is None else f"{round(v * 100)}%"


# --------------------------------------------------------------------------- subjects


class _Subject:
    """Grammatical subject for a player: "You were" vs "blackSheep was"."""

    def __init__(self, name: str, second_person: bool) -> None:
        self.second = second_person
        self.name = name

    @property
    def nom(self) -> str:
        return "You" if self.second else self.name

    @property
    def obj(self) -> str:
        return "you" if self.second else self.name

    @property
    def poss(self) -> str:
        return "Your" if self.second else f"{self.name}'s"

    def be(self) -> str:
        return f"{self.nom} {'were' if self.second else 'was'}"


def _player_name(result: AnalysisResult, pid: object) -> str:
    if isinstance(pid, bool):
        return str(pid)
    if isinstance(pid, int):
        for p in result.replay.players:
            if p.id == pid:
                return p.name
        return f"Player {pid}"
    if pid is None:
        return "A player"
    return str(pid)


def _player_subject(result: AnalysisResult, pid: object) -> _Subject:
    focus = result.replay.focus_player_id
    second = focus is not None and isinstance(pid, int) and pid == focus
    return _Subject(_player_name(result, pid), second)


def _team_label(result: AnalysisResult, team_id: int) -> str:
    """ "Your team" if the focus player is on `team_id`, else "Team <n>"."""
    focus = result.replay.focus_player_id
    if focus is not None:
        for t in result.replay.teams:
            if t.id == team_id and focus in t.players:
                return "Your team"
    return f"Team {team_id}"


def _join_parts(parts: list[str]) -> str:
    return "; ".join(p for p in parts if p)


def _paren(parts: list[str]) -> str:
    joined = _join_parts(parts)
    return f" ({joined})" if joined else ""


# --------------------------------------------------------------------------- templates


def _supply_block(f: Finding, r: AnalysisResult) -> str:
    ev = f.evidence
    s = _player_subject(r, f.player)
    text = f"{s.be()} supply blocked at {fmt_mmss(f.start)}"
    if _num(ev.get("duration_s")) is not None:
        text += f" for at least {fmt_secs(ev['duration_s'])}"
    if _num(ev.get("supply")) is not None:
        text += f" ({fmt_int(ev['supply'])} supply)"
    if _num(ev.get("minerals")) is not None:
        text += f" with {fmt_int(ev['minerals'])} minerals banked"
    return text


def _high_bank(f: Finding, r: AnalysisResult) -> str:
    ev = f.evidence
    s = _player_subject(r, f.player)
    threshold = ev.get("threshold")
    text = f"{s.nom} banked"
    text += f" over {fmt_int(threshold)}" if _num(threshold) is not None else " heavily"
    if _num(ev.get("duration_s")) is not None:
        text += f" for {fmt_secs(ev['duration_s'])}"
    text += f" from {fmt_mmss(f.start)}"
    if _num(ev.get("peak")) is not None:
        text += f" (peak {fmt_int(ev['peak'])})"
    return text


def _low_workers(f: Finding, r: AnalysisResult) -> str:
    ev = f.evidence
    s = _player_subject(r, f.player)
    workers = ev.get("workers")
    if _num(workers) is not None:
        text = f"{s.nom} had {fmt_int(workers)} workers at 4:00"
    else:
        text = f"{s.nom} had too few workers at 4:00"
    parts = []
    if _num(ev.get("threshold")) is not None:
        parts.append(f"target {fmt_int(ev['threshold'])}")
    if _num(ev.get("game_avg")) is not None:
        parts.append(f"game average {fmt_dec(ev['game_avg'])}")
    if _num(ev.get("team_avg")) is not None:
        parts.append(f"team average {fmt_dec(ev['team_avg'])}")
    if _num(ev.get("counterpart")) is not None:
        parts.append(f"counterpart {fmt_int(ev['counterpart'])}")
    return text + _paren(parts)


def _late_expansion(f: Finding, r: AnalysisResult) -> str:
    ev = f.evidence
    s = _player_subject(r, f.player)
    base_n = _num(ev.get("base"))
    if base_n is None:
        base_label = "base"
    elif int(base_n) in _BASE_ORDINALS:
        base_label = f"{_BASE_ORDINALS[int(base_n)]} base"
    else:
        base_label = f"base {int(base_n)}"
    finished = ev.get("finished")
    missing = bool(_num(ev.get("missing"))) or _num(finished) is None
    parts = []
    if _num(ev.get("target_s")) is not None:
        parts.append(f"target {fmt_time(ev['target_s'])}")
    if _num(ev.get("counterpart_finished")) is not None:
        parts.append(f"counterpart finished {fmt_time(ev['counterpart_finished'])}")
    if missing:
        text = f"{s.nom} had no {base_label} by {fmt_mmss(f.end)}"
    else:
        text = f"{s.poss} {base_label} finished {fmt_time(finished)}"
    return text + _paren(parts)


def _army_collapse(f: Finding, r: AnalysisResult) -> str:
    ev = f.evidence
    s = _player_subject(r, f.player)
    lost, before = ev.get("lost"), ev.get("army_before")
    window = _num(ev.get("window_s"))
    end = f.start + window if window is not None else f.end
    if _num(lost) is not None and _num(before) is not None:
        text = f"{s.nom} lost {fmt_int(lost)} of {fmt_int(before)} army value"
    elif _num(lost) is not None:
        text = f"{s.nom} lost {fmt_int(lost)} army value"
    else:
        text = f"{s.poss} army collapsed"
    text += f" {fmt_mmss(f.start)}–{fmt_mmss(end)}"
    if _num(ev.get("killed")) is not None:
        text += f" while killing {fmt_int(ev['killed'])}"
    return text


def _early_ally_death(f: Finding, r: AnalysisResult) -> str:
    ev = f.evidence
    departed = ev.get("departed_player")
    if departed is None or isinstance(departed, float):
        departed = int(departed) if isinstance(departed, float) else f.player
    s = _player_subject(r, departed)
    how = ev.get("how")
    if how == "eliminated":
        verb = f"{s.obj} {'were' if s.second else 'was'} eliminated"
    elif how == "left":
        verb = f"{s.obj} left"
    else:
        verb = f"{s.obj} departed"
    team = _team_label(r, f.team)
    played_on = ev.get("played_on_s")
    if _num(played_on) is not None:
        text = f"{team} played a player down for {fmt_time(played_on)}"
    else:
        text = f"{team} played a player down"
    return f"{text} after {verb} at {fmt_mmss(f.start)}"


def _team_army_deficit(f: Finding, r: AnalysisResult) -> str:
    ev = f.evidence
    team = _team_label(r, f.team)
    poss = "Your team's" if team == "Your team" else f"{team}'s"
    ratio = r.generated_with.thresholds.get("team_army_deficit_ratio")
    if _num(ratio) is not None:
        text = f"{poss} army value was at or below {fmt_pct(ratio)} of the enemy's"
    else:
        text = f"{poss} army value trailed the enemy's"
    text += f" {fmt_mmss(f.start)}–{fmt_mmss(f.end)}"
    parts = []
    if _num(ev.get("min_ratio")) is not None:
        parts.append(f"lowest {fmt_pct(ev['min_ratio'])}")
    if _num(ev.get("peak_gap")) is not None:
        parts.append(f"largest gap {fmt_int(ev['peak_gap'])}")
    return text + _paren(parts)


def _generic(f: Finding, r: AnalysisResult) -> str:
    label = str(f.type).replace("_", " ")
    if f.scope == "team" or f.player is None:
        who = _team_label(r, f.team)
    else:
        who = _player_subject(r, f.player).nom
    return f"{who}: {label} {fmt_mmss(f.start)}–{fmt_mmss(f.end)}"


_TEMPLATES: dict[str, Callable[[Finding, AnalysisResult], str]] = {
    "supply_block": _supply_block,
    "high_bank": _high_bank,
    "low_workers": _low_workers,
    "late_expansion": _late_expansion,
    "army_collapse": _army_collapse,
    "early_ally_death": _early_ally_death,
    "team_army_deficit": _team_army_deficit,
}


def finding_text(finding: Finding, result: AnalysisResult) -> str:
    """One sentence describing `finding`, filled from its evidence."""
    template = _TEMPLATES.get(finding.type, _generic)
    try:
        return template(finding, result)
    except (TypeError, ValueError, KeyError, AttributeError):
        return _generic(finding, result)
