"""Markdown report rendering and output writing (design/DESIGN.md §8).

Pure templating over an AnalysisResult: no analysis, deterministic, byte-stable output.
"""

from __future__ import annotations

import bisect
import json
from pathlib import Path

from sc2koach.gametime import fmt_mmss
from sc2koach.models import (
    AnalysisResult,
    Coaching,
    Finding,
    MetricsBundle,
    Player,
    Series,
    Team,
)
from sc2koach.report.templates import (
    NA,
    finding_text,
    fmt_int,
    fmt_secs,
    fmt_time,
)

SAMPLE_EVERY_S = 30
NO_ISSUES = "No issues detected by the current rules."
_DASH = "—"
_SOURCE_LABELS = {"slot": "lobby slot", "player_id": "player id", "manual": "manual"}


# --------------------------------------------------------------------------- helpers


def _esc(text: object) -> str:
    """Make text safe inside a Markdown table cell."""
    return str(text).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines


def _cost(f: Finding) -> float:
    value = f.evidence.get("est_cost")
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return 0.0


def _by_cost(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: (-_cost(f), f.id))


def _signed(value: float) -> str:
    v = round(value)
    return "0" if v == 0 else f"{v:+,}"


def _sample(series: Series, mark: float) -> float | None:
    """Value of the series point nearest `mark` (ties go to the earlier point)."""
    if not series:
        return None
    times = [p[0] for p in series]
    i = bisect.bisect_left(times, mark)
    candidates = [j for j in (i - 1, i) if 0 <= j < len(series)]
    best = min(candidates, key=lambda j: (abs(times[j] - mark), times[j]))
    return series[best][1]


def _marks(until: float) -> list[float]:
    if until < 0:
        return []
    return [float(m) for m in range(0, int(until) + 1, SAMPLE_EVERY_S)]


def _scalar(value: object) -> str:
    if value is None:
        return NA
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else repr(value)
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _flatten(data: dict, prefix: str = "") -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for key in data:
        value = data[key]
        full = f"{prefix}{key}"
        if isinstance(value, dict) and value:
            out += _flatten(value, f"{full}.")
        else:
            out.append((full, _scalar(value)))
    return sorted(out)


class _Ctx:
    def __init__(self, result: AnalysisResult) -> None:
        self.result = result
        self.replay = result.replay
        self.players: dict[int, Player] = {p.id: p for p in self.replay.players}
        self.metrics: dict[int, MetricsBundle] = {m.player: m for m in result.metrics}
        self.coaching: dict[int, Coaching] = {c.player: c for c in result.coaching or []}
        focus = self.replay.focus_player_id
        self.focus: Player | None = self.players.get(focus) if focus is not None else None
        self.ordered = self._order_players()
        self.teams = self._order_teams()

    def _order_players(self) -> list[Player]:
        def slot_key(p: Player) -> tuple:
            return (p.lobby_slot is None, p.lobby_slot or 0, p.id)

        players = list(self.replay.players)
        if self.focus is None:
            return sorted(players, key=lambda p: (p.team, p.id))
        f = self.focus
        mates = sorted((p for p in players if p.team == f.team and p.id != f.id), key=slot_key)
        opps = sorted(
            (p for p in players if p.team != f.team), key=lambda p: (p.team, *slot_key(p))
        )
        return [f, *mates, *opps]

    def _order_teams(self) -> list[Team]:
        teams = sorted(self.replay.teams, key=lambda t: t.id)
        if self.focus is not None:
            teams.sort(key=lambda t: t.id != self.focus.team)
        return teams

    def name(self, pid: int | None) -> str:
        if pid is None:
            return NA
        p = self.players.get(pid)
        return p.name if p else f"Player {pid}"

    def team_players(self, team: Team) -> list[Player]:
        ids = set(team.players)
        return [p for p in self.ordered if p.id in ids or (not ids and p.team == team.id)]


def _departure(p: Player) -> tuple[str, float] | None:
    if p.left_at is not None and (p.eliminated_at is None or p.left_at <= p.eliminated_at):
        return "Left", p.left_at
    if p.eliminated_at is not None:
        return "Eliminated", p.eliminated_at
    return None


