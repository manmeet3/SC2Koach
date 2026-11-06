"""Static game data sc2reader doesn't provide (supply *provided*, town halls, Land abilities)."""

SUPPLY_CAP = 200

# Orbital Command "Calldown: Extra Supplies": permanently adds supply to the target depot.
EXTRA_SUPPLIES_ABILITY = "ExtraSupplies"
EXTRA_SUPPLIES = 8

WORKER_TYPES = frozenset({"SCV", "Probe", "Drone", "DroneBurrowed"})

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
