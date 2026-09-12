"""Decoding, optional hardware, the update report, settings and writes."""

from __future__ import annotations

import pytest
from modbus_connection import (
    IllegalDataAddressError,
    IllegalDataValueError,
    ModbusTimeoutError,
)
from modbus_connection.mock import MockModbusUnit, WriteEvent

from brink_flair_modbus import (
    ActiveFunction,
    BaudRate,
    BrinkFlair,
    BypassStatus,
    Co2SensorStatus,
    EbusPowerStatus,
    FanControlType,
    FanStatus,
    FlowSwitchPosition,
    FlowType,
    FrostStatus,
    GeoHeatExchangerStatus,
    GeoValveOutput,
    Language,
    ModbusControl,
    ModbusInterfaceType,
    PreheaterStatus,
    SignalOutputMode,
    SignalOutputState,
    SwitchPosition,
    VentilationMode,
)

from .conftest import FILTER_FLOW, OPERATING_HOURS, SERIAL, TOTAL_FLOW


async def test_identity(appliance: BrinkFlair) -> None:
    await appliance.async_update()
    identity = appliance.identity
    assert identity.serial_number == SERIAL
    assert identity.software_version == "S1.01.03.0001"
    assert identity.hardware_version == "H1.1"
    assert identity.appliance_type == 42
    assert identity.dipswitch == 7


async def test_a_serial_number_that_is_not_bcd_reads_as_none(
    mock_modbus_unit: MockModbusUnit, appliance: BrinkFlair
) -> None:
    """A nibble above 9 cannot be a BCD digit, so the number is unknown."""
    mock_modbus_unit.input[4010] = [0x1234, 0x5678, 0x90AB]
    await appliance.async_update()
    assert appliance.identity.serial_number is None


async def test_statuses(appliance: BrinkFlair) -> None:
    await appliance.async_update()
    m = appliance.measurements
    assert m.active_function is ActiveFunction.AUTO_MODBUS
    assert m.fan_control_type is FanControlType.CONSTANT_FLOW
    assert m.ventilation_mode is VentilationMode.NORMAL
    assert m.supply_fan_status is FanStatus.RUNNING
    assert m.exhaust_fan_status is FanStatus.RUNNING
    assert m.bypass_status is BypassStatus.CLOSED
    assert m.preheater_status is PreheaterStatus.INACTIVE
    assert m.frost_status is FrostStatus.NO_FROST
    assert m.flow_switch_position is FlowSwitchPosition.NORMAL
    assert m.signal_output is SignalOutputState.ZERO_VOLT
    assert m.ebus_power_status is EbusPowerStatus.POWER_ON
    assert m.filter_dirty is False


async def test_an_unreadable_flow_switch_is_a_reading_not_a_decode_failure(
    mock_modbus_unit: MockModbusUnit, appliance: BrinkFlair
) -> None:
    """255 is the spec's "more than one contact closed"."""
    mock_modbus_unit.input[4080] = 255
    await appliance.async_update()
    assert appliance.measurements.flow_switch_position is FlowSwitchPosition.INVALID


async def test_flows_and_speeds_are_whole_numbers(appliance: BrinkFlair) -> None:
    await appliance.async_update()
    m = appliance.measurements
    assert m.supply_flow_setpoint == 150
    assert m.supply_flow == 148
    assert m.supply_mass_flow == 175
    assert m.supply_fan_speed == 2100
    assert m.supply_anemometer_speed == 2050
    assert m.exhaust_flow == 152
    assert m.exhaust_fan_speed == 2150


async def test_temperatures_pressures_and_humidities_are_tenths(
    appliance: BrinkFlair,
) -> None:
    await appliance.async_update()
    m = appliance.measurements
    assert m.supply_fan_temperature == pytest.approx(19.5)
    assert m.exhaust_fan_temperature == pytest.approx(21.2)
    assert m.supply_humidity == pytest.approx(45.2)
    assert m.rht_humidity == pytest.approx(48.3)
    assert m.supply_pressure == pytest.approx(45.2)


async def test_signed_readings_go_negative(appliance: BrinkFlair) -> None:
    """Pressure and the NTC probes are signed; humidity and flow are not."""
    await appliance.async_update()
    m = appliance.measurements
    assert m.exhaust_pressure == pytest.approx(-38.9)
    assert m.ntc1_temperature == pytest.approx(-3.5)
    assert m.ntc2_temperature == pytest.approx(18.8)


async def test_the_counters_span_two_registers(appliance: BrinkFlair) -> None:
    """4113, 4116 and 4118 each hold a 32-bit total, high word first."""
    await appliance.async_update()
    m = appliance.measurements
    assert m.operating_time == OPERATING_HOURS
    assert m.filter_hours == 1200
    assert m.filter_flow == FILTER_FLOW
    assert m.total_flow == TOTAL_FLOW


