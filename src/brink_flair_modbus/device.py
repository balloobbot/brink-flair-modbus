"""The device object: one Brink HRA reached through a ``ModbusUnit``.

The appliance's register map splits cleanly into sub-systems, and four of
them belong to hardware an appliance may not have — a display, the Plus
extension PCB, a geo heat exchanger and CO2 sensors. Which of those are
present is settled once, by probing at setup, so every poll after that is a
fixed list of components to read. One sub-system failing does not take the
rest of the poll with it; the caller gets an :class:`UpdateReport` saying
which refreshed and which did not.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from modbus_connection import (
    IllegalDataAddressError,
    IllegalFunctionError,
    ModbusConnectionError,
    ModbusError,
    ModbusTimeoutError,
)
from modbus_connection.model import Component

from .control import Commands, Control
from .identity import Identity
from .measurements import Co2Sensors, GeoHeatExchanger, Measurements
from .modules import ExtensionModule, UserInterface
from .parameters import Parameters

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

MANUFACTURER = "Brink"
MODEL = "Flair"

# The sub-systems every appliance has, in the order a poll reads them.
CORE_READINGS = ("measurements", "control")

# The optional ones, by attribute name, again in poll order.
OPTIONAL_READINGS = ("geo_heat_exchanger", "co2_sensors", "user_interface", "extension")


async def _optional[C: Component](component: C) -> C | None:
    """Read an optional sub-system; ``None`` if this appliance lacks it."""
    try:
        await component.async_update()
    except (IllegalDataAddressError, IllegalFunctionError):
        return None
    return component


@dataclass
class UpdateReport:
    """What one poll managed to refresh."""

    updated: list[str] = field(default_factory=list)
    failed: dict[str, ModbusError] = field(default_factory=dict)


class BrinkFlair:
    """A Brink heat recovery appliance with a UWA2-B control PCB.

    Takes a :class:`~modbus_connection.ModbusUnit`; the caller owns the
    connection, so the appliance can be reached over its RS-485 line directly
    or through a Modbus RTU gateway.
    """

    manufacturer = MANUFACTURER
    model = MODEL
    """The product line. Input register 4004 carries an appliance type, but
    the spec states it is internal and "has no external value", so nothing in
    the map names the individual model."""

    def __init__(self, unit: ModbusUnit) -> None:
        self._unit = unit

        self.identity = Identity(unit)
        """The base module's versions and serial number. Read once at setup."""

        self.measurements = Measurements(unit)
        """What the appliance reports about its own running."""

        self.control = Control(unit)
        """Whether and how Modbus is driving the appliance."""

        self.commands = Commands(unit)
        """The filter-warning reset and the appliance reset. Written, never read."""

        self.parameters = Parameters(unit)
        """The settings. Read at setup, and again only when asked."""

        # Optional hardware: settled by the first update.
        self.geo_heat_exchanger: GeoHeatExchanger | None = None
        self.co2_sensors: Co2Sensors | None = None
        self.user_interface: UserInterface | None = None
        self.extension: ExtensionModule | None = None

        self._readings: tuple[str, ...] | None = None
        self._settings = ("parameters",)

    async def _async_setup(self) -> None:
        """Read what cannot change, and settle which sub-systems are present.

        Runs from the first update, and again on the next one if the
        appliance was unreachable.
        """
        await self.identity.async_update()

        self.geo_heat_exchanger = await _optional(GeoHeatExchanger(self._unit))
        self.co2_sensors = await _optional(Co2Sensors(self._unit))
        self.user_interface = await _optional(UserInterface(self._unit))
        self.extension = await _optional(ExtensionModule(self._unit))

        self._readings = CORE_READINGS + tuple(
            name for name in OPTIONAL_READINGS if getattr(self, name) is not None
        )

    async def _async_poll(
        self, names: tuple[str, ...], report: UpdateReport
    ) -> UpdateReport:
        """Read each named sub-system on its own, recording what happened."""
        for name in names:
            try:
                await getattr(self, name).async_update(notify=False)
            except ModbusConnectionError:
                raise  # the link is down; the rest would only wait for timeouts
            except ModbusTimeoutError as err:
                if not report.updated and not report.failed:
                    raise  # nothing answered yet: assume the rest time out too
                report.failed[name] = err
            except ModbusError as err:
                report.failed[name] = err
            else:
                report.updated.append(name)
        return report

    def _notify(self, report: UpdateReport) -> None:
        """Fire the listeners of everything this update refreshed."""
        for name in report.updated:
            getattr(self, name).notify()

    async def _async_ensure_setup(self) -> tuple[str, ...]:
        """The polled sub-systems, running setup first if it has not run."""
        if self._readings is None:
            await self._async_setup()
            assert self._readings is not None
        return self._readings

    async def async_update_readings(self) -> UpdateReport:
        """Refresh what the appliance measures and what it is being told to do."""
        readings = await self._async_ensure_setup()
        report = await self._async_poll(readings, UpdateReport())
        self._notify(report)
        return report

    async def async_update_settings(self) -> UpdateReport:
        """Refresh the settings.

        Seventeen round trips over a 19200-baud line, so poll this far less
        often than the readings — or not at all, if nothing else writes them.
        """
        await self._async_ensure_setup()
        report = await self._async_poll(self._settings, UpdateReport())
        self._notify(report)
        return report

    async def async_update(self) -> UpdateReport:
        """Refresh every sub-system, the settings included."""
        readings = await self._async_ensure_setup()
        report = await self._async_poll(readings, UpdateReport())
        await self._async_poll(self._settings, report)
        self._notify(report)
        return report

    async def async_read_raw(self) -> dict[str, dict[int, int | bool]]:
        """Every register this appliance is read from, undecoded.

        For a diagnostics download. The identity and the settings come along
        even though a reading poll skips them: a dump is read to find out how
        the appliance is set up. :attr:`commands` stays out — those registers
        clear themselves when read. Nothing notifies: a download is not a poll.
        """
        readings = await self._async_ensure_setup()
        raw: dict[str, dict[int, int | bool]] = {}
        for name in ("identity", *readings, *self._settings):
            read = await getattr(self, name).async_read_raw(notify=False)
            for space, values in read.items():
                raw.setdefault(space, {}).update(values)
        return {space: dict(sorted(values.items())) for space, values in raw.items()}
