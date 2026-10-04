# NickLink v1.3 design review — 2026-10-01

v1.3 adds an on-board 6-axis IMU for motion tracking, robotics and tap-activated projects. Everything else matches v1.2 (section below), apart from the items listed here. **Pinout is unchanged from v1.2.**

| | v1.2 | v1.3 |
|---|---:|---:|
| Outline | 33.19 × 25.5 mm (846 mm²) | **33.99 × 25.5 mm (867 mm²)** |
| vs v1.1 (1122 mm²) | −25% | **−23%** |
| Parts | 33 | 42 |

**IMU circuit** (designed as ST LSM6DSV16X, LCSC C5267406; built as the pin- and register-compatible **LSM6DSV, C41785564**, see [JLC order round](#jlc-order-round-2026-10-02); LGA-14 2.5 × 3 mm):

| Pin | Connection | Why |
|---|---|---|
| SCL / SDA | PB6 / PB7 (I2C1) | 4.7 kΩ pull-ups R7/R9 back on the bus |
| SDO/SA0 | GND | I2C address 0x6A |
| CS | 3V3 | I2C mode |
| INT1 | PA0 through R10 10 kΩ | WKUP pin: tap or motion can wake the MCU from Standby; R10 limits INT1's power-up low state to a weak pull-down |
| VDD, VDDIO | 3V3, each with its own 100 nF | datasheet recommendation |
| SDx, SCx | GND | datasheet: "connect to Vdd_IO or GND" (must not float) |
| INT2 | not connected | drives low by default; every interrupt source can route to INT1 |
| OCS_Aux, SDO_Aux | 3V3 | datasheet allows tying them to VDDIO; gives CS a short path to VDD |

The connections were checked against datasheet DS13510 (see `tools/imu_research.md`). The schematic uses a project symbol (`nicklink.kicad_sym`) with the LSM6DSM pinout, which is identical, and pin types set for I2C use.

**Placement and routing**
- The IMU sits on the top side, in the right channel between the MCU and J1, below the RESET button. Its caps and the ferrite go in a row underneath. R10 (INT1) sits in the MCU's bottom-right courtyard notch, and the I2C pull-ups sit beside PB6/PB7. An earlier draft added a 3.3 mm bottom row for the IMU; this layout fits it into existing gaps instead, so the board stays at v1.2's height.
- The position is away from the LDO's heat (gyro bias drift) and from USB cable strain.
- Orientation: pin 1 (SA0) is top-left. The VDDIO/GND row faces its caps below, and all SMD bodies stay ≥ 1 mm from the board edge.
- A top-copper keep-out covers the area inside the IMU's pad ring, per ST's LGA guidance: no tracks, vias or pour under the package.
- **Deviation:** ST suggests about 10 mm from screws. Here the H4 screw keep-out is 2.4 mm from the IMU body (5.7 mm centre to centre), because the board is only 25.5 mm tall. Mount without over-tightening.
- **Crystal nets are now pre-routed** as locked top-layer tracks (HSE_IN 8.1 mm, HSE_OUT 5.1 mm, no vias), so autoroute variation can't push them onto vias.
- **ESD channels swapped:** USB D+ uses the USBLC6's I/O2 channel and D− uses I/O1. The two channels are identical, and this order means D+ and D− no longer cross at the MCU. USB D+ is 11.8 mm with no vias and D− is 10.9 mm with one via, including the A/B row ties and the pull-up branch (second-wave layout).
- **Minimum track width lowered from 0.13 mm to 0.10 mm.** This covers Freerouting's 0.112 mm neck-downs at fine-pitch pads, which are within JLC's standard 2-layer capability. The default 0.15 mm signal width is unchanged.
- Sixteen small parts (passives near USB, the I2C pull-ups, the IMU, its caps and RESET) carry ≤ 0.1 mm offsets, found by a seeded search (`NICKLINK_SEED=13`; the post-review layout uses seed 3). Freerouting's result is very sensitive to placement, and these offsets give 100% routing with short crystal and USB nets.

**JLCPCB rules** (README, "JLCPCB design rules"): v1.3 is checked against JLC's published limits via the board setup and `nicklink.kicad_dru`. Changes made to comply:
- USB4085 pads enlarged to a 0.18 mm annular ring.
- Edge clearance raised to 0.3 mm (Economic PCBA).
- Silkscreen text 1.0 mm tall and lines 0.15 mm wide. The label strips grew from 1.2 to 1.4 mm, which adds 0.8 mm of board width.
- Silk-to-pad clearance 0.15 mm and a 0.10 mm minimum solder-mask web.

## Five-reviewer audit (2026-10-01) and fixes

Five independent reviewers checked v1.3 at commit a913740, one area each. They checked against datasheets, the GCT drawing, JLC's own EasyEDA footprints and the board data. I re-verified the key claims (INT1 default state in DS13510; the EasyEDA pin-1 positions) before changing anything.

| Area | Grade | Must-fix findings |
|---|---|---|
| Power / protection | C | U3 CPL rotation would short VBUS; LDO output cap 19 mm from OUT |
| MCU core / clock | B | U1 CPL rotation 90° off; weak VDD/VDDA decoupling layout |
| USB-C / data | B | 0.36 mm holes too tight for the receptacle tails |
| IMU / headers / labels | B | INT1 holds A0 low from power-up; PB6/PB7 and NRST mislabelled 5 V tolerant |
| Fab / BOM / CPL / mechanics | C+ | CPL rotations for U1/U3/U4 wrong vs JLC's footprints; USB hole fit |

**Fixed:**
- **CPL rotations:** `tools/fab.sh` adds per-footprint JLC corrections (LQFP-48 −90°, SOT-666 +180°, LGA-14 +180°), checked against JLC's EasyEDA footprints. U1 = 0, U3 = 90, U4 = 180.
- **LDO:** output cap C8 sits next to U2 OUT (0.95 mm, top layer). C12 becomes 10 µF 0603 for input decoupling and USB hot-plug damping. *(Superseded: the reliability pass changed C12 to 4.7 µF, and the second wave fitted the 16 V 0402 Samsung CL05A475MO5NUNC, C318563. Not 10 µF 0603.)* Two 0.3 mm thermal vias go under the exposed pad (project footprint `WSON-6-…_ThermalVias03`).
- **IMU INT1:** goes to A0 through a new 10 kΩ resistor, R10. INT1's power-up "forced to ground" state is now only a weak pull-down on A0.
- **USB4085:** 0.38 mm holes in 0.74 mm pads. That is inside GCT's 0.40 ± 0.05 mm spec and keeps JLC's 0.18 mm ring. The 0.11 mm pad gap is covered by a footprint-scoped DRC rule; JLC's minimum is 0.10 mm. The GND pins use thermal reliefs for hand soldering.
- **IMU layout:**
  - No pour under the package body; the GND pads are reached by traces (TN0018).
  - The local fan-out is pre-routed: GND vias above and below the package, a 3V3 rail under it joining VDDIO, VDD and the 3V3 pads of FB1, C14 and C15. The bottom-layer GND link runs in under the MCU.
  - OCS_Aux/SDO_Aux are tied to VDDIO (the datasheet allows this) to give CS a short path to VDD.
- **VDDA:** C6 and C7 are next to the VDDA pin; C9 (NRST) is after them.
- **Stitching:** vias now respect the long axis of the USB shell slots.
- **Docs:** PB6/PB7 (IMU 3.6 V limit) and NRST are marked 3.3 V only. I2C pull-ups must go to 3.3 V only. Also added: ENIG finish, plastic hardware under the screw heads, and the D+ back-feed behaviour when powered from J1.1.
- **Layout:** the MCU and its clock/decoupling group sit 0.25 mm left of centre, so fan-out vias fit between the MCU's right pads and the IMU/RESET column.

**Known limitations, not changed:**
- C13 (the USBLC6 VBUS decoupler) can't sit at U3's VBUS pin, because D+/D− box that pin in. The internal Zener still clamps.
- The C2 (VDD pin 24) ground return is long.
- No reverse-polarity protection or fuse on J1.1.
- The green user LED (InGaN at about 0.4 mA) is dim; R6 could drop to about 680 Ω.

**Verification** (KiCad 10.0.6): ERC 0 errors / 0 warnings; DRC 0 violations, 0 unconnected, 0 schematic-parity issues (`checks/`).

**Bring-up additions:** scan I2C1 (expect 0x6A); read WHO_AM_I (0Fh) and expect 0x70; enable tap detection on INT1 and check that A0 pulses; confirm that A0 is not driven from outside while INT1 is push-pull.

**Cost:** the LSM6DSV16X is a JLC Extended part, about $3.44 each or $2.47 each at 100, plus a loading fee. The other new parts are Basic: 4.7 kΩ (C25900), 100 nF (C1525).


## Reliability pass (2026-10-02)

This pass follows up the audit's known limitations and an STM32 best-practice audit (AN2586, AN4879, AN2867, DS5319; `tools/_work/audit_stm32/`). It adds a SPICE suite (`sim/`) and an emulated test firmware (`firmware/`).

**Power path**, now VBUS → R12 → D2 → VSYS → LDO, plus VSYS → F1 → Q1 → J1.1:

| Change | Why | Evidence |
|---|---|---|
| **R12 1 Ω 0805 anti-surge** (Yageo SR0805, 0.5 W) in series with VBUS | USB hot-plug ringing reached 6.1–11.4 V at LDO IN without it (abs max 6.0 V on the TLV755 then fitted) | SPICE bench 11: 5.38 V worst case over 8 cable/clamp corners; R12 pulse 13 W / 44 µJ, about 100 W rated. *(The fitted regulator is the TLV76733, 18 V; see the second review wave.)* |
| **C12 10 µF → 4.7 µF**; the 10 µF 3V3 bulk (C5) removed | USB inrush ≤ 50 µC | 33 µC as built |
| **F1 0.5 A PPTC (16 V) + Q1 DMP2165UW** on the J1.1 branch only | 5V-pin short (J1.1 is next to GND) or reversed supply | A short trips F1 while the MCU keeps running; Q1 blocks a reversed supply. *(Superseded: VSYS collapses during the trip and the MCU resets once. See the second-wave notes and the README.)* |
| **C4 (VDD3) 100 nF → 4.7 µF** | DS5319 Fig. 14: the 4.7 µF must be on VDD3 | — |
| **D+ pull-up from VBUS**: R2 2.2 kΩ + R11 4.7 kΩ (1.5 kΩ Thevenin to 3.4 V) | AN4879 §3.1.1: the pull-up must only be present with VBUS. This removes the J1.1 back-feed into the host. | — |
| **R6 1k5 → 330 Ω** | The user LED was dim at 0.4 mA | 1.32 mA typical, 0.95–1.79 mA across bins, PC13 limit 3 mA |

R12 costs headroom: LDO IN is 3.81 V at 250 mA from a 4.40 V hub port. 500 mA from 4.40 V is 8 mV into worst-case dropout, but that is beyond the 250 mA thermal budget anyway.

**Layout and routing**

- **Locked tracks:**
  - C13 now faces J2, with VBUS locked from U3 pin 5 through C13 to J2.A4.
  - The USB-C orientation ties are locked: VBUS B4–A9 and B9–A4, plus a B.Cu cross-link above the B row; D+ B6–A6 on B.Cu; D− A7–B7 on F.Cu.
  - The D+ pull-up's VBUS feed is locked.
  - The C2/IMU 3V3 feed is locked: from the LDO output cap down to C2, then on to the IMU's VDD loop.
  - The IMU's bottom GND pads have a short return to its decoupling caps.
- **GND vias** for R3 and VSS_2 (pin 35), which the new parts had boxed in.
- **`tools/stitch.py`:** stitching vias are now checked per fill island, and a via survives only if it joins islands anchored to real GND copper. KiCad treats a zone as a single item, so its own connectivity can't see a floating island pair. `tools/gndnet.py` reports GND clusters the same way.

**STM32 checklist** (no hardware change needed, documented in the README):
- PVD in firmware, since there is no BOR. Bench 3 shows a 200 mV window where VDD is below 2.0 V but not yet reset.
- CSS/HSE fallback.
- JTAG reset state of PA15/PB3/PB4.
- Injection limits: none allowed on PA4/PA5/PC13–15.
- A0's permanent 10 kΩ pull-down from INT1.
- I2C at 400 kHz is good up to about 75 pF.

**Simulation** (`sim/`, ngspice): every check passes except:
- **Margin:** 500 mA from 4.40 V; the PVD window above; crystal drive level, which depends on the OSC_IN swing (measure at bring-up); and a +17 dB VDDA LC peak at 288 kHz (a 1 Ω in series with C7 would fix it, but it is left as is).
- **Fail:** I2C at 400 kHz with 100 pF of bus capacitance.

**Firmware** (`firmware/`): bare-metal bring-up firmware, with its pin table generated from `spec.py`. A Renode model of the board (custom RCC and LSM6DSV16X peripherals) runs 10 Robot Framework tests:
- 72 MHz from HSE, and the HSI fallback when the HSE fails;
- the user LED;
- IMU WHO_AM_I, samples, tap/double-tap, and wake on INT1 → PA0;
- the generated pin map;
- a walk of every header GPIO, driven one at a time;
- input monitoring;
- NRST and software reset.

All 10 pass. Emulation proves the firmware and the pin map, not the silicon.

**Superseded "known limitations":**
- C13 now sits on the locked VBUS path.
- J1.1 has a fuse and reverse protection.
- The user LED is brighter.
- The C2 GND return was shortened in the audit round.


## Second review wave (2026-10-02)

Five independent reviewers re-checked the reliability-pass board (commit d48be23), one area each. They used the datasheets, the GCT drawing, JLC/LCSC data, the board's copper (traced with the pcbnew API), new SPICE benches and the firmware emulation.

| Area | Grade | Must-fix |
|---|---|---|
| Power / protection / SPICE | C+ | A live supply plugged onto J1.1 rings VSYS past the TLV755's 6.0 V absolute maximum (R12 isn't in that path) |
| MCU core / firmware | B | Emulation suite failing on a stale pin-map expectation; no VTOR, so `stm32flash -g` hangs |
| USB-C / ESD | B | VBUS_D runs under the shell's GND standoff dimples |
| IMU / GPIO / full use | B+ | The stale pin-map test above; nothing else |
| Fab / DFM / CPL | B+ | None. CPL, BOM and JLC limits verified, gerbers reproduce. |

**Fixed:**
- **U2: TLV75533 → TLV76733DRVR** (C2848334). It uses the same DRV0006A land pattern, and the CPL correction stays 0.
  - VIN and EN are rated to 18 V.
  - SNS is tied to OUT and pin 5 to GND (TLV767 Table 5-1).
  - It still regulates at 250 mA from a 4.40 V port.
  - New SPICE bench 12 covers J1.1 hot-plug and 1.5–3 µH USB cables.
- **C12** is now a 16 V X5R part (CL05A475MO5NUNC, C318563).
- **VBUS_D** hops to B.Cu between the shell legs. An F.Cu keep-out covers the dimples, so nothing else routes there.
- **IMU:** the pour keep-out grows to 3.5 × 3.0 mm, so the pour stays clear of the GND pads. The bottom GND via moves outside the package body, and the 3V3 rail moves 0.07 mm.
- **Stitching and repair vias** now keep off SMD pads (`stitch.py`, `fixroute.py`). This removes the via found in Y1's pad.
- **The router keeps out of the screw-head areas** (r 2 mm) and straightens its paths.
- **Firmware:**
  - VTOR is set first in `Reset_Handler`.
  - The clock comes up from HSI with the PLL off, then the PLL, flash wait states and ADC /6.
  - CSS has an NMI fallback to HSI, and PVD is set to 2.9 V.
  - New `standby` (WKUP on A0) and `adc` commands.
  - Pin-map test fixed; 10/10 pass.
- **Re-route:**
  - Net classes: signals are 0.127 mm with 0.127 mm clearance, GND and the 3V3 rails 0.2 mm (3V3 was 0.3 mm), and VBUS/VSYS/5 V stay 0.3 mm.
  - Seed 3 then routes 100% with Freerouting alone, so no hand-finished copper remains.
  - DRC 0/0/0 and ERC 0/0. One GND cluster; no via within 0.1 mm of any SMD pad.
  - Crystal nets unchanged (top layer, no vias).
- **Docs:**
  - The 5V-pin output is 4.2–4.4 V at 200 mA, and a J1.1 short resets the MCU once.
  - No battery on J1.1 while USB is plugged in.
  - The PC13–15 3 mA limit is a shared total.
  - I2C1/SPI1-remap (ES096), TIM4/USART1-remap and I2C1-remap conflicts.
  - Never set the IMU's `I2C_I3C_disable` bit.
  - The OCS_Aux/SDO_Aux ties and H4 distance corrected; pinout.csv regenerated.

**Not changed (accepted):**
- **USBLC6 on stubs, not flow-through.** ST's Fig. 7 calls this layout unsuitable. The stubs are about 1.5–2 mm, which adds tens of volts at IEC 8 kV edges. Flow-through needs D+ to swap layers next to U3, and there is no room for that via.
- **VDDA caps:** C6/C7's copper path is 8–9 mm with two vias, and the FB1/C7 LC filter has a +17 dB peak at 288 kHz. Rotating the caps would force PA1/PA2 onto vias at the 0.5 mm pin pitch.
- **J1.1 hot-plug with leads over 1 µH:** the most pessimistic capacitor model puts the ring past Q1's ±12 V gate rating. Documented: connect first, then switch the supply on. An extra series resistor would clear every corner, but there is no room for it.
- **R12 in a J1.1 short while on USB:** 7–13 W for about 0.1 s until F1 trips. That is probably survivable once (Yageo's 5 s overload qualification), but not verified for the ½ W part. Test at first article.
- **D+ during hot-plug:** the VBUS-derived pull-up can briefly put up to 4.2 V on D+ while the MCU is still unpowered (FT limit 4.0 V at VDD = 0) for a few µs, in 2 of 8 corners.
- **VTERM:** 3.0–3.6 V holds only for VBUS 4.40–5.28 V; at 5.5 V it reaches 3.75 V (PA12 is FT).
- **Hard-wired D+ pull-up:** firmware that doesn't use USB still shows a device at the host. Drive PA12 low to hide it.

## JLC order round (2026-10-02)

Uploading the v1.3 files to a real JLCPCB Economic PCBA order turned up five problems that no DRC or review had caught. All are fixed in the fab outputs; the copper is unchanged.

| JLC said | Cause | Fix |
|---|---|---|
| U4 "Standard Only" (unselectable on Economic PCBA) | JLC flags the LSM6DSV16X, C5267406, as "PCBA Type: Standard Only, X-ray Inspection Required". Almost every ST IMU it stocks has the same flag. | U4 is now the **LSM6DSV, C41785564** ("Economic and Standard"). See below. |
| "Multiple lines in the BOM have been matched to the same part" on R1/R8/R10, R4/R5, R7/R9/R11, SW1/SW2 | `fab.sh` grouped the BOM by value + footprint, so one LCSC part ended up on two lines (`_NoSilk` footprint variants; RESET/BOOT0 values) and JLC unselected both | The BOM is grouped by LCSC number: 26 lines, one per part |
| Headers and USB-C not assembled | The BOM left THT parts out for hand soldering | JLC assembles them (Economic PCBA includes wave-soldered THT). J1/J3 are HanElectricity 2541WV-2x10P, C5383109. |
| "Component may be offset from the PCB" | The CPL used the board's lower-left corner as its origin, while the Gerbers use KiCad's page coordinates, so every part sat 100 / 125.5 mm off the board | The CPL is written in the Gerber frame (kicad pos coordinates as exported). `fab.sh` asserts that every part lands inside the outline. |
| (preview) THT parts misplaced | JLC's footprints for the header (drawn horizontal, origin at the pad-array centre) and USB4085 (origin 2.975 / 2.180 mm from A1) differ from KiCad's | Per-LCSC rotation and origin corrections (`JLC_ROT`, `JLC_OFS`), read from the EasyEDA footprints |

**IMU swap.** LCSC's datasheet for C41785564 is ST's DS13476 (LSM6DSV). Checked against the board and firmware:
- **Pins:** all 14 have the same functions and mode-1 (I2C) connections as the LSM6DSV16X. SDx/SCx go to Vdd_IO or GND (tied to GND), OCS_Aux/SDO_Aux to Vdd_IO or unconnected (Vdd_IO), CS is high and SA0 low.
- **Registers:** every register the test firmware touches has the same address and bits, and WHO_AM_I is 0x70. That covers IF_CFG, CTRL1/2/3/6/8, ALL_INT_SRC, WAKE_UP_SRC, TAP_SRC, FUNCTIONS_ENABLE, TAP_CFG0–2, TAP_THS_6D, TAP_DUR, WAKE_UP_THS/DUR and MD1_CFG. The tap and wake LSB scaling is identical too.
- **SFLP:** game rotation vector in the FIFO (tag 0x13), SFLP_GAME_EN in EMB_FUNC_EN_A (04h) and SFLP_ODR (5Eh). Same as the LSM6DSV16X.
- **Lost:** the machine-learning core, Qvar and the analog hub. None is used: Qvar and the analog hub need pins 2/3, which are grounded.
- **JLC footprint:** "LGA-14 ...-TL", pin 1 top-left like KiCad's, so its CPL correction is 0°. The LSM6DSV16X's was "-BR", +180°.
- **Unverified:** ST's store lists only LSM6DSV and LSM6DSVTR as order codes. "LSM6DSVETR" is the JLC/LCSC code, so confirm WHO_AM_I and SFLP output on the first boards.
- **Cost:** about $6.14 each at JLC for 5, against about $3 for the LSM6DSV16X.

**Order settings used:** 5 boards, all 5 assembled, Economic PCBA top side, 1.6 mm, **ENIG with green mask**.
- On Economic PCBA, 1.6 mm ENIG is offered only with green.
- Black and white mask need 0.13 mm between pads to keep a mask bridge (0.10 mm for green), and the USB-C pads are 0.11 mm apart.
- JLC's quote was $134.47 before shipping.

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
| USB_D+ / USB_D− | v1.2 numbers; see the v1.3 section for the current board. Fine for 12 Mbit/s full speed; not an impedance-controlled pair. |
| VDDA | through the 0402 ferrite to 100 nF + 1 µF (v1.3 moves both next to the VDDA pin) |

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
4. **The USB-C connector and headers are hand-soldered** (through-hole). *(Superseded: JLC assembles them since the 2026-10-02 order round.)*
5. **First article:** short check; current-limited 5 V; measure 5V/3V3/VDDA; SWD attach and RESET button; HSE startup; USB enumeration in both orientations; BOOT+RESET into the USART1 bootloader; user LED; then the peripherals you need.