async def test_the_clock_splits_into_hours_and_minutes(appliance: BrinkFlair) -> None:
    await appliance.async_update()
    assert appliance.measurements.time is not None
    assert appliance.measurements.time.isoformat() == "14:35:00"


async def test_a_clock_outside_the_day_reads_as_none(
    mock_modbus_unit: MockModbusUnit, appliance: BrinkFlair
) -> None:
    mock_modbus_unit.input[4110] = 0x1900  # hour 25
    await appliance.async_update()
    assert appliance.measurements.time is None


async def test_the_date_words_stay_raw(appliance: BrinkFlair) -> None:
    """The spec describes 4111-4112 as both nibbles and bytes, so neither is
    decoded — see :attr:`Measurements.date_high`."""
    await appliance.async_update()
    assert appliance.measurements.date_high == 0x0A19
    assert appliance.measurements.date_low == 0x1A00


async def test_optional_hardware_is_found_at_setup(appliance: BrinkFlair) -> None:
    await appliance.async_update()

    assert appliance.geo_heat_exchanger is not None
    assert appliance.geo_heat_exchanger.status is GeoHeatExchangerStatus.CLOSED

    assert appliance.co2_sensors is not None
    assert appliance.co2_sensors.sensor_1_status is Co2SensorStatus.RUNNING
    assert appliance.co2_sensors.sensor_1_value == 650
    assert appliance.co2_sensors.sensor_2_status is Co2SensorStatus.NOT_INITIALIZED

    assert appliance.user_interface is not None
    assert appliance.user_interface.software_version == "S1.01.02.0012"
    assert appliance.user_interface.language_version == "S1.01.00.0005"
    assert appliance.user_interface.second_software_version == "S1.01.03.0009"
    assert appliance.user_interface.local_switch == 2

    assert appliance.extension is not None
    assert appliance.extension.ntc_temperature == pytest.approx(12.0)
    assert appliance.extension.contact_1_closed is False
    assert appliance.extension.contact_2_closed is True
    assert appliance.extension.analogue_input_1 == pytest.approx(2.5)
    assert appliance.extension.analogue_output_1 == pytest.approx(5.0)
    assert appliance.extension.relay_output_2 is SignalOutputState.TWENTY_FOUR_VOLT


async def test_a_module_reports_its_hardware_version_in_bcd(
    appliance: BrinkFlair,
) -> None:
    """0x0201 is 2.1 as BCD, where the base module's bytes would give the same
    two numbers only because both are below 10."""
    await appliance.async_update()
    assert appliance.user_interface is not None
    assert appliance.user_interface.hardware_version == "H2.1"


async def test_hardware_a_bare_appliance_lacks_stays_none(
    bare_appliance: BrinkFlair,
) -> None:
    """A refused probe means the appliance does not have that sub-system."""
    report = await bare_appliance.async_update()

    assert bare_appliance.geo_heat_exchanger is None
    assert bare_appliance.co2_sensors is None
    assert bare_appliance.user_interface is None
    assert bare_appliance.extension is None
    assert report.updated == ["measurements", "control", "parameters"]
    assert report.failed == {}


async def test_the_report_names_every_sub_system_it_refreshed(
    appliance: BrinkFlair,
) -> None:
    report = await appliance.async_update()
    assert report.updated == [
        "measurements",
        "control",
        "geo_heat_exchanger",
        "co2_sensors",
        "user_interface",
        "extension",
        "parameters",
    ]
    assert report.failed == {}


async def test_one_sub_system_failing_does_not_fail_the_poll(
    mock_modbus_unit: MockModbusUnit, appliance: BrinkFlair
) -> None:
    """A CO2 board pulled after setup leaves the rest of the poll intact."""
    await appliance.async_update()
    mock_modbus_unit.fail_read(4200, IllegalDataAddressError(), register_type="input")

    report = await appliance.async_update_readings()

    assert "co2_sensors" not in report.updated
    assert isinstance(report.failed["co2_sensors"], IllegalDataAddressError)
    assert "measurements" in report.updated


async def test_an_appliance_that_answers_nothing_raises(
    mock_modbus_unit: MockModbusUnit, appliance: BrinkFlair
) -> None:
    """Nothing answered, so the timeout is the poll's result rather than a
    line in its report."""
    mock_modbus_unit.fail_requests(ModbusTimeoutError())
    with pytest.raises(ModbusTimeoutError):
        await appliance.async_update()


