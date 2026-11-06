"""Static game data sc2reader doesn't provide (supply *provided*, town halls, Land abilities)."""

SUPPLY_CAP = 200

# Orbital Command "Calldown: Extra Supplies": permanently adds supply to the target depot.
EXTRA_SUPPLIES_ABILITY = "ExtraSupplies"
EXTRA_SUPPLIES = 8
EXTRA_SUPPLIES_TARGETS = frozenset({"SupplyDepot", "SupplyDepotLowered"})

WORKER_TYPES = frozenset({"SCV", "Probe", "Drone", "DroneBurrowed"})
# sc2reader flags MULEs as workers, but the game's worker count excludes them.
NON_WORKER_TYPES = frozenset({"MULE"})

# Elimination (design/DESIGN.md §5): a player is out when their last structure dies.
# Corrections to sc2reader's is_building flag for what the game counts as a structure.
STRUCTURE_EXTRA_TYPES = frozenset(
    {"ShieldBattery", "RefineryRich", "ExtractorRich", "AssimilatorRich"}
)
NON_STRUCTURE_TYPES = frozenset({"CreepTumor", "CreepTumorBurrowed", "CreepTumorQueen"})

# --------------------------------------------------------------------------- rulesets (§4)

# Newest game build whose rules were verified against real replays (M0 spike).
KNOWN_MAX_BUILD = 98310
# Newest data pack bundled with sc2reader 1.9.0; later builds reuse it.
SC2READER_MAX_DATAPACK = 97364

# Values a replay can't tell us, keyed by the first build they apply to. Builds use the latest
# entry with min_build <= build. Keys: "extra_supplies" (Calldown: Extra Supplies amount).
RULESETS: list[dict] = [
    {"min_build": 0, "overrides": {"extra_supplies": EXTRA_SUPPLIES}},
]


def resolve_overrides(build: int) -> dict[str, float]:
    """Overrides for a game build: the latest RULESETS entry with min_build <= build."""
    best: dict | None = None
    for entry in RULESETS:
        if entry["min_build"] <= build and (
            best is None or entry["min_build"] >= best["min_build"]
        ):
            best = entry
    return dict(best["overrides"]) if best else {}


TOWN_HALL_TYPES = frozenset(
    {
        "CommandCenter",
        "CommandCenterFlying",
        "OrbitalCommand",
        "OrbitalCommandFlying",
        "PlanetaryFortress",
        "Nexus",
        "Hatchery",
        "Lair",
        "Hive",
    }
)

# Types a town hall can be built as (UnitInitEvent / starting UnitBornEvent).
TOWN_HALL_BUILD_TYPES = frozenset({"CommandCenter", "Nexus", "Hatchery"})

FLYING_TOWN_HALLS = {
    "CommandCenterFlying": "CommandCenter",
    "OrbitalCommandFlying": "OrbitalCommand",
}

LAND_ABILITIES = {
    "LandCommandCenter": "CommandCenter",
    "LandOrbitalCommand": "OrbitalCommand",
}

# Supply provided once the unit is finished, on the standard ruleset. Game builds can change these
# (design/DESIGN.md §4): build 97563 uses 13 for CC/Nexus and 4 for Hatchery. Use supply_table()
# with the replay's first snapshot rather than this dict directly.
SUPPLY_PROVIDED = {
    "CommandCenter": 15,
    "CommandCenterFlying": 15,
    "OrbitalCommand": 15,
    "OrbitalCommandFlying": 15,
    "PlanetaryFortress": 15,
    "Nexus": 15,
    "Hatchery": 6,
    "Lair": 6,
    "Hive": 6,
    "SupplyDepot": 8,
    "SupplyDepotLowered": 8,
    "Pylon": 8,
    "Overlord": 8,
    "OverlordTransport": 8,
    "Overseer": 8,
    "OverseerSiegeMode": 8,
}

_TERRAN_PROTOSS_HALLS = (
    "CommandCenter",
    "CommandCenterFlying",
    "OrbitalCommand",
    "OrbitalCommandFlying",
    "PlanetaryFortress",
    "Nexus",
)
_ZERG_HALLS = ("Hatchery", "Lair", "Hive")
STANDARD_STARTING_WORKERS = 12


def supply_table(race: str, start_food_made: float) -> dict[str, float]:
    """Supply-provided table for one player, calibrated from their first snapshot.

    At game start a player has one town hall (plus one Overlord for Zerg), so the first
    snapshot's food_made gives the town hall value for this patch.
    """
    table = dict(SUPPLY_PROVIDED)
    if race == "Zerg":
        hall = start_food_made - SUPPLY_PROVIDED["Overlord"]
        names = _ZERG_HALLS
    else:
        hall = start_food_made
        names = _TERRAN_PROTOSS_HALLS
    if hall > 0:
        for name in names:
            table[name] = hall
    return table
