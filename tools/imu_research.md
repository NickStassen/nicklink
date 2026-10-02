# LSM6DSV16X IMU: parts research for NickLink (STM32F103, 3.3 V, I2C1)

Main source: ST datasheet **DS13510 Rev 4 (May 2023)**. I pulled it from LCSC's mirror because st.com timed out from this machine:
https://datasheet.lcsc.com/datasheet/pdf/7d66556bb254f99e058243c7371e051d.pdf?productCode=C5267406
(the canonical copy is https://www.st.com/resource/en/datasheet/lsm6dsv16x.pdf). Page numbers below refer to DS13510.

The datasheet gives the package as **2.5 x 3.0 x 0.86 mm** (Figure 33, p.172). That is 0.86 mm, not the 0.83 mm in the brief.

## 1. Pinout (Table 2, p.11; Figure 5, p.9)

| Pin | Name | Mode 1 function (no aux sensors) |
|---|---|---|
| 1 | SDO/SA0 | I2C address LSB (SA0) / SPI SDO |
| 2 | SDx/AH1/Qvar1 | "Connect to Vdd_IO or GND if the analog hub and Qvar are disabled." |
| 3 | SCx/AH2/Qvar2 | "Connect to Vdd_IO or GND if the analog hub and Qvar are disabled." |
| 4 | INT1 | Programmable interrupt |
| 5 | Vdd_IO | I/O supply, footnote: "Recommended 100 nF filter capacitor." |
| 6 | GND | 0 V |
| 7 | GND | 0 V |
| 8 | Vdd | Core supply, footnote: "Recommended 100 nF filter capacitor." |
| 9 | INT2 | Programmable interrupt 2 / DEN |
| 10 | OCS_Aux | "Connect to Vdd_IO or leave unconnected" (footnote: "Leave pin electrically unconnected and soldered to PCB.") |
| 11 | SDO_Aux | "Connect to Vdd_IO or leave unconnected" (same footnote) |
| 12 | CS | "1: SPI idle mode / I2C / MIPI I3C communication enabled; 0: SPI communication mode / I2C / MIPI I3C disabled" |
| 13 | SCL | I2C SCL / SPI SPC |
| 14 | SDA | I2C SDA / SPI SDI / 3-wire SDO |

**The KiCad `Sensor_Motion:LSM6DSM` symbol can be reused.** I read its pins in the KiCad 10 docker image: 1 SDO/SA0, 2 SDX, 3 SCX, 4 INT1, 5 VDDIO, 6 GND, 7 GND, 8 VDD, 9 INT2, 10 OCS_Aux, 11 SDO_Aux, 12 CS, 13 SCL, 14 SDA. Every number matches Table 2 above. The names differ only cosmetically (SDX for SDx/AH1/Qvar1, SCX for SCx/AH2/Qvar2). Its default footprint is `Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y`.

One electrical difference: the LSM6DSM symbol types pin 7 GND as `passive`, while pin 6 is `power_in`. This only affects ERC.

## 2. I2C-mode connections

- **CS (pin 12): tie to Vdd_IO (+3.3V).** CS = 1 enables I2C. CS does have a default internal pull-up (Table 23, p.50: "Default: input with pull-up", which is disabled only when I2C_I3C_disable = 1). I still recommend a hard tie, because a floating CS could drop the part into SPI mode. Figure 28 (p.47) shows the mode-1 I2C hookup.
- **SDO/SA0 (pin 1): address select.** Confirmed (sec. 5.1.2, p.22): "If the SDO/SA0 pin is connected to the supply voltage, LSb is 1 (address 1101011b); else if the SDO/SA0 pin is connected to ground, the LSb value is 0 (address 1101010b)."
  - SA0 = GND gives **0x6A**; SA0 = Vdd_IO gives **0x6B**. In 8-bit form these are D4h/D5h and D6h/D7h (Table 12).
  - SA0 has **no** pull-up by default (SDO_PU_EN = 0), so it must be strapped. **Recommendation: SA0 to GND (0x6A).**
- **SDx / SCx (pins 2, 3): tie to GND or Vdd_IO. Do not leave them floating.** This differs from the LSM6DSM/DSOX habit of floating them. **Recommendation: GND.** This also suits the LSM6DSOX, whose datasheet says "Connect to VDDIO or GND".
- **OCS_Aux / SDO_Aux (pins 10, 11): leave unconnected (pads soldered).** In modes 1 and 2 both have internal pull-ups by default. Table 23 note: "Pull-up is disabled if bit OIS_PU_DIS = 1 in register PIN_CTRL (02h)". Figure 28 draws them as NC.
- **INT2 (pin 9): leave unconnected.** It is an output that is "forced to ground" by default (Table 23), so it never floats. Optionally route it to a spare GPIO or test pad.

## 3. Decoupling and supply

- Datasheet (p.47): "Power supply decoupling capacitors (C1, C2 = 100 nF ceramic) should be placed as near as possible to the supply pin of the device."
  - Fit **one 100 nF on Vdd (pin 8) and one 100 nF on Vdd_IO (pin 5)**.
  - Place each right at its pin and return it to pins 6/7 GND by the shortest path.
  - Part: JLC Basic **C1525** (Samsung CL05B104KO5NNNC, 100 nF 16 V X7R 0402), https://jlcpcb.com/partdetail/C1525
- **Sharing one 3.3 V rail is fine.** Table 4 (p.14) gives Vdd 1.71 to 3.6 V and Vdd_IO 1.08 to 3.6 V. Searching the datasheet turned up no sequencing or "Vdd_IO ≤ Vdd" rule. Keep the two separate 100 nF caps anyway.
- Optional: many boards add 1 µF bulk on the shared rail. ST does not require it. This is my suggestion only.

## 4. I2C pull-ups

- Datasheet (p.21): "Both the lines must be connected to Vdd_IO through external pull-up resistors."
  - Figure 28 shows "Pull-up to be added, Rpu=10kOhm".
  - The I2C interface supports fast mode (400 kHz) and fast mode plus (1 MHz).
- **4.7 kΩ is confirmed as a good choice.** My arithmetic, not from ST:
  - Fast-mode rise time is ≤ 300 ns, and t_r ≈ 0.85·R·C. With 4.7 kΩ that allows about **75 pF** of bus capacitance.
  - A short on-board bus is about 10 to 30 pF, so there is room for 1 or 2 short-lead modules.
  - Minimum R for 3 mA at V_OL 0.4 V: (3.3 − 0.4)/3 mA ≈ **1 kΩ**.
  - Most breakout modules carry their own 4.7k or 10k pull-ups, which sit in parallel and lower the total. Check that the parallel total stays ≥ about 1.5 kΩ.
  - Drop to 2.2 kΩ only if the bus capacitance exceeds about 75 pF, for example long cables.
- Part: JLC **Basic C25900** (UNI-ROYAL 0402WGF4701TCE, 4.7 kΩ ±1%, 0402, 62.5 mW). LCSC shows 10.1 M in stock at about $0.002 each. https://jlcpcb.com/partdetail/C25900
- **Internal pull-ups on the IMU** (Table 23 p.50, Tables 28/30 p.57-58; internal value 30 to 50 kΩ):

  | Pin | Default | Control |
  |---|---|---|
  | SDA | off | SDA_PU_EN, IF_CFG (03h) bit 7, default 0 |
  | SCL | none | not configurable |
  | SA0 | off | SDO_PU_EN, PIN_CTRL (02h), default 0 |
  | CS | on | removed only by I2C_I3C_disable = 1 |
  | OCS_Aux, SDO_Aux | on | OIS_PU_DIS = 1 in PIN_CTRL (02h) disables them |
  | SDx, SCx | off | SHUB_PU_EN, IF_CFG |

  Nothing needs changing for this design.

## 5. INT1 output

- From IF_CFG (03h), Table 30 p.58:
  - **PP_OD (bit 3): 0 = push-pull (default), 1 = open-drain.** Applies to INT1 and INT2.
  - **H_LACTIVE (bit 4): 0 = active high (default), 1 = active low.**
- Before configuration INT1 is "output forced to ground" (Table 23).
- So the default is **push-pull, active-high**: no pull-up needed, and the MCU uses a rising-edge EXTI.
- IF_CFG is not reset by a software reset.
- PA0 is also the STM32F103 WKUP pin (rising edge). It pairs naturally with an active-high INT1 for wake from Standby.

## 6. PCB layout (ST TN0018 and the ST community article)

I could not download TN0018 itself: st.com timed out and Mouser served a bot-check page. The rules below come from TN0018 excerpts quoted in search results and from ST's article https://community.st.com/t5/mems-and-sensors/how-to-optimize-your-pcb-design-for-mems-sensors/ta-p/605083. TN0018 links: https://www.st.com/resource/en/technical_note/tn0018-surface-mounting-guidelines-for-mems-sensors-in-an-lga-package-stmicroelectronics.pdf (Mouser mirror: https://www.mouser.com/pdfDocs/tn0018-surface-mounting-guidelines-for-mems-sensors-in-an-lga-package-stmicroelectronics.pdf).

Actionable rules:
- **Keep traces, vias and copper pours off the top layer under the package** (ST article: "Never place any routing or via on the top side under the device"; TN0018: "no vias or traces below the sensor footprint"). For accelerometers and gyros, ST allows a power plane or signal routing on the bottom side.
- **Route symmetrically.** Traces should leave each pad outward, parallel to the pad's long edge, all at the same width. Connect GND pads with normal traces, not by flooding pour into the pad.
- **All lands the same size.** TN0018 rule when the gap between pins is > 200 µm: land = package pin + 0.1 mm in each dimension. Package pins are 0.475 x 0.25 mm (Figure 33), so the target land is **0.575 x 0.35 mm**.
  - The KiCad footprint pads are 0.625 x 0.35 mm, 0.05 mm longer than the TN0018 figure. Fine for JLC; trim them if you want an exact TN0018 match.
- **Soldermask: NSMD.** The mask opening is the land + 0.1 mm, and ST recommends opening the mask outside the land. KiCad's default mask expansion is close to this; at JLC a 0.5 mm pitch can lose the web between pads, which is acceptable.
- **Keep away from mechanical stress and heat:**
  - Avoid screws, mounting holes, standoffs, connectors and push-buttons, and keep away from board protrusions and flex points. ST article: keep "at least 10 mm away from the source of the external force", and place the sensor between fasteners.
  - Keep away from heat sources: the LDO, MCU hot spots, any battery.
- **Do not let anything touch the package.** No epoxy, potting, heat sink or shield in contact. Side solder fillets are not allowed: LGA packages have metal traces on their sides.
- **Unverified, quoted from memory of TN0018 rather than read:** stencil about 100 to 127 µm with apertures 1:1 to the lands; no specific board-edge distance in mm. Get TN0018 manually if you need exact figures.

## 7. JLCPCB / LCSC

LCSC API figures were queried on 2026-10-01 (https://wmsc.lcsc.com/ftps/wm/product/detail?productCode=...). Library type comes from the jlcpcb.com part pages.

| Part | C-number | Package | LCSC stock | Price (1 / 10 / 100) | JLC type |
|---|---|---|---|---|---|
| **LSM6DSV16XTR** | **C5267406** | LGA-14 (2.5x3) | 6,187 | $3.44 / $2.99 / $2.47 | **Extended** (verified) |
| LSM6DSOXTR (fallback) | C481766 | LGA-14 (2.5x3) | 4,456 | $3.92 / $3.41 / $2.79 | page did not state the type; **Extended assumed (unverified)** |
| LSM6DSOTR (fallback) | C2655100 | LGA-14 (2.5x3) | 4,761 | $3.92 / $3.38 / $2.52 | **Extended** (verified) |
| 4.7 kΩ 1% 0402 | C25900 | 0402 | 10.1 M | about $0.002 | **Basic** (verified) |
| 100 nF X7R 0402 | C1525 | 0402 | (not shown) | | **Basic** (verified) |

The JLC pages for C481766 and C2655100 note MSL 3 and X-ray inspection. Extended parts add the usual per-unique-part setup fee.

Links: https://jlcpcb.com/partdetail/STMicroelectronics-LSM6DSV16XTR/C5267406 · https://www.lcsc.com/product-detail/C5267406.html · https://jlcpcb.com/partdetail/STMicroelectronics-LSM6DSOXTR/C481766 · https://jlcpcb.com/partdetail/STMicroelectronics-LSM6DSOTR/C2655100

**The fallbacks drop in with no netlist change.** I checked the LSM6DSOX datasheet (DS12814 Rev 3, from LCSC): it has the same 14-pin assignment, SDx/SCx "Connect to VDDIO or GND", and OCS_Aux "Leave unconnected". The DSOX/DSO register maps differ, though; for example their INT pin config bits live in CTRL3_C, not IF_CFG. They are therefore not a firmware drop-in.

## 8. KiCad 10 library

Checked in the `kicad/kicad:10.0` docker image.

- **There is no LSM6DSV16X symbol.** `Sensor_Motion` holds only LSM6DS3, LSM6DSL and LSM6DSM.
  - **Use `Sensor_Motion:LSM6DSM` with Value = LSM6DSV16X** (pin numbers verified in section 1).
  - Change its Datasheet field to the DS13510 URL.
- **Footprint: `Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y`**, the symbol's default.
  - Its 14 pads run 1–4 down the left (3 mm side), 5–7 along the bottom, 8–11 up the right, and 12–14 along the top, matching ST's numbering.
  - Do not use `Bosch_LGA-14_3x2.5mm_P0.5mm`, which has a different pin arrangement.
- A JLC 3D model or rotation check is still needed at CPL time. Not verified.

## 9. Firmware notes

- **SFLP game rotation vector:**
  - The on-chip sensor fusion low-power (SFLP) block produces a 6-axis game rotation vector (quaternion), plus gravity vector and gyro bias.
  - Enable it with SFLP_GAME_EN in EMB_FUNC_EN_A (04h, embedded-function bank).
  - Set the rate in SFLP_ODR (5Eh, embedded bank): 15/30/60/**120 (default)**/240/**480 Hz max** (Table 324).
  - The quaternion is delivered **only through the FIFO** ("The X, Y, Z quaternion components are stored in FIFO", p.2; FIFO tag 0x13). Enable SFLP_GAME_FIFO_EN, read X/Y/Z as half-floats, and compute W from them.
  - 480 Hz of FIFO words is easy at 400 kHz I2C.
- **Tap and wake-up on INT1:**
  - Single-tap, double-tap, wake-up, free-fall, 6D and activity/inactivity all route to INT1 through MD1_CFG (5Eh, main bank): INT1_SINGLE_TAP, INT1_DOUBLE_TAP, INT1_WU, INT1_FF, INT1_6D, INT1_SLEEP_CHANGE.
  - They require **INTERRUPTS_ENABLE = 1 in FUNCTIONS_ENABLE (50h)**.
  - INT1_CTRL (0Dh) covers data-ready and FIFO interrupts.
- **Driver:** ST's `lsm6dsv16x-pid` C driver (STMicroelectronics GitHub `STMems_Standard_C_drivers`) covers all of this. I am citing it from knowledge; I did not fetch it.
- **STM32F103 I2C:** the I2C peripheral has known errata (BUSY-flag lock-up after a reset mid-transfer). Add a bus-recovery routine that toggles SCL 9 times as GPIO.

## Recommended connection list

| Pin | Name | Net |
|---|---|---|
| 1 | SDO/SA0 | GND (address 0x6A) |
| 2 | SDx | GND |
| 3 | SCx | GND |
| 4 | INT1 | IMU_INT1 to PA0 (push-pull, active-high default; no pull-up) |
| 5 | Vdd_IO | +3.3V, with its own 100 nF (C1525) at the pin |
| 6 | GND | GND |
| 7 | GND | GND |
| 8 | Vdd | +3.3V, with its own 100 nF (C1525) at the pin |
| 9 | INT2 | NC (optional test pad or spare GPIO) |
| 10 | OCS_Aux | NC (pad soldered) |
| 11 | SDO_Aux | NC (pad soldered) |
| 12 | CS | +3.3V (hard tie, selects I2C) |
| 13 | SCL | I2C1_SCL to PB6, 4.7 kΩ (C25900) to +3.3V |
| 14 | SDA | I2C1_SDA to PB7, 4.7 kΩ (C25900) to +3.3V |

Fit one pull-up pair per bus, not per device.
