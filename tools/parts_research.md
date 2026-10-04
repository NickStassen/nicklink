> **As built (v1.3). Order from `fabrication/v1.3/nicklink_BOM_JLC.csv`, not from the v1.2 study below.**
>
> - **U2:** TI TLV76733DRVR, LCSC **C2848334**. Same WSON-6 land as the TLV755 in section 1, but pin 2 is SNS (tied to OUT) and pin 5 is GND, not NC. VIN/EN absolute maximum is **18 V**, not 6.0 V. Do not order TLV75533PDRVR C2861750.
> - **C12:** 4.7 µF 16 V 0402, Samsung CL05A475MO5NUNC, LCSC **C318563**. Not 10 µF 0603 C19702.
> - **R6:** 330 Ω (C25104), about 1.3 mA. Not 1.5 kΩ and not 1 kΩ. The green LED is brighter than the 0.4 mA note this file used to give.
> - **U4:** ST LSM6DSV, C41785564, on I2C1 (PB6/PB7), address 0x6A. Not the LSM6DSV16X.
> - **J1, J3:** HanElectricity 2541WV-2x10P, C5383109. **J2:** GCT USB4085, C7095263. All three are in the CPL. JLC assembles them. Do not plan to hand-solder them.
> - **LEDs:** Everlight 16-213 red C264407 and green C74338, both 0402. The 0603 KENTO notes below are the v1.2 study.

# NickLink parts research

Researched 2026-10-01 for v1.2. The body still records that study. Where it names TLV75533PDRVR, a 10 µF 0603 input cap, or a 1.5 kΩ user-LED resistor as the part to fit, that choice was superseded by the list above.

**How LCSC numbers were checked:** each C-number was looked up in JLCPCB's own parts-search backend (the `selectSmtComponentList` API behind jlcpcb.com/parts). That lookup returns the MPN, manufacturer, package, library type (`base` = Basic, `expand` = Extended), the "preferred" flag and stock. Stock figures are from 2026-10-01. Spot checks on lcsc.com product pages (C51118, C82942, C7519, C191023, C231329) agreed. Datasheets came from LCSC's datasheet links or from the manufacturers.

Per-part pages: `https://jlcpcb.com/partdetail/<C-number>` and `https://www.lcsc.com/product-detail/<C-number>.html`.

**v1.2 change from the lead (superseded for the LDO):** v1.2 used **TI TLV75533PDRVR (WSON-6 2x2)**. The fitted v1.3 regulator is **TI TLV76733DRVR, C2848334** (see the banner). The ESD part **ST USBLC6-2P6 (SOT-666)** is still fitted. AP2112K and USBLC6-2SC6 were fallbacks only.

## Summary table

