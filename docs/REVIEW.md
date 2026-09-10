# PCB review and compact revision C — 2026-09-10

The working KiCad PCB is revision C. Revision B is preserved in `review/rev_b_snapshot/` and `fab/rev_b/`; the original design is in `review/original/`. The schematic and header pin assignments are unchanged from B.

## Result

| Item | Original | Revision B | Revision C |
|---|---:|---:|---:|
| Outline, Edge.Cuts centerlines | 53.5 × 41.7 mm | 38 × 39 mm | **34 × 33 mm** |
| Bounding rectangle area | 2230.95 mm² | 1482 mm² | **1122 mm²** |
| Header components, excluding USB | 8 | 2 | 2 |
| Different header footprints | 5 | 1 | 1 |
| M2 mounting holes | 4 | 4 | **4** |
| Routed track length, excluding vias | 1615.7 mm | 1142.4 mm | 1071.2 mm |

Revision C is **24.3% smaller than B** and **49.7% smaller than the original**, by bounding rectangle area. Both headers remain identical standard **2×10, 2.54 mm, vertical through-hole** parts. All 33 original GPIO/interface signals plus reset remain exposed. Header pin assignments are unchanged from B; the headers exchange physical sides.

## Placement changes in C

- Rotated the MCU 90° to put USB pins toward the connector and oscillator/analog pins toward the lower component group.
- Moved USB and the boot switch onto the top edge, with the regulator directly below the switch. Grouped its output tantalum and ceramic capacitors alongside it and placed the input capacitor beside its input pin.
- Placed each MCU supply decoupler by its corresponding supply pin. Grouped the crystal, load capacitors, reset capacitor and analog bypass capacitors below the MCU.
- Aligned the pull resistors as a compact group above the MCU, freeing its left-side escape routing. Grouped the power LED and its resistor on the right.
- Retained all four M2 holes. The lower pair is inside the header rows, eliminating the former bottom margin. Footprint courtyard checks pass, including the mounting-hole clearances.
- Rebuilt routing around the new placement, reserving short crystal/USB connections and supply paths first. Added ten ground stitching vias, including a dedicated connection for the VDDA bypass capacitor's ground island.
- Rebuilt the rear pin legends as aligned columns with explicit pin numbers; front labels identify both headers, RUN/BOOT and the power indicator.

Mounting centers measured from the outline's upper-left bounding corner, looking from the top (X right, Y down):

| Hole | X (mm) | Y (mm) |
|---|---:|---:|
| H1 | 3.0 | 2.8 |
| H2 | 31.0 | 2.8 |
| H3 | 10.0 | 30.0 |
| H4 | 24.5 | 30.0 |

These are revised mounting positions. Use the current board/drill data for mechanical design.

## Findings corrected

- Two incomplete ground thermals in the original board. Revision C has ground pours on both layers, direct ground connections at the USB connector and small SMD ground pads, header thermals, and ten ground stitching vias.
- USB shield was explicitly unconnected; it is now bonded to circuit ground. The connector remains the same GCT USB4085 footprint/pinout.
- PB2/BOOT1 was floating at reset. Added R8, 10k to GND, while keeping PB2 on the header. This makes the BOOT0 switch select flash or the system bootloader predictably unless external circuitry overrides PB2.
- C6 changed from 10nF to 100nF, retaining C7=1uF on VDDA, following ST's decoupling guidance.
- C12 changed from 22uF to 4.7uF on USB VBUS to reduce the directly connected input capacitance/inrush. This alone is not an inrush compliance measurement.
- C13 changed from ceramic 0805 to a polarized 22uF/10V solid-tantalum case-A footprint for the AMS1117 output. The exact capacitor MPN/ESR still needs selection; the previous ceramic supplier ID must not be reused.
- The MCU symbol previously identified an STM32F103C4 despite its C8 value. It now uses the C8 symbol and datasheet with the same physical pin mapping.
- Removed the mixed SMD/THT header assortment and misleading/colliding header labels. Rear silkscreen now lists all 40 pin numbers and GPIO names; front marks headers, RUN/BOOT and power LED.
- Short, locked crystal and USB routes were laid out before routing the remaining signals. Crystal routes have no vias. USB D+ has no vias; D− uses two for the short connector-side crossover. Total copper per net including contact ties/branches is 13.1 mm (D+) and 13.0 mm (D−); these are not endpoint-to-endpoint length-matching measurements. Crystal net totals are 3.9 mm and 12.0 mm.
- Power routing uses a 0.30 mm preferred width, with short 0.25 mm MCU decoupling connections. General signals use 0.15 mm and USB/crystal use 0.20 mm. Clearance remains 0.13 mm. Vias are 0.60/0.30 mm diameter/drill. The project minimum via diameter was changed accordingly, retaining 0.13 mm minimum annular ring. Silkscreen clearance was increased from 0 to 0.10 mm and the final board still passes.
- Bottom copper is correctly classified as a signal layer. Project-local library tables fix missing-library warnings. Existing trimmed USB/switch silkscreen geometry is stored explicitly in `pcb_hello_world.pretty`; copper/pad geometry was preserved.

## Verification

KiCad **10.0.4**, on the final saved board:

- ERC: **0 errors, 0 warnings** (`final-erc.rpt`).
- DRC, including all track errors, zone refill and schematic parity: **0 violations, 0 unconnected items, 0 parity issues** (`final-drc.json`).
- No DRC exclusions were added. Existing ERC ignored-check settings were retained and appear in the ERC report.
- Exported netlist compared pin-by-pin with the intended transformation: every retained circuit pin and every new header pin matched (`tools/check_netlist.py`).
- Front/back renders and copper plots visually inspected. The schematic is unchanged from revision B. The assembly drawing carries component references omitted from crowded front silkscreen.

