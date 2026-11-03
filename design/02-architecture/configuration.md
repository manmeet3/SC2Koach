# Configuration

Who is analyzed is never configured: every player in the replay is always analyzed. Configuration only decides **perspective** (focus player), **identity matching**, and optional **roster** tracking.

## Precedence
CLI flags > config file (`sc2koach.toml` in the working directory, then `~/.config/sc2koach/config.toml`) > built-in defaults.

## Focus player
| CLI flag | Config key | Meaning |
|---|---|---|
| `--focus <name>` | `focus.name` | Display name of the focus player (default `blacksheep`) |
| `--focus-id <handle>` | `focus.toon_handle` | Battle.net toon handle (e.g. `1-S2-1-1234567`); unique and stable across name changes |
| `--alias <name>` (repeatable) | `focus.aliases` | Other names/accounts belonging to the same person |

**Matching order:** toon handle → name → aliases (case-insensitive). If several players match, or none do, the CLI warns, sets `focus_player_id = null`, and writes the report in neutral third person. It never guesses.

## Roster (optional)
```toml
[[roster]]
name = "blacksheep"
toon_handle = "1-S2-1-1234567"
aliases = ["blacksheep2"]

[[roster]]
name = "teammate1"
```
- **No roster (default):** treat teammates as random ladder partners. History is still stored for every player; the team view groups results by mode and partner/opponent composition.
- **Roster present:** roster members are matched with the same rules as the focus player. Phase 3/4 history and team views then group by roster member. `--focus` may name any roster member.

## Counterpart pairing
| CLI flag | Config key | Meaning |
|---|---|---|
| `--pair <nameA>:<nameB>` (repeatable) | — | Manually pair two opposing players for this run, overriding the default |

Default pairing is **nominal**: lobby-slot order within each team, falling back to player id order. Replays can't tell us who actually fought whom, so counterpart comparisons are labeled as nominal and never drive findings on their own.

## Thresholds
All detection thresholds and ranking weights live in `[thresholds]` with Gold–Platinum defaults (see [moment-detection](../03-components/moment-detection.md)). Race-specific values use per-race keys, e.g.:
```toml
[thresholds]
supply_block_min_s = 7
trade_grace_s = 20

[thresholds.low_workers_at_4m]
Terran = 26
Protoss = 26
Zerg = 30

[report]
top_n = 3
```
Unknown keys are an error (catches typos). The effective values are written to the findings JSON and the report appendix.

## Exit codes
`0` success · `1` unexpected error · `2` unsupported replay (1v1, FFA, archon, AI) · `3` corrupt/unparseable replay or parser failure · `4` invalid config.