| # | Function | Chosen MPN | LCSC | JLC lib | Verified | Key datasheet facts |
|---|---|---|---|---|---|---|
| 1 | 3V3 LDO, as built | TI **TLV76733DRVR** (WSON-6-EP 2x2) | **C2848334** | Extended | Pinout checked on the v1.3 schematic | Pins: 1 OUT, 2 SNS (tied to OUT), 3 GND, 4 EN, 5 GND, 6 IN, pad = GND. VIN/EN absolute max **18 V**. Replaces TLV75533PDRVR C2861750 (6.0 V abs max), which section 1 studied for v1.2. Do not order C2861750. |
| 1b | LDO fallback | Diodes AP2112K-3.3TRG1 (SOT-25) | C51118 | Extended | Yes | Pins 1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT. 1 µF ceramic X5R/X7R in and out. Dropout at 600 mA: 250 typ / 400 max mV. θJA 184 °C/W. VIN up to 6.0 V recommended, 6.5 V absolute max. |
| 2 | USB ESD | ST **USBLC6-2P6** (SOT-666) | **C15999** (genuine ST, 2.9k stock). C2827693 is the TECH PUBLIC second source (46k stock). | Extended | Yes | Pins: 1 I/O1, 2 GND, 3 I/O2, 4 I/O2, 5 VBUS, 6 I/O1. Same pinout as SC6. 3.5 pF max line capacitance, VRM 5.25 V. |
| 2b | ESD fallback | ST USBLC6-2SC6 (SOT-23-6L) | C7519 | Extended | Yes | Same die and pinout. |
| 3 | VBUS→+5V Schottky | Hottech **1N5819WS** (SOD-323) | **C191023** | **Basic** | Yes (4.9M stock) | 40 V, 1 A rated. VF ≈ 0.30 V at 100 mA and ≈ 0.37 V at 500 mA (typ curve, 25 °C), 0.60 V max at 1 A. Pd 250 mW at 25 °C, derated to 0 at 125 °C. IR 0.5 mA max at 40 V. |
| 4 | Reset/boot switch | Omron **B3U-1000P** | **C231329** | Extended | Yes (142k stock, $0.19) | Omron PCB pads at ±1.7 mm centres, 0.8 x 1.7 mm. KiCad `SW_SPST_B3U-1000P` uses ±1.7 mm, 0.9 x 1.7 mm, so it matches. |
| 4b | Cheaper switch | hanxia HX-B3U-1000P-1.6N | C49234121 | Extended | MPN/stock yes; **footprint not verified (no datasheet on JLC/LCSC)** | $0.08 vs $0.19. Also extended, so it saves no setup fee. Not recommended. |
| 5 | 8 MHz crystal | YXC **X32258MOB4SI** (YSX321SL, SMD3225-4P) | **C2682775** | Extended | Yes (83k stock) | CL 12 pF, ESR 150 Ω max (datasheet; the JLC listing says 180 Ω), C0 ≤3 pF, C1 ≤5 fF, ±10/±20 ppm, drive level 100 µW. Crystal sits on pads 1–3, pads 2 and 4 are GND. |
| 5c | Crystal load caps | FH 0402CG150J500NT, **15 pF** C0G 50 V 0402 | **C1548** | **Basic** | Yes | Alternative: 18 pF C1549 (Basic). |
| 6r | Red LED, as built | Everlight 16-213/R6C-AQ2R2B/3T (0402) | **C264407** | Extended | On the v1.3 BOM | Power LED, with R3 1.5 kΩ. The KENTO 0603 C2286 notes in section 6 are the v1.2 study. |
| 6g | Green LED, as built | Everlight 16-213/GHC-YR1S1/3T (0402) | **C74338** | Extended | On the v1.3 BOM | User LED on PC13. R6 is **330 Ω (C25104)**, about 1.3 mA, not 1.5 kΩ or 1 kΩ. The KENTO 0603 C12624 notes in section 6 are the v1.2 study. |
| 7 | Ferrite bead | Murata **BLM15AG121SN1D** (0402) | **C85812** | Extended (no 0402 bead exists in JLC Basic) | Yes | 120 Ω ±25% at 100 MHz, 550 mA rated, 0.19 Ω max DCR. The Basic option is 0603 BLM18PG121SN1D **C14709** (120 Ω, 2 A, 0.05 Ω). |
| 8 | 100 nF 0402 X7R 16 V | Samsung CL05B104KO5NNNC | **C1525** | **Basic** | Yes | |
| 8 | 1 µF 0402 | Samsung CL05A105KA5NQNC (X5R **25 V**) | **C52923** | **Basic** | Yes | The 10 V version (CL05A105KP5NNNC, C14445) is Extended. 25 V is the better choice anyway. |
| 8 | 10 µF 0603 X5R 10 V | Samsung CL10A106KP8NNNC | **C19702** | **Basic** | Yes | **Not fitted.** v1.2 study only. C12 is 4.7 µF 16 V 0402, Samsung CL05A475MO5NUNC, **C318563**. |
| 8 | 10 kΩ 0402 1% | UNI-ROYAL 0402WGF1002TCE | **C25744** | **Basic** | Yes | |
| 8 | 5.1 kΩ 0402 1% | UNI-ROYAL 0402WGF5101TCE | **C25905** | **Basic** | Yes | |
| 8 | 1.5 kΩ 0402 1% | UNI-ROYAL 0402WGF1501TCE | **C25867** | **Basic** | Yes | |
| 9 | MCU | ST STM32F103C8T6 (LQFP-48) | C8734 | Extended, **Preferred** (no loading fee) | Yes (150k stock) | See section 9. |
| 10 | USB-C | GCT **USB4085-GF-A** | **C7095263** | Extended (JLC lists it as "Plugin", i.e. THT) | Yes (3.6k stock, $1.40) | Through-hole, right-angle USB 2.0 Type-C receptacle, 16 pins. JLC assembles it (Economic PCBA, wave soldered). Its EasyEDA footprint origin is 2.975 / 2.180 mm from pad A1 (`JLC_OFS` in `tools/fab.sh`). |
| 11 | 2x10 headers (J1, J3) | HanElectricity **2541WV-2x10P** | **C5383109** | Extended ("Plugin") | Yes (4.6k stock, $0.07) | Male, vertical, 2.54 mm, 6 mm pins, 3 mm tail, gold. JLC assembles them. Same EasyEDA footprint (horizontal, origin at the pad centre: -90° and a centring offset in the CPL) as hanxia HX PZ2.54-2x10P ZZ, C42372518 (10k stock), the second source. |
| 12 | IMU (U4), as built | ST **LSM6DSV** (JLC/LCSC code LSM6DSVETR) | **C41785564** | Extended, **Economic and Standard** | Yes (979 stock, ~$6.14 at qty 5) | Replaces the LSM6DSV16X C5267406, which JLC lists as Standard PCBA only. Same pinout, registers, WHO_AM_I and SFLP; see docs/REVIEW.md, JLC order round. EasyEDA footprint "-TL" (pin 1 top-left): CPL correction 0°. |