async def test_setup_runs_again_after_an_unreachable_appliance(
    mock_modbus_unit: MockModbusUnit, appliance: BrinkFlair
) -> None:
    mock_modbus_unit.fail_requests(ModbusTimeoutError())
    with pytest.raises(ModbusTimeoutError):
        await appliance.async_update()

    mock_modbus_unit.fail_requests(None)
    report = await appliance.async_update()

    assert appliance.identity.serial_number == SERIAL
    assert appliance.extension is not None
    assert report.failed == {}


async def test_settings(appliance: BrinkFlair) -> None:
    await appliance.async_update()
    p = appliance.parameters
    assert p.flow_preset_0 == 50
    assert p.flow_preset_3 == 300
    assert p.pwm_supply_preset_2 == 50
    assert p.flow_type is FlowType.CONSTANT_FLOW
    assert p.imbalance_allowed is True
    assert p.imbalance_value == 5
    assert p.offset_imbalance_supply == -5
    assert p.bypass_temperature_dwelling == pytest.approx(22.0)
    assert p.bypass_temperature_outside == pytest.approx(10.0)
    assert p.bypass_temperature_hysteresis == pytest.approx(2.0)
    assert p.frost_control_minimum_inlet_temperature == pytest.approx(17.0)
    assert p.filter_warning_days == 90
    assert p.co2_sensor_1_high == 2000
    assert p.signal_output_mode is SignalOutputMode.FILTER_WARNING_AND_ERROR_STATUS
    assert p.geo_valve_output is GeoValveOutput.RELAY_OUTPUT_1
    assert p.language is Language.DUTCH
    assert p.modbus_interface_type is ModbusInterfaceType.EXTERNAL_CONNECT
    assert p.modbus_slave_address == 20
    assert p.modbus_speed is BaudRate.BPS_19200


def test_every_baud_rate_code_names_its_line_speed() -> None:
    """A consumer paces its frames from the speed, not from the code."""
    assert BaudRate.BPS_19200.bits_per_second == 19200
    assert [rate.bits_per_second for rate in BaudRate] == [
        1200,
        2400,
        4800,
        9600,
        19200,
        38400,
        57600,
        115200,
    ]


async def test_the_settings_are_not_read_by_a_readings_poll(
    appliance: BrinkFlair, mock_modbus_unit: MockModbusUnit
) -> None:
    await appliance.async_update()
    mock_modbus_unit.read_events.clear()

    await appliance.async_update_readings()

    settings_block = range(6000, 7993)
    assert not [b for b in mock_modbus_unit.read_events if b.address in settings_block]


async def test_writing_a_setting_scales_it_back(
    appliance: BrinkFlair, mock_modbus_unit: MockModbusUnit
) -> None:
    """A temperature is written in degrees and lands on the wire in tenths."""
    written: list[WriteEvent] = []
    mock_modbus_unit.on_write(written.append)

    await appliance.parameters.write("bypass_temperature_dwelling", 24.5)

    assert written == [WriteEvent("holding", 6101, [245], 0x06)]


async def test_writing_an_enum_setting(
    appliance: BrinkFlair, mock_modbus_unit: MockModbusUnit
) -> None:
    await appliance.parameters.write("flow_type", FlowType.CONSTANT_MASS_FLOW)
    assert await mock_modbus_unit.read_holding_registers(6030, 1) == [2]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("bypass_temperature_dwelling", 40.0),  # above the spec's 35.0 °C
        ("bypass_temperature_dwelling", 22.2),  # off the spec's 0.5 °C step
        ("imbalance_value", 25),  # above the spec's 20 %
        ("offset_imbalance_supply", -20),  # below the spec's -15 %
        ("filter_warning_days", 0),  # below the spec's 1 day
        ("co2_sensor_1_low", 100),  # below the spec's 400 ppm
        ("modbus_slave_address", 248),  # above the spec's 247
        ("flow_preset_1", 123),  # off the spec's 5 m³/h step
        ("pwm_supply_preset_0", 10),  # between the spec's 0 and 15 %
    ],
)
async def test_a_value_the_spec_forbids_never_reaches_the_bus(
    appliance: BrinkFlair, mock_modbus_unit: MockModbusUnit, field: str, value: float
) -> None:
    written: list[WriteEvent] = []
    mock_modbus_unit.on_write(written.append)

    with pytest.raises(ValueError):
        await appliance.parameters.write(field, value)

    assert written == []


@pytest.mark.parametrize("value", [0, 15, 100])
async def test_a_pwm_preset_takes_off_and_the_spec_s_range(
    appliance: BrinkFlair, value: int
) -> None:
    await appliance.parameters.write("pwm_supply_preset_0", value)


