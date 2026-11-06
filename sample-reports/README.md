# Sample reports

Real reports from games where **blackSheep**, **EpicNoobSauc** and **humm** played together as a 3v3 team: 87 replays in the pool, all on the same side. They were generated with:

```powershell
sc2koach analyze "replays/<file>.SC2Replay" -o sample-reports/<name>.md --focus blackSheep
```

How to read them: [Reading your report](../docs/reading-your-report.md) · [Findings guide](../docs/findings-guide.md).

## Games

| Report | Date | Map | Length | Result | Teams | Why it's here |
|---|---|---|---|---|---|---|
| [Sandstorm CE (29)](2026-10-25-sandstorm-ce-29-win.md) | 2026-10-25 | Sandstorm CE | 17:37 | Win | PPT vs **PTZ** | Long macro win, ahead on army from about 3:00; includes the [findings JSON](2026-10-25-sandstorm-ce-29-win.findings.json) |
| [Megastructure (27)](2026-10-25-megastructure-27-win.md) | 2026-10-25 | Megastructure | 17:55 | Win | **TTZ** vs PTT | Long win as double Terran + Zerg |
| [Voracity (40)](2026-10-17-voracity-40-loss.md) | 2026-10-17 | Voracity | 11:36 | Loss | **PTZ** vs PTZ | Mirror-race loss; also from each player's point of view (below) |
| [Radiator LE (19)](2026-10-23-radiator-le-19-loss.md) | 2026-10-23 | Radiator LE | 14:29 | Loss | PTT vs **PTZ** | Mid-length loss |
| [Voracity (27)](2026-07-31-voracity-27-loss.md) | 2026-07-31 | Voracity | 18:13 | Loss | **PPZ** vs TZZ | Build 97563, the 8-starting-worker ruleset (`w8-th13`); worker targets adjust automatically |

Bold = this team.

## One game, three points of view

The same replay, Voracity (40), with each player as the focus. The findings are identical; only "you" and the order of player sections change. This is how to run a [team review](../docs/improvement-playbook.md#reviewing-a-game-as-a-team).

| Focus | Report |
|---|---|
| blackSheep | [2026-10-17-voracity-40-loss.md](2026-10-17-voracity-40-loss.md) |
| EpicNoobSauc | [2026-10-17-voracity-40-loss-focus-epicnoobsauc.md](2026-10-17-voracity-40-loss-focus-epicnoobsauc.md) |
| humm | [2026-10-17-voracity-40-loss-focus-humm.md](2026-10-17-voracity-40-loss-focus-humm.md) |

## Trends per player

`python scripts/trends.py replays --player <name>` across every replay each player appears in (wins vs losses):

| Player | Games (W / L / unknown) | SQ wins → losses | Biggest gaps in losses | File |
|---|---|---|---|---|
| blackSheep | 365 (169 / 46 / 150) | 76 → 70 | team army deficit (+59 pts), late expansion (+11), low workers (+9) | [trends-blacksheep.txt](trends-blacksheep.txt) |
| EpicNoobSauc | 106 (40 / 23 / 43) | 89 → 85 | team army deficit (+70 pts), army collapse (+51), low workers (+19) | [trends-epicnoobsauc.txt](trends-epicnoobsauc.txt) |
| humm | 136 (61 / 32 / 43) | 74 → 70 | team army deficit (+53 pts), army collapse (+15), late expansion (+10) | [trends-humm.txt](trends-humm.txt) |

**For this team:** all three players' losses are dominated by the **team army falling far behind** (in 62–72% of losses vs 0–13% of wins). The shared fix is fighting together and not fighting while behind ([team_army_deficit](../docs/findings-guide.md#team_army_deficit)). Individually: EpicNoobSauc's losses also show **army collapses** (78% of losses vs 28% of wins); blackSheep and humm more often **miss a third base** in losses (46% and 47%).

> Note: `high_bank` tops most Top priorities lists but doesn't separate wins from losses; compare SQ instead ([why](../docs/reading-your-report.md#how-to-weigh-top-priorities)).

## Privacy

These reports name every player in each game, including opponents. Remove this folder, or replace opponent names, if that shouldn't be public.