## Key numbers

- **3V3 load budget (v1.2 study of the TLV75533PDRVR, not the fitted TLV76733; 40 °C ambient, Tj ≤ 100 °C, so ΔT = 60 K):**
  - With TI's JEDEC 2s2p (4-layer) RθJA of 100.2 °C/W, the LDO can dissipate 0.60 W. That allows **428 mA at VIN = 4.7 V**, or 352 mA at VIN = 5.0 V (a hot VBUS).
  - A small 2-layer board will be worse. At an estimated ~150 °C/W (**my estimate, not verified**) the limits are 286 mA at 4.7 V and 235 mA at 5.0 V.
  - **Recommended continuous 3V3 budget: 250 mA total**, including the MCU (~50 mA at 72 MHz with peripherals on). Up to ~400 mA is reasonable if the EP has vias into solid GND copper on both layers.
  - The AP2112K fallback (184 °C/W) allows 233 mA at 4.7 V and 192 mA at 5.0 V, so its budget is **~200 mA**.
- **Crystal:** X32258MOB4SI (C2682775), CL = 12 pF.
  - C = 2·(12 − Cs) gives 18/16/14 pF for Cs = 3/4/5 pF. **Use 15 pF C0G (C1548, Basic).** That gives an effective CL of 10.5–12.5 pF. Pulling is about 11 ppm/pF (C1 = 5 fF), so the error is ≤ ~15 ppm. USB full speed tolerates ±2500 ppm.
  - Gain margin: gm_crit = 4·ESR·(2πf)²·(C0+CL)² = 4·150·(2π·8 MHz)²·(15 pF)² = **0.34 mA/V**. The F103 HSE gm is **25 mA/V min**, so the **gain margin is ≈73**, far above AN2867's minimum of 5. Using the JLC-listed 180 Ω ESR still gives 61.
  - A 20 pF crystal (X32258MSB4SI, C2682774) would need 30–34 pF caps and has a margin of ≈31. The 12 pF part is better.
  - Note: DS5319 suggests "10 pF … rough estimate of combined pin and board capacitance". Taken literally, that would mean ~4 pF caps. I followed your 3–5 pF stray (per-pin Cin(HSE) is 5 pF, so the lumped value across the crystal is ~3–4 pF). If a measured HSE runs fast, go to 18 pF (C1549).
- **LEDs at 1.5 kΩ from 3.3 V (v1.2 resistor value; fitted R6 is 330 Ω):**
  - Red: (3.3 − 1.85)/1.5k = **0.97 mA**, roughly 7–15 mcd.
  - Green: (3.3 − 2.4)/1.5k = **0.60 mA** (0.47 mA in the highest VF bin). Scaling the 210–430 mcd at 5 mA rating gives roughly 25–50 mcd. That is clearly visible, and in fact **brighter than the red**. No resistor change is needed for visibility.
  - If you want the two to look equally bright, use 5.1 kΩ on the green (≈0.2 mA, and it reuses an existing BOM line).
