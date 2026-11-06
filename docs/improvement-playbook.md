# Improvement playbook: from reports to winning more

sc2Koach tells you **what** went wrong and **when**. This page is about turning that into practice, for you and your teammates, game after game.

- [What wins your games](#what-wins-your-games)
- [After every session (10 minutes)](#after-every-session-10-minutes)
- [Find your recurring problems](#find-your-recurring-problems)
- [Reviewing a game as a team](#reviewing-a-game-as-a-team)
- [A four-week plan](#a-four-week-plan)
- [Team habits checklist](#team-habits-checklist)
- [How to tell you're improving](#how-to-tell-youre-improving)

---

## What wins your games

Measured on **201 decided 2v2/3v3 games** from your replay folder (1,142 player-games; everyone in those lobbies, not just you). Correlation, not proof, but a good guide to where effort pays off.

| Signal | Winners | Losers | Team that was better on this won |
|---|---|---|---|
| **SQ** (spending vs income) | median 77 | median 65 | **86%** of games |
| **Long team army deficit** (≤ 60% of enemy army for 60s+) | 15% of teams | **77%** of teams | — |
| **Workers at 4:00** | median 25 | median 23 | **72%** |
| **Never took a third base** | 21% of players | **45%** of players | — |
| **Army collapses** per player per game | 0.79 | **1.26** | — |
| **Teammate left/eliminated early** | 29% of teams | **51%** of teams | — |
| 2nd base finished | median 3:35 | median 3:42 | 57% (weak) |
| Average bank | 1,166 | 953 | 43% (lower bank lost more often) |
| Supply-blocked seconds before 10:00 | 32 | 25 | 42% (more blocks won more often) |

**What this means:**
- **Fights and army size decide most games.** A long team army deficit is the clearest losing sign. Don't take bad fights, fight together, and keep production up.
- **SQ beats raw bank.** Winners bank *more* because they earn more. Judge banking by SQ.
- **Economy basics still matter:** 2 more workers at 4:00 and a third base separate winners from losers.
- **Supply blocks don't predict losses here.** They still cost production, but fix the items above first.

Your personal numbers will differ; [find them](#find-your-recurring-problems).

---

## After every session (10 minutes)

1. **Analyze the games you played** (PowerShell):

   ```powershell
   $replays = "$env:USERPROFILE\Documents\StarCraft II\Accounts\<id>\<toon>\Replays\Multiplayer"
   New-Item -ItemType Directory -Force reports | Out-Null
   Get-ChildItem $replays -Filter *.SC2Replay |
       Where-Object LastWriteTime -gt (Get-Date).AddHours(-6) |
       ForEach-Object { sc2koach analyze $_.FullName -o "reports\$($_.BaseName).md" }
   ```

2. **Pick your worst loss.** Open its report.
3. **Read the Team section first.** When did the army gap turn against you? Was there an early ally death?
4. **Read your Players section,** then [weigh the Top priorities](reading-your-report.md#how-to-weigh-top-priorities) (promote collapses, deficits, missing third and low workers; check SQ before worrying about `high_bank`).
5. **Watch 2–3 key moments** in the replay ([how](reading-your-report.md#checking-a-finding-in-the-replay)).
6. **Write one sentence:** "Next game I will ___." Make it concrete and checkable ("third CC started by 5:30", "no supply blocks after 5:00"), not vague ("macro better").

---

## Find your recurring problems

One game is noise; twenty games show patterns. `scripts/trends.py` analyzes every replay a player appears in and compares their wins with their losses:

```powershell
python scripts/trends.py replays --player blacksheep            # all games
python scripts/trends.py replays --player blacksheep --last 30  # recent form
python scripts/trends.py replays --player <teammate>            # works for anyone
```

Example output (made-up numbers):

```
Alpha: 40 games (20 W / 14 L / 6 result unknown), races {'Terran': 38, 'Protoss': 2}

        Games  Workers@4  SQ  2nd base  3rd base  No 3rd  Blocked s
   All     40         23  70      3:58      9:10     33%         80
  Wins     20         25  74      3:41      8:52     15%         85
Losses     14         22  66      4:31      9:40     57%         70

Share of games where each finding fired (yours, or your team's):
  finding                 all   wins  losses
  army_collapse           45%    35%     57%
  team_army_deficit       35%     5%     71%
  ...

Biggest difference between your losses and wins (start here):
  team_army_deficit: fires in 66 percentage points more of your losses
  low_workers: fires in 25 percentage points more of your losses
  army_collapse: fires in 22 percentage points more of your losses
```

Read it as: **"In games I lose, what goes wrong that doesn't in games I win?"** The "start here" list is your personal priority order. In the example: coordinate fights so the team army doesn't fall behind, keep making workers to 25 by 4:00, and get the natural down by ~3:45 (losses averaged 4:31).

"Result unknown" games are ones where the replay doesn't record a winner, usually because someone left before the end.

---

## Reviewing a game as a team

Everyone in the team can run the same replay from their own point of view:

```powershell
sc2koach analyze game.SC2Replay --focus Alpha   -o reports\game-alpha.md
sc2koach analyze game.SC2Replay --focus Bravo   -o reports\game-bravo.md
sc2koach analyze game.SC2Replay --focus Charlie -o reports\game-charlie.md
```

The findings are identical; only the wording ("you") and order change. A 15-minute team review:

1. **Team section together (5 min).** Find the moment the army gap turned. What was each player doing in the 60 seconds before? Was anyone fighting alone?
2. **Summary table (3 min).** Compare workers, SQ and base timings side by side. Is one player consistently behind? That player's opponent is often the one the enemy team targets.
3. **One fix per player (5 min).** Each person picks one finding from their own section.
4. **One team agreement (2 min).** For example: "we move out together at 7:30", "anyone attacked calls 'help' and everyone moves immediately", "nobody leaves before the end; send your bank first if you must".

---

## A four-week plan

Focus on one thing a week; check it with the report after every game.

| Week | Focus | Target (check in the report) |
|---|---|---|
| 1 | **Fight together** | No `army_collapse` where your ally's army wasn't there; team army deficits shorter than 60s |
| 2 | **Spend your money** | SQ 75+ in most games; add production whenever you see `high_bank` with SQ < 70 |
| 3 | **Economy basics** | 25+ workers at 4:00; 2nd base finished by ~3:45; 3rd by ~8:30 |
| 4 | **Supply and defense** | No supply block over 15s after 5:00; respond to every attack on an ally within 15s |

After week 4, run `scripts/trends.py --last 30` and compare with week 0.

---

## Team habits checklist

Print this, or pin it in your Discord:

- [ ] Constant worker production to ~66 (22 per saturated base).
- [ ] Supply built ahead: 6–8 below cap early, 12–16 below mid game, two at a time with 3+ production buildings.
- [ ] Third base planned before the game, taken by ~8:30.
- [ ] Production added whenever money piles up (SQ 75+).
- [ ] Move out **together**, at an agreed time, toward one target.
- [ ] When an ally is attacked, move your army **immediately**.
- [ ] Don't fight while the enemy army is clearly bigger; defend and rebuild.
- [ ] Send resources to an ally who is rebuilding.
- [ ] Nobody leaves early. If you must, send your bank to an ally first.

---

## How to tell you're improving

- **Per game:** fewer Top priorities about collapses and deficits; SQ trending up; base timings earlier.
- **Per month:** `scripts/trends.py --last 30` shows the "losses vs wins" gaps shrinking, and your Wins row's numbers become your All row.
- **What the tool can't measure yet:** micro, scouting, build orders, upgrades and APM (later phases). If the report looks clean but you still lose, those are the next places to look in the replay.
