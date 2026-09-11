#!/usr/bin/env python3

"""Query a Brink HRA and print every value.

Reads one appliance once and dumps it to the terminal — the quickest way to
check a real appliance with no application around it. Which optional modules
it has comes from probing it, so nothing has to be passed on the command line
beyond how to reach it.

::

    uv run script/query.py /dev/ttyUSB0 --unit 20 --baudrate 19200 --parity E
    uv run script/query.py 192.168.1.50 --transport tcp --unit 20
"""

from __future__ import annotations

import argparse
import asyncio

from modbus_connection import ModbusError
from modbus_connection.cli_helper import (
    CountingUnit,
    add_connection_args,
    connect_from_args,
    print_component,
)

from brink_flair_modbus import BrinkFlair

# The appliance speaks Modbus RTU on RS-485 and nothing else. Over TCP it is
# reached through a gateway that forwards those RTU frames, so the framing
# stays rtu either way. The first pair is what --transport defaults to.
CONNECTIONS = (("serial", "rtu"), ("tcp", "rtu"))

DEFAULT_UNIT = 20
"""The appliance's factory slave address (setting 14.2)."""


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_connection_args(parser, connections=CONNECTIONS)
    parser.add_argument("--unit", type=int, default=DEFAULT_UNIT, help="Modbus unit id")
    args = parser.parse_args()

    try:
        connection = await connect_from_args(args)
    except ModbusError as err:
        print(f"Could not connect: {err}")
        return 1

    counting = CountingUnit(connection.for_unit(args.unit))
    appliance = BrinkFlair(counting)
    try:
        report = await appliance.async_update()
    except ModbusError as err:
        print(f"Could not read the appliance: {err}")
        return 1
    finally:
        await connection.close()

    print(f"{appliance.manufacturer} {appliance.model}")
    print_component(appliance.identity, title="Identity")
    print_component(appliance.measurements, title="Measurements")
    print_component(appliance.control, title="Remote control")
    if appliance.geo_heat_exchanger is not None:
        print_component(appliance.geo_heat_exchanger, title="Geo heat exchanger")
    if appliance.co2_sensors is not None:
        print_component(appliance.co2_sensors, title="CO2 sensors")
    if appliance.user_interface is not None:
        print_component(appliance.user_interface, title="Display")
    if appliance.extension is not None:
        print_component(appliance.extension, title="Extension module UWA2-E")
    print_component(appliance.parameters, title="Settings")

    for name, failure in sorted(report.failed.items()):
        print(f"\n{name} did not answer: {failure}")
    print(f"\n{counting.reads} Modbus reads")
    return 0


raise SystemExit(asyncio.run(main()))