def _mmr(p: Player) -> str:
    return NA if p.mmr is None else str(p.mmr)


def _base_finished(m: MetricsBundle | None, n: int) -> str:
    if m is None:
        return NA
    for e in m.expansions:
        if e.n == n:
            return fmt_mmss(e.finished)
    return _DASH


def _workers_at_4m(m: MetricsBundle | None, with_reason: bool = False) -> str:
    if m is None:
        return NA
    ws = m.workers_at_4m
    if ws.value is not None:
        return fmt_int(ws.value)
    if with_reason and ws.reason:
        return f"{NA} ({ws.reason.replace('_', ' ')})"
    return NA


def _supply_summary(m: MetricsBundle | None) -> str:
    if m is None:
        return NA
    total = sum(b.duration_s for b in m.supply_blocks)
    return f"{len(m.supply_blocks)} / {fmt_secs(total)}"


def _counterpart(ctx: _Ctx, p: Player) -> str:
    if p.counterpart_id is None:
        return NA
    label = _SOURCE_LABELS.get(p.counterpart_source or "", "")
    name = ctx.name(p.counterpart_id)
    return f"{name} ({label})" if label else name


# --------------------------------------------------------------------------- sections


def _header(ctx: _Ctx) -> list[str]:
    game = ctx.replay.game
    sides = [", ".join(p.name for p in ctx.team_players(t)) or f"Team {t.id}" for t in ctx.teams]
    comps = " vs ".join(t.composition for t in ctx.teams)
    title = f"# {' vs '.join(sides)} — {game.map} ({game.mode}, {comps})"

    date = game.played_at[:10] if game.played_at else NA
    if ctx.focus is not None:
        team = next((t for t in ctx.teams if t.id == ctx.focus.team), None)
        outcome = team.result if team is not None else "Unknown"
        result_line = "Result unknown" if outcome == "Unknown" else outcome
    else:
        winners = [t for t in ctx.teams if t.result == "Win"]
        if len(winners) == 1:
            result_line = f"Team {winners[0].id} won"
        elif any(t.result == "Tie" for t in ctx.teams):
            result_line = "Tie"
        else:
            result_line = "Result unknown"
    rules = ctx.replay.rules
    info = (
        f"{date} · {fmt_mmss(game.duration_s)} · {result_line} · "
        f"build {game.build} ({rules.ruleset_id})"
    )
    focus = ctx.focus.name if ctx.focus is not None else "none (neutral report)"
    return [title, "", info, "", f"Focus: {focus}", ""]


def _team_section(ctx: _Ctx, top_findings: list[Finding]) -> list[str]:
    out = ["## Team", "", "### Army value (every 30s)", ""]
    tm = {t.team: t for t in ctx.result.team_metrics}
    teams = [t for t in ctx.teams if t.id in tm]
    if not teams:
        out += ["No team army data.", ""]
    else:
        header = ["Time", *(f"Team {t.id}" for t in teams)]
        two = len(teams) == 2
        if two:
            header.append("Gap")
            out += [f"Gap = Team {teams[0].id} − Team {teams[1].id}.", ""]
        rows = []
        for mark in _marks(ctx.replay.game.duration_s):
            values = [_sample(tm[t.id].army_value, mark) for t in teams]
            row = [fmt_mmss(mark), *(fmt_int(v) for v in values)]
            if two:
                a, b = values
                row.append(NA if a is None or b is None else _signed(a - b))
            rows.append(row)
        out += _table(header, rows) + [""]

    out += ["### Eliminations", ""]
    elims = []
    for team in ctx.teams:
        metrics = tm.get(team.id)
        if metrics is None:
            continue
        for e in sorted(metrics.eliminations, key=lambda e: (e.departed_at, e.player)):
            left = e.left_at is not None and (
                e.eliminated_at is None or e.left_at <= e.eliminated_at
            )
            verb = "left" if left else "was eliminated"
            line = (
                f"- {ctx.name(e.player)} (Team {team.id}) {verb} at {fmt_mmss(e.departed_at)}; "
                f"the team played on for {fmt_mmss(e.team_played_on_s)}"
            )
            elims.append(line + (" (early)" if e.early else ""))
    out += (elims or ["None."]) + [""]

    out += ["### Team findings", ""]
    if top_findings:
        for i, f in enumerate(top_findings, 1):
            out.append(f"{i}. {fmt_mmss(f.start)} — {finding_text(f, ctx.result)} (`{f.id}`)")
    else:
        out.append("No team issues detected by the current rules.")
    return out + [""]


