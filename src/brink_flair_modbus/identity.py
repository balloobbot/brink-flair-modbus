"""What the base module UWA2-B is — input registers 4000-4012 (spec §2.1).

Nothing here changes while the appliance runs, so it is read once at setup and
never polled. Registers 4006-4009 are undocumented and sit between the two
runs the spec gives, so the ranges below keep every read off them.
"""

from __future__ import annotations

from modbus_connection.model import Component, NumberField, raw_register

from .bcd import bcd_digits
from .model import count, format_hardware_version, format_software_version

SERIAL_NUMBER = 4010
SERIAL_NUMBER_WORDS = 3
SERIAL_NUMBER_DIGITS = 12


def _serial_digits(raw: int) -> str:
    """Decode the twelve packed-BCD digits of 4010-4012."""
    return bcd_digits(raw, SERIAL_NUMBER_DIGITS)


class Identity(Component):
    """The base module's versions, type and serial number."""

    register_space = "input"
    register_ranges = ((4000, 4005), (SERIAL_NUMBER, 4012))

    _software_type_major = raw_register(4000)
    _software_minor_fix = raw_register(4001)
    _software_build = raw_register(4002)
    _hardware = raw_register(4003)

    appliance_type = count(4004)
    """An internal number for the functional appliance. The spec states it has
    no external value, so it is left as the raw count."""

    dipswitch = count(4005)
    """The 0-63 the type-and-subtype dipswitch is set to."""

    serial_number: NumberField[str] = NumberField(
        SERIAL_NUMBER,
        count=SERIAL_NUMBER_WORDS,
        signed=False,
        convert=_serial_digits,
    )
    """Twelve BCD digits. A value that is not BCD decodes to ``None``."""

    @property
    def software_version(self) -> str | None:
        """The base module's software version, e.g. ``S1.01.03.0001``."""
        return format_software_version(
            self._software_type_major, self._software_minor_fix, self._software_build
        )

    @property
    def hardware_version(self) -> str | None:
        """The base module's hardware version, e.g. ``H1.1``.

        Read as plain bytes: the spec gives this register as "Numbers in bytes
        range [00..99]" where it gives the other two modules' as BCD.
        """
        return format_hardware_version(self._hardware, bcd=False)
