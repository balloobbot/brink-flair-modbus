"""Coded values of the UWA2-B/UWA2-E register map (spec §2.1, §2.2 and §2.3).

Every enum here transcribes one register's code list. Where the document
itself is ambiguous, the ambiguity is recorded on the class rather than
resolved silently — see the README's "Where the spec is unclear".
"""

from __future__ import annotations

from enum import IntEnum


class ActiveFunction(IntEnum):
    """What the appliance is currently doing, from input register 4020."""

    STANDBY = 0
    BOOTLOADER = 1
    NON_BLOCKING_ERROR = 2
    BLOCKING_ERROR = 3
    MANUAL = 4
    HOLIDAY = 5
    NIGHT_VENTILATION = 6
    PARTY = 7
    BYPASS_BOOST = 8
    NORMAL_BOOST = 9
    AUTO_CO2 = 10
    AUTO_EBUS = 11
    AUTO_MODBUS = 12
    AUTO_LAN_WLAN_PORTAL = 13
    AUTO_LAN_WLAN_LOCAL = 14


class FanControlType(IntEnum):
    """How the fans are being driven, from input register 4021."""

    INITIALIZING = 0
    CONSTANT_FLOW = 1
    CONSTANT_PWM = 2
    OFF = 3
    ERROR = 4
    MASS_BALANCE = 5
    STANDBY = 6


class VentilationMode(IntEnum):
    """The ventilation mode in force, from input register 4022."""

    HOLIDAY = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    AUTO = 4


class FanStatus(IntEnum):
    """A fan's state, from input registers 4030 and 4040.

    The spec's list starts at 2; codes 0 and 1 are not assigned and decode to
    ``None``.
    """

    NO_COMMUNICATION = 2
    IDLE = 3
    RUNNING = 4
    BLOCKED = 5
    FAN_ERROR = 6


class BypassStatus(IntEnum):
    """The bypass valve's state, from input register 4050.

    The spec words the five codes "initialize / open / close / open / closed",
    naming both 1 and 3 "open". Read as a moving valve and a settled one, the
    pair 1/2 is the movement and 3/4 the position, which is the only reading
    that gives each code a distinct meaning. Nothing in the document says so.
    """

    INITIALIZE = 0
    OPENING = 1
    CLOSING = 2
    OPEN = 3
    CLOSED = 4


class PreheaterStatus(IntEnum):
    """The preheater's state, from input register 4060."""

    INITIALIZE = 0
    INACTIVE = 1
    ACTIVE = 2
    TEST_MODE = 3


class FrostStatus(IntEnum):
    """Where frost protection has got to, from input register 4070.

    Which of these an appliance ever reports depends on its type.
    """

    NOT_INITIALIZED = 0
    POWER_UP_DELAY = 1
    NO_FROST = 2
    NO_FROST_DELAY = 3
    FROST_CONTROL_START_DELAY = 4
    WAIT_FOR_ICING = 5
    ICE_DETECTED_DELAY = 6
    HEATING = 7
    WAIT_FOR_FREE_HEATER = 8
    FAN_CONTROL_START_DELAY = 9
    FAN_CONTROL_WAIT_DELAY = 10
    FAN_CONTROL = 11
    FAN_OFF_DELAY = 12
    FAN_OFF = 13
    FAN_RESTARTING = 14
    ERROR = 15
    TEST_MODE = 16


class FlowSwitchPosition(IntEnum):
    """The mechanical flow switch, from input register 4080.

    ``INVALID`` is the spec's 255: more than one contact is closed, so no
    position can be read off the switch.
    """

    HOLIDAY = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3
    INVALID = 255


class SignalOutputState(IntEnum):
    """A 0/24 V output's state — input registers 4090, 4541 and 4542."""

    ZERO_VOLT = 0
    TWENTY_FOUR_VOLT = 1


class EbusPowerStatus(IntEnum):
    """The eBus supply's state, from input register 4101."""

    POWER_UP = 0
    INITIALIZE_POWER = 1
    POWER_OFF = 2
    POWER_ON = 3
    WAIT_FOR_POWER_OFF = 4
    SLAVE_POWER_OFF = 5


class GeoHeatExchangerStatus(IntEnum):
    """The geo heat exchanger valve, from input register 4150."""

    OPEN_LOW = 0
    CLOSED = 1
    OPEN_HIGH = 2


class Co2SensorStatus(IntEnum):
    """A CO2 sensor's state — input registers 4200, 4202, 4204 and 4206."""

    ERROR = 0
    NOT_INITIALIZED = 1
    IDLE = 2
    WARMING_UP = 3
    RUNNING = 4
    CALIBRATING = 5
    SELF_TEST = 6


