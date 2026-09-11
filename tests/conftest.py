"""Fixtures: a Brink HRA over modbus-connection's in-memory mock backend.

Every register of this map is one 16-bit word except the four counters at
4113-4119, which the seeds below give as two-word lists, high word first.
There are no coils and no discrete inputs.
"""

from __future__ import annotations

import pytest
from modbus_connection import IllegalDataAddressError
from modbus_connection.mock import MockModbusUnit

from brink_flair_modbus import BrinkFlair


def words(value: int) -> list[int]:
    """Split a 32-bit raw value into its two registers, high word first."""
    return [(value >> 16) & 0xFFFF, value & 0xFFFF]


def signed(value: int) -> int:
    """The 16-bit raw pattern a negative value is stored as."""
    return value & 0xFFFF


SERIAL = "123456789012"
OPERATING_HOURS = 12345
FILTER_FLOW = 987654
TOTAL_FLOW = 5432109

# The base module's own block: input registers 4000-4012.
IDENTITY: dict[int, int | list[int]] = {
    4000: 0x5301,  # type "S", major 1
    4001: 0x0103,  # minor 01, fix 03
    4002: 1,  # build 0001
    4003: 0x0101,  # hardware H1.1, plain bytes
    4004: 42,  # appliance type
    4005: 7,  # dipswitch
    4010: [0x1234, 0x5678, 0x9012],  # serial number in BCD
}

# What the appliance reports about itself: input registers 4020-4119.
MEASUREMENTS: dict[int, int | list[int]] = {
    4020: 12,  # active function -> auto modbus
    4021: 1,  # fan control type -> constant flow
    4022: 2,  # ventilation mode -> normal
    4023: 452,  # supply pressure -> 45.2 Pa
    4024: signed(-389),  # exhaust pressure -> -38.9 Pa
    4030: 4,  # supply fan -> running
    4031: 150,  # supply flow setpoint -> 150 m³/h
    4032: 148,
    4033: 175,  # supply mass flow -> 175 kg/h
    4034: 2100,  # supply fan -> 2100 rpm
    4035: 2050,
    4036: 195,  # supply fan temperature -> 19.5 °C
    4037: 452,  # supply humidity -> 45.2 %
    4040: 4,  # exhaust fan -> running
    4041: 150,
    4042: 152,
    4043: 178,
    4044: 2150,
    4045: 2100,
    4046: 212,  # exhaust fan temperature -> 21.2 °C
    4047: 501,
    4050: 4,  # bypass -> closed
    4051: 0,
    4060: 1,  # preheater -> inactive
    4061: 0,
    4070: 2,  # frost -> no frost
    4071: 0,
    4072: 0,
    4080: 2,  # flow switch -> normal
    4081: signed(-35),  # NTC1 -> -3.5 °C
    4082: 188,  # NTC2 -> 18.8 °C
    4083: 483,  # RHT sensor -> 48.3 %
    4090: 0,  # signal output -> 0 V
    4100: 0,  # filters -> not dirty
    4101: 3,  # eBus -> power on
    4110: 0x0E23,  # 14:35
    4111: 0x0A19,  # the two undecodable date words
    4112: 0x1A00,
    4113: words(OPERATING_HOURS),
    4115: 1200,  # filter hours
    4116: words(FILTER_FLOW),
    4118: words(TOTAL_FLOW),
}

# Optional hardware: the geo valve, the CO2 sensors, the display, the UWA2-E.
GEO: dict[int, int | list[int]] = {4150: 1}  # closed

CO2: dict[int, int | list[int]] = {
    4200: 4,  # sensor 1 -> running
    4201: 650,  # 650 ppm
    4202: 1,  # sensor 2 -> not initialized
    4203: 0,
    4204: 1,
    4205: 0,
    4206: 1,
    4207: 0,
}

USER_INTERFACE: dict[int, int | list[int]] = {
    4400: 0x5301,
    4401: 0x0102,
    4402: 12,  # -> S1.01.02.0012
    4403: 0x0201,  # hardware H2.1, in BCD
    4404: 5,
    4405: 3,
    4410: 0x5301,
    4411: 0x0100,
    4412: 5,  # language data -> S1.01.00.0005
    4413: 0x5301,
    4414: 0x0103,
    4415: 9,  # the second software version -> S1.01.03.0009
    4420: 2,  # display switch -> normal
    4421: 0,
}