- **5 V-tolerant (FT) pins on LQFP-48 (DS5319 Rev 18, Table 5):**
  - **FT:** PA8, PA9, PA10, PA11, PA12, PA13, PA14, PA15, PB2, PB3, PB4, PB6, PB7, PB8, PB9, PB10, PB11, PB12, PB13, PB14, PB15.
  - **Not FT:** PA0–PA7, PB0, PB1, **PB5**, PC13, PC14, PC15.

## 1. LDO: TLV75533PDRVR (v1.2 study, not fitted)

**TLV75533PDRVR, C2861750** (TI, WSON-6-EP(2x2), Extended, 16,284 in stock, $0.28).
Source: https://www.ti.com/lit/ds/symlink/tlv755p.pdf (SBVS320D, Sept 2024)

- **Pinout (Table 4-1, DRV column):** OUT = 1, NC = 2 and 5, GND = 3, EN = 4, IN = 6, thermal pad internally connected to GND ("connect to a large-area ground plane"). This matches the lead's mapping.
  - The KiCad `Package_SON:WSON-6-1EP_2x2mm_P0.65mm_EP1x1.6mm` footprint numbers pads 1–3 down the left side, 4–6 up the right side, and pad 7 is the 1.0 x 1.6 mm EP. Its description references the same TI DRV package.
  - Watch out: the KiCad footprint also has two unnumbered paste-only pads on the EP. That is normal.
- **Capacitors:** CIN 1 µF min and COUT 1 µF min (Recommended Operating Conditions). The footnote requires >0.47 µF effective at the pin, assuming 50% derating. COUT max is 200 µF. Use X5R/X7R ceramic (7.1.1).
  - A 1 µF 0402 25 V X5R (C52923) at 3.3 V keeps roughly 0.5–0.7 µF after DC bias. That is borderline for this TLV755 study, which suggested **10 µF 0603 (C19702) or 2x 1 µF on OUT, and ≥1 µF on IN.** That 10 µF part is not on the v1.3 board. C12 is 4.7 µF 16 V 0402, C318563, and C8 (LDO output) is 1 µF, C52923.
- **Dropout (3.3 V ≤ VOUT < 5 V, 500 mA):** 150 typ / 215 max mV from −40 to 85 °C, 238 mV max from −40 to 125 °C. At 4.7 V in there is about 1.2 V of headroom.
- **Thermal (5.4):** DRV RθJA is **100.2 °C/W** (JEDEC high-K), RθJB 64.3, RθJC(bot) 34.7. Thermal shutdown trips at 165 °C. Recommended Tj is ≤125 °C.
- **Input voltage:** recommended **1.45–5.5 V**, absolute max **6.0 V**. EN has the same limits.
  - On USB VBUS (≤5.25 V, or ≤5.5 V for a USB-C source) behind the Schottky this is fine.
  - Anything fed to the 5 V header pin that bypasses the Schottky must stay ≤5.5 V. There is no margin for a 6 V wall-wart.
- **Other notes:**
  - EN high threshold is 1 V min, so tie EN to IN.
  - There is no reverse-current protection. VOUT > VIN + 0.3 V exceeds absolute max (7.1.4). Do not back-feed 3V3 from a header while 5 V is absent unless you add a diode.
  - Short-circuit limit is 355 mA (foldback).
- **Layout (7.4.1):** put the caps close to the part, use copper planes, add thermal vias around and under the EP, and the EP must be soldered.

**AP2112K-3.3TRG1, C51118** (Diodes, SOT-25, Extended, $0.17). Fallback only.
Source: https://www.diodes.com/assets/Datasheets/AP2112.pdf (DS39724 Rev 2-2)

- Pins 1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT. This matches your list.
- 1 µF in and out. Ceramic is fine and X5R/X7R is recommended (Note 4).
- Dropout at 600 mA: 250 typ / 400 max mV.
- θJA (SOT25) 184 °C/W, θJC 96 °C/W.
- VIN 2.5–6.0 V recommended, 6.5 V absolute max.
- The JLC stock under MPN "AP2112K-3.3TRG1" also includes TECH PUBLIC clones (C23380830, C3021085). **Use C51118** for the genuine Diodes part.

**SOT-23-5 alternatives** (all Extended at JLC; none of them is Basic):