async def test_setting_a_flow_rate_puts_the_appliance_in_that_mode_first(
    appliance: BrinkFlair, mock_modbus_unit: MockModbusUnit
) -> None:
    """8002 is only honoured while 8000 says flow rate, so both are written."""
    written: list[WriteEvent] = []
    mock_modbus_unit.on_write(written.append)

    await appliance.control.async_set_flow_rate(225)

    assert written == [
        WriteEvent("holding", 8000, [int(ModbusControl.FLOW_RATE)], 0x06),
        WriteEvent("holding", 8002, [225], 0x06),
    ]


async def test_setting_a_switch_position_puts_the_appliance_in_that_mode_first(
    appliance: BrinkFlair, mock_modbus_unit: MockModbusUnit
) -> None:
    written: list[WriteEvent] = []
    mock_modbus_unit.on_write(written.append)

    await appliance.control.async_set_switch_position(SwitchPosition.HIGH)

    assert written == [
        WriteEvent("holding", 8000, [int(ModbusControl.SWITCH_POSITION)], 0x06),
        WriteEvent("holding", 8001, [int(SwitchPosition.HIGH)], 0x06),
    ]


async def test_releasing_control_hands_the_appliance_back(
    appliance: BrinkFlair, mock_modbus_unit: MockModbusUnit
) -> None:
    await appliance.control.async_release()
    assert await mock_modbus_unit.read_holding_registers(8000, 1) == [ModbusControl.OFF]


async def test_standby_is_asked_for_with_a_code_a_read_never_answers(
    appliance: BrinkFlair, mock_modbus_unit: MockModbusUnit
) -> None:
    """A read of 8003 answers 0/1 for the state; a write takes 1/2."""
    await appliance.async_update()
    assert appliance.control.standby is False

    await appliance.control.async_request_standby(True)
    assert await mock_modbus_unit.read_holding_registers(8003, 1) == [1]

    await appliance.control.async_request_standby(False)
    assert await mock_modbus_unit.read_holding_registers(8003, 1) == [2]


async def test_the_one_shot_commands_are_written_as_one(
    appliance: BrinkFlair, mock_modbus_unit: MockModbusUnit
) -> None:
    written: list[WriteEvent] = []
    mock_modbus_unit.on_write(written.append)

    await appliance.commands.write("reset_filter_warning", 1)
    await appliance.commands.write("appliance_reset", 1)

    assert written == [
        WriteEvent("holding", 8010, [1], 0x06),
        WriteEvent("holding", 8011, [1], 0x06),
    ]


async def test_a_command_value_the_spec_gives_no_meaning_is_refused(
    appliance: BrinkFlair,
) -> None:
    with pytest.raises(ValueError, match="writing 1"):
        await appliance.commands.write("reset_filter_warning", 2)


async def test_a_rejected_write_leaves_the_setting_alone(
    appliance: BrinkFlair, mock_modbus_unit: MockModbusUnit
) -> None:
    """The appliance may refuse a value this library thinks is in range."""
    mock_modbus_unit.fail_write(6120, IllegalDataValueError())
    with pytest.raises(IllegalDataValueError):
        await appliance.parameters.write("filter_warning_days", 120)
    assert await mock_modbus_unit.read_holding_registers(6120, 1) == [90]


async def test_read_raw_covers_the_settings_and_skips_the_commands(
    appliance: BrinkFlair,
) -> None:
    """A diagnostics dump reads how the appliance is set up, but must not
    consume the one-shot command results."""
    raw = await appliance.async_read_raw()

    assert raw["input"][4000] == 0x5301  # the identity
    assert raw["input"][4032] == 148  # a reading
    assert raw["input"][4523] == 25  # the extension module
    assert raw["holding"][6101] == 220  # a setting
    assert raw["holding"][8000] == 2  # the remote-control state
    assert 8010 not in raw["holding"]
    assert 8011 not in raw["holding"]
    assert sorted(raw) == ["holding", "input"]


async def test_a_bare_appliance_dumps_only_what_it_has(
    bare_appliance: BrinkFlair,
) -> None:
    raw = await bare_appliance.async_read_raw()
    assert 4500 not in raw["input"]
    assert raw["input"][4032] == 148


async def test_each_component_notifies_its_own_listeners(
    appliance: BrinkFlair, mock_modbus_unit: MockModbusUnit
) -> None:
    await appliance.async_update()
    fired: list[str] = []
    appliance.measurements.add_update_listener(lambda: fired.append("measurements"))
    assert appliance.co2_sensors is not None
    appliance.co2_sensors.add_update_listener(lambda: fired.append("co2"))

    mock_modbus_unit.fail_read(4200, IllegalDataAddressError(), register_type="input")
    await appliance.async_update_readings()

    assert fired == ["measurements"]
