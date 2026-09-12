# Open questions

The register map here is transcribed from a document that contradicts itself
in places, and nothing in it has been checked against an appliance. Each
question below states what this library assumes, what settling it would
change, and how to settle it.

Tick one off by opening a pull request that changes the code and strikes the
question, or an issue saying the assumption held.

Most of these need only one run:

```bash
uv run script/query.py /dev/ttyUSB0 --unit 20 --baudrate 19200 --parity E --raw
```

Keep the whole output. The decoded half answers the questions about values,
the `--raw` half is the evidence, and it loads into a test with
modbus-connection's `load_raw`.

## Settled by one query run

- [ ] **Does the appliance answer a read that spans its gaps?**
  Every component declares `register_ranges` for the rows the document
  lists, so a read never reaches an address it does not name. That costs
  round trips: a full poll is 19 requests where gap planning would be about
  four. Nothing in the document says whether the appliance serves the gaps.

  Run the query script, then again with the ranges dropped:

  ```python
  appliance.measurements.register_ranges = None
  appliance.measurements.max_gap = 32
  ```

  If it still reads, say so and the ranges can go. If it raises an
  illegal-data-address error, the ranges are earning their keep and this
  question closes for good.

- [ ] **Is the word order of the 32-bit counters right?**
  Operating time (4113), filter flow (4116) and total flow (4118) each span
  two registers, and the document states no word order. They decode high
  word first, the Modbus convention.

  Wrong is obvious: `operating_time` reads in the millions rather than in
  hours, and the two flows disagree with each other's scale.

- [ ] **Do the hardware versions decode?**
  4003 is documented as plain bytes, 4403 and 4503 as BCD. The two agree
  below 10, so only an appliance with a version at 10 or above tells them
  apart. Compare `hardware_version` against what the display shows.

- [ ] **Which of the display's two software versions is which?**
  4400-4402 and 4413-4415 carry the same description and the same example.
  Both are exposed, as `software_version` and `second_software_version`.
  Compare both against the display.

- [ ] **Is "filters used in m3/h" a volume?**
  The units column for 4116-4117 and 4118-4119 reads `m3/h`, while the same
  row's text calls it an amount of flow since a reset. They are exposed in
  `m³`. Watching either against the flow rate settles it.

- [ ] **Do fan status codes 0 and 1 ever appear?**
  4030 and 4040 document codes 2 to 6. Anything below decodes to `None`.

## Need poking at the appliance

- [ ] **What does the bypass report while it moves?**
  4050's codes read "initialize / open / close / open / closed", naming both
  1 and 3 "open". `BypassStatus` reads 1 and 2 as the movement and 3 and 4
  as the position, which is the only reading that gives all five a distinct
  meaning. Watch `bypass_status` while the bypass opens.

- [ ] **Are baud-rate codes 6 and 7 57600 and 115200?**
  The document writes them "56k" and "115k", and the display's own menu
  "56k" and "115k2". `BaudRate.BPS_57600` and `BPS_115200` assume the usual
  rates. Set the appliance to each and see what a link at those speeds does.

- [ ] **What does the four-position switch default accept?**
  6031 is described as the default position of a four-position switch, while
  its own row gives minimum 0 and maximum 1. The row's bounds are enforced,
  so writing 2 or 3 is refused here. Try writing one from the display's side
  and read the register back.

- [ ] **Is flow preset 2 really in steps of 150?**
  6002 says "Step size: 150" where its three neighbours say 5. The
  permissive reading is used, since rejecting a value the appliance accepts
  is the worse failure. Write a multiple of 5 that is not a multiple of 150
  and read it back.

- [ ] **Do the one-shot command registers clear themselves on read?**
  8010 and 8011 are documented to answer the outcome of the last request and
  reset to 0 once read. They are written and never read here, and
  `async_read_raw()` leaves them out. Reading one twice after a filter reset
  would confirm it.

- [ ] **Do the date registers decode at all?**
  4111 is labelled "Date high nibble" and 4112 "Date lower nibbles", while
  the description spanning both says "high byte = days, low byte = years ...
  only decennia". Nibbles and bytes cannot both be right, and neither
  accounts for a month. Both words are exposed raw as `date_high` and
  `date_low`. Read them at a known date, from an appliance whose clock is
  set, and the encoding should fall out.
