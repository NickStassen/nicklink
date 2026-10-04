# NickLink v1.3 power and analog SPICE suite

ngspice testbenches for the power and analog parts of the board: USB hot-plug, the LDO, brown-out, NRST, the LEDs, I2C edges, the HSE crystal and the VDDA filter. Part values come from `tools/spec.py`.

## Run

```sh
sim/run.sh               # all testbenches, then plots + results/summary.md (~1 min)
sim/run.sh hotplug i2c   # only testbenches whose name contains one of the words
python3 sim/analyze.py   # rebuild plots/summary from existing results/*.dat
python3 sim/xtal.py      # crystal numbers only (with a self-check)
```

ngspice runs in a throwaway Docker image (`nicklink-ngspice`, Ubuntu 24.04 + ngspice 42). `run.sh` builds it from `sim/Dockerfile` the first time, so nothing is installed on the host. Plotting uses the host's python3 + numpy + matplotlib. `sim/.spiceinit` turns on PSpice compatibility (`ngbehavior=psa`), which the TI model needs.

Outputs go to `sim/results/`: `summary.md` (the full report, generated), `*.png` plots, and raw `*.dat` / `*.log` (ignored by git).

| File | |
|---|---|
| `tb/01_hotplug.cir` … `tb/12_j11_hotplug.cir` | Testbenches. Each header says what it checks and what counts as pass. |
| `models/TLV75533P_TRANS.lib` | **TI vendor model**, SBVM831 "TLV75533P Unencrypted PSpice Transient Model" (ti.com/lit/zip/SBVM831), unmodified |
| `models/parts.lib` | Fitted models: 1N5819WS, USBLC6 VBUS Zener, SMF5.0A, BLM15AG121 ferrite, Everlight LEDs, switch, DMP2165UW (Q1, gate at GND) |
| `models/caps.lib` | MLCCs with DC-bias derating |
| `models/board.lib` | The +5V → 3V3 / VDDA rail as one subcircuit (U2, C8, C5, C1–C4, C14, C15, FB1, C6, C7, D1+R3) |
| `analyze.py` | Metrics, verdicts, plots, `results/summary.md` |
| `xtal.py` | Test 7, AN2867 calculation |

## Models and assumptions

- **TLV75533P:** the TI transient model runs in ngspice unchanged. Testbenches add `.ic v(…u1_n08530)=0`, because ngspice ignores the soft-start capacitor's `IC=0` without UIC. Checked against datasheet Fig. 5-8 (1→500 mA, 1 µF): the model gives −64 / +41 mV, the datasheet shows about −60 / +70 mV. Limits of the model:
  - **No small-signal loop.** The output is a behavioural source behind 36 mΩ, so phase margin cannot be simulated. Its load-step dip also barely depends on COUT, so the step results are conservative for this board's 6.6 µF.
  - Dropout is a fixed 150 mV at any load. The datasheet gives 0.30 Ω typ / 0.43 Ω max at 500 mA. Test 3 reports both.
  - No VIN absolute-maximum behaviour. Test 1 compares the +5V peak against 6.0 V instead.
  - It has UVLO (1.3 V), foldback current limit and the 120 Ω discharge.
- **USBLC6-2P6:** ST's model could not be downloaded (st.com blocks scripted access). The VBUS–GND Zener is behavioural: BV ≥ 6 V (datasheet minimum only) with 1.25 Ω dynamic resistance, from VCL 12 V @ 1 A / 17 V @ 5 A. BV is swept over 6 V and 9 V (9 V is an assumed weak sample).
- **MLCC derating:** C(V) = C0 / (1 + (V/V0)²), roughly fitted to published Samsung/Murata DC-bias curves (±15 %, 25 °C, no ageing):

  | Part | At 3.3 V | At 5 V |
  |---|---:|---:|
  | 10 µF 0603 X5R 10 V | 55 % | 35 % |
  | 1 µF 0402 X5R 25 V | 60 % | 40 % |
  | 100 nF 0402 X7R 16 V | 80 % | 64 % |

  C12 and C13 use a voltage-dependent C in the hot-plug test. Everything else uses the linear value at its rail voltage, because ngspice's behavioural capacitor stalls when a node sits still next to the TI model.
