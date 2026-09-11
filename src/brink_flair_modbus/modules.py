"""The two modules an appliance may carry besides its base PCB (spec §2.1).

The display (UIF) answers input registers 4400-4421 and the Plus extension
PCB UWA2-E answers 4500-4544. Both are optional hardware, so each is probed
once at setup and left out of the poll when it is not there.

Each module's version registers never change, but they sit in the same
declared block as its readings, so reading them costs nothing over reading
the readings alone. They stay here rather than becoming a component of their
own. Both modules give their hardware version as BCD, where the base module
gives plain bytes.
"""

from __future__ import annotations

from modbus_connection.model import Component, boolean, enum, raw_register

from .enums import SignalOutputState
from .model import count, format_hardware_version, format_software_version, tenths


class UserInterface(Component):
    """The display module — input registers 4400-4421."""

    register_space = "input"
    register_ranges = ((4400, 4405), (4410, 4415), (4420, 4421))

    _software_type_major = raw_register(4400)
    _software_minor_fix = raw_register(4401)
    _software_build = raw_register(4402)
    _hardware = raw_register(4403)

    device_type = count(4404)
    dipswitch = count(4405)

    _language_type_major = raw_register(4410)
    _language_minor_fix = raw_register(4411)
    _language_build = raw_register(4412)

    _second_type_major = raw_register(4413)
    _second_minor_fix = raw_register(4414)
    _second_build = raw_register(4415)

    local_switch = count(4420)
    """The ventilation position set on the display, currently 0-3."""

    local_button = count(4421)
    """The display's button value. The spec gives the register a name and
    nothing else — no range, no type, no code list."""

    @property
    def software_version(self) -> str | None:
        """The display's software version, e.g. ``S1.01.03.0001``."""
        return format_software_version(
            self._software_type_major, self._software_minor_fix, self._software_build
        )

    @property
    def hardware_version(self) -> str | None:
        """The display's hardware version, e.g. ``H1.1``."""
        return format_hardware_version(self._hardware, bcd=True)

    @property
    def language_version(self) -> str | None:
        """The version of the language data loaded in the display."""
        return format_software_version(
            self._language_type_major, self._language_minor_fix, self._language_build
        )

    @property
    def second_software_version(self) -> str | None:
        """The version 4413-4415 reports.

        The spec lists two software versions for this module — 4400-4402 and
        4413-4415 — under the same description with the same example, and
        says nothing about what separates them. Both are exposed rather than
        one being guessed at.
        """
        return format_software_version(
            self._second_type_major, self._second_minor_fix, self._second_build
        )


class ExtensionModule(Component):
    """The Plus extension PCB UWA2-E — input registers 4500-4544."""

    register_space = "input"
    register_ranges = ((4500, 4505), (4520, 4524), (4541, 4544))

    _software_type_major = raw_register(4500)
    _software_minor_fix = raw_register(4501)
    _software_build = raw_register(4502)
    _hardware = raw_register(4503)

    device_type = count(4504)
    dipswitch = count(4505)

    ntc_temperature = tenths(4520, unit="°C")

    contact_1_closed = boolean(4521)
    contact_2_closed = boolean(4522)

    analogue_input_1 = tenths(4523, unit="V", signed=False)
    """0-100 on the wire for 0.0-10.0 V."""

    analogue_input_2 = tenths(4524, unit="V", signed=False)

    relay_output_1 = enum(4541, SignalOutputState)
    relay_output_2 = enum(4542, SignalOutputState)

    analogue_output_1 = tenths(4543, unit="V", signed=False)
    analogue_output_2 = tenths(4544, unit="V", signed=False)

    @property
    def software_version(self) -> str | None:
        """The extension module's software version, e.g. ``S1.01.03.0001``."""
        return format_software_version(
            self._software_type_major, self._software_minor_fix, self._software_build
        )

    @property
    def hardware_version(self) -> str | None:
        """The extension module's hardware version, e.g. ``H1.1``."""
        return format_hardware_version(self._hardware, bcd=True)