| Part | LCSC | Iout | Thermal | Notes |
|---|---|---|---|---|
| TLV75533PDBVR (SOT-23-5) | C404027 | 500 mA | RθJA 231 °C/W JEDEC, 100.8 on TI EVM | Same die as the chosen part. The WSON is ~2.3x better. |
| ME6211C33M5G-N | C82942 | 500 mA | Pd 300 mW (no θJA given) | Cheapest ($0.06). Weakest thermals. |
| RT9013-33GB | C47773 | 500 mA | θJA 250 °C/W | 400 mV dropout at 500 mA. |
| XC6220B331MR-G (SOT-25) | C86534 | 1 A | 166.7 °C/W on Torex 40x40 mm 2-layer board | Best SOT-25 thermals, but $$ |

**Verdict (v1.2, superseded):** TLV75533PDRVR was the best of this set thermally (100 °C/W) and was in stock. Do not fit it on v1.3. The board uses TLV76733DRVR, C2848334.

## 2. ESD: USBLC6-2P6 (primary), with USBLC6-2SC6 as fallback

Source: ST USBLC6-2 datasheet, which covers both packages (Doc ID 11265; LCSC copy on the C7519 page). The current ST URL is https://www.st.com/resource/en/datasheet/usblc6-2.pdf.

- **Pinout (Fig. 1, identical for SOT23-6L "USBLC6-2SC6" and SOT-666 "USBLC6-2P6", top view):** 1 I/O1, 2 GND, 3 I/O2, 4 I/O2, 5 VBUS, 6 I/O1. This **matches** your list.
  - Pins 1 and 6 are the same internal node, and so are 3 and 4. The part is flow-through.
- **Layout:**
  - ST's Fig. 18 ("PCB layout considerations") shows **D+in on pin 1, GND on pin 2 and D−in on pin 3 on the connector side**. D+out (pin 6), VBUS (pin 5) and D−out (pin 4) are on the MCU side, with **CBUS = 100 nF at pin 5**.
  - The text says to "put the protection device as close as possible to the disturbance source (generally the connector)". Keep the I/O, VBUS and GND tracks as short as possible, because ~6 nH of track adds about 144 V of clamp overshoot in ST's example. Use a direct via to the GND plane at pin 2.
  - So: **pins 1–3 face the USB-C connector, pins 4–6 face the MCU, and put 100 nF from pin 5 to GND.**
- **Ratings:** VRM 5.25 V, Ci/o-GND 2.5 typ / 3.5 max pF, IEC 61000-4-2 ±8 kV contact / ±15 kV air.
- **LCSC:**
  - USBLC6-2P6 **C15999** is genuine ST, SOT-666-6, 2,924 in stock, $0.25. Low stock: check it before ordering.
  - C2827693 is a TECH PUBLIC "USBLC6-2P6" (SOT-666-6, 46k in stock, $0.15) and is a pin-compatible clone.
  - Several other "USBLC6-2P6" listings are actually **SOT-563** (e.g. C5199178, C21713974, C49451919). Do not pick those blindly. SOT-563 and SOT-666 are close but not the same land pattern.
  - SC6 fallback: C7519 (genuine ST).

## 3. Schottky: 1N5819WS, C191023 (Basic)

Source: Hottech datasheet via LCSC: https://www.lcsc.com/datasheet/lcsc_datasheet_2409300937_Guangdong-Hottech-1N5819WS_C191023.pdf

- 1N5819WS and B5819WS are the same device class (40 V / 1 A, SOD-323). B5819WS listings (C7420331, C64886) are Extended or Preferred. **C191023 is the only Basic one**, so it was chosen.
- **VF (typical curve, 25 °C):** ≈0.30 V at 100 mA, ≈0.37 V at 500 mA. The datasheet maximum is 0.60 V at 1 A.
- **Ratings:**
  - IF(AV) is 1 A on paper. In practice SOD-323 is thermally limited: Pd is 250 mW at 25 °C, derated linearly to 0 at 125 °C, which gives ~212 mW at 40 °C.
  - At 500 mA that is 0.37 × 0.5 = 0.185 W, which is marginal. **Keep the +5 V rail draw at ≤ ~400 mA through the diode.**
