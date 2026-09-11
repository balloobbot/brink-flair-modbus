"""brink-flair-modbus — read and drive a Brink HRA over Modbus.

Construct :class:`BrinkFlair` with a ``modbus_connection.ModbusUnit``, call
``await appliance.async_update()``, then read the values as plain
attributes::

    appliance.measurements.supply_flow
    appliance.measurements.exhaust_fan_temperature

The register map is transcribed from *Installation regulations Modbus
UWA2-B/UWA2-E* (614882-D), committed under ``docs/``. It is the map of the
control PCB rather than of one appliance, so it covers the Brink HRA range
that carries a UWA2-B, with or without the Plus extension PCB UWA2-E.
"""

from .control import Commands, Control
from .device import MANUFACTURER, MODEL, BrinkFlair, UpdateReport
from .enums import (
    ActiveFunction,
    BaudRate,
    BypassMode,
    BypassStatus,
    Co2SensorStatus,
    DateFormat,
    DigitalInputFanFunction,
    DigitalInputFunction,
    EbusPowerStatus,
    ExternalHeaterMode,
    FanControlType,
    FanStatus,
    FlowSwitchPosition,
    FlowType,
    FrostStatus,
    GeoHeatExchangerStatus,
    GeoValveOutput,
    GeoValvePosition,
    Language,
    ModbusControl,
    ModbusInterfaceType,
    PreheaterStatus,
    SignalOutputMode,
    SignalOutputState,
    StandbyRequest,
    SwitchPosition,
    SwitchType,
    TimeNotation,
    VentilationMode,
)
from .identity import Identity
from .measurements import Co2Sensors, GeoHeatExchanger, Measurements
from .modules import ExtensionModule, UserInterface
from .parameters import SLAVE_ADDRESS_MAX, SLAVE_ADDRESS_MIN, Parameters

__all__ = [
    "MANUFACTURER",
    "MODEL",
    "SLAVE_ADDRESS_MAX",
    "SLAVE_ADDRESS_MIN",
    "ActiveFunction",
    "BaudRate",
    "BrinkFlair",
    "BypassMode",
    "BypassStatus",
    "Co2SensorStatus",
    "Co2Sensors",
    "Commands",
    "Control",
    "DateFormat",
    "DigitalInputFanFunction",
    "DigitalInputFunction",
    "EbusPowerStatus",
    "ExtensionModule",
    "ExternalHeaterMode",
    "FanControlType",
    "FanStatus",
    "FlowSwitchPosition",
    "FlowType",
    "FrostStatus",
    "GeoHeatExchanger",
    "GeoHeatExchangerStatus",
    "GeoValveOutput",
    "GeoValvePosition",
    "Identity",
    "Language",
    "Measurements",
    "ModbusControl",
    "ModbusInterfaceType",
    "Parameters",
    "PreheaterStatus",
    "SignalOutputMode",
    "SignalOutputState",
    "StandbyRequest",
    "SwitchPosition",
    "SwitchType",
    "TimeNotation",
    "UpdateReport",
    "UserInterface",
    "VentilationMode",
]
