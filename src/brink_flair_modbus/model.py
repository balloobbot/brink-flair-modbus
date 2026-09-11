"""Field presets and version decoding for the UWA2-B/UWA2-E register map.

Every value in the map is one 16-bit register unless the spec gives it a
``[0..4294967295]`` range, which the four counters at 4113-4119 have and
nothing else does. So the presets below spell out only the two rules the spec
repeats: a temperature, a pressure, a humidity and a voltage are stored in
tenths, and everything else is the raw count.

The spec states no word order for the 32-bit counters, so they decode with
modbus-connection's ``"big"`` default — the Modbus convention, high word in
the lower address.
"""

from __future__ import annotations

from modbus_connection.model import NumberField, WriteValidator, gauge, integer

from .bcd import bcd_byte

TENTHS = 0.1
"""The scale of every value the spec calls "in tenth of"."""


def tenths(
    address: int,
    *,
    unit: str,
    signed: bool = True,
    writable: bool | WriteValidator = False,
) -> NumberField[float]:
    """A value the spec stores in tenths — a temperature, pressure or volt."""
    return gauge(address, TENTHS, signed=signed, unit=unit, writable=writable)


def humidity(address: int) -> NumberField[float]:
    """A relative humidity, stored 0-1000 for 0.0-100.0 %."""
    return gauge(address, TENTHS, signed=False, unit="%")


def count(
    address: int, *, unit: str | None = None, writable: bool | WriteValidator = False
) -> NumberField[int]:
    """An unsigned whole number — a flow, a speed, a percentage, a code."""
    return integer(address, signed=False, unit=unit, writable=writable)


def signed_count(
    address: int, *, unit: str | None = None, writable: bool | WriteValidator = False
) -> NumberField[int]:
    """A signed whole number, for the few settings the spec marks signed."""
    return integer(address, unit=unit, writable=writable)


def format_software_version(
    type_major: int | None, minor_fix: int | None, build: int | None
) -> str | None:
    """Render the three version registers as the spec's ``S1.01.03.0001``.

    The first register carries the type letter in ASCII in its high byte and
    the major number in its low byte, the second the minor and fix numbers one
    per byte, and the third the build number as a whole word. A register that
    has not been read makes the whole version ``None``.
    """
    if type_major is None or minor_fix is None or build is None:
        return None
    return (
        f"{chr(type_major >> 8)}{type_major & 0xFF}"
        f".{minor_fix >> 8:02d}.{minor_fix & 0xFF:02d}.{build:04d}"
    )


def format_hardware_version(word: int | None, *, bcd: bool) -> str | None:
    """Render a hardware-version register as the spec's ``H1.1``.

    High byte is the major number and low byte the minor. The spec gives the
    base module's as plain bytes and the UIF and extension modules' as BCD,
    which differ for any number above 9.
    """
    if word is None:
        return None
    major, minor = (word >> 8) & 0xFF, word & 0xFF
    if bcd:
        major, minor = bcd_byte(major), bcd_byte(minor)
    return f"H{major}.{minor}"
