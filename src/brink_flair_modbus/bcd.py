"""Packed BCD — the encoding the spec names for the serial number and versions.

The serial number at 4010 is stated as "Numbers in BCD", and the hardware
version of the UIF and extension modules as "Major and minor in BCD format".
The base module's own hardware version is stated as plain bytes instead, so it
does not come through here — see :mod:`~brink_flair_modbus.model`.
"""

from __future__ import annotations


def bcd_digits(raw: int, count: int) -> str:
    """Decode *count* packed-BCD digits; a nibble above 9 is not BCD."""
    digits = f"{raw:0{count}x}"
    if len(digits) > count or not digits.isdigit():
        raise ValueError(f"not packed BCD: 0x{raw:0{count}X}")
    return digits


def bcd_byte(raw: int) -> int:
    """Decode one packed-BCD byte into the 0-99 it stands for."""
    return int(bcd_digits(raw & 0xFF, 2))
