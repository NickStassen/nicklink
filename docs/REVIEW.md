# NickLink v1.3 design review — 2026-10-01

v1.3 adds an on-board 6-axis IMU for motion tracking, robotics and tap-activated projects. Everything else matches v1.2 (section below), apart from the items listed here. **Pinout is unchanged from v1.2.**

| | v1.2 | v1.3 |
|---|---:|---:|
| Outline | 33.19 × 25.5 mm (846 mm²) | **33.99 × 25.5 mm (867 mm²)** |
| vs v1.1 (1122 mm²) | −25% | **−23%** |
| Parts | 33 | 38 |

**IMU circuit** (ST LSM6DSV16X, LGA-14 2.5 × 3 mm, LCSC C5267406):

| Pin | Connection | Why |
|---|---|---|
| SCL / SDA | PB6 / PB7 (I2C1) | 4.7 kΩ pull-ups R7/R9 back on the bus |
| SDO/SA0 | GND | I2C address 0x6A |
| CS | 3V3 | I2C mode |
| INT1 | PA0 | WKUP pin: tap or motion can wake the MCU from Standby |
| VDD, VDDIO | 3V3, each with its own 100 nF | datasheet recommendation |
| SDx, SCx | GND | datasheet: "connect to Vdd_IO or GND" (must not float) |
| INT2, OCS_Aux, SDO_Aux | not connected | INT2 drives low by default; the aux pins have internal pull-ups |

The connections were checked against datasheet DS13510 (see `tools/imu_research.md`). The schematic uses a project symbol (`nicklink.kicad_sym`) with the LSM6DSM pinout, which is identical, and pin types set for I2C use.

**Placement and routing**
- The IMU sits on the top side, in the right channel between the MCU and J1, below the RESET button. Its caps go in a row underneath, the ferrite moves into the MCU's bottom-right courtyard notch, the 10 µF bulk cap moves to the top-left pocket, and the I2C pull-ups sit beside PB6/PB7. An earlier draft added a 3.3 mm bottom row for the IMU; this layout fits it into existing gaps instead, so the board stays at v1.2's height.
- The position is away from the LDO's heat (gyro bias drift) and from USB cable strain.
- Orientation: pin 1 (SA0) is top-left. The VDDIO/GND row faces its caps below, and all SMD bodies stay ≥ 1 mm from the board edge.
- A top-copper keep-out covers the area inside the IMU's pad ring, per ST's LGA guidance: no tracks, vias or pour under the package.
- **Deviation:** ST suggests about 10 mm from screws. Here it is about 5 mm (H4), because the board is only 25.5 mm tall. Mount without over-tightening.
- **Crystal nets are now pre-routed** as locked top-layer tracks (HSE_IN 8.1 mm, HSE_OUT 5.1 mm, no vias), so autoroute variation can't push them onto vias.
- **ESD channels swapped:** USB D+ uses the USBLC6's I/O2 channel and D− uses I/O1. The two channels are identical, and this order means D+ and D− no longer cross at the MCU. USB D+/D− are about 11 / 10 mm.
- **Minimum track width lowered from 0.13 mm to 0.10 mm.** This covers Freerouting's 0.112 mm neck-downs at fine-pitch pads, which are within JLC's standard 2-layer capability. The default 0.15 mm signal width is unchanged.
- Sixteen small parts (passives near USB, the I2C pull-ups, the IMU, its caps and RESET) carry ≤ 0.1 mm offsets, found by a seeded search (`NICKLINK_SEED=13`). Freerouting's result is very sensitive to placement, and these offsets give 100% routing with short crystal and USB nets.

**JLCPCB rules** (README, "JLCPCB design rules"): v1.3 is checked against JLC's published limits via the board setup and `nicklink.kicad_dru`. Changes made to comply:
- USB4085 pads enlarged to a 0.18 mm annular ring.
- Edge clearance raised to 0.3 mm (Economic PCBA).
- Silkscreen text 1.0 mm tall and lines 0.15 mm wide. The label strips grew from 1.2 to 1.4 mm, which adds 0.8 mm of board width.
- Silk-to-pad clearance 0.15 mm and a 0.10 mm minimum solder-mask web.

**Verification** (KiCad 10.0.6): ERC 0 errors / 0 warnings; DRC 0 violations, 0 unconnected, 0 schematic-parity issues (`checks/`).

**Bring-up additions:** scan I2C1 (expect 0x6A); read WHO_AM_I (0Fh) and expect 0x70; enable tap detection on INT1 and check that A0 pulses; confirm that A0 is not driven from outside while INT1 is push-pull.

**Cost:** the LSM6DSV16X is a JLC Extended part, about $3.44 each or $2.47 each at 100, plus a loading fee. The other new parts are Basic: 4.7 kΩ (C25900), 100 nF (C1525).

---

# NickLink v1.2 design review — 2026-10-01

v1.2 has two goals: a smaller board, and the quality-of-life fixes found when reviewing v1.1 (no 5 V pin, undocumented fixed I2C pull-ups, no reset button, SWD split across headers, a non-standard 16 MHz crystal, no user LED, no USB ESD protection). The pinout changes along the way, so v1.2 is **not** pin-compatible with v1.1.

## Result

| | v1.1 | v1.2 |
|---|---:|---:|
| Outline | 34 × 33 mm | **33.19 × 25.5 mm** |
| Area | 1122 mm² | **846 mm² (−24.6%)** |
| Headers | 2 × 2×10, 2.54 mm | same |
| M2 mounting holes | 4 | 4 |
| Front pin labels | none | all 40 pins |
| Parts (excl. holes) | 30 | 33 |