- **DMP2165UW (Q1):** body diode drain → source (0.7 V at 1 A) plus a two-way channel switch, on while V(5V_F) > 1.2 V, 90 mΩ (the gate is tied to GND).
- **1N5819WS:** fitted to the Hottech typical curve (0.30 V @ 100 mA, 0.37 V @ 500 mA).
- **LEDs:** fitted through VF at 20 mA (datasheet min/typ/max bins) and the typical IV curve near 1 mA. The low-current end of the min/max bins is assumed.
- **Ferrite (BLM15AG121SN1D):** 0.10 Ω + (0.45 µH ∥ 150 Ω ∥ 1 pF), about 120 Ω at 100 MHz. This is approximate; Murata's netlist was not used.
- **STM32F103 limits** (DS5319):
  - VDD minimum 2.0 V.
  - PDR 1.80 / 1.88 / 1.96 V, tRSTTEMPO 1–4.5 ms.
  - NRST: RPU 30/40/50 kΩ, VIL 0.8 V, VIH 2.0 V, a pulse ≥ 300 ns is always recognised.
  - PC13 sinks ≤ 3 mA.
  - HSE gm ≥ 25 mA/V.
- **Hot-plug source:** an ideal 5.5 V step (USB-C vSafe5V maximum) with a 10 ns contact closure. This is the worst case: a real host adds its own bulk capacitance, ESR and contact bounce.

## What each test checks

1. **USB hot-plug.** Cable L 0.5/1 µH × R 0.1/0.3 Ω, USBLC6 BV 6/9 V, 8 circuit variants. Pass if the +5V peak is ≤ 5.75 V; 5.75–6.0 V is MARGIN; above 6.0 V (TLV755 VIN absolute maximum) is FAIL. Inrush charge must be ≤ 50 µC (USB 2.0 §7.2.4.1, equal to 10 µF at 5 V).
2. **LDO.** Start-up (monotonic, overshoot < 3 %) and load steps 0→50→250→50→0 mA with 1 µs edges, fed from VBUS = 5.0 V and 4.40 V through R12 and D2 (so each load step is also a line step on VSYS). Pass if 3V3 stays within 3.3 V ±3 % and settles within 10 mV in < 100 µs. Stability is checked against TI's capacitor condition, because the model has no loop.
3. **Brown-out.** VSYS (LDO IN) ramps down at 50 and 250 mA constant-current loads. Records the VSYS level (and the VBUS equivalent, VSYS + VF + I·R12) at which 3V3 crosses 3.2 V, 3.0 V, 2.0 V and PDR, plus the D2 drop at 100/250/500 mA.
4. **NRST.** Power-on RC delay over the RPU range, RESET press and release, the internal 20 µs reset pulse against 100 nF, and the BOOT0 levels.
5. **LEDs.** D1 and D3 current over the VF bins at the as-built R6 = 330 Ω, plus an R6 sweep, with ≤ 3 mA at the minimum-VF bin.
6. **I2C.** Rise and fall times with 4.7 kΩ and 20/40/100 pF at 400 kHz (tr ≤ 300 ns) and 100 kHz (tr ≤ 1000 ns).
7. **Crystal (analytic, `xtal.py`).** AN2867 gm_crit and gain margin, load capacitance and frequency pulling, drive level against the 100 µW rating.
8. **VDDA filter.** AC transfer from 3V3 to VDDA, as built and with a damping resistor.
9. **Hot-plug fix candidates** (`tb/09_hotplug_fixes.cir`). The power reviewer's topology and its variants (A–D), plus follow-up candidates E–E'', all at the same corners as test 1. Pass needs all three: LDO IN peak ≤ 5.8 V, inrush ≤ 50 µC (full-bias estimate), and 3V3 still regulating at 500 mA with USB at 4.40 V.
10. **C12 as an RC snubber** (`tb/10_snubber_hotplug.cir`, `tb/10_snubber_loadstep.cir`). Topology A with no series R in the main path; instead C12 4.7 µF 0402 sits behind Rs (0.5 / 1.0 / 2.2 Ω), optionally with a 100 nF or 1 µF 0402 directly on VSYS. Reports hot-plug peak, inrush, Rs pulse power and energy, and load steps through a 1 µH cable. Pass: VSYS peak ≤ 5.8 V and inrush ≤ 50 µC.
11. **Hot-plug, current spec.py power path** (`tb/11_hotplug_v13.cir`, `NL_RAIL_V13` in `models/board.lib`). R12 swept over 1.0 (as built) / 1.5 / 2.2 Ω, same 8 corners. Also reports the drop and LDO IN at 250 / 500 mA from 4.40 V and 4.75 V, and R12 power.
12. **Hot-plug into J1.1, and long USB cables** (`tb/12_j11_hotplug.cir`). R12 is not in the J1.1 path: J1.1 → Q1 → F1 → VSYS. A stiff 5.0 / 5.5 V supply is stepped onto J1.1 through 0.1 µH / 30 mΩ (short stiff link) to 2 µH / 0.1 Ω (long bench leads), with F1 at 0.1 Ω (minimum) and 0.3 Ω (typical), and C12 both bias-dependent and linear 1.3 µF. The same bench steps USB through 1.5 / 2 / 3 µH cables at 5.25 / 5.5 V. U2 is passive (Iq only), so one run was scored two ways and was not re-run. The 6.0 V rows are the old TLV755 VIN/EN limit (not fitted). The fitted part is the TLV76733DRVR (18 V abs max); the limit used for that score is Q1's ±12 V VGS, with C12 and F1 at 16 V. Those fitted-part rows are "U2 -> TLV76733" in `results/summary.md` (J1.1 hot-plug MARGIN, long-cable USB PASS). Do not read a 6.0 V FAIL as the current board.