These checks establish connectivity and geometric clearance. They do not establish signal integrity, ESD immunity, regulator stability under every load, USB compliance, or successful operation of an assembled prototype.

## Remaining design/bring-up items

1. **USB and CAN cannot operate simultaneously on this STM32F103.** They share packet RAM. The board supports using either interface; simultaneous operation requires an architectural change, not a reroute. CAN pins PB8/PB9 are 3.3V logic for an **external CAN transceiver**, not CANH/CANL, and need the appropriate firmware remap.
2. **The existing `.ioc` clock configuration is not ready for this 16MHz crystal/USB design.** It still records an HSI-derived 8MHz configuration. Configure HSE=16MHz and a valid 48MHz USB clock before testing USB. Firmware was not changed. BOOT selects the factory USART1 bootloader on this part; it does not add a factory USB DFU bootloader.
3. **Choose exact C12, C13 and Y1 parts before assembly.** Validate C13's ESR/stability with the actual AMS1117 manufacturer. Match Y1 load capacitance to the retained 10pF C0G capacitors, including pin/PCB parasitics. Previous supplier codes are carried over only where useful and are marked unvalidated.
4. **No external USB ESD protection or USB power current limiter is fitted.** Decide whether to add them for the intended handling/environment. The short two-layer USB route has not been designed against a fabricator-specific 90-ohm stackup or electrically compliance-tested; the bottom return copper is shared with GPIO routing. A clean DRC is not a USB compliance result.
5. **3V3 header pins are outputs when USB supplies the board.** There is no source selection or reverse-current protection. Do not connect another powered 3V3 source at the same time. Check regulator temperature and total USB current with the intended external load; do not infer an available 800mA header budget from the regulator nameplate.
6. **First article checks:** continuity/short check before power, current-limited 5V startup, 3V3/VDDA measurement, SWD attach/reset, oscillator startup, then USB enumeration in both cable orientations and the chosen peripheral tests. C13 is polarized; pad 1 is positive.

## Header pinout

Top view, USB at the top: **J3 is left, J1 is right** (opposite physical sides from revision B). Pin 1 is the square pad at the upper left of each header. Odd pins run down the left column and even pins down the right. The back-side legend uses explicit pin numbers; do not reinterpret it as a top-view pin drawing.

| Pin | J1 | J3 |
|---:|---|---|
| 1 | 3V3 regulated output | 3V3 regulated output |
| 2 | GND | GND |
| 3 | PC13 | PB8 / CAN RX logic |
| 4 | PC14 | PB9 / CAN TX logic |
| 5 | PC15 | PB6 / I2C SCL |
| 6 | NRST / reset | PB7 / I2C SDA |
| 7 | PA0 | PB5 |
| 8 | PA1 | PB4 |
| 9 | PA2 | PB3 |
| 10 | PA3 | PA15 |
| 11 | PA4 | PA14 / SWCLK |
| 12 | PA5 / SPI SCK | PA13 / SWDIO |
| 13 | PA6 / SPI MISO | PA9 / UART TX |
| 14 | PA7 / SPI MOSI | PA10 / UART RX |
| 15 | PB0 | PA8 |
| 16 | PB1 | PB15 |
| 17 | PB2 / BOOT1 (10k pull-down) | PB14 |
| 18 | PB10 | PB13 |
| 19 | PB11 | PB12 |
| 20 | GND | GND |

For SWD connect J3.11=SWCLK, J3.12=SWDIO, J3.1=target voltage reference, and J3.2 or J3.20=GND. Reset is J1.6. Do not use a debugger's powered supply output as the target-voltage sense connection when USB is powering the board.

`pinout.csv` also maps each new signal to its original header pin(s).

## Deliverables

- Root `.kicad_pcb`, `.kicad_sch`, `.kicad_pro`: current revision.
- `top.png`, `bottom.png`: current visual previews.
- `schematic.pdf`, `assembly.pdf`, `copper.pdf`: review drawings.
- `../fab/rev_c/`: refreshed Gerbers, separate plated/non-plated drill files, BOM and SMD placement CSV. Placement rotations and component sourcing require assembler review.
- `original/`: original design and old fabrication package.
- `tools/`: scripts used during the revision, kept as an audit trail; intermediate scripts are not a one-command rebuild pipeline. Running the placement scripts again intentionally discards routing.

## Reference documents

- [ST AN2586: STM32F10xxx hardware design, decoupling and boot configuration](https://www.st.com/resource/en/application_note/an2586-getting-started-with-stm32f10xxx-hardware-development-stmicroelectronics.pdf).
- [ST STM32F103x8/xB datasheet](https://www.st.com/resource/en/datasheet/stm32f103c8.pdf).
- [ST AN4879: USB hardware and PCB guidelines, including USB/CAN shared-memory limitation](https://www.st.com/resource/en/application_note/DM00296349-.pdf).
- [AMS1117 manufacturer datasheet](http://www.advanced-monolithic.com/pdf/ds1117.pdf). Manufacturer site was unavailable during this review; final capacitor sourcing remains explicitly open. A distributor-hosted manufacturer datasheet was also consulted.
- [TI USB peripheral VBUS capacitance guidance](https://e2e.ti.com/support/processors-group/processors/f/processors-forum/1041212/amic110-usb-peripheral-design-guide).
- [C&K PCM12 slide-switch datasheet](https://www.ckswitches.com/media/1424/pcm.pdf).
