# Reading your report

A walk through each section of `report.md`, what the numbers mean, and how to get from "a finding" to "what I'd do differently". Examples use made-up names.

- [Header](#header)
- [Team](#team)
- [Summary](#summary)
- [Players](#players)
- [Key Moments](#key-moments)
- [Appendix](#appendix)
- [How to weigh Top priorities](#how-to-weigh-top-priorities)
- [Checking a finding in the replay](#checking-a-finding-in-the-replay)

---

## Header

```
# Alpha, Bravo, Charlie vs Delta, Echo, Foxtrot — Sandstorm CE (3v3, PTZ vs PPT)

2026-10-25 · 17:37 · Win · build 98310 (w12-th15)

Focus: Alpha
```

- Teams, map, mode, and each team's races (sorted, so `PTZ` = one Protoss, one Terran, one Zerg).
- Date, game length, result **for the focus player's team**, game build and [ruleset](how-it-works.md#game-patches-change-the-rules).
- **Focus:** whose point of view this is. If the focus name isn't in the game, it says `none` and the whole report is neutral third person.

---

## Team

The team section answers: **did we lose because the team lost, or because someone fell behind?**

### Army value (every 30s)

```
Gap = Team 1 − Team 2.

| Time | Team 1 | Team 2 | Gap    |
| 8:00 | 4,150  | 6,875  | -2,725 |
| 9:30 | 6,960  | 11,600 | -4,640 |
```

Total army value of each team every 30 seconds. The focus player's team is the first column, and the line above the table says how the gap is computed (focus team minus the other, so negative means you're behind). Watch for:
- **When the gap opens.** A gap that opens around 4:00–6:00 usually comes from an early attack or a much greedier/faster economy. One that opens around 8:00–12:00 is usually a lost fight or a production gap.
- **Sudden drops.** A drop of thousands in 30 seconds is a fight. Match it with `army_collapse` findings to see whose army it was.
- **Recovery.** Did the team rebuild after a lost fight, or keep losing value?

### Eliminations

Who left or was eliminated, when, and how long the rest of the team played on. A teammate leaving with minutes left means the team played 2v3 or 1v2 from then on. Leaves in the last few seconds are just the end of the game.

### Team findings

`early_ally_death` and `team_army_deficit`, ordered by estimated cost. These are **shared** problems: no single player owns them.

---

## Summary

One row per player: the focus player first, then teammates, then opponents.

| Column | Meaning | Rough guide (your games) |
|---|---|---|
| Workers@4:00 | Workers at the 3:56 snapshot | Median ≈ 24 T, 27 P, 24 Z. Winners averaged 2 more than losers |
| Avg bank | Average unspent minerals + gas | Context only; see SQ |
| **SQ** | Spending quotient: spending relative to income | **The single best predictor of winning in your games.** Winners ≈ 77, losers ≈ 65 |
| Supply blocks | Count / total seconds blocked | A few short ones are normal; one long late block costs a lot of production |
| 2nd base / 3rd base | When each finished | Median 2nd: T 4:08, P 3:49, Z 2:31. 45% of losers never took a third |
| Nominal counterpart | The opponent in your lobby position | Comparison only |

**MMR** is shown when the replay has it. Arranged teams often show the same number for all members (a team rating), so don't read it as each person's own MMR.

---

## Players

One section per player, the focus player first.

### Top priorities

```
1. 9:10 — You lost 2,100 of 2,800 army value 9:10–9:40 while killing 600 (`f-031`)
2. 5:00 — Your second base finished 5:40 (target 5:00; counterpart finished 4:02) (`f-012`)
3. 2:44 — You were supply blocked at 2:44 for at least 14s (21 supply) with 82 minerals banked (`f-004`)
```

The player's three findings with the highest estimated cost. Read [how to weigh them](#how-to-weigh-top-priorities) before taking the order literally. A player with none gets "No issues detected by the current rules". That means none of the seven rules fired, not that the game was perfect.

If a player left or was eliminated, this section says so (e.g. "Left at 17:30"). Their metrics stop at that time.

### Metrics

- **Workers at 4:00, bank (mean, peak) and SQ.**
- **Nominal counterpart** with the same numbers side by side.
- **Supply blocks table:** start, duration (at least), supply, minerals banked at the time.
- **Expansions table:** base number, started, finished, and source (`start`, `built`, or `landed` for a flown Command Center).
- **Army value every 30s:** how the player's army grew. Flat stretches mean no army was being built, often because of a supply block or banking.

---

## Key Moments

```
| Time | Player | Type           | Detail                                                       | ID      |
| 2:16 | Delta  | `supply_block` | Delta was supply blocked at 2:16 for at least 23s ...        | `f-001` |
| 4:00 | Echo   | `low_workers`  | Echo had 19 workers at 4:00 (target 20; game average 22.8 …) | `f-004` |
```

Every finding in the game, in time order. Use it as a **timeline to scrub the replay**: jump to each time and watch what the player was doing. Team findings show "Team n" in the Player column.

---

## Appendix

- **Thresholds:** every setting used for this run (see [configuration](configuration.md#thresholds)).
- **Warnings:** anything to be careful about (see [warning codes](configuration.md#warning-codes)).
- **Versions, replay SHA-256 and rules drift:** for reproducing or debugging a report.

---

## How to weigh Top priorities

The estimated cost puts very different mistakes on one scale, but it is **rough** and has a known bias:

> **Banking findings (`high_bank`) dominate the ranking.** In your 365 games, `high_bank` is the #1 priority for 75% of players, yet the team that banked *less* won only 43% of the time. Winners bank more because they have bigger economies. Banking matters, but measured against income (SQ), not on its own.

What actually separated wins from losses in your 201 decided 2v2/3v3 games ([full numbers](improvement-playbook.md#what-wins-your-games)):

1. **Team army deficits and army collapses**: losing teams had a long army deficit in 77% of games (winners 15%), and losing players had 60% more army collapses.
2. **Spending relative to income (SQ)**: the team with the higher average SQ won 86% of games.
3. **Taking a third base**: 45% of losing players never took one, against 21% of winners.
4. **Early workers**: the team with more workers at 4:00 won 72% of games.
5. **Teammates leaving or dying early**: 51% of losing teams vs 29% of winning teams.

So when you read Top priorities, **promote** `army_collapse`, `team_army_deficit`, `late_expansion` (especially a missing third) and `low_workers`, and treat `high_bank` as "check my SQ". If your SQ is 75+, a big bank was probably fine (you were rich); if it's under 65, the bank is a real problem.

---

## Checking a finding in the replay

Every finding has a time. To see *why* it happened:

1. Open the replay in StarCraft II and drag the timeline to about **15 seconds before** the finding's time.
2. Switch vision to that player, and open the in-game observer panels (Income, Army, Units Lost, Production).
3. Ask the question that matches the finding:

| Finding | Question to answer while watching |
|---|---|
| `supply_block` | Where was the player's camera? Why wasn't a depot/pylon/overlord started 20–30s earlier? |
| `high_bank` | Were production buildings idle? Was the player busy fighting or moving out? |
| `low_workers` | Did worker production stop? When, and why (scouting, early attack, forgot)? |
| `late_expansion` | Was the delay planned (all-in) or forced (pressure)? Was it safe to expand earlier? |
| `army_collapse` | Who was the army fighting, where, and were the allies there? Was it a bad engagement or a bad unit matchup? |
| `early_ally_death` | Could the rest of the team have helped earlier? Was the attack scouted? |
| `team_army_deficit` | Did the team fall behind on production, or lose a fight and not rebuild? |

4. Write down **one concrete thing** that would have prevented it ("build a depot when supply is 8 below the cap", "move out together at 7:00, not separately"). The [improvement playbook](improvement-playbook.md) turns those notes into practice.