def _summary_section(ctx: _Ctx) -> list[str]:
    header = [
        "Player",
        "Race",
        "Team",
        "MMR",
        "Workers@4:00",
        "Avg bank",
        "SQ",
        "Supply blocks (count / total)",
        "2nd base",
        "3rd base",
        "Nominal counterpart",
    ]
    rows = []
    for p in ctx.ordered:
        m = ctx.metrics.get(p.id)
        rows.append(
            [
                _esc(p.name),
                p.race,
                str(p.team),
                _mmr(p),
                _workers_at_4m(m),
                fmt_int(m.unspent.mean) if m else NA,
                fmt_int(m.unspent.sq) if m else NA,
                _supply_summary(m),
                _base_finished(m, 2),
                _base_finished(m, 3),
                _esc(_counterpart(ctx, p)),
            ]
        )
    note = (
        "MMR is n/a when the replay has none; arranged teams may share a team rating, "
        "so teammates can show the same MMR. Counterparts are nominal (paired by lobby slot "
        "or player id) unless marked manual."
    )
    return ["## Summary", "", *_table(header, rows), "", note, ""]


def _priorities(ctx: _Ctx, p: Player, top_n: int) -> list[str]:
    coaching = ctx.coaching.get(p.id)
    if coaching is not None and coaching.priorities:
        out = []
        for i, pr in enumerate(sorted(coaching.priorities, key=lambda x: x.rank), 1):
            ids = ", ".join(f"`{fid}`" for fid in pr.finding_ids)
            out.append(f"{i}. **{pr.title}**" + (f" ({ids})" if ids else ""))
            out.append(f"   - Why: {pr.why}")
            out.append(f"   - Drill: {pr.drill}")
        return out
    mine = [f for f in ctx.result.findings if f.scope == "player" and f.player == p.id]
    top = _by_cost(mine)[: max(top_n, 0)]
    if not top:
        return [NO_ISSUES]
    return [
        f"{i}. {fmt_mmss(f.start)} — {finding_text(f, ctx.result)} (`{f.id}`)"
        for i, f in enumerate(top, 1)
    ]


def _player_metrics(ctx: _Ctx, p: Player) -> list[str]:
    m = ctx.metrics.get(p.id)
    if m is None:
        return ["No metrics available."]
    u = m.unspent
    out = [
        f"- Workers at 4:00: {_workers_at_4m(m, with_reason=True)}",
        f"- Bank: mean {fmt_int(u.mean)}, peak {fmt_int(u.peak)}, SQ {fmt_int(u.sq)}",
    ]
    if p.counterpart_id is not None:
        cm = ctx.metrics.get(p.counterpart_id)
        cp = _counterpart(ctx, p)
        if cm is not None:
            cp += (
                f" — workers at 4:00 {_workers_at_4m(cm)}, mean bank {fmt_int(cm.unspent.mean)}"
                f", SQ {fmt_int(cm.unspent.sq)}"
            )
        out.append(f"- Nominal counterpart: {cp}")
    out.append("")

    if m.supply_blocks:
        rows = [
            [fmt_mmss(b.start), fmt_secs(b.duration_s), fmt_int(b.supply), fmt_int(b.minerals)]
            for b in sorted(m.supply_blocks, key=lambda b: b.start)
        ]
        out += ["Supply blocks:", "", *_table(["Start", "Duration", "Supply", "Minerals"], rows)]
    else:
        out.append("Supply blocks: none")
    out.append("")

    if m.expansions:
        rows = [
            [str(e.n), fmt_time(e.started, _DASH), fmt_mmss(e.finished), e.source]
            for e in sorted(m.expansions, key=lambda e: (e.n, e.finished))
        ]
        out += ["Expansions:", "", *_table(["Base", "Started", "Finished", "Source"], rows)]
    else:
        out.append("Expansions: none")
    out.append("")

    until = min(p.end_t, ctx.replay.game.duration_s)
    samples = [f"{fmt_mmss(mark)} {fmt_int(_sample(m.army_value, mark))}" for mark in _marks(until)]
    out.append("Army value (every 30s): " + (" · ".join(samples) if samples else NA))
    return out