EXTENSION: dict[int, int | list[int]] = {
    4500: 0x5301,
    4501: 0x0100,
    4502: 3,  # -> S1.01.00.0003
    4503: 0x0101,  # hardware H1.1, in BCD
    4504: 9,
    4505: 1,
    4520: 120,  # extension NTC -> 12.0 °C
    4521: 0,  # contact 1 open
    4522: 1,  # contact 2 closed
    4523: 25,  # analogue input 1 -> 2.5 V
    4524: 100,  # analogue input 2 -> 10.0 V
    4541: 0,  # relay 1 -> 0 V
    4542: 1,  # relay 2 -> 24 V
    4543: 50,  # analogue output 1 -> 5.0 V
    4544: 0,
}

# The settings, holding registers 6000-7992.
PARAMETERS: dict[int, int | list[int]] = {
    6000: 50,  # flow presets -> 50/100/150/300 m³/h
    6001: 100,
    6002: 150,
    6003: 300,
    6010: 15,  # PWM presets, supply and exhaust interleaved
    6011: 15,
    6012: 30,
    6013: 30,
    6014: 50,
    6015: 50,
    6016: 100,
    6017: 100,
    6030: 1,  # flow type -> constant flow
    6031: 1,
    6032: 0,
    6033: 1,  # imbalance allowed
    6034: 5,  # imbalance -> 5 %
    6035: signed(-5),
    6036: 5,
    6100: 0,  # bypass -> automatic
    6101: 220,  # from the dwelling -> 22.0 °C
    6102: 100,  # from outside -> 10.0 °C
    6103: 20,  # hysteresis -> 2.0 °C
    6104: 0,
    6105: 3,
    6110: 0,
    6111: 170,  # minimum inlet -> 17.0 °C
    6120: 90,  # filter warning after 90 days
    6130: 0,  # no external heater
    6131: 210,
    6140: 1,  # RHT sensor on
    6141: 0,
    6150: 1,  # CO2 sensors on
    6151: 400,
    6152: 2000,
    6153: 400,
    6154: 2000,
    6155: 400,
    6156: 2000,
    6157: 400,
    6158: 2000,
    6170: 3,  # signal output -> filter warning and error status
    6171: 0,
    6200: 0,
    6201: 0,
    6202: 7,
    6203: 7,
    6210: 0,
    6211: 0,
    6212: 7,
    6213: 7,
    6220: 0,
    6221: 0,
    6222: 100,
    6230: 0,
    6231: 0,
    6232: 100,
    6240: 1,  # geo heat exchanger on
    6241: 50,  # -> 5.0 °C
    6242: 250,  # -> 25.0 °C
    6243: 0,
    6244: 2,  # driven from relay output 1
    6900: 1,  # Dutch
    6901: 0,
    6902: 1,
    6903: 0x0915,
    6904: 2026,
    6905: 0x0E23,
    6906: 0x0400,
    7990: 1,  # external Modbus connection
    7991: 20,  # the factory slave address
    7992: 4,  # 19200 baud
}

# The remote-control block, 8000-8003. 8010 and 8011 are never read.
CONTROL: dict[int, int | list[int]] = {
    8000: 2,  # Modbus drives the flow rate
    8001: 2,
    8002: 150,
    8003: 0,  # not in standby
}


def seed(unit: MockModbusUnit, *, optional: bool = True) -> MockModbusUnit:
    """Seed *unit* with the whole map; *optional* adds the optional hardware.

    With ``optional=False`` the four optional blocks are refused with an
    illegal-data-address exception, which is what an appliance without that
    hardware is assumed to answer.
    """
    unit.input.update(IDENTITY)
    unit.input.update(MEASUREMENTS)
    unit.holding.update(PARAMETERS)
    unit.holding.update(CONTROL)
    if optional:
        unit.input.update(GEO)
        unit.input.update(CO2)
        unit.input.update(USER_INTERFACE)
        unit.input.update(EXTENSION)
    return unit


@pytest.fixture
def appliance(mock_modbus_unit: MockModbusUnit) -> BrinkFlair:
    """A fully equipped appliance: display, UWA2-E, geo valve and CO2 sensors."""
    return BrinkFlair(seed(mock_modbus_unit))


@pytest.fixture
def bare_appliance(mock_modbus_unit: MockModbusUnit) -> BrinkFlair:
    """A base appliance: a UWA2-B and nothing else."""
    unit = seed(mock_modbus_unit, optional=False)
    for address in (4150, 4200, 4400, 4500):
        unit.fail_read(address, IllegalDataAddressError(), register_type="input")
    return BrinkFlair(unit)