- **Leakage:** 0.5 mA max at 40 V and 25 °C (10 mA at 100 °C). At 5 V reverse it is roughly 5–10 µA (curve). That is fine for back-feed blocking. Expect VBUS to sit slightly above 0 V when the header supplies 5 V and no cable is attached.
- **Polarity:**
  - The datasheet outline shows the band on the "−" (cathode) end.
  - KiCad `Diode_SMD:D_SOD-323` puts pad 1 at x = −1.05, and the silkscreen bracket's closed end (x = −1.61) is on the pad 1 side. That follows the KiCad convention of **pad 1 = cathode = band**.
  - Symbol pin K → pad 1. Matches.

## 4. Tactile switch: B3U-1000P, C231329

Source: https://omronfs.omron.com/en_US/ecb/products/pdf/en-b3u.pdf

- B3U-1000P is the top-actuated version without a ground terminal or boss.
- **Omron PCB pad:** 4.2 mm outer and 2.6 mm inner, so 0.8 x 1.7 mm pads at ±1.7 mm.
- **KiCad `SW_SPST_B3U-1000P`:** pads 1/2 at ±1.7 mm, 0.9 x 1.7 mm. Its description is literally Omron's ("Ultra-small-sized Tactile Switch… without Ground Terminal, without Boss"). It matches.
- **LCSC/JLC:** C231329 is genuine Omron, SMD 3x2.5 mm, Extended, 142k in stock, $0.19. JLC has no Basic switch in this size.
- **Cheaper drop-ins:**
  - HX-B3U-1000P-1.6N (C49234121, hanxia, $0.08, 51k in stock) is named as a clone. **Its land pattern is unverified**, because neither JLC nor LCSC has a datasheet for it.
  - Other 3x2.5 mm parts (XKB TS-3025, Korean Hroparts K2-1822) are Extended too, and their footprints are unverified.
  - Since every candidate is Extended, the setup fee is the same. **Stay with genuine B3U-1000P.**

## 5. Crystal: X32258MOB4SI, C2682775

Source: https://www.lcsc.com/datasheet/lcsc_datasheet_2411121006_YXC-Crystal-Oscillators-X32258MOB4SI_C2682775.pdf

- YSX321SL, 8.000 MHz, fundamental AT-cut.
- **Specs:** CL 12 pF, ESR (R1) **150 Ω max**, C0 3 pF max, C1 5 fF max, ±10 ppm at 25 °C, ±20 ppm from −40 to 85 °C, drive level 100 µW.
- **Pads:** the YXC footprint diagram shows the crystal between **pads 1 and 3 (diagonal), with pads 2 and 4 = GND**. Numbering is counter-clockwise from the bottom-left in top view.
  - KiCad `Crystal_SMD_3225-4Pin_3.2x2.5mm` places pad 1 at (−1.1, +0.85) bottom-left, 2 bottom-right, 3 top-right, 4 top-left. It **matches**.
- **JLC Basic:** there is no 8 MHz 3225 crystal in JLC Basic. The Basic 8 MHz parts are C12674 (HC-49S-SMD) and C115962 (5032-2P), which are different footprints. Keep the Extended 3225.
- **gm check:**
  - DS5319 Table 22 gives HSE 4–16 MHz, RF = 200 kΩ, and **gm = 25 mA/V min** (startup).
  - The AN2867 criterion is gain margin = gm/gm_crit > 5, with gm_crit = 4·ESR·(2πF)²·(C0+CL)².
  - Result: 0.34 mA/V, so the **margin is 73. It passes easily.**
  - Sources: AN2867 Rev 15 copy at https://www.ecsxtal.com/store/pdf/stm32-microcontroller-application-note-092823.pdf, and https://ecsxtal.com/considerations-when-designing-crystals-into-stm32-microcontrollers/
- **Load caps: 15 pF C0G 0402, C1548 (Basic).**

## 6. LEDs

The 0603 KENTO parts in this section are the v1.2 study. The fitted LEDs are the 0402 Everlights in the banner (C264407, C74338), and the user-LED resistor is 330 Ω, not 1.5 kΩ.

- **Red:** KT-0603R **C2286** (Basic).
  - Datasheet: https://www.lcsc.com/datasheet/lcsc_datasheet_1810231112_Hubei-KENTO-Elec-KT-0603R_C2286.pdf
  - The I-V curve reaches ~1 mA at ≈1.85 V.
