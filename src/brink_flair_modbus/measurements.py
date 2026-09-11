"""What the appliance measures — input registers (FC04) of spec §2.1.

The appliance's own readings sit in 4020-4119 and are one component: they are
always present, they change every poll, and none of them can fail without the
rest. The three blocks past them belong to hardware an appliance may not have
— a geo heat exchanger and up to four CO2 sensors — so each is a component of
its own, probed once at setup. A missing one then does not fail the poll.

Each component declares ``register_ranges`` for the rows the spec documents,
so a read never reaches into the gaps between them. The map is full of gaps
the default 16-register ``max_gap`` would happily read across, and the spec
never says whether the appliance answers for an address it does not
implement. A refused block fails a whole update, so the ranges buy safety at
the cost of round trips — see the README.
"""

from __future__ import annotations

from datetime import time as time_of_day

from modbus_connection.model import Component, boolean, enum, raw_register, uint32

from .enums import (
    ActiveFunction,
    BypassStatus,
    Co2SensorStatus,
    EbusPowerStatus,
    FanControlType,
    FanStatus,
    FlowSwitchPosition,
    FrostStatus,
    GeoHeatExchangerStatus,
    PreheaterStatus,
    SignalOutputState,
    VentilationMode,
)
from .model import count, humidity, tenths

CURRENT_TIME = 4110
HOURS_PER_DAY = 24
MINUTES_PER_HOUR = 60


class Measurements(Component):
    """Everything the appliance reports about its own running."""

    register_space = "input"
    register_ranges = (
        (4020, 4024),
        (4030, 4037),
        (4040, 4047),
        (4050, 4051),
        (4060, 4061),
        (4070, 4072),
        (4080, 4083),
        (4090, 4090),
        (4100, 4101),
        (CURRENT_TIME, 4119),
    )

    active_function = enum(4020, ActiveFunction)
    """Which function is driving the appliance right now."""

    fan_control_type = enum(4021, FanControlType)
    """How the fans are regulated at this moment, which is not the configured
    :class:`~brink_flair_modbus.enums.FlowType`: it also carries the
    initialising, error and standby states."""

    ventilation_mode = enum(4022, VentilationMode)
    supply_pressure = tenths(4023, unit="Pa")
    exhaust_pressure = tenths(4024, unit="Pa")

    supply_fan_status = enum(4030, FanStatus)
    supply_flow_setpoint = count(4031, unit="m³/h")
    supply_flow = count(4032, unit="m³/h")
    supply_mass_flow = count(4033, unit="kg/h")
    supply_fan_speed = count(4034, unit="rpm")
    supply_anemometer_speed = count(4035, unit="rpm")
    supply_fan_temperature = tenths(4036, unit="°C")
    supply_humidity = humidity(4037)

    exhaust_fan_status = enum(4040, FanStatus)
    exhaust_flow_setpoint = count(4041, unit="m³/h")
    exhaust_flow = count(4042, unit="m³/h")
    exhaust_mass_flow = count(4043, unit="kg/h")
    exhaust_fan_speed = count(4044, unit="rpm")
    exhaust_anemometer_speed = count(4045, unit="rpm")
    exhaust_fan_temperature = tenths(4046, unit="°C")
    exhaust_humidity = humidity(4047)

    bypass_status = enum(4050, BypassStatus)
    bypass_position = raw_register(4051)
    """The valve's position relative to its zero point, in steps. The spec
    gives a range of 0-0xFFFF and no scale, so it is the raw word."""

    preheater_status = enum(4060, PreheaterStatus)
    preheater_capacity = count(4061, unit="%")

    frost_status = enum(4070, FrostStatus)
    frost_heater_power = count(4071, unit="%")
    fan_frost_reduction = count(4072, unit="%")
    """How far frost protection has cut the fans back; 0 % is no reduction."""

    flow_switch_position = enum(4080, FlowSwitchPosition)
    """The mechanical switch's position.

    ``INVALID`` is a reading rather than a decode failure: the spec assigns
    255 to "more than one contact closed", so it is a member of the enum.
    """

    ntc1_temperature = tenths(4081, unit="°C")
    ntc2_temperature = tenths(4082, unit="°C")
    rht_humidity = humidity(4083)

    signal_output = enum(4090, SignalOutputState)
    """Whether the signal output is driven, per its configured
    :class:`~brink_flair_modbus.enums.SignalOutputMode`."""

    filter_dirty = boolean(4100)
    """Whether the appliance is asking for its filters to be changed."""

    ebus_power_status = enum(4101, EbusPowerStatus)

    _time = raw_register(CURRENT_TIME)

    date_high = raw_register(4111)
    """The first of the two date words, undecoded.

    The spec labels 4111 "Date high nibble" and 4112 "Date lower nibbles"
    while describing the pair as "high byte = days, low byte = years ... only
    decennia". Nibbles and bytes cannot both be right and neither accounts for
    a month, so both words are left raw rather than decoded wrongly.
    """

    date_low = raw_register(4112)
    """The second of the two date words, undecoded — see :attr:`date_high`."""

    operating_time = uint32(4113, unit="h")
    """Hours the appliance has run. Thirty-two bits over 4113-4114."""

    filter_hours = count(4115, unit="h")
    """Hours run since the last filter reset."""

    filter_flow = uint32(4116, unit="m³")
    """Air moved since the last filter reset. Thirty-two bits over 4116-4117.

    The spec's units column reads "m3/h" for what its own text calls an
    "amount of flow ... since last filter reset", which is a volume.
    """

    total_flow = uint32(4118, unit="m³")
    """Air moved since the appliance was put into use. Thirty-two bits over
    4118-4119, with the same units wording as :attr:`filter_flow`."""

    @property
    def time(self) -> time_of_day | None:
        """The appliance's clock: high byte is the hour, low byte the minute."""
        raw = self._time
        if raw is None:
            return None
        hour, minute = raw >> 8, raw & 0xFF
        if hour >= HOURS_PER_DAY or minute >= MINUTES_PER_HOUR:
            return None
        return time_of_day(hour, minute)


class GeoHeatExchanger(Component):
    """The geo heat exchanger's valve — one input register, 4150.

    Its own component because the spec marks it "Extension module if function
    is supported": an appliance without one need not answer for 4150, and an
    update that fails must not take the rest of the poll with it.
    """

    register_space = "input"
    register_ranges = ((4150, 4150),)

    status = enum(4150, GeoHeatExchangerStatus)


class Co2Sensors(Component):
    """Up to four CO2 sensors — input registers 4200-4207.

    A sensor that is not fitted reports its own status rather than refusing
    the read, so all four are declared and the statuses say which are real.
    """

    register_space = "input"
    register_ranges = ((4200, 4207),)

    sensor_1_status = enum(4200, Co2SensorStatus)
    sensor_1_value = count(4201, unit="ppm")
    sensor_2_status = enum(4202, Co2SensorStatus)
    sensor_2_value = count(4203, unit="ppm")
    sensor_3_status = enum(4204, Co2SensorStatus)
    sensor_3_value = count(4205, unit="ppm")
    sensor_4_status = enum(4206, Co2SensorStatus)
    sensor_4_value = count(4207, unit="ppm")