The board is now exactly as tall as the headers (25.4 mm body + edge clearance). Its width comes from the top row: hole, USB-C, hole, plus the two headers and their label strips.

## Changes and rationale

**Size**
- The board height equals the header length. Previously 6 mm sat above the headers for the USB connector, switch and holes. All four holes moved into the middle column: the top pair flank the USB connector, the bottom pair flank the crystal.
- Hole footprints use ISO 7380 button-head keep-outs (3.5 mm head, 4.1 mm courtyard) instead of the generic 5 mm.
- AMS1117 (SOT-223) plus a 22 µF tantalum became a TLV75533 (2×2 mm WSON) with 1 µF ceramics. This saves about 45 mm² and removes the open question about tantalum ESR.
- USBLC6 in SOT-666, LEDs in 0402, ferrite bead in 0402.
- The 3.0 × 2.5 mm Omron B3U buttons sit in the side channels between the MCU and the headers. Traces pass between their pads and underneath on the bottom layer.
- The project-local USB4085 courtyard is now the shield pads + 0.25 mm. Before, it was about 0.3 mm wider per side than the copper.

**Front labels** (requested): the header plastic covers its whole footprint, so labels sit in strips beside each pin column (v1.2: 1.2 mm strips, 0.8 mm text; v1.3: 1.4 mm strips, 1.0 mm text for JLC). The text is rotated, in short form (`A9`, `B12`, `RST`). This costs about 3.2 mm of width compared with a label-free layout and is the main reason v1.2 isn't narrower. The project copies of the header and button footprints have no silkscreen so the labels fit; their copper is unchanged from KiCad's library.

**Quality-of-life fixes**
- **5 V on J1.1:** USB VBUS → 1N5819WS → 5V rail. The diode lets the 5V pin act as an input without back-feeding the USB host. Input must stay ≤ 5.5 V (TLV755 maximum).
- **RESET button** on NRST. NRST now sits on J3.10, beside SWDIO/SWCLK/SWO, so a debugger connects to one header.
- **BOOT button** replaces the BOOT0 slide switch: hold BOOT, tap RESET. 10 kΩ pull-down on BOOT0; the 10 kΩ PB2/BOOT1 pull-down is kept.
- **8 MHz crystal** (YXC X32258MOB4SI, 12 pF load, 15 pF C0G caps). 16 MHz worked electrically, but 8 MHz matches the clock trees that Blue Pill, STM32duino and CubeMX assume, and sits mid-range of the 4–16 MHz HSE spec. Gain margin is about 73 by AN2867 (requirement ≥ 5).
- **I2C pull-ups removed** from PB6/PB7. They were fixed, undocumented and stiff (1.5 kΩ), and most I2C modules bring their own.
- **User LED** on PC13, active low (sink only).
- **ESD:** USBLC6-2P6 on D+/D− with 100 nF on its VBUS pin, per ST's layout guidance.

**Pinout:** header pins follow the MCU's package order, so the fanout is nearly planar. Function pairs share a row: UART1, SWDIO/SWCLK, SWO/NRST, I2C1, CAN, UART2, SPI2. Both headers have 3V3 and GND; J1 adds 5V.

## Routing

The board is autorouted with Freerouting after placement, on two layers with GND pours on both. Stitching vias are added afterwards and kept clear of silkscreen text. The design rules are unchanged from v1.1:

- Tracks: 0.15 mm signal, 0.30 mm power, 0.25 mm ground.
- Clearance: 0.13 mm.
- Vias: 0.6 / 0.3 mm.
- Copper to edge: 0.2 mm.

Critical nets, from `tools/netreport.py`:

| Net | Routing |
|---|---|
| HSE_IN / HSE_OUT | 6.0 / 4.2 mm, top layer only, no vias |
| USB_D+ / USB_D− | 10.9 mm (top only) / 15.6 mm (2 vias), including the pull-up branch. Fine for 12 Mbit/s full speed; not an impedance-controlled pair. |
| VDDA | through the 0402 ferrite, 100 nF + 1 µF at the pin |

## Verification

KiCad 10.0.6 (Docker `kicad/kicad:10.0`):

- ERC: **0 errors, 0 warnings** (`checks/final-erc.rpt`). The v1.1 ignored-check set is unchanged.
- The netlist exported from the schematic is checked pin-by-pin against `tools/spec.py` (`tools/check_netlist.py`).
- DRC with schematic parity and all track errors: **0 violations, 0 unconnected, 0 parity issues** (`checks/final-drc.json`). No DRC exclusions.
- Front/back renders and copper plots inspected.

These checks establish connectivity and geometry. They do not establish signal integrity, ESD performance, regulator thermals or a working prototype.

## Open items / bring-up risks

1. **Regulator thermals.** The 250 mA 3V3 budget assumes about 150 °C/W on this two-layer board, an estimate scaled from TI's 100 °C/W four-layer figure. Measure the temperature at the intended load.
2. **Crystal load.** 15 pF assumes 3–5 pF stray. If the HSE measures fast, use 18 pF (LCSC C1549).
3. **JLC Extended parts** (each adds a loading fee): TLV75533, USBLC6-2P6 (genuine ST stock is limited; a TECH PUBLIC alternative exists), B3U buttons, the 8 MHz crystal, the 0402 ferrite, and possibly the LEDs. See `tools/parts_research.md`.
4. **The USB-C connector and headers are hand-soldered** (through-hole).
5. **First article:** short check; current-limited 5 V; measure 5V/3V3/VDDA; SWD attach and RESET button; HSE startup; USB enumeration in both orientations; BOOT+RESET into the USART1 bootloader; user LED; then the peripherals you need.