## Results (`results/summary.md` is regenerated on every run)

The table below shows the **as-built v1.3 rail** (R12, C12 4.7 µF 0402, R6 330 Ω, from `tools/spec.py`). `analyze.py` regenerates it between the markers. Bench 12 rows that compare VSYS with 6.0 V are the **old TLV755** limit, not the fitted TLV76733DRVR. The fitted-part scores are the "U2 -> TLV76733" rows in `results/summary.md` (J1.1 MARGIN, long USB cables PASS). The peaks were not re-simulated.
- Benches 2–4 and 11 use the current rail: R12 1 Ω, C12 4.7 µF 0402, C4 4.7 µF 0402 at VDD3, no C5.
- Bench 5 reports R6 = 330 Ω.
- Benches 6–8 are unchanged parts.
- The v1.3-original rows (C12 10 µF, C5 10 µF, no R12) are kept only where they explain why R12 was added.
- Fix studies (benches 1, 9 and 10 variants, the VDDA damping option, other R6 values) are in the second table of `results/summary.md`.

<!-- results:start -->
| Test | Check | Result | Verdict |
|---|---|---|---|
| 1 Hot-plug | As built (bench 11): R12 1 ohm, C12 4.7u 0402, C4 4.7u; LDO IN peak <= 5.8 V, inrush <= 50 uC | LDO IN pk 5.38 V, VBUS pk 6.17 V, inrush 33 uC, LDO IN @4.40 V/500 mA 3.53 V | **PASS** |
| 1 Hot-plug | As built: 3V3 at 500 mA from USB 4.40 V (above the 250 mA thermal budget) | LDO IN 3.53 V vs 3.538 V needed (max dropout); 3V3 ~3.29 V | **MARGIN** |
| 1 Hot-plug | v1.3 original (no R12, C12 10u, C5 10u) - why R12 was added: peak +5V vs 6.0 V abs max | 6.13..11.42 V | **FAIL** |
| 1 Hot-plug | v1.3 original - inrush charge vs USB 50 uC | 63 uC (C12 + 3V3 caps via soft-start) | **FAIL** |
| 12 J1.1 hot-plug | Old TLV755 limit, not fitted: 5.0 / 5.5 V supply plugged onto J1.1 (leads 0.1-2 uH, F1 0.1 / 0.3 ohm); VSYS <= 6.0 V. Fitted part is the TLV76733 row in the second table (MARGIN) | VSYS pk 5.42..9.17 V (linear C12), up to 19.3 V (bias C12); 2 of 20 corners <= 6.0 V | **FAIL (against 6.0 V only)** |
| 12 J1.1 hot-plug | Old TLV755 limit, not fitted: USB hot-plug, 1.5-3 uH cables (2-4 m), 5.25 / 5.5 V; LDO IN <= 6.0 V. Fitted TLV76733 score for this peak is PASS (<= 12 V) | <= 2 uH at 5.25 V: 5.92 V; worst (3 uH, 5.5 V): 7.34 V | **MARGIN (against 6.0 V only)** |
| 2 LDO | Start-up: monotonic, overshoot < 3 % | 367 us to 90 %, overshoot 0.02 % | **PASS** |
| 2 LDO | Load steps 0/50/250 mA, 1 us edges: within 3.3 V +-3 %, settle < 100 us | worst deviation 31 mV, settle 28 us | **PASS** |
| 2 LDO | Stability: TI condition COUT_eff >= 0.47 uF, nominal 1..200 uF, ceramic ESR (vendor model has no loop, no phase margin) | COUT_eff 3.2 uF; C8 alone 0.60 uF | **PASS** |
| 3 Brown-out | Min VBUS for regulation at 250 mA (USB min 4.75 V, 4.40 V at a bus-powered hub) | VBUS >= 4.01 V (datasheet-max dropout + VF + 250 mA x R12) | **PASS** |
| 3 Brown-out | Window VDD < 2.0 V (spec min) before PDR (1.80..1.96 V) resets the MCU | VSYS 2.16 -> 1.96 V (200 mV of input sag, unprotected) | **MARGIN** |
| 3 Brown-out | Schottky D2 drop at 100 / 250 / 500 mA | 0.30 V / 0.34 V / 0.37 V | **PASS** |
| 4 NRST | Power-on: NRST to VIH 2.0 V after VDD = 2.0 V (RPU 30..50 k, C9 100 nF), budget 20 ms | <= 3.7 ms (on top of the chip's own 1..4.5 ms POR delay) | **PASS** |
| 4 NRST | RESET button: NRST < 0.8 V in < 1 us, held >= 300 ns; release time | release 3.7 ms | **PASS** |
| 4 NRST | Internal 20 us reset pulse pulls 100 nF below VIL (assumed 50 ohm driver) | yes | **PASS** |
| 4 NRST | BOOT0: 10 k pull-down, button to 3V3 | pressed 3.3 V / released 0 V, 0.33 mA while pressed | **PASS** |
| 5 LEDs | Red D1 with R3 1k5, all VF bins | 0.84..1.12 mA | **PASS** |
| 5 LEDs | Green D3 with R6 330 (as built): typ >= 1 mA, PC13 sink <= 3 mA at min VF | typ 1.32 mA, 0.95..1.79 mA over VF bins | **PASS** |
| 6 I2C | 400 kHz, 4.7 k, 20 pF: tr <= 300 ns | tr 80 ns, tf 1 ns | **PASS** |
| 6 I2C | 400 kHz, 4.7 k, 40 pF: tr <= 300 ns | tr 160 ns, tf 2 ns | **PASS** |
| 6 I2C | 400 kHz, 4.7 k, 100 pF: tr <= 300 ns | tr 398 ns, tf 4 ns | **FAIL** |
| 6 I2C | 100 kHz, 4.7 k, 20 pF: tr <= 1000 ns | tr 80 ns, tf 1 ns | **PASS** |
| 6 I2C | 100 kHz, 4.7 k, 40 pF: tr <= 1000 ns | tr 160 ns, tf 2 ns | **PASS** |
| 6 I2C | 100 kHz, 4.7 k, 100 pF: tr <= 1000 ns | tr 398 ns, tf 5 ns | **PASS** |
| 7 Crystal | AN2867 gain margin >= 5 | 73 (gm_crit 0.34 mA/V) | **PASS** |
| 7 Crystal | Load capacitance / pulling | CL 10.5..12.5 pF, -5..+19 ppm | **PASS** |
| 7 Crystal | Drive level <= 100 uW (worst-case ESR, swing unknown) | 55 uW at 2 Vpp, 149 uW at 3.3 Vpp; limit at 2.7 Vpp | **MARGIN** |
| 8 VDDA filter | Attenuation above 10 MHz; LC resonance peak | -67 dB @10 MHz, -64 dB @100 MHz; peak +17.1 dB @ 288 kHz | **MARGIN** |
<!-- results:end -->

Plots:

| Plot | Shows |
|---|---|
| `results/hotplug_variants.png` | +5V at each variant's worst corner |
| `results/hotplug_base.png` | As-built VBUS, +5V, 3V3 and cable current |
| `results/ldo_steps.png` | LDO start-up and load steps |
| `results/brownout.png` | Brown-out ramp |
| `results/nrst.png` | NRST waveforms |
| `results/led_r6.png` | Green LED current vs R6 |
| `results/i2c.png` | I2C rise times |
| `results/vdda.png` | VDDA filter response |
| `results/hotplug_fixes.png` | Worst-case LDO IN peak for each test-9 candidate |
| `results/snubber.png` | Test 10: worst VSYS peak per snubber variant, and VSYS after the 250 mA step |

`results/summary.md` has the full numbers, including every hot-plug corner.

## Hot-plug fix candidates (test 9, run 2026-10-02)

Topology A: VBUS → U3/C13 → D2 → VSYS (C12 4.7 µF 0402, LDO IN) → F1 PTC → Q1 → J1.1 (open). VSYS and LDO IN are the same net.

- The inrush column adds the charge the fixed-value 3V3 capacitors undercount (+10.5 µC with C5 = 10 µF, +5.9 µC with 4.7 µF).
- The drop column is D2's typical VF plus I × R.
- Regulation at 500 mA needs LDO IN ≥ 3.3 V + 238 mV (TLV755 maximum dropout).

| Option | LDO IN peak (worst corner) | Inrush | Drop 250 / 500 mA | LDO IN at 500 mA, USB 4.40 V | Verdict |
|---|---:|---:|---:|---|---|
| A: C12 4.7 µF 0402, F1 on header side (F1 R makes no difference with the header open) | 12.71 V | 53 µC | 0.34 / 0.37 V | 4.03 V, regulates | FAIL |
| B: F1 between VBUS and D2, R = 0.1 / 0.3 / 0.6 Ω | 11.38 / 9.27 / 6.65 V | 52 / 51 / 50 µC | 0.36–0.49 / 0.42–0.67 V | 3.98–3.73 V, regulates | FAIL |
| C: A + 0.5 Ω in series | 7.35 V | 50 µC | 0.46 / 0.62 V | 3.78 V, regulates | FAIL |
| C: A + 1.0 Ω in series | 5.38 V | 48 µC | 0.59 / 0.87 V | 3.53 V, **dropout** (8 mV short) | FAIL |
| D: A with C12 2.2 µF 0402 | 11.76 V | 45 µC | 0.34 / 0.37 V | 4.03 V, regulates | FAIL |
| **E: C12 4.7 µF 0603 + 0.75 Ω (1206) in series + C5 4.7 µF 0603** | **5.45 V** | **37 µC** | 0.52 / 0.75 V | 3.65 V, regulates | **PASS** |
| E': as E, but C12 4.7 µF 0402 | 5.95 V | 35 µC | 0.52 / 0.75 V | 3.65 V, regulates | FAIL |
| E'': C12 10 µF 0603 + 0.5 Ω in series + C5 4.7 µF | 5.49 V | 54 µC | 0.46 / 0.62 V | 3.78 V, regulates | FAIL |

Shrinking C12 without adding resistance makes the ring worse, not better. A smaller C raises the cable/C12 impedance, so a larger series resistance is needed to damp it. The PTC's 0.1–0.6 Ω spread is not a dependable damper.

**Not the fitted board.** This study recommended option E. v1.3 is built with R12 = 1 Ω 0805 and C12 = 4.7 µF 16 V **0402** (Samsung CL05A475MO5NUNC, C318563), not a 0603 and not an extra 0.75 Ω. The study's suggestion, left here as history, was:
- a 4.7 µF **0603** for C12 (it holds about 2 µF at 5 V, where a 0402 holds about 1.3 µF);
- a 0.75 Ω 1206 resistor between VBUS (after U3/C13) and D2 (188 mW at 500 mA);
- C5 reduced to 4.7 µF 0603. Effective COUT would have been about 3.7 µF, still well above TI's 0.47 µF minimum.

Minimum package rating at 500 mA for each series resistor:

| Resistor | Power at 500 mA | Minimum package |
|---|---:|---|
| 0.5 Ω | 125 mW | 0805 (no margin; 1206 preferred) |
| 0.75 Ω | 188 mW | 1206 |
| 1.0 Ω | 250 mW | 1206 at its rating (1210/2010 preferred) |

The pass depends on the 0603 4.7 µF derating, which is an assumed curve (43 % at 5 V). Check the chosen part's DC-bias curve: it needs about 2 µF or more at 5.3 V.

500 mA is an electrical check only. At 500 mA the LDO dissipates about 0.18 W at USB 4.40 V, 0.47 W at 5.0 V and 0.72 W at 5.5 V, so most of that range is beyond the 250 mA thermal budget in the main README.

## C12 as an RC snubber (test 10, run 2026-10-02)

Topology A: VBUS → U3/C13 → D2 → VSYS (= LDO IN), with J1.1 open and no series R in the main path. C12 4.7 µF 0402 sits behind Rs; Cd is an optional extra cap directly on VSYS. The peak is the worst of the 8 corners from test 1. Inrush includes the charge the fixed-value 3V3 capacitors undercount. Rs energy is per plug-in; steady-state Rs power is about zero because no DC flows.

| Rs | Cd on VSYS | VSYS peak | Inrush | Rs peak power / energy | Verdict |
|---:|---|---:|---:|---|---|
| 0.5 Ω | none / 100 nF / 1 µF | 7.59 / 7.65 / 8.15 V | 50 / 51 / 54 µC | 17–22 W / 36–39 µJ | FAIL |
| 1.0 Ω | none | 5.74 V | 48 µC | 15 W / 41 µJ | PASS (no local CIN) |
| 1.0 Ω | 100 nF | 5.75 V | 49 µC | 17 W / 42 µJ | PASS |
| 1.0 Ω | 1 µF | 6.21 V | 53 µC | 27 W / 47 µJ | FAIL |
| 2.2 Ω | none | 5.67 V | 48 µC | 14 W / 45 µJ | PASS (no local CIN) |
| 2.2 Ω | 100 nF / 1 µF | 6.39 / 8.36 V | 49 / 53 µC | 17–28 W / 46–52 µJ | FAIL |
| **1.0 Ω** | **100 nF, plus C5 → 4.7 µF** | **5.75 V** | **35 µC** | 17 W / 42 µJ (≈2.5 µs equivalent pulse) | **PASS** |

**Load steps (0/50/250 mA through a 1 µH cable).** 3V3 stays at 3.287–3.330 V in every variant, the same as with C12 directly on VSYS: the vendor model's line rejection hides input-side differences. VSYS rings 103–122 mV peak-to-peak with the snubber, against 143 mV with C12 4.7 µF directly on VSYS. The snubber damps the cable/CIN resonance (`results/snubber.png`). Phase margin still can't be simulated, because the vendor model has no loop.

**CIN rule.** TI asks for ≥ 1 µF nominal (≥ 0.47 µF effective) at IN. The snubbed C12 holds 1.31 µF at 5 V, but it only acts as a capacitor below about 1/(2π·Rs·C) = 120 kHz at 1 Ω; above that the LDO sees Rs. So it meets the rule at DC and low frequency, not at high frequency. Directly at the pin there is only Cd: 100 nF gives about 0.06 µF effective, and 1 µF gives about 0.39 µF. **None of the passing snubber variants meets TI's rule with a capacitor directly at the pin.** A 1 µF there would, but it undoes the damping (6.21 V peak).

**Best snubber: Rs = 1.0 Ω, C12 4.7 µF 0402, 100 nF 0402 directly at LDO IN, and C5 reduced to 4.7 µF.** That gives 5.75 V and 35 µC. Keeping C5 at 10 µF works too, at 49 µC.
- The peak margin is thin, only 50 mV under 5.8 V. Rs = 2.2 Ω with the 100 nF fails.
- Rs carries no DC, so the 0402's 62.5 mW continuous rating doesn't apply. What matters is about 42 µJ in a pulse of a few µs (17 W peak) on every plug-in. Use a pulse-rated (anti-surge) 0603 or 0805 thick-film resistor, or check the 0402's single-pulse curve.

**Compared with option E** (test 9, 0.75 Ω in series in the main path):

| | Snubber | Option E |
|---|---|---|
| Peak margin | 50 mV | 0.35 V (5.45 V peak) |
| DC drop | none (LDO IN 4.03 V at 500 mA, USB 4.40 V) | 0.37 V more |
| C12 | behind Rs | directly at the LDO pin |

**Option E was this study's recommendation, and it is not what was built.** The fitted path is R12 = 1 Ω with C12 4.7 µF 16 V 0402 (test 11), not the 0603 in option E.

## Hot-plug, current spec.py power path (test 11, run 2026-10-02)

Path: VBUS (C13, U3, R2 + R11 bleed) → R12 → D2 → VSYS = LDO IN (C12 4.7 µF 0402, F1 → Q1 → J1.1 open). The 3V3 bank is C4 4.7 µF 0402, C8 1 µF and five 100 nF, with no C5. Effective COUT is about 3.2 µF, still above TI's 0.47 µF minimum.

- Peaks are the worst of the 8 corners from test 1.
- Inrush includes the 6.5 µC the fixed-value 3V3 capacitors undercount.
- The drop is I·R12 plus D2's typical VF.
- "Regulates" means LDO IN ≥ 3.3 V + 0.476 Ω × I (TLV755 maximum dropout).

| R12 | LDO IN peak | VBUS peak | Inrush | Drop 250 / 500 mA | LDO IN from 4.40 V, 250 / 500 mA | LDO IN from 4.75 V, 250 / 500 mA | R12 power at 300 / 500 mA |
|---:|---:|---:|---:|---:|---|---|---|
| **1.0 Ω (as built)** | **5.38 V** | 6.17 V | **33 µC** | 0.59 / 0.87 V | 3.81 / 3.53 V (8 mV into dropout) | 4.16 / 3.88 V | 90 / 250 mW |
| 1.5 Ω | 5.26 V | 5.74 V | 33 µC | 0.71 / 1.12 V | 3.69 / 3.28 V, dropout | 4.04 / 3.63 V | 135 / 375 mW |
| 2.2 Ω | 5.25 V | 6.21 V | 33 µC | 0.89 / 1.47 V | 3.51 / 2.93 V, dropout | 3.86 / 3.28 V, dropout | 198 / 550 mW |

**Keep R12 = 1.0 Ω.** It passes hot-plug with 0.42 V margin under 5.8 V, and inrush is 33 µC against the 50 µC limit. Going to 1.5 Ω or 2.2 Ω buys only 0.12–0.13 V of peak, but costs 0.25–0.6 V of headroom at 500 mA.

At 500 mA from 4.40 V, the 1 Ω case is 8 mV into worst-case dropout, so 3V3 sits at about 3.29 V instead of 3.30 V. That is harmless, and 500 mA is beyond the 250 mA thermal budget anyway. At ≤ 250 mA every option regulates from 4.40 V.

R12 dissipates 250 mW at 500 mA, half the 500 mW stated in spec.py's note. Check that rating in the Yageo SR0805 datasheet: a standard 0805 is 125 mW. The hot-plug pulse it absorbs is a few µs at about 4 A.

## Design recommendations

1. **Hot-plug: done in spec.py.** R12 = 1 Ω was added (test 11: 5.38 V peak, 33 µC). The rest of this item is the original analysis of the v1.3 original power path. A ceramic-only input rings. 10 µF ceramic (about 3.5 µF at 5 V) with 0.5–1 µH of cable gives Z0 ≈ 0.4–0.5 Ω, and with only 0.1–0.3 Ω of damping, D2 then latches the ring peak onto C12. The +5V rail reaches 6.1–11.4 V, above the then-fitted TLV755's 6 V absolute maximum and above that original C12's 10 V rating. The fitted regulator is the 18 V TLV76733, and C12 is the 16 V 4.7 µF 0402.
   - A TVS does not fix it: VBR ≥ 6.4 V plus the clamp slope is still above 6 V on +5V.
   - Bulk capacitance only works at ≥ 47 µF with ESR, which breaks the USB inrush limit.
   - **Recommended:** add a 1 Ω resistor (0805, ≥ 0.125 W) in series between VBUS (after U3/C13) and D2. Peak becomes 5.26 V and peak current falls from 14 A to 4 A. The cost is about 0.25 V more drop at 250 mA. Regulation still holds down to VBUS ≈ 4.0 V, inside USB's 4.40 V minimum.
   - 0.5 Ω also passes (5.51 V), with less margin.
   - A PTC with its own hold resistance would also add a fuse. Use one only if its minimum resistance is ≥ 0.5 Ω.
2. **Inrush: done in spec.py.** As built it is 33 µC. Original analysis (63–70 µC vs 50 µC): The charge comes from C12 plus the 3V3 bank, which soft-start fills within 0.4 ms. Reduce **C12 and C5 to 4.7 µF**: that gives 30 µC simulated (about 36 µC with full bias dependence), and with the series resistor the peak is still 5.26 V. COUT stays above TI's minimum (about 4 µF effective). This matters only for strict USB-IF compliance; hosts tolerate it in practice.
3. **Green LED: done in spec.py**, with R6 = 330 Ω (1.32 mA typical, 0.95–1.79 mA). The original suggestion was 220 Ω: 1.67 mA typical, 2.36 mA at the minimum-VF bin (PC13 sink ≤ 3 mA). No single value holds 1.5–2 mA across the whole 2.7–3.7 V VF bin range from 3.3 V. The maximum-VF bin gets 1.17 mA.
4. **I2C (FAIL at 100 pF).** 4.7 kΩ is fine up to about 75 pF at 400 kHz. If off-board modules push the bus near 100 pF, use 400 kHz only with ≤ 3.3 kΩ total pull-up (limit 3.54 kΩ at 100 pF), or run at 100 kHz. Document this beside the "keep combined pull-up above 1.5 kΩ" note in the README. The driver model's fall time (≈5 ns) is faster than UM10204's 12 ns Fm minimum; on the real part, select the slower GPIO speed setting.
5. **Brown-out (MARGIN).** The F103 has no BOR, only a PDR at 1.8–1.96 V. Between VDD = 2.0 V and PDR the MCU runs out of spec without being reset. Enable the **PVD** (for example 2.9 V) in firmware if flash writes or a sagging 5V-pin supply are possible.
6. **Crystal drive level (MARGIN).** Gain margin is ample. Drive level exceeds 100 µW only if OSC_IN swings more than 2.7 Vpp with a worst-case-ESR crystal. Measure OSC_IN at bring-up with a ≤ 1 pF probe. If it is above about 2.7 Vpp, add Rext (start at about 1.3 kΩ, then re-check the gain margin).
7. **VDDA (MARGIN).** FB1 resonates with C6/C7 at about 290 kHz (+17 dB). There is no known source on 3V3 at that frequency, so this is informational. A 1 Ω resistor in series with C7 (or a 1 µF part with higher ESR) damps the peak to +2.8 dB.

## Limitations

These benches cover the circuit, not the layout: there is no trace inductance, no thermal model and no temperature corners. MLCC derating, the USBLC6 breakdown voltage and the LED low-current bins are estimates. A first article should confirm the hot-plug result with a scope on +5V while plugging in a short cable from a stiff 5 V supply.
