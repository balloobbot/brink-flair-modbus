"""The query helper's view of the appliance.

``script/query.py`` prints every component by reflection, so a property that
raises on a value the appliance gave would only show up when someone ran it
against hardware. These tests walk the same path with no device.
"""

from __future__ import annotations

import io
import json

from modbus_connection.cli_helper import print_component
from modbus_connection.mock import MockModbusUnit
from modbus_connection.model import Component

from brink_flair_modbus import BrinkFlair


def components(appliance: BrinkFlair) -> list[Component | None]:
    """Every component the query script prints."""
    return [
        appliance.identity,
        appliance.measurements,
        appliance.control,
        appliance.geo_heat_exchanger,
        appliance.co2_sensors,
        appliance.user_interface,
        appliance.extension,
        appliance.parameters,
    ]


async def test_every_component_prints(appliance: BrinkFlair) -> None:
    await appliance.async_update()

    out = io.StringIO()
    for component in components(appliance):
        assert component is not None
        print_component(component, file=out)

    printed = out.getvalue()
    assert "supply_flow" in printed
    assert "148 m³/h" in printed  # the unit comes off the field
    assert "auto_modbus" in printed  # an enum prints its name
    assert "S1.01.03.0001" in printed  # a computed property prints too
    assert "14:35:00" in printed


async def test_nothing_raises_on_an_appliance_that_answered_zero(
    appliance: BrinkFlair, mock_modbus_unit: MockModbusUnit
) -> None:
    """A fresh or odd appliance must not break the one tool used to debug it."""
    await appliance.async_update()
    for space in ("input", "holding"):
        store = getattr(mock_modbus_unit, space)
        for address in list(store):
            store[address] = 0
    await appliance.async_update()

    out = io.StringIO()
    for component in components(appliance):
        assert component is not None
        print_component(component, file=out)

    assert out.getvalue()


async def test_the_raw_dump_survives_being_written_down(appliance: BrinkFlair) -> None:
    """``--raw`` prints this, and an issue carries it as JSON.

    JSON has no integer keys, so every address is written as a string. A
    maintainer replaying the dump needs them to come back as the numbers
    they were, which is what modbus-connection's ``load_raw`` does.
    """
    raw = await appliance.async_read_raw()

    restored = json.loads(json.dumps(raw))

    assert restored.keys() == raw.keys()
    assert {
        space: {int(address): value for address, value in values.items()}
        for space, values in restored.items()
    } == raw