def _players_section(ctx: _Ctx, top_n: int) -> list[str]:
    out = ["## Players", ""]
    for p in ctx.ordered:
        out += [f"### {p.name} ({p.race}, Team {p.team}, MMR {_mmr(p)})", ""]
        dep = _departure(p)
        if dep is not None:
            out += [f"{dep[0]} at {fmt_mmss(dep[1])}.", ""]
        out += ["#### Top priorities", "", *_priorities(ctx, p, top_n), ""]
        out += ["#### Metrics", "", *_player_metrics(ctx, p), ""]
    return out


def _key_moments(ctx: _Ctx) -> list[str]:
    out = ["## Key Moments", ""]
    findings = sorted(ctx.result.findings, key=lambda f: (f.start, f.id))
    if not findings:
        return out + ["No findings.", ""]
    rows = []
    for f in findings:
        who = f"Team {f.team}" if f.scope == "team" or f.player is None else ctx.name(f.player)
        rows.append(
            [
                fmt_mmss(f.start),
                _esc(who),
                f"`{f.type}`",
                _esc(finding_text(f, ctx.result)),
                f"`{f.id}`",
            ]
        )
    return out + _table(["Time", "Player", "Type", "Detail", "ID"], rows) + [""]


def _appendix(ctx: _Ctx) -> list[str]:
    r = ctx.result
    out = ["## Appendix", "", "### Thresholds", ""]
    flat = _flatten(r.generated_with.thresholds)
    out += [f"- `{k}`: {v}" for k, v in flat] or ["None recorded."]
    out += ["", "### Warnings", ""]
    warnings = []
    for w in r.warnings:
        line = f"- `{w.code}`: {w.message}"
        if w.player is not None:
            line += f" ({ctx.name(w.player)})"
        warnings.append(line)
    out += (warnings or ["None."]) + [""]

    game, rules = ctx.replay.game, ctx.replay.rules
    release = f" (release {game.release})" if game.release else ""
    verified = "verified" if rules.verified_build else "unverified"
    out += [
        "### Versions",
        "",
        f"- Tool version: {r.tool_version}",
        f"- sc2reader: {r.generated_with.sc2reader or NA}",
        f"- Schema version: {r.schema_version}",
        f"- Game build: {game.build}{release}",
        f"- Ruleset: {rules.ruleset_id} ({verified})",
        f"- sc2reader datapack: {rules.sc2reader_datapack or NA}",
        f"- Replay SHA-256: `{game.replay_sha256}`",
        "",
        "### Rules drift",
        "",
    ]
    drift = [f"- `{k}`: {NA if v is None else f'{v:.3f}'}" for k, v in sorted(rules.drift.items())]
    out += (drift or ["None measured."]) + [""]
    return out


# --------------------------------------------------------------------------- public API


def render_markdown(result: AnalysisResult, top_n: int = 3) -> str:
    """Render the Markdown report. Pure and byte-stable for a given result."""
    ctx = _Ctx(result)
    team_findings = _by_cost([f for f in result.findings if f.scope == "team"])
    lines = [
        *_header(ctx),
        *_team_section(ctx, team_findings),
        *_summary_section(ctx),
        *_players_section(ctx, top_n),
        *_key_moments(ctx),
        *_appendix(ctx),
    ]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def findings_json(result: AnalysisResult) -> str:
    data = result.model_dump(mode="json", by_alias=True)
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def json_path_for(md_path: Path) -> Path:
    """report.md -> report.findings.json"""
    return Path(md_path).with_suffix(".findings.json")


def write_outputs(result: AnalysisResult, md_path: Path, top_n: int = 3) -> tuple[Path, Path]:
    """Write `<name>.md` and `<name>.findings.json`; returns (md_path, json_path)."""
    md_path = Path(md_path)
    json_path = json_path_for(md_path)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    with open(md_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render_markdown(result, top_n=top_n))
    with open(json_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(findings_json(result))
    return md_path, json_path
