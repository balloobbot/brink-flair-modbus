"""Driving the appliance — remote-control registers 8000-8011 (spec §2.3).

Two components, split by what a read of the register means.

:class:`Control` covers 8000-8003, where a read answers the last accepted
command, so it is polled like any other state. :class:`Commands` covers the
two one-shot actions at 8010-8011, where a read answers whether the action
ran and **clears itself in doing so**. Reading those on a poll would consume
the outcome before a caller asked for it, so they are written and never read
— which is also why :class:`Control` declares ranges that stop at 8003.

The spec warns that a power cycle forgets everything in 8000-8011: a
consumer that drives the appliance over Modbus has to set it up again after
the appliance loses mains.
"""

from __future__ import annotations

from typing import Any

from modbus_connection.model import Component, NumberField, boolean, enum, raw_register

from .enums import ModbusControl, StandbyRequest, SwitchPosition
from .model import count

MODBUS_CONTROL = 8000
SWITCH_POSITION = 8001
FLOW_RATE = 8002
STANDBY = 8003

RESET_FILTER_WARNING = 8010
APPLIANCE_RESET = 8011

ACTION_REQUESTED = 1


def _action(value: Any) -> int:
    """Only 1 asks for the action; the spec gives no other value a meaning."""
    if int(value) != ACTION_REQUESTED:
        raise ValueError(f"an action is requested by writing {ACTION_REQUESTED}")
    return ACTION_REQUESTED


class Control(Component):
    """Whether and how Modbus is driving the appliance."""

    register_ranges = ((MODBUS_CONTROL, STANDBY),)

    modbus_control: NumberField[ModbusControl] = enum(
        MODBUS_CONTROL, ModbusControl, writable=True
    )
    """Whether Modbus drives the appliance, and by which of the two means.

    The appliance follows :attr:`switch_position` only while this is
    ``SWITCH_POSITION``, and :attr:`flow_rate` only while it is ``FLOW_RATE``.
    :meth:`async_set_switch_position` and :meth:`async_set_flow_rate` set both
    registers in the right order.
    """

    switch_position: NumberField[SwitchPosition] = enum(
        SWITCH_POSITION, SwitchPosition, writable=True
    )
    """The switch position asked for. A read answers the last one accepted."""

    flow_rate = count(FLOW_RATE, unit="m³/h", writable=True)
    """The flow rate asked for, 0 or between the appliance's own minimum and
    maximum. The spec makes those bounds depend on the appliance, so nothing
    is validated here beyond the register's own width."""

    standby = boolean(STANDBY)
    """Whether the appliance is in standby.

    Read-only, because a read and a write of 8003 do not share a meaning: a
    read answers the state, a write asks for a change. Use
    :meth:`async_request_standby`. The appliance can also be put into and out
    of standby from its own display, so this is the state rather than an echo
    of the last request.
    """

    async def async_request_standby(self, standby: bool) -> None:
        """Ask the appliance to enter or leave standby."""
        request = StandbyRequest.SET_STANDBY if standby else StandbyRequest.SET_NORMAL
        await self.modbus_unit.write_register(STANDBY, request)

    async def async_set_switch_position(self, position: SwitchPosition) -> None:
        """Hand the appliance a switch position, switching to that mode first."""
        await self.modbus_unit.write_register(
            MODBUS_CONTROL, ModbusControl.SWITCH_POSITION
        )
        await self.modbus_unit.write_register(SWITCH_POSITION, position)

    async def async_set_flow_rate(self, flow: int) -> None:
        """Hand the appliance a flow rate, switching to that mode first."""
        await self.modbus_unit.write_register(MODBUS_CONTROL, ModbusControl.FLOW_RATE)
        await self.modbus_unit.write_register(FLOW_RATE, flow)

    async def async_release(self) -> None:
        """Stop driving the appliance and give it back its own controls."""
        await self.modbus_unit.write_register(MODBUS_CONTROL, ModbusControl.OFF)


class Commands(Component):
    """The two one-shot actions: write 1 to ask for one.

    Never polled — a read of either register answers the outcome of the last
    request and clears itself, so nothing here is a value to look at.
    """

    reset_filter_warning = raw_register(RESET_FILTER_WARNING, writable=_action)
    """Clear the filter warning and start the filter counters again."""

    appliance_reset = raw_register(APPLIANCE_RESET, writable=_action)
    """Restart the appliance."""
