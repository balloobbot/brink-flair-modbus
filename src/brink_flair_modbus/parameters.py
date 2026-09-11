"""The appliance's settings — holding registers 6000-7992 (spec §2.2).

Settings change only when someone writes them, so they are their own
component: a poll does not read them, and a consumer that wants them
refreshes this on whatever schedule suits it.

Every setting the spec documents is writable, and each carries the validator
for the bounds and step its own row states. A validator sees the value in the
units the attribute uses, so a temperature is vetted in degrees rather than in
the tenths that go on the wire. Values are checked before anything reaches the
bus, which matters here: the spec gives no error behaviour for a setting
written out of range.

Three kinds of rule the spec states cannot be enforced from one field, and are
documented rather than checked:

* the ordering between presets (flow preset 1 must not drop below preset 0);
* the flow presets' own bounds, which the spec says "depends on type of HRA";
* register 6002's "Step size: 150" where its three neighbours say 5. The
  permissive reading is used — a multiple of 5 — because rejecting a value the
  appliance would have accepted is the worse failure.
"""

from __future__ import annotations

from typing import Any

from modbus_connection.model import (
    Component,
    NumberField,
    WriteValidator,
    boolean,
    enum,
    raw_register,
)

from .enums import (
    BaudRate,
    BypassMode,
    DateFormat,
    DigitalInputFanFunction,
    DigitalInputFunction,
    ExternalHeaterMode,
    FlowType,
    GeoValveOutput,
    GeoValvePosition,
    Language,
    ModbusInterfaceType,
    SignalOutputMode,
    SwitchType,
    TimeNotation,
)
from .model import count, signed_count, tenths

FLOW_STEP = 5
FLOW_OFF = 0
PWM_MIN = 15
PWM_MAX = 100
PWM_OFF = 0
SLAVE_ADDRESS_MIN = 1
SLAVE_ADDRESS_MAX = 247


def _whole(low: int, high: int, *, step: int = 1) -> WriteValidator:
    """Reject a whole number outside the spec's range or off its step."""

    def validate(value: Any) -> int:
        number = int(value)
        if not low <= number <= high:
            raise ValueError(f"must be {low}-{high}")
        if (number - low) % step:
            raise ValueError(f"must be {low}-{high} in steps of {step}")
        return number

    return validate


def _in_tenths(low: int, high: int, *, step: int = 1) -> WriteValidator:
    """Reject a tenths-scaled value outside the spec's raw range or step.

    The bounds are the spec's own raw numbers; the value is in the attribute's
    units, so 6101's 150-350 vets a request of 22.0 °C.
    """

    def validate(value: Any) -> float:
        raw = round(float(value) * 10)
        if not low <= raw <= high:
            raise ValueError(f"must be {low / 10}-{high / 10}")
        if (raw - low) % step:
            raise ValueError(f"must be {low / 10}-{high / 10} in steps of {step / 10}")
        return raw / 10

    return validate


def _flow_preset(value: Any) -> int:
    """Reject a flow preset that is neither off nor a step of the spec's 5.

    The spec makes the bounds depend on the appliance, so only the step and
    the "extra value" of 0 can be checked here.
    """
    flow = int(value)
    if flow == FLOW_OFF:
        return FLOW_OFF
    if flow < 0 or flow % FLOW_STEP:
        raise ValueError(f"must be 0 or a multiple of {FLOW_STEP} m³/h")
    return flow


def _pwm_preset(value: Any) -> int:
    """Reject a PWM preset outside the spec's 15-100, 0 being off."""
    pwm = int(value)
    if pwm == PWM_OFF:
        return PWM_OFF
    if not PWM_MIN <= pwm <= PWM_MAX:
        raise ValueError(f"must be 0 or {PWM_MIN}-{PWM_MAX} %")
    return pwm