- **Green:** KT-0603G **C12624** (**Extended**). JLC Basic has 0603 red and white only, and green only in 0805: KT-0805G **C2297**, Basic.
  - Datasheet: https://www.lcsc.com/datasheet/lcsc_datasheet_1806151818_Hubei-KENTO-Elec-KT-0603G_C12624.pdf
  - It is InGaN emerald (λd 513–528 nm). The I-V curve starts at ~1 mA at ≈2.4 V, and VF bins at 5 mA run from 2.6 to 3.1 V.
- **At 1.5 kΩ (v1.2 study, not the fitted R6):** red ≈0.97 mA, green ≈0.47–0.60 mA. The green would be visibly bright (tens of mcd, brighter than the red). v1.3 fits R6 = 330 Ω instead. Do not change it to 1 kΩ or leave it at 1.5 kΩ.
- **v1.2 option, not done:** to avoid one Extended setup fee, the study suggested switching the green LED to 0805 (C2297). v1.3 keeps the 0402 Everlight.
- **MCU pin choice:** do not source LED current from PC13–PC15 (see section 9). Sinking ≤3 mA is allowed.

## 7. Ferrite bead

- JLC Basic has **no 0402 ferrite**. Its Basic beads are 0603 C1002 and C14709, and 0805 C1015 and C1017.
- **0402 choice:** Murata BLM15AG121SN1D **C85812** (Extended, $0.01, 387k in stock). It is 120 Ω ±25% at 100 MHz, **rated 550 mA**, with 0.19 Ω max DCR. That easily exceeds 50 mA, with a 10 mV drop at 50 mA.
  - Datasheet: https://www.lcsc.com/datasheet/lcsc_datasheet_2304140030_Murata-Electronics-BLM15AG121SN1D_C85812.pdf
- **If the layout can take 0603:** BLM18PG121SN1D **C14709** is Basic (120 Ω, 2 A, 0.05 Ω) and saves one Extended fee.
- Sunlord GZ1005 0402 parts are not Basic at JLC.

## 8. Passives (all Basic, all verified)

| Value | MPN | LCSC |
|---|---|---|
| 100 nF 0402 X7R 16 V | CL05B104KO5NNNC | C1525 |
| 1 µF 0402 X5R 25 V | CL05A105KA5NQNC | C52923 |
| 10 µF 0603 X5R 10 V (not fitted) | CL10A106KP8NNNC | C19702 |
| 10 kΩ 0402 1% | 0402WGF1002TCE | C25744 |
| 5.1 kΩ 0402 1% | 0402WGF5101TCE | C25905 |
| 1.5 kΩ 0402 1% | 0402WGF1501TCE | C25867 |
| 15 pF 0402 C0G 50 V (crystal) | 0402CG150J500NT | C1548 |
| 18 pF 0402 C0G 50 V (alt) | 0402CG180J500NT | C1549 |

There is no Basic 1 µF 0402 at 10 V (C14445 is Extended). The 25 V Basic part is better for DC bias anyway.

## 9. STM32F103C8 facts

