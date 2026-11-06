# Findings guide: what each finding means and what to do about it

Every finding in a report is one of seven types. For each one, this guide covers:

- **In the game:** what was happening on screen.
- **How it's detected:** the exact rule, so you know what triggered it.
- **Reading the numbers:** what each part of the sentence means.
- **Does it lose games?** What your own replays say (201 decided 2v2/3v3 games, 1,142 player-games).
- **What to do:** concrete changes, with race-specific notes.
- **Drill:** something to practice.
- **When to ignore it:** cases where the finding is technically right but not a mistake.

All thresholds are defaults and can be changed in [configuration](configuration.md#thresholds).

Contents: [supply_block](#supply_block) · [high_bank](#high_bank) · [low_workers](#low_workers) · [late_expansion](#late_expansion) · [army_collapse](#army_collapse) · [early_ally_death](#early_ally_death) · [team_army_deficit](#team_army_deficit) · [Priority order for your group](#priority-order-for-your-group)

---

## supply_block

> *"You were supply blocked at 5:07 for at least 51s (46 supply) with 745 minerals banked"*

**In the game:** your supply counter read something like `46/46`. Every production building was waiting, the money was there, and nothing could be built until a Supply Depot, Pylon or Overlord finished.

**How it's detected:** at a snapshot, all of these are true:
- supply cap below 200 (being maxed out at 200/200 is not a block);
- less than 1 free supply, so not even a worker fits;
- you have a town hall;
- you have at least 50 minerals.

Consecutive blocked snapshots are merged. The block ends when a supply building finishes (from unit events) or the next snapshot shows free supply. Blocks shorter than 7s are ignored.

**Reading the numbers:** "at least 51s" is a lower bound; the block may have started up to 7s earlier. "(46 supply)" is your cap during the block. "745 minerals banked" shows how much production you were sitting on.

**Does it lose games?** Not on its own, in your data. Winners had slightly *more* blocked seconds before 10:00 (median 32s vs 25s), because growing economies hit the cap more often. But every block is production you can never get back, and **long mid-game blocks (30s+ after 5:00) are expensive**: one 50s block with 3–4 production buildings is roughly 4–6 units missing from the next fight.

**What to do:**
- **Build supply before you need it.** A supply building takes about 18–21 seconds. Start one when you have about one production cycle of supply left:
  - early game (under ~40 supply): when you're **6–8 below** the cap;
  - mid game: when you're **12–16 below**, and build **two at a time** once you have 3+ production buildings;
  - one more for every town hall or production building you add.
- **Make it part of your production loop.** Every time you queue units, glance at supply. If the gap is under one round of production, build supply right then.
- **Watch for "freeze" moments**: during fights, when moving out, or while microing at an ally's base. Most long blocks start then. Before moving out, queue a supply building.
- **Terran:** keep a worker assigned to depots in the mid game. **Calldown: Extra Supplies** (Orbital Command) instantly adds 8 supply to a depot when you're caught blocked.
- **Protoss:** Pylons also power buildings and warp-ins; place spare Pylons at your natural/third early so they're ready.
- **Zerg:** Overlords come from larva, so plan them into your inject cycles (one Overlord for every 8 supply of larva you're about to spend). Before a big drone or army round, make 2–3 Overlords first.

**Drill:** play a custom game against the AI and aim for **zero supply blocks to 10:00**. Then check your report: the Summary column should read `0 / 0s`.

**When to ignore it:** blocks during an all-in where you've stopped building on purpose, or the last seconds before the game ends.

---

## high_bank

> *"You banked over 1,200 for 361s from 11:26 (peak 4,460)"*

**In the game:** minerals and gas piled up instead of becoming units, buildings or upgrades.

**How it's detected:** your bank (minerals + gas, minus anything an ally sent you in the last 20s) stays above a threshold for **at least 30 seconds**. The threshold is **800** if the run starts before 6:00, and **1,200** after. One finding per continuous run.

**Reading the numbers:** "over 1,200" is the threshold, "361s" how long it lasted, "peak 4,460" the highest bank in that run.

**Does it lose games?** **On its own, no.** In your games the team with the *lower* average bank won only 43% of the time: winners have bigger economies and float more. What matters is **spending relative to income**, which is the **SQ** number in the Summary. The team with the higher SQ won **86%** of games (winners' median SQ 77, losers' 65).

> ⚠️ This finding's estimated cost is inflated, so it lands at #1 in "Top priorities" for most players. Check SQ before treating it as your top problem: if SQ is 75+, the bank came from being rich; under 65, it's real.

**What to do:**
- **Add production.** If you bank 1,000+ regularly in the mid game, you don't have enough production buildings for your income. Rule of thumb on 2 bases: Terran 5–8 production buildings, Protoss 6–8 Gateways plus Robo/Stargate, Zerg 2–3 Queens injecting plus a macro Hatchery.
- **Spend in cycles:** queue from all production buildings, then return to them every 15–20 seconds. Hotkey your production.
- **Turn excess into a base or upgrades.** A bank of 400+ before 6:00 is a third base or an upgrade you haven't started.
- **Feed your ally.** In team games, if you're floating and an ally is rebuilding after a lost fight, send them resources. sc2Koach doesn't count resources you send as banking.
- **Terran:** don't let MULE income pile up; add Barracks when you add Orbitals.
- **Protoss:** Warp Gate production has a cooldown; add Gateways rather than banking for warp-ins.
- **Zerg:** a growing bank usually means **too few larva**: missed injects, or a macro Hatchery needed.

**Drill:** in your next 5 games, look only at your **SQ**. Aim for 70+, then 80+.

**When to ignore it:** saving deliberately for a big expansion or tech switch, or the final minutes of a won game.

---

## low_workers

> *"You had 20 workers at 4:00 (target 22; game average 24.5; team average 23.0; counterpart 26)"*

**In the game:** your town halls weren't constantly making workers in the first four minutes.

**How it's detected:** worker count at the 3:56 snapshot is below the target for your race: **22 Terran, 23 Protoss, 19 Zerg**. These are the slowest quarter of players in your own games. On the 8-starting-worker ruleset (build 97563) the targets are 2 lower.

**Reading the numbers:** the target, then context: average across the whole game, your team's average, and your nominal counterpart's count.

**Does it lose games?** **Yes.** The team with more workers at 4:00 won **72%** of your games. Winners had a median of 25 workers vs 23 for losers, and losers were flagged twice as often.

**What to do:**
- **Never stop making workers before ~60–70** (16 on minerals + 6 on gas per base: 22 per saturated base, 3 bases ≈ 66).
- **Queue 1–2 workers at a time** on every town hall and return to it every 12 seconds. Hotkey your town halls.
- **Don't pull workers to defend unless necessary**, and put them back right away.
- **Terran:** constant SCVs from every Command Center; MULEs add income on top, not instead.
- **Protoss:** use **Chrono Boost on Nexuses** for Probes in the first 4–5 minutes.
- **Zerg:** drone hard early; Queens injecting on cooldown give the larva to do it.

**Drill:** custom game vs AI, workers only: reach your race's **winners' median (25+) at 4:00**, then 28+.

**When to ignore it:** a deliberate one-base all-in, or a heavy early attack you had to fight off with workers (check the replay).

---

## late_expansion

> *"Your second base finished 5:40 (target 5:00; counterpart finished 4:02)"*
> *"You had no third base by 13:50 (target 10:00)"*

**In the game:** your natural (2nd) or third (3rd) base was late or never built, so your income stayed capped.

**How it's detected:** a base counts only when a town hall finishes (or a Command Center lands) **more than 15 map units from every town hall location you've ever had**. In-base CCs, macro Hatcheries, Orbital/Lair upgrades and rebuilding a lost base don't count. It fires when:

| Base | Terran | Protoss | Zerg |
|---|---|---|---|
| 2nd finished after | 5:00 | 4:30 | 3:00 |
| 3rd finished after | 10:00 | 9:00 | 8:00 |

It also fires if the base never came while you were still in the game past the target. These targets are the slowest quarter of your games, so they're **forgiving**; better players expand much earlier.

**Does it lose games?** The **third base** matters most: **45% of losing players never took one, against 21% of winners**. Natural timing matters less (winners' median 3:35 vs 3:42), but very late naturals still show up in losses.

**What to do:**
- **Stretch targets** (your winners' medians): **2nd base finished ≈ 3:35, 3rd ≈ 8:15.** Typical ladder macro play is earlier still (natural ≈ 2:30–3:15).
- **Plan the third.** Decide before the game when you'll start it (e.g. "third CC at 5:00 after my first push"), not "when it feels safe".
- **In team games, expand behind your allies.** On shared-natural maps, coordinate who defends while someone expands.
- **Terran:** you can build a Command Center in your main and **fly it** to the third (the report counts landed CCs).
- **Protoss:** a Nexus is 400 minerals; if you're banking (see `high_bank`), that's your third.
- **Zerg:** a third Hatchery by 4:00–5:00 is standard; a missing third usually means too much early army.

**Drill:** write your build's expansion times on a sticky note, e.g. "Nexus start 1:30, third start 5:30", and check the Expansions table after each game.

**When to ignore it:** intentional one- or two-base all-ins, and games where you were under constant attack (check whether the Team army gap was already negative).

---

## army_collapse

> *"You lost 2,100 of 2,800 army value 9:10–9:40 while killing 600"*

**In the game:** your army died in a short fight and didn't trade well: you lost far more than you killed.

**How it's detected:** within any 30-second window, you lost **at least 60%** of the army value you had at the start of the window (which must be at least 1,000), **and** you lost more than you killed. Overlapping windows merge into one finding.

**Reading the numbers:** army value before, lost in the window, and killed in the same window. "Lost 2,100 … while killing 600" means a net loss of 1,500 resources in 30 seconds.

**Does it lose games?** **Yes, strongly.** Losing players had **1.26 collapses per game vs 0.79** for winners, and the average collapse cost was almost twice as high (2,310 vs 1,327).

**What to do:** watch the replay from 30 seconds before the collapse and identify which of these it was:
- **Fighting alone.** In team games, the enemy often hits one player with two or three armies. *Fix:* move out together with your ally; agree on a rally point; if attacked alone, retreat toward your ally's army rather than fighting.
- **Bad engagement.** Fighting into a choke, up a ramp, or into static defense or siege. *Fix:* fight in the open, near your own bases, or not at all.
- **Bad composition.** Your units counter-picked (e.g. Marines into Banelings/Colossus, Zerglings into Hellbats/Archons). *Fix:* scout their composition before the fight; add the counter unit.
- **Caught moving.** Army strung out in a line or caught crossing the map. *Fix:* group up before moving; position at a defensive spot between bases.
- **No retreat.** The fight was clearly lost but you kept fighting. *Fix:* when the fight turns, pull back and save half the army.

**Drill:** after each game, pick your **largest collapse** and write one sentence: "I lost it because ___; next time I will ___."

**When to ignore it:** trades that won the game (e.g. sacrificing an army to kill a base), or a final all-in. Check whether your team army gap improved afterwards.

---

## early_ally_death

> *"Your team played a player down for 6:10 after Bravo left at 7:40"*

**In the game:** a teammate quit or lost all their buildings, and the rest of the team kept playing for at least another minute, outnumbered.

**How it's detected:** a player's end time (left or eliminated) comes at least **60s** before the rest of the team stopped playing.

**Does it lose games?** **Yes.** 51% of losing teams had one, against 29% of winning teams. Of the players who left more than 10s before the end, **72% were on the losing team**. Some of that is people leaving lost games, but playing 2v3 or 1v2 for minutes rarely ends well.

**What to do:**
- **Defend each other.** Most early deaths are the enemy team ganging up on one player. When an ally is attacked, **move your army immediately**: the first 10–20 seconds decide whether they survive.
- **Scout for the double-team:** enemy armies moving together toward one base.
- **Share resources.** Send minerals/gas to an ally rebuilding after a lost fight; sc2Koach doesn't count resources you send against you.
- **Don't leave early.** Your units stay on the field under your allies' control, but a human playing them is worth far more. If you must leave, **send your bank to an ally first**.
- **For the survivor:** turtle, defend, and expand behind static defense rather than taking even fights while outnumbered.

**Drill:** agree on a team call: "**help at <base>**". The moment anyone is attacked, everyone moves their army there and counts aloud to 15.

**When to ignore it:** disconnects.

---

## team_army_deficit

> *"Your team's army value was at or below 60% of the enemy's 8:00–10:30 (lowest 35%; largest gap 4,200)"*

**In the game:** for at least a minute, your team's combined army was much smaller than the enemy's. Any fight in that window was likely lost.

**How it's detected:** the team's army value is **at most 60%** of the enemy's for **at least 60s**, counting only times when the enemy army is at least 1,500 (so tiny early armies don't count).

**Reading the numbers:** the time window, the lowest ratio reached (35% means you had about a third of their army), and the largest gap in army value.

**Does it lose games?** **This is the strongest signal in your data.** Losing teams had a deficit window in **77%** of games, against **15%** for winners. When winners had one, it typically started early (around 5:00) and they recovered; losers' typically started around 8:20.

**What to do:**
- **Find where it started.** Look at the Team army table: did the gap open slowly (the enemy out-produced you) or suddenly (a lost fight; check `army_collapse` around that time)?
- **Slow gap → production.** Compare each player's army line in the Players section. Someone who teched or expanded heavily without army leaves the team exposed. Agree on army timings, e.g. "everyone has 60 supply of army by 8:00".
- **Sudden gap → don't fight while behind.** After a lost fight, rebuild and defend together; don't trickle units into the enemy.
- **Coordinate the attack.** Move out together, at an agreed time, toward one target.
- **Use the gap as a signal in-game.** If the enemy army clearly outnumbers yours, defend and trade with static defense rather than engaging in the open.

**Drill:** after each game, find the time the army gap first goes clearly against you in the Team table. Discuss as a team: "what was each of us doing in the 60 seconds before?"

**When to ignore it:** deliberate tech or economy windows (e.g. everyone teching to late game) that you planned for, as long as you didn't take fights during them.

---

## Priority order for your group

Based on what separates wins from losses in your own replays ([full table](improvement-playbook.md#what-wins-your-games)):

1. **Don't lose the army for free:** `army_collapse`, `team_army_deficit`. Fight together, fight in good spots, don't fight while behind.
2. **Spend what you earn:** keep **SQ above 75**. Add production instead of banking.
3. **Take a third base:** by about 8:00–9:00.
4. **Workers to 25+ at 4:00:** constant production from every town hall.
5. **Protect each other:** respond to attacks on allies immediately; don't leave early.
6. **Supply:** no blocks longer than 15s after 5:00.

Fix one at a time. The [improvement playbook](improvement-playbook.md) has a weekly plan.