class Parameters(Component):
    """Everything the appliance can be configured to do.

    Read once at setup, and again only when a consumer asks. The ranges keep
    every read inside the rows the spec documents — see
    :mod:`~brink_flair_modbus.measurements` for why.
    """

    register_ranges = (
        (6000, 6003),
        (6010, 6017),
        (6030, 6036),
        (6100, 6105),
        (6110, 6111),
        (6120, 6120),
        (6130, 6131),
        (6140, 6141),
        (6150, 6158),
        (6170, 6171),
        (6200, 6203),
        (6210, 6213),
        (6220, 6222),
        (6230, 6232),
        (6240, 6244),
        (6900, 6906),
        (7990, 7992),
    )

    flow_preset_0 = count(6000, unit="m³/h", writable=_flow_preset)
    """The holiday flow. Must not exceed :attr:`flow_preset_1`."""

    flow_preset_1 = count(6001, unit="m³/h", writable=_flow_preset)
    """The low flow. Must sit between presets 0 and 2."""

    flow_preset_2 = count(6002, unit="m³/h", writable=_flow_preset)
    """The normal flow. Must sit between presets 1 and 3."""

    flow_preset_3 = count(6003, unit="m³/h", writable=_flow_preset)
    """The high flow. Must not fall below :attr:`flow_preset_2`."""

    pwm_supply_preset_0 = count(6010, unit="%", writable=_pwm_preset)
    pwm_exhaust_preset_0 = count(6011, unit="%", writable=_pwm_preset)
    pwm_supply_preset_1 = count(6012, unit="%", writable=_pwm_preset)
    pwm_exhaust_preset_1 = count(6013, unit="%", writable=_pwm_preset)
    pwm_supply_preset_2 = count(6014, unit="%", writable=_pwm_preset)
    pwm_exhaust_preset_2 = count(6015, unit="%", writable=_pwm_preset)
    pwm_supply_preset_3 = count(6016, unit="%", writable=_pwm_preset)
    pwm_exhaust_preset_3 = count(6017, unit="%", writable=_pwm_preset)

    flow_type: NumberField[FlowType] = enum(6030, FlowType, writable=True)
    """How the fans are regulated, default constant flow."""

    switch_default_position = count(6031, writable=_whole(0, 1))
    """The position taken when no four-position switch is connected.

    The spec calls it the default of a four-position switch while bounding it
    to 0-1, so only those two are accepted.
    """

    use_display_as_switch = boolean(6032, writable=True)
    imbalance_allowed = boolean(6033, writable=True)

    imbalance_value = count(6034, unit="%", writable=_whole(0, 20))
    """How much more the supply fan moves than the exhaust fan."""

    offset_imbalance_supply = signed_count(6035, unit="%", writable=_whole(-15, 15))
    offset_imbalance_exhaust = signed_count(6036, unit="%", writable=_whole(-15, 15))

    bypass_mode: NumberField[BypassMode] = enum(6100, BypassMode, writable=True)

    bypass_temperature_dwelling = tenths(
        6101, unit="°C", writable=_in_tenths(150, 350, step=5)
    )
    bypass_temperature_outside = tenths(
        6102, unit="°C", writable=_in_tenths(70, 150, step=5)
    )
    bypass_temperature_hysteresis = tenths(
        6103, unit="°C", writable=_in_tenths(0, 50, step=5)
    )

    bypass_boost = boolean(6104, writable=True)

    bypass_boost_switch_position = count(6105, writable=_whole(0, 3))
    """The preset the fans run at while a bypass boost is open."""

    frost_control_temperature = tenths(
        6110, unit="°C", writable=_in_tenths(0, 30, step=5)
    )
    frost_control_minimum_inlet_temperature = tenths(
        6111, unit="°C", writable=_in_tenths(70, 220, step=5)
    )

    filter_warning_days = count(6120, unit="d", writable=_whole(1, 365))
    """Days of running before the appliance asks for a filter change."""

    external_heater_mode: NumberField[ExternalHeaterMode] = enum(
        6130, ExternalHeaterMode, writable=True
    )
    postheater_setpoint = tenths(6131, unit="°C", writable=_in_tenths(150, 300, step=5))

    rht_sensor_mode = boolean(6140, writable=True)
    rht_sensor_sensitivity = signed_count(6141, writable=_whole(-2, 2))

    co2_sensor_mode = boolean(6150, writable=True)

    co2_sensor_1_low = count(6151, unit="ppm", writable=_whole(400, 2000))
    co2_sensor_1_high = count(6152, unit="ppm", writable=_whole(400, 2000))
    co2_sensor_2_low = count(6153, unit="ppm", writable=_whole(400, 2000))
    co2_sensor_2_high = count(6154, unit="ppm", writable=_whole(400, 2000))
    co2_sensor_3_low = count(6155, unit="ppm", writable=_whole(400, 2000))
    co2_sensor_3_high = count(6156, unit="ppm", writable=_whole(400, 2000))
    co2_sensor_4_low = count(6157, unit="ppm", writable=_whole(400, 2000))
    co2_sensor_4_high = count(6158, unit="ppm", writable=_whole(400, 2000))

    signal_output_mode: NumberField[SignalOutputMode] = enum(
        6170, SignalOutputMode, writable=True
    )

    central_heating_on_exhaust = boolean(6171, writable=True)
    """Set when a central-heating flue shares the appliance's exhaust channel."""

    switch_type_input_1: NumberField[SwitchType] = enum(6200, SwitchType, writable=True)
    digital_input_1_function: NumberField[DigitalInputFunction] = enum(
        6201, DigitalInputFunction, writable=True
    )
    digital_input_1_supply_fan: NumberField[DigitalInputFanFunction] = enum(
        6202, DigitalInputFanFunction, writable=True
    )
    digital_input_1_exhaust_fan: NumberField[DigitalInputFanFunction] = enum(
        6203, DigitalInputFanFunction, writable=True
    )

    switch_type_input_2: NumberField[SwitchType] = enum(6210, SwitchType, writable=True)
    digital_input_2_function: NumberField[DigitalInputFunction] = enum(
        6211, DigitalInputFunction, writable=True
    )
    digital_input_2_supply_fan: NumberField[DigitalInputFanFunction] = enum(
        6212, DigitalInputFanFunction, writable=True
    )
    digital_input_2_exhaust_fan: NumberField[DigitalInputFanFunction] = enum(
        6213, DigitalInputFanFunction, writable=True
    )

    analogue_input_1_mode = boolean(6220, writable=True)
    analogue_input_1_minimum = tenths(
        6221, unit="V", signed=False, writable=_in_tenths(0, 100, step=5)
    )
    analogue_input_1_maximum = tenths(
        6222, unit="V", signed=False, writable=_in_tenths(0, 100, step=5)
    )

    analogue_input_2_mode = boolean(6230, writable=True)
    analogue_input_2_minimum = tenths(
        6231, unit="V", signed=False, writable=_in_tenths(0, 100, step=5)
    )
    analogue_input_2_maximum = tenths(
        6232, unit="V", signed=False, writable=_in_tenths(0, 100, step=5)
    )

    geo_heat_exchanger = boolean(6240, writable=True)
    """Whether the geo heat exchanger runs. Needs the Plus PCB."""

    geo_minimum_temperature = tenths(6241, unit="°C", writable=_in_tenths(0, 100))
    geo_maximum_temperature = tenths(6242, unit="°C", writable=_in_tenths(150, 400))

    geo_valve_default_position: NumberField[GeoValvePosition] = enum(
        6243, GeoValvePosition, writable=True
    )
    geo_valve_output: NumberField[GeoValveOutput] = enum(
        6244, GeoValveOutput, writable=True
    )

    language: NumberField[Language] = enum(6900, Language, writable=True)
    date_format: NumberField[DateFormat] = enum(6901, DateFormat, writable=True)
    time_notation: NumberField[TimeNotation] = enum(6902, TimeNotation, writable=True)

    date_month_day = raw_register(6903, writable=True)
    """The clock's date: high byte is the month, low byte the day."""

    date_year = raw_register(6904, writable=True)
    """The clock's year."""

    time_of_day = raw_register(6905, writable=True)
    """The clock's time: high byte is the hour, low byte the minute."""

    date_time_rest = raw_register(6906, writable=True)
    """High byte is the day of the week, low byte the seconds."""

    modbus_interface_type: NumberField[ModbusInterfaceType] = enum(
        7990, ModbusInterfaceType, writable=True
    )

    modbus_slave_address = count(
        7991, writable=_whole(SLAVE_ADDRESS_MIN, SLAVE_ADDRESS_MAX)
    )
    """The appliance's unit id, 1-247, default 20.

    A successful write takes effect immediately, so the ``ModbusUnit`` this
    component was built from no longer addresses the appliance: build a new
    unit at the new id.
    """

    modbus_speed: NumberField[BaudRate] = enum(7992, BaudRate, writable=True)
    """The link speed, default 19200. Like the address, a write takes effect
    immediately and the existing connection no longer reaches the appliance."""
