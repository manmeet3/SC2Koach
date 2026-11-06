import pytest

from sc2koach.gamedata import SUPPLY_PROVIDED, supply_table


@pytest.mark.parametrize(
    "race,start,hall,expected",
    [
        ("Terran", 15, "OrbitalCommand", 15),
        ("Protoss", 15, "Nexus", 15),
        ("Zerg", 14, "Hive", 6),
        # build 97563 ruleset (observed in the M0 spike)
        ("Terran", 13, "CommandCenterFlying", 13),
        ("Protoss", 13, "Nexus", 13),
        ("Zerg", 12, "Hatchery", 4),
    ],
)
def test_supply_table_calibrates_town_halls(race, start, hall, expected):
    table = supply_table(race, start)
    assert table[hall] == expected
    assert table["Pylon"] == table["SupplyDepot"] == table["Overlord"] == 8


def test_supply_table_does_not_mutate_defaults():
    supply_table("Terran", 13)
    assert SUPPLY_PROVIDED["CommandCenter"] == 15