class FlowType(IntEnum):
    """How the fans are regulated, holding register 6030, default CONSTANT_FLOW."""

    CONSTANT_PWM = 0
    CONSTANT_FLOW = 1
    CONSTANT_MASS_FLOW = 2


class BypassMode(IntEnum):
    """What the bypass is allowed to do, holding register 6100, default AUTOMATIC."""

    AUTOMATIC = 0
    CLOSED = 1
    OPEN = 2


class ExternalHeaterMode(IntEnum):
    """Which external heater is fitted, holding register 6130, default NONE."""

    NONE = 0
    PRE_HEATER = 1
    POST_HEATER = 2


class SignalOutputMode(IntEnum):
    """What raises the signal output, holding register 6170, default OFF."""

    OFF = 0
    FILTER_WARNING = 1
    ERROR_STATUS = 2
    FILTER_WARNING_AND_ERROR_STATUS = 3


class SwitchType(IntEnum):
    """A digital input's resting state — holding registers 6200 and 6210."""

    NORMALLY_OPEN = 0
    NORMALLY_CLOSED = 1


class DigitalInputFunction(IntEnum):
    """What a digital input does — holding registers 6201 and 6211."""

    OFF = 0
    ON = 1
    ON_IF_BYPASS_OPEN_CONDITIONS_SATISFIED = 2
    BYPASS_CONTROL = 3
    EXTERNAL_VALVE_CONTROL = 4


class DigitalInputFanFunction(IntEnum):
    """What a digital input does to one fan — holding registers 6202-6203 and
    6212-6213."""

    FAN_OFF = 0
    ABSOLUTE_MINIMUM_FLOW = 1
    PREDEFINED_FLOW_MODE_1 = 2
    PREDEFINED_FLOW_MODE_2 = 3
    PREDEFINED_FLOW_MODE_3 = 4
    ACCORDING_TO_POSITION_SWITCH = 5
    ABSOLUTE_MAXIMUM_FLOW = 6
    UNCHANGED = 7


class GeoValvePosition(IntEnum):
    """Where the geo valve sits at 0 V output, holding register 6243."""

    CLOSED = 0
    OPEN = 1


class GeoValveOutput(IntEnum):
    """Which UWA2-E output drives the geo valve, holding register 6244."""

    ANALOGUE_OUTPUT_1 = 0
    ANALOGUE_OUTPUT_2 = 1
    RELAY_OUTPUT_1 = 2
    RELAY_OUTPUT_2 = 3


class Language(IntEnum):
    """The display language, holding register 6900."""

    ENGLISH = 0
    DUTCH = 1


class DateFormat(IntEnum):
    """How the display orders a date, holding register 6901."""

    DAY_MONTH_YEAR = 0
    MONTH_DAY_YEAR = 1


class TimeNotation(IntEnum):
    """How the display writes a time, holding register 6902."""

    TWELVE_HOUR = 0
    TWENTY_FOUR_HOUR = 1


class ModbusInterfaceType(IntEnum):
    """Which Modbus interface is in use, holding register 7990."""

    INTERNAL = 0
    EXTERNAL_CONNECT = 1
    EXTERNAL_CUSTOMER = 2


class BaudRate(IntEnum):
    """The link speed of holding register 7992, default 19200 bit/s.

    The spec writes codes 6 and 7 as "56k" and "115k"; the appliance's own
    settings menu writes the same two as "56k" and "115k2". Both are the usual
    57600 and 115200, which is what the names say.
    """

    BPS_1200 = 0
    BPS_2400 = 1
    BPS_4800 = 2
    BPS_9600 = 3
    BPS_19200 = 4
    BPS_38400 = 5
    BPS_57600 = 6
    BPS_115200 = 7


class ModbusControl(IntEnum):
    """Whether Modbus drives the appliance, remote-control register 8000."""

    OFF = 0
    SWITCH_POSITION = 1
    FLOW_RATE = 2


class SwitchPosition(IntEnum):
    """The switch position Modbus asks for, remote-control register 8001.

    The same four codes as :class:`FlowSwitchPosition` without its ``INVALID``:
    a position can be requested, but not the switch's unreadable state.
    """

    HOLIDAY = 0
    LOW = 1
    NORMAL = 2
    HIGH = 3


class StandbyRequest(IntEnum):
    """What a write to remote-control register 8003 asks for.

    A read of 8003 answers the appliance's standby state instead, which
    :attr:`~brink_flair_modbus.control.Control.standby` decodes.
    """

    NO_ACTION = 0
    SET_STANDBY = 1
    SET_NORMAL = 2
