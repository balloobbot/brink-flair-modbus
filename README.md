# brink-flair-modbus

Read and drive a **Brink heat recovery appliance** over Modbus.

Brink's HRA range — the Flair units and their siblings — runs on a UWA2-B
control PCB, optionally with the Plus extension PCB UWA2-E beside it. The
UWA2-B speaks **Modbus RTU on RS-485** and nothing else. This library maps its
registers to typed Python attributes: what the appliance measures, how it is
configured, and the remote-control block that lets a building system drive it.

One register map covers the range, because it is the control PCB's map rather
than any one appliance's. The optional parts of it — the display, the UWA2-E,
a geo heat exchanger, up to four CO2 sensors — are settled by probing the
appliance at setup, so nothing has to be configured to match the hardware.

This is a device library built on
[modbus-connection](https://github.com/home-assistant-libs/modbus-connection).
It takes a `ModbusUnit` and never opens a connection of its own — the consumer
owns the link, and so chooses the transport.

## Wiring and link settings

Connect to X15 on the UWA2-B, or to X06 on the UWA2-E where the appliance is a
Plus version. Cascaded appliances are reached through the master's UWA2-E. The
RS-485 terminator is the jumper X12 on the UWA2-B (X07 on the UWA2-E); remove
it where the appliance is not at the end of the bus.

Out of the factory the appliance answers **unit id 20 at 19200 baud, 8 data
bits, even parity, 1 stop bit**. All four are settings on the appliance's own
display (step 14.1 to 14.4), and step 14.1 has to say `Modbus` before the port
does anything. They are also writable over Modbus once you are talking to it —
see [Writing](#writing).

## Install

```bash
pip install brink-flair-modbus
```

Install `brink-flair-modbus[tmodbus]` to pull in a backend as well; the library
itself works over any of
[modbus-connection's backends](https://home-assistant-libs.github.io/modbus-connection/getting-started/backends/).

## Usage

```python
import asyncio

from modbus_connection import ModbusSerialParams
from modbus_connection.tmodbus import ModbusConnection

from brink_flair_modbus import BrinkFlair


async def main() -> None:
    connection = ModbusConnection(
        ModbusSerialParams(device="/dev/ttyUSB0", baudrate=19200, parity="E")
    )
    try:
        appliance = BrinkFlair(connection.for_unit(20))
        await appliance.async_update()

        print("Serial number:", appliance.identity.serial_number)
        print("Supply flow:", appliance.measurements.supply_flow, "m³/h")
        print("Exhaust temperature:", appliance.measurements.exhaust_fan_temperature)
        print("Filters dirty:", appliance.measurements.filter_dirty)
    finally:
        await connection.close()


asyncio.run(main())
```

### Over an RTU-to-TCP gateway

The appliance has no Ethernet of its own, but a serial gateway in front of the
RS-485 line reaches it over the network. The gateway forwards RTU frames, so
the framing stays `rtu` — the only line that changes is the connection:

```python
from modbus_connection import ModbusTcpParams

connection = ModbusConnection(ModbusTcpParams(host="192.168.1.50", framer="rtu"))
```

Set `framer="rtu"` explicitly. `ModbusTcpParams` defaults to `socket`, which is
native Modbus TCP — the right choice only for a gateway configured to
translate rather than to forward.

One appliance object models one appliance, so build one per unit id. Several
cascaded appliances reach the consumer as several unit ids on one connection:

```python
appliances = {unit_id: BrinkFlair(connection.for_unit(unit_id)) for unit_id in (20, 21)}
```

## What it reads

| Component | Space | Registers | Contents | Polled |
| --- | --- | --- | --- | --- |
| `identity` | input (FC04) | 4000-4012 | Versions, appliance type, serial number | once, at setup |
| `measurements` | input (FC04) | 4020-4119 | Function, fans, bypass, preheater, frost, sensors, clock, counters | every poll |
| `geo_heat_exchanger` | input (FC04) | 4150 | The geo valve's state | every poll, if fitted |
| `co2_sensors` | input (FC04) | 4200-4207 | Four sensors, status and ppm | every poll, if fitted |
| `user_interface` | input (FC04) | 4400-4421 | The display's versions and its switch | every poll, if fitted |
| `extension` | input (FC04) | 4500-4544 | The UWA2-E's NTC, contacts, analogue I/O and relays | every poll, if fitted |
| `parameters` | holding (FC03/FC06) | 6000-7992 | Every setting | once at setup, then on request |
| `control` | holding (FC03/FC06) | 8000-8003 | Whether Modbus is driving the appliance | every poll |
| `commands` | holding (FC06) | 8010-8011 | Filter-warning reset, appliance reset | never — written only |

`async_update()` refreshes everything. `async_update_readings()` refreshes the
polled components alone and `async_update_settings()` the settings alone, so a
consumer can put the two on different intervals — which is what you want,
since the settings cost more requests than the readings and change only when
someone writes them.

Both return an `UpdateReport` naming which sub-systems refreshed and which
failed, so one missing sub-system does not cost you the rest of the poll.

```python
report = await appliance.async_update_readings()
report.updated  # ['measurements', 'control', 'co2_sensors', ...]
report.failed  # {'extension': IllegalDataAddressError(...)}
```

`await appliance.async_read_raw()` returns every register the appliance is read
from, undecoded, for a diagnostics dump. It deliberately leaves out 8010 and
8011 — see [Writing](#writing).

### What a poll costs

A fully equipped appliance polls its readings in **19 requests** and reads its
settings in **17**; a bare UWA2-B polls in **11**. Setup adds two reads for the
identity and one probe per optional sub-system. The numbers are pinned in
`tests/test_read_plan.py`.

That is more requests than the register map strictly needs, and the reason is
deliberate. Every component declares `register_ranges` for the rows the spec
documents, which stops a read from ever reaching an address the spec does not
list. The alternative — modbus-connection's default gap planning — would read
4020-4119 in **one** request instead of ten, but only if the appliance answers
for the gaps in between. The spec never says whether it does, and a refused
block fails the whole update rather than just that register. Nineteen requests
on a 19200-baud line is well under a second, so the safe reading wins until
someone measures an appliance.

If yours does answer across the gaps, you can say so before the first poll:

```python
appliance.measurements.register_ranges = None  # fall back to gap planning
appliance.measurements.max_gap = 32
```

The read plan is built and cached on the first update, so set this first. If
you try it, please open an issue with what the appliance did.

## Checking a real appliance

`script/query.py` reads one appliance once and prints everything it has, which
is the quickest way to see whether it is wired and addressed correctly:

```bash
uv run script/query.py /dev/ttyUSB0 --unit 20 --baudrate 19200 --parity E
uv run script/query.py 192.168.1.50 --transport tcp --unit 20
```

It probes for the optional modules, prints each sub-system under its own
heading, names any that did not answer, and finishes with the read count — so
the numbers above are visible against real hardware and not only in the tests.

## Writing

### Settings

Every setting the spec documents is writable, and each is validated against
the bounds and step of its own row before anything goes on the bus. A scaled
setting is written in its own units, not in the tenths that go on the wire:

```python
from brink_flair_modbus import BypassMode

await appliance.parameters.write("bypass_temperature_dwelling", 24.5)  # °C
await appliance.parameters.write("bypass_mode", BypassMode.OPEN)
await appliance.parameters.write("filter_warning_days", 180)
```

Three rules the spec states are documented rather than enforced, because one
field cannot check them: the ordering between the flow and PWM presets, the
flow presets' own bounds (the spec makes them depend on the appliance), and
register 6002's "Step size: 150" against its three neighbours' 5 — where the
permissive reading is used, since rejecting a value the appliance would have
taken is the worse failure.

Writing `modbus_slave_address` or `modbus_speed` takes effect immediately, so
the connection you wrote it over no longer reaches the appliance. Build a new
unit, or a new connection, at the new settings.

### Driving the appliance

The remote-control block is a mode register plus the value that mode uses, so
setting a flow rate means setting both in the right order. `Control` does that
for you:

```python
from brink_flair_modbus import SwitchPosition

await appliance.control.async_set_flow_rate(225)  # m³/h
await appliance.control.async_set_switch_position(SwitchPosition.HIGH)
await appliance.control.async_request_standby(True)
await appliance.control.async_release()  # give the appliance its controls back
```

`async_request_standby` is a method rather than a writable field because a read
and a write of register 8003 do not mean the same thing: a read answers whether
the appliance is in standby, a write asks it to change. `control.standby` is
the state.

The spec warns that **a power cycle forgets the whole 8000-8011 block**. An
appliance driven over Modbus has to be set up again after it loses mains.

### The two one-shot commands

```python
await appliance.commands.write("reset_filter_warning", 1)
await appliance.commands.write("appliance_reset", 1)
```

These are written and never read. Reading 8010 or 8011 answers whether the
action ran — and clears itself in doing so — so polling them would consume the
outcome before anyone asked for it. That is why they are a component of their
own, why `control` declares ranges that stop at 8003, and why they stay out of
`async_read_raw()`.

## Where the register map comes from

The document is committed under `docs/`, so the register definitions can be
checked against it without hunting for it, and so a later revision shows up as
a visible diff rather than a silent change.

- [`docs/modbus-uwa2-b-uwa2-e-installation-regulations-614882.pdf`](docs/modbus-uwa2-b-uwa2-e-installation-regulations-614882.pdf)
  — *Installation regulations Modbus UWA2-B/UWA2-E*, 614882-D, from
  <https://www.brinkclimatesystems.nl/documenten/modbus-uwa2-b-uwa2-e-installation-regulations-614882.pdf>

Its §2.1 is the input registers, §2.2 the holding registers and §2.3 the
remote-control block. Addresses are used exactly as the document's "Modbus
address" column gives them.

## Where the spec is unclear

None of these is resolved here — the model follows the document, and each is
recorded so anyone with an appliance on the bench can settle it.

**Whether the appliance answers for its gaps.** The one unknown with a
measurable cost, and the reason a poll takes 19 requests rather than 4. See
[What a poll costs](#what-a-poll-costs).

**The word order of the 32-bit counters.** Operating time, filter flow and
total flow each span two registers, and the document states no word order for
them. They decode high word first, the Modbus convention and
modbus-connection's default. A wrong guess here is obvious against hardware:
`operating_time` would read in the millions.

**The date registers do not decode.** 4111 is labelled "Date high nibble" and
4112 "Date lower nibbles", while the description spanning both says "high byte
= days, low byte = years ... only decennia". Nibbles and bytes cannot both be
right, and neither account has room for a month. Both words are exposed raw as
`date_high` and `date_low`. The time at 4110 is unambiguous and decodes to a
`datetime.time`.

**The bypass status names two codes "open".** Register 4050's list reads
"initialize / open / close / open / closed". Read as a moving valve and a
settled one, 1/2 are the movement and 3/4 the position, which is the only
reading that gives all five codes a distinct meaning. `BypassStatus` is named
that way; the document does not say so.

**The UIF module reports two software versions.** 4400-4402 and 4413-4415 are
listed under the same description with the same example, and nothing
distinguishes them. Both are exposed, as `software_version` and
`second_software_version`.

**Hardware versions are bytes in one place and BCD in another.** The base
module's 4003 is given as "Numbers in bytes range [00..99]"; the UIF's 4403 and
the extension's 4503 as "Major and minor in BCD format". Each is decoded as its
own row states. The two agree for any number below 10, so an appliance can only
settle this once a version reaches double figures.

**"Filters used in m3/h" is a volume.** The units column of 4116-4117 and
4118-4119 reads `m3/h` for what the same row's text calls an "amount of flow
... since last filter reset". They are exposed in `m³`.

**Baud-rate codes 6 and 7 are written loosely.** The spec gives them as "56k"
and "115k", and the appliance's own settings menu as "56k" and "115k2". Both
are the usual 57600 and 115200, which is what `BaudRate.BPS_57600` and
`BPS_115200` are named for.

**The four-position switch default is bounded to two.** Register 6031 is
described as the default position of a four-position switch while its own row
gives minimum 0 and maximum 1. The row's bounds are enforced.

**Codes 0 and 1 of the fan status are unassigned.** 4030 and 4040 list codes 2
to 6. Either of the two below them decodes to `None`.

## License

MIT