Sources: DS5319 Rev 18 (https://www.st.com/resource/en/datasheet/stm32f103c8.pdf, LCSC copy on C8734), AN2606, RM0008.

- **FT pins (Table 5, LQFP48 column):**
  - **5 V tolerant:** PA8–PA15, PB2, PB3, PB4, PB6–PB15.
  - **Not tolerant:** PA0–PA7, PB0, PB1, PB5, PC13–PC15.
  - Caveats:
    - The FT absolute max is VDD + 4.0 V (Table 6). FT is not 5 V tolerant while VDD is unpowered: the limit is then 4.0 V.
    - The internal pull-up/pull-down must be disabled to hold more than VDD + 0.3 V (Table 35, note 3).
    - PA11/PA12 (USB) and PA9/PA10 (USART1) are FT.
- **PC13–PC15 (Table 5, note 5):** these pins are supplied through the backup power switch, which "only sinks a limited amount of current (3 mA)".
  - In output mode, speed must be ≤2 MHz with ≤30 pF load.
  - They "must not be used as a current source (e.g. to drive a LED)". So an LED on PC13 must be wired to sink current, at ≤3 mA.
- **HSE:** a 4–16 MHz crystal or ceramic resonator (Table 22: fOSC_IN 4 / 8 typ / 16 MHz). Confirmed.
- **Clock tree:**
  - 8 MHz HSE → PLL ×9 → 72 MHz SYSCLK, which is the maximum.
  - The USB prescaler (RCC_CFGR.USBPRE = 0) divides the PLL by 1.5, giving 48 MHz.
  - The DS5319 clock-tree note requires both HSE and PLL enabled, with USBCLK at 48 MHz.
  - Confirmed. RM0008 RCC_CFGR via https://community.st.com/t5/stm32-mcus-embedded-software/sysclk-and-usb-prescaler-confusion/td-p/547793 and https://github.com/zephyrproject-rtos/zephyr/issues/47146
- **System bootloader (AN2606):** BOOT0 = 1 and BOOT1 (PB2) = 0 select system memory. On F10xxx the bootloader uses USART1 with PA9 = TX and PA10 = RX, 8 data bits, even parity, 1 stop bit, and auto-baud on 0x7F.
  - Confirmed. https://wiki.cuvoodoo.info/lib/exe/fetch.php?media=stm32f1xx:an2606_boot_mode.pdf
  - Note: PB2/BOOT1 is FT.
  - On F103 there is no USB DFU in the system bootloader; that only exists on connectivity-line parts.
- **NRST:** "permanent pull-up resistor" RPU = 30/40/50 kΩ (Table 38, §5.3.14). Fig. 31 recommends **0.1 µF from NRST to GND**. So a 100 nF cap plus a button to GND is sufficient. Confirmed.

## 10. USB4085-GF-A, C7095263

- **JLC/LCSC:** GCT, packaging listed as "Plugin" (= THT). Extended, 3,640 in stock, $1.40.
- **Distributors** (DigiKey https://www.digikey.com/en/products/detail/gct/USB4085-GF-A/9859662, element14 https://my.element14.com/gct-global-connector-technology/usb4085-gf-a/usb-conn-2-0-type-c-r-a-rcpt-16pos/dp/2924867): "USB 2.0 Type C, Receptacle, 16 Position, Through Hole, Right Angle". Confirmed as **a THT USB-C 2.0 receptacle**.
- **GCT drawing (LCSC datasheet):**
  - Pins: A1/A12/B1/B12 GND, A4/A9/B4/B9 VBUS, A5 CC1, B5 CC2, A6 Dp1, A7 Dn1, B6 Dp2, B7 Dn2, A8 SBU1, B8 SBU2.
  - Ratings: VBUS 5 A combined, GND 6.25 A combined, other pins 0.25 A each, 48 V DC.
  - Use 5.1 kΩ (C25905) from each of CC1 and CC2 to GND, and tie Dp1 to Dp2 and Dn1 to Dn2.

## Not verified / caveats

- Real RθJA of the v1.2 TLV75533PDRVR study on this 2-layer board. The ~150 °C/W figure is an estimate; TI only gives the JEDEC 4-layer value of 100.2. It is not a measurement of the fitted TLV76733.
- Footprint compatibility of the HX-B3U-1000P-1.6N clone (no datasheet available).
- Crystal drive level with the F103 HSE was not computed. The YXC part is rated 100 µW and 8 MHz at CL = 12 pF is a normal operating point, but this is unverified.
- The 1N5819WS VF and leakage values at 100/500 mA are read from typical curves, not guaranteed maxima.
- The ST website timed out from here. The ST datasheets used were DS5319 Rev 18 (via LCSC) and USBLC6-2 Doc ID 11265 Rev 5 (via LCSC). The pinout and layout guidance have not changed between revisions as far as I know, but I did not diff against the latest ST revision.
- Stock and prices are from 2026-10-01. USBLC6-2P6 C15999 (2.9k) and USB4085 C7095263 (3.6k) have the thinnest stock.

**Extended-part count for JLC, v1.2 study** (each unique Extended part adds a loading fee; Preferred parts and Basic parts do not). The fitted LDO is TLV76733DRVR C2848334, not TLV75533PDRVR, and the LEDs are the 0402 Everlights, not KT-0603G. See the banner.

- In this v1.2 set, TLV75533PDRVR, USBLC6-2P6, X32258MOB4SI, B3U-1000P and KT-0603G are always Extended.
- BLM15AG121 is also Extended if you keep the 0402 ferrite.
- The STM32 is Preferred, so it adds no fee.
- The cheap reductions are the green LED to 0805 (C2297) and the ferrite to 0603 (C14709).
- Footprint references: https://gitlab.com/kicad/libraries/kicad-footprints
