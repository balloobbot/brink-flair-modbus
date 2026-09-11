"""What a poll costs on the wire.

The appliance sits on a 19200-baud RS-485 line, so the number of requests is
the number that matters. Every component here declares ``register_ranges``
for the rows the spec documents, which is what keeps a read off the gaps
between them — and what makes a poll cost more requests than the gaps alone
would. Both halves of that trade are pinned here rather than left to drift.
"""

from __future__ import annotations

from modbus_connection.mock import MockModbusUnit
from modbus_connection.model import Component

from brink_flair_modbus import BrinkFlair

# Every block of input registers the spec documents past the identity, with
# the component that reads it.
READING_BLOCKS = [
    ("input", 4020, 5),  # function, fan control, mode, the two pressures
    ("input", 4030, 8),  # the supply fan
    ("input", 4040, 8),  # the exhaust fan
    ("input", 4050, 2),  # the bypass
    ("input", 4060, 2),  # the preheater
    ("input", 4070, 3),  # frost protection
    ("input", 4080, 4),  # the flow switch and the loose sensors
    ("input", 4090, 1),  # the signal output
    ("input", 4100, 2),  # the filters and the eBus supply
    ("input", 4110, 10),  # the clock, the date words and the four counters
    ("holding", 8000, 4),  # what Modbus has told the appliance to do
]

OPTIONAL_BLOCKS = [
    ("input", 4150, 1),  # the geo heat exchanger
    ("input", 4200, 8),  # the four CO2 sensors
    ("input", 4400, 6),  # the display's versions
    ("input", 4410, 6),  # its language data and second version
    ("input", 4420, 2),  # its switch and button
    ("input", 4500, 6),  # the UWA2-E's versions
    ("input", 4520, 5),  # its NTC, contacts and analogue inputs
    ("input", 4541, 4),  # its relays and analogue outputs
]

SETTINGS_BLOCKS = 17
"""The holding-register runs of spec §2.2, counted from ``Parameters``."""


def blocks(unit: MockModbusUnit) -> list[tuple[str, int, int]]:
    """The reads the unit received, as (space, address, count)."""
    return [(b.register_type, b.address, b.count) for b in unit.read_events]


async def test_a_full_appliance_polls_its_readings_in_nineteen_reads(
    appliance: BrinkFlair, mock_modbus_unit: MockModbusUnit
) -> None:
    """One request per documented run, and not one register outside them."""
    await appliance.async_update()  # first poll: setup reads the fixed blocks
    mock_modbus_unit.read_events.clear()

    await appliance.async_update_readings()

    assert blocks(mock_modbus_unit) == READING_BLOCKS + OPTIONAL_BLOCKS


async def test_a_bare_appliance_polls_in_eleven_reads(
    bare_appliance: BrinkFlair, mock_modbus_unit: MockModbusUnit
) -> None:
    """Hardware the appliance does not have costs nothing after setup."""
    await bare_appliance.async_update()
    mock_modbus_unit.read_events.clear()

    await bare_appliance.async_update_readings()

    assert blocks(mock_modbus_unit) == READING_BLOCKS


async def test_setup_reads_the_identity_and_probes_the_optional_hardware(
    appliance: BrinkFlair, mock_modbus_unit: MockModbusUnit
) -> None:
    """The identity's two runs, then one probe per optional sub-system."""
    await appliance.async_update()

    assert blocks(mock_modbus_unit)[:2] == [("input", 4000, 6), ("input", 4010, 3)]
    assert ("input", 4150, 1) in blocks(mock_modbus_unit)


async def test_the_identity_is_read_once(
    appliance: BrinkFlair, mock_modbus_unit: MockModbusUnit
) -> None:
    await appliance.async_update()
    mock_modbus_unit.read_events.clear()

    await appliance.async_update()

    assert ("input", 4000, 6) not in blocks(mock_modbus_unit)


async def test_the_settings_cost_seventeen_reads(
    appliance: BrinkFlair, mock_modbus_unit: MockModbusUnit
) -> None:
    await appliance.async_update()
    mock_modbus_unit.read_events.clear()

    await appliance.async_update_settings()

    read = blocks(mock_modbus_unit)
    assert len(read) == SETTINGS_BLOCKS
    assert all(space == "holding" for space, _, _ in read)
    assert read[0] == ("holding", 6000, 4)
    assert read[-1] == ("holding", 7990, 3)


async def test_the_one_shot_commands_are_never_read(
    appliance: BrinkFlair, mock_modbus_unit: MockModbusUnit
) -> None:
    """Reading 8010 or 8011 clears the outcome it reports, so no poll may."""
    await appliance.async_update()
    await appliance.async_read_raw()

    covered = {
        address
        for space, start, count in blocks(mock_modbus_unit)
        if space == "holding"
        for address in range(start, start + count)
    }
    assert covered.isdisjoint({8010, 8011})


async def test_a_wider_plan_can_be_asked_for_before_the_first_poll(
    appliance: BrinkFlair, mock_modbus_unit: MockModbusUnit
) -> None:
    """The escape hatch the README documents, for an appliance that answers
    across the map's gaps: drop the ranges and let gap planning merge."""
    measurements: Component = appliance.measurements
    measurements.register_ranges = None
    measurements.max_gap = 32

    await appliance.async_update()

    reads = [b for b in blocks(mock_modbus_unit) if 4020 <= b[1] <= 4119]
    assert reads == [("input", 4020, 100)]
