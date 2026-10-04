"""Turn ngspice outputs in results/ into metrics, PASS/MARGIN/FAIL verdicts, PNG plots and
results/summary.md. Run by run.sh after the testbenches; re-runnable on its own."""
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import xtal

R = Path(__file__).parent / "results"
TB = Path(__file__).parent / "tb"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
INK2 = "#52514e"
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.color": "#e4e3df", "axes.edgecolor": INK2,
                     "axes.prop_cycle": matplotlib.cycler(color=SERIES), "lines.linewidth": 1.6,
                     "font.size": 9, "axes.titlesize": 10, "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
ROWS = []  # (test, check, result, verdict, top, sort key)


def row(test, check, result, verdict, top=True, key=None):
    """top=True: the as-built v1.3 board (summary/README headline table); False: fix studies and
    v1.3-original comparisons (second table)."""
    ROWS.append((test, check, result, verdict, top, key if key is not None else float(test.split()[0]) + 0.5))


def load(name):
    return np.loadtxt(R / f"{name}.dat", skiprows=1).T


def cases(log):
    return re.findall(r"CASE (\S+) (.*)", (R / log).read_text())


def limit(ax, y, text, below=False):
    ax.axhline(y, color=INK2, ls="--", lw=1)
    ax.annotate(text, (ax.get_xlim()[1], y), xytext=(-4, -11 if below else 3), textcoords="offset points", ha="right", color=INK2)


def first_cross(t, v, level, rising=True, after=0.0):
    m = t >= after
    t, v = t[m], v[m]
    idx = np.nonzero(v >= level if rising else v <= level)[0]
    return t[idx[0]] if len(idx) else np.nan


def verdict(value, ok, marg):
    """ok/marg are callables on value."""
    return "PASS" if ok(value) else "MARGIN" if marg(value) else "FAIL"


# ---------------------------------------------------------------------------- 01 hot-plug
def hotplug():
    labels = dict(re.findall(r"^\* VARIANT (\d+): (.*)$", (TB / "01_hotplug.cir").read_text(), re.M))
    by_var = {}
    for name, rest in cases("01_hotplug.log"):
        p = dict(kv.split("=") for kv in rest.split())
        t, vb, p5, p3, i = load(name)
        q = np.trapezoid(i - i[-1], t)
        by_var.setdefault(p["variant"], []).append(dict(name=name, LC=float(p["LC"]), RC=float(p["RC"]), BV=float(p["BV"]),
                                                       vbus=vb.max(), p5=p5.max(), ipk=i.max(), q=q, p3=p3.max()))
    lines = ["| Variant | worst +5V peak | worst VBUS peak | peak current | inrush charge | verdict |", "|---|---|---|---|---|---|"]
    worst = {}
    for v in sorted(by_var, key=int):
        cs = by_var[v]
        w = max(cs, key=lambda c: c["p5"])
        worst[v] = w
        q = max(c["q"] for c in cs)
        vd = verdict(w["p5"], lambda x: x <= 5.75, lambda x: x <= 6.0)
        lines.append(f"| {v}: {labels[v]} | {w['p5']:.2f} V (L {w['LC']*1e6:.1f} uH, R {w['RC']} ohm, BV {w['BV']:.0f}) | "
                     f"{max(c['vbus'] for c in cs):.2f} V | {max(c['ipk'] for c in cs):.2f} A | {q*1e6:.0f} uC | {vd} |")
        if v == "0":
            row("1 Hot-plug", "v1.3 original (no R12, C12 10u, C5 10u) - why R12 was added: peak +5V vs 6.0 V abs max",
                f"{min(c['p5'] for c in cs):.2f}..{w['p5']:.2f} V", vd, key=1.1)
            row("1 Hot-plug", "v1.3 original - inrush charge vs USB 50 uC", f"{q*1e6:.0f} uC (C12 + 3V3 caps via soft-start)",
                verdict(q, lambda x: x <= 50e-6, lambda x: x <= 60e-6), key=1.1)
        else:
            vq = verdict(q, lambda x: x <= 50e-6, lambda x: x <= 60e-6)
            row("1 Hot-plug", f"Fix option {v}: {labels[v]}", f"+5V peak {w['p5']:.2f} V, inrush {q*1e6:.0f} uC",
                vd if vd == vq else f"{vd} (peak) / {vq} (inrush)", top=False)
    # full table of every corner
    corner = ["| case | variant | L (uH) | R (ohm) | BV (V) | VBUS pk | +5V pk | I pk | Q (uC) |", "|---|---|---|---|---|---|---|---|---|"]
    for v in sorted(by_var, key=int):
        for c in by_var[v]:
            corner.append(f"| {c['name']} | {v} | {c['LC']*1e6:.1f} | {c['RC']} | {c['BV']:.0f} | {c['vbus']:.2f} | {c['p5']:.2f} | {c['ipk']:.2f} | {c['q']*1e6:.0f} |")
    # plots: +5V at each variant's worst corner, and the as-built worst case in detail
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for k, v in enumerate(sorted(by_var, key=int)):
        t, vb, p5, p3, i = load(worst[v]["name"])
        m = t < 60e-6
        ax.plot(t[m] * 1e6, p5[m], color=SERIES[k], label=f"{v}: {labels[v]}  ({worst[v]['p5']:.2f} V)")
    ax.set(xlabel="time after plug-in (us)", ylabel="+5V (V)", title="Hot-plug, +5V at each variant's worst cable/clamp corner (5.5 V source)")
    limit(ax, 6.0, "TLV755 VIN abs max 6.0 V")
    ax.legend(fontsize=7, loc="lower right")
    fig.tight_layout(); fig.savefig(R / "hotplug_variants.png"); plt.close(fig)
    t, vb, p5, p3, i = load(worst["0"]["name"])
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(8, 5), sharex=True)
    m = t < 60e-6
    a1.plot(t[m] * 1e6, vb[m], label="VBUS"); a1.plot(t[m] * 1e6, p5[m], label="+5V"); a1.plot(t[m] * 1e6, p3[m], label="+3.3V")
    limit(a1, 6.0, "6.0 V"); a1.legend(fontsize=8); a1.set(ylabel="V", title=f"v1.3 original, worst corner ({worst['0']['name']}: 1 uH / 0.1 ohm cable)")
    a2.plot(t[m] * 1e6, i[m], color=SERIES[3]); a2.set(xlabel="time (us)", ylabel="cable current (A)")
    fig.tight_layout(); fig.savefig(R / "hotplug_base.png"); plt.close(fig)
    return "\n".join(lines), "\n".join(corner)


# ---------------------------------------------------------------------------- 02 LDO
def ldo():
    out = []
    steps = [(2e-3, "0->50 mA"), (3e-3, "50->250 mA"), (4e-3, "250->50 mA"), (5e-3, "50->0 mA")]
    fig, axs = plt.subplots(1, 5, figsize=(12, 3.4), gridspec_kw={"width_ratios": [1.4, 1, 1, 1, 1]})
    worst_dev, worst_settle = 0.0, 0.0
    for k, (name, rest) in enumerate(cases("02_ldo.log")):
        t, p5, p3, p3a, iin, vv = load(name)
        vin = float(rest.split("=")[1])
        t_on = first_cross(t, p5, 1.45)
        t90 = first_cross(t, p3, 0.9 * 3.3) - t_on
        vss = p3[(t > 1.5e-3) & (t < 2e-3)].mean()
        over = (p3[t < 2e-3].max() - vss) / vss * 100
        mono = np.all(np.diff(p3[(t > t_on) & (t < t_on + t90)]) > -1e-3)
        out.append(f"VBUS {vin} V: start-up {t90*1e6:.0f} us to 90 % (datasheet tSTR 550 us typ), overshoot {over:.2f} %, monotonic {mono}, Vout {vss:.4f} V")
        if k == 0:
            row("2 LDO", "Start-up: monotonic, overshoot < 3 %", f"{t90*1e6:.0f} us to 90 %, overshoot {over:.2f} %",
                "PASS" if mono and over < 3 else "FAIL")
        axs[0].plot(t * 1e3, p3, label=f"VBUS {vin} V")
        for j, (ts, lab) in enumerate(steps):
            m = (t >= ts - 20e-6) & (t < ts + 200e-6)
            seg, tt = p3[(t >= ts) & (t < ts + 0.95e-3)], t[(t >= ts) & (t < ts + 0.95e-3)]
            final = seg[-50:].mean()
            dev = max(3.3 - seg.min(), seg.max() - 3.3)
            outside = np.nonzero(np.abs(seg - final) > 10e-3)[0]
            settle = (tt[outside[-1]] - ts) if len(outside) else 0.0
            worst_dev, worst_settle = max(worst_dev, dev), max(worst_settle, settle)
            out.append(f"  {lab}: min {seg.min():.4f} V, max {seg.max():.4f} V, settles (10 mV) in {settle*1e6:.0f} us")
            axs[j + 1].plot((t[m] - ts) * 1e6, p3[m])
            axs[j + 1].set(title=lab, xlabel="us after edge")
        if k == 0:
            # datasheet Fig. 5-8 validation (separate circuit in the same run)
            pre = vv[(t > 1.8e-3) & (t < 2e-3)].mean()
            dip = vv[(t > 2e-3) & (t < 2.1e-3)].min() - pre
            ovs = vv[(t > 2.1e-3) & (t < 2.3e-3)].max() - vv[(t > 2.25e-3) & (t < 2.3e-3)].mean()
            out.append(f"Model check vs datasheet Fig. 5-8 (1->500 mA, 1 uF): dip {dip*1e3:.0f} mV / overshoot +{ovs*1e3:.0f} mV "
                       "(datasheet ~-60 / +70 mV)")
    vd = verdict(worst_dev, lambda x: x <= 0.099 and worst_settle < 100e-6, lambda x: x <= 0.15)
    row("2 LDO", "Load steps 0/50/250 mA, 1 us edges: within 3.3 V +-3 %, settle < 100 us",
        f"worst deviation {worst_dev*1e3:.0f} mV, settle {worst_settle*1e6:.0f} us", vd)
    axs[0].set(title="3V3: start-up + load steps", xlabel="ms", ylabel="V"); axs[0].legend(fontsize=7)
    for a in axs[1:]:
        a.set_ylim(3.26, 3.34)
    fig.tight_layout(); fig.savefig(R / "ldo_steps.png"); plt.close(fig)
    # stability: TI condition on effective capacitance (same derating formula as caps_lin.lib)
    def c_at(c0, v0, vb=3.3):
        return c0 / (1 + (vb / v0) ** 2)
    ceff = c_at(1e-6, 4.04) + c_at(4.7e-6, 3.1) + 5 * c_at(100e-9, 6.6)  # C8, C4 (0402), C1-3/C14/C15
    cnom = 1e-6 + 4.7e-6 + 5 * 100e-9
    out.append(f"Effective COUT at 3.3 V: {ceff*1e6:.2f} uF ({cnom*1e6:.1f} uF nominal, +1.08 uF VDDA behind FB1); "
               f"C8 alone at OUT pin: {c_at(1e-6, 4.04)*1e6:.2f} uF")
    row("2 LDO", "Stability: TI condition COUT_eff >= 0.47 uF, nominal 1..200 uF, ceramic ESR (vendor model has no loop, no phase margin)",
        f"COUT_eff {ceff*1e6:.1f} uF; C8 alone {c_at(1e-6, 4.04)*1e6:.2f} uF", "PASS" if 0.47e-6 <= ceff and cnom <= 200e-6 else "FAIL")
    return "\n".join(out)


# ---------------------------------------------------------------------------- 03 brown-out
def brownout():
    out = []
    vd_ = load("schottky_dc")
    i_d, v_d = vd_
    R12 = 1.0
    vf = {ma: float(np.interp(ma / 1e3, i_d, v_d)) for ma in (100, 250, 500)}
    out.append("D2 VF (fitted typ model): " + ", ".join(f"{k} mA {v:.3f} V" for k, v in vf.items()) + " (datasheet typ ~0.30 / 0.37 V at 100 / 500 mA)")
    fig, ax = plt.subplots(figsize=(7, 4))
    thr = [3.2, 3.0, 2.0, 1.88, 1.80]
    for k, (name, rest) in enumerate(cases("03_brownout.log")):
        t, p5, p3 = load(name)
        il = float(rest.split("=")[1])
        m = t > 5e-3
        lev = {th: float(p5[m][np.nonzero(p3[m] < th)[0][0]]) for th in thr}
        vfi = float(np.interp(il, i_d, v_d))
        out.append(f"Load {il*1e3:.0f} mA: 3V3 < " + ", ".join(f"{th} V at +5V = {lev[th]:.2f} V" for th in thr)
                   + f"; VBUS = VSYS + VF + I*R12 = VSYS + {vfi + il*R12:.2f} V")
        rds_max = 0.215 / 0.5 * 1.2  # datasheet max dropout at 500 mA (85 C), +20 % for 125 C
        out.append(f"   datasheet-max estimate: regulation lost below VSYS = {3.3 + il*rds_max:.2f} V "
                   f"(VBUS {3.3 + il*rds_max + vfi + il*R12:.2f} V); sim (fixed 150 mV model) {lev[3.2]:.2f} V")
        ax.plot(p5[m], p3[m], label=f"{il*1e3:.0f} mA load", color=SERIES[k])
        if k == 1:
            vmin = 3.3 + il * rds_max + vfi + il * R12
            row("3 Brown-out", "Min VBUS for regulation at 250 mA (USB min 4.75 V, 4.40 V at a bus-powered hub)",
                f"VBUS >= {vmin:.2f} V (datasheet-max dropout + VF + 250 mA x R12)",
                verdict(vmin, lambda x: x < 4.2, lambda x: x < 4.4))
            row("3 Brown-out", "Window VDD < 2.0 V (spec min) before PDR (1.80..1.96 V) resets the MCU",
                f"VSYS {lev[2.0]:.2f} -> {lev[1.80]:.2f} V ({(lev[2.0]-lev[1.80])*1e3:.0f} mV of input sag, unprotected)",
                "MARGIN")
    row("3 Brown-out", "Schottky D2 drop at 100 / 250 / 500 mA", " / ".join(f"{v:.2f} V" for v in vf.values()),
        "PASS" if vf[500] < 0.45 else "MARGIN")
    ax.invert_xaxis()
    ax.set(xlabel="VSYS = LDO IN falling (V)", ylabel="+3.3V (V)", title="Brown-out: 3V3 vs falling VSYS (vendor LDO model)")
    limit(ax, 2.0, "STM32 VDD min 2.0 V"); limit(ax, 1.88, "PDR 1.88 V typ", below=True)
    ax.legend(fontsize=8, loc="upper right"); fig.tight_layout(); fig.savefig(R / "brownout.png"); plt.close(fig)
    return "\n".join(out)


# ---------------------------------------------------------------------------- 04 NRST
def nrst():
    out = []
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.6))
    worst_rel, fall_ok, int_ok, rel_btn = 0, True, True, 0
    for k, (name, rest) in enumerate(cases("04_nrst.log")):
        t, p3, nr, b0 = load(name)
        rpu = f"{float(rest.split('=')[1])/1e3:.0f}k"
        t_vdd = first_cross(t, p3, 2.0)
        t_por = first_cross(t, p3, 1.92)
        t_rel = first_cross(t, nr, 2.0)
        t_fall = first_cross(t, nr, 0.8, rising=False, after=30e-3) - 30e-3
        t_rel2 = first_cross(t, nr, 2.0, after=32e-3) - 32e-3
        nmin = nr[(t > 50e-3) & (t < 50.03e-3)].min()
        low_int = np.sum(np.diff(t[(t > 50e-3) & (t < 50.03e-3)])[nr[(t > 50e-3) & (t < 50.03e-3)][:-1] < 0.8])
        b_on, b_off = b0[(t > 61e-3) & (t < 62e-3)].min(), b0[(t > 65e-3)].max()
        worst_rel = max(worst_rel, t_rel - t_vdd)
        rel_btn = max(rel_btn, t_rel2)
        fall_ok &= t_fall < 1e-6
        int_ok &= nmin < 0.8
        out.append(f"RPU {rpu}: VDD 2.0 V at {t_vdd*1e3:.2f} ms; NRST reaches 2.0 V {(t_rel - t_vdd)*1e3:.2f} ms later "
                   f"(internal POR+tRSTTEMPO 1..4.5 ms after {t_por*1e3:.2f} ms); button: < 0.8 V in {t_fall*1e9:.0f} ns, "
                   f"release to 2.0 V in {t_rel2*1e3:.2f} ms; 20 us internal pulse: NRST min {nmin:.2f} V, < 0.8 V for {low_int*1e6:.1f} us; "
                   f"BOOT0 pressed {b_on:.2f} V / released {b_off:.3f} V")
        a1.plot(t * 1e3, nr, label=f"NRST, RPU {rpu}", color=SERIES[k])
        m = (t > 49.99e-3) & (t < 50.06e-3)
        a2.plot((t[m] - 50e-3) * 1e6, nr[m], color=SERIES[k], label=f"RPU {rpu}")
    a1.plot(t * 1e3, p3, color=INK2, lw=1, label="3V3")
    a1.set(xlabel="ms", ylabel="V", title="NRST: power-up, RESET button 30-32 ms", xlim=(0, 40)); a1.legend(fontsize=7)
    a2.set(xlabel="us after internal reset", ylabel="V", title="Internal 20 us reset pulse (50 ohm pull-down, assumed)")
    limit(a2, 0.8, "VIL 0.8 V"); a2.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(R / "nrst.png"); plt.close(fig)
    row("4 NRST", "Power-on: NRST to VIH 2.0 V after VDD = 2.0 V (RPU 30..50 k, C9 100 nF), budget 20 ms",
        f"<= {worst_rel*1e3:.1f} ms (on top of the chip's own 1..4.5 ms POR delay)", "PASS" if worst_rel < 20e-3 else "FAIL")
    row("4 NRST", "RESET button: NRST < 0.8 V in < 1 us, held >= 300 ns; release time", f"release {rel_btn*1e3:.1f} ms",
        "PASS" if fall_ok else "FAIL")
    row("4 NRST", "Internal 20 us reset pulse pulls 100 nF below VIL (assumed 50 ohm driver)", "yes" if int_ok else "no",
        "PASS" if int_ok else "MARGIN")
    row("4 NRST", "BOOT0: 10 k pull-down, button to 3V3", "pressed 3.3 V / released 0 V, 0.33 mA while pressed", "PASS")
    return "\n".join(out)


# ---------------------------------------------------------------------------- 05 LEDs
def led():
    rows = []
    for m in re.finditer(r"LED R6=(\S+) (.*)", (R / "05_led.log").read_text()):
        d = dict(kv.split("=") for kv in m.group(2).split())
        rows.append((float(m.group(1)), {k: float(v) for k, v in d.items()}))
    r15 = dict(rows)[1500.0]
    out = [f"D1 red, R3 1k5: {r15['Ir_min']*1e3:.2f} / {r15['Ir_typ']*1e3:.2f} / {r15['Ir_max']*1e3:.2f} mA (min-VF / typ / max-VF bin)",
           f"D3 green, R6 330 (as built): {dict(rows)[330.0]['Ig_min']*1e3:.2f} / {dict(rows)[330.0]['Ig_typ']*1e3:.2f} / {dict(rows)[330.0]['Ig_max']*1e3:.2f} mA; "
           f"R6 1k5 (v1.3 original): {r15['Ig_min']*1e3:.2f} / {r15['Ig_typ']*1e3:.2f} / {r15['Ig_max']*1e3:.2f} mA",
           "| R6 | green min-VF bin | typ | max-VF bin |", "|---|---|---|---|"]
    out += [f"| {r:.0f} | {d['Ig_min']*1e3:.2f} mA | {d['Ig_typ']*1e3:.2f} mA | {d['Ig_max']*1e3:.2f} mA |" for r, d in rows]
    e12 = [r for r, d in rows if r in (100, 120, 150, 180, 220, 270, 330, 390, 470, 560, 680, 820, 1000, 1200, 1500)
           and 1.5e-3 <= d["Ig_typ"] <= 2e-3 and d["Ig_min"] <= 3e-3]
    best = min(e12, key=lambda r: abs(dict(rows)[r]["Ig_typ"] - 1.75e-3))
    b = dict(rows)[best]
    row("5 LEDs", "Red D1 with R3 1k5, all VF bins", f"{r15['Ir_max']*1e3:.2f}..{r15['Ir_min']*1e3:.2f} mA", "PASS")
    a = dict(rows)[330.0]
    row("5 LEDs", "Green D3 with R6 330 (as built): typ >= 1 mA, PC13 sink <= 3 mA at min VF",
        f"typ {a['Ig_typ']*1e3:.2f} mA, {a['Ig_max']*1e3:.2f}..{a['Ig_min']*1e3:.2f} mA over VF bins",
        "PASS" if a["Ig_typ"] >= 1e-3 and a["Ig_min"] <= 3e-3 else "MARGIN")
    row("5 LEDs", "Green D3 with R6 1k5 (v1.3 original, dim)", f"{r15['Ig_max']*1e3:.2f}..{r15['Ig_min']*1e3:.2f} mA (typ {r15['Ig_typ']*1e3:.2f})", "MARGIN", top=False)
    row("5 LEDs", f"R6 = {best:.0f} ohm (centre of 1.5..2 mA typ): PC13 sink <= 3 mA at min VF",
        f"typ {b['Ig_typ']*1e3:.2f} mA, min-VF {b['Ig_min']*1e3:.2f} mA, max-VF {b['Ig_max']*1e3:.2f} mA", "PASS", top=False)
    fig, ax = plt.subplots(figsize=(7, 4))
    rr = np.array([r for r, _ in rows])
    for k, (key, lab) in enumerate((("Ig_min", "min-VF bin"), ("Ig_typ", "typical"), ("Ig_max", "max-VF bin"))):
        ax.plot(rr, [d[key] * 1e3 for _, d in rows], marker="o", ms=4, label=f"green D3, {lab}", color=SERIES[k])
    ax.axhspan(1.5, 2.0, color=SERIES[2], alpha=0.12, lw=0)
    ax.set_xscale("log"); ax.set(xlabel="R6 (ohm)", ylabel="I(D3) (mA)", title="Green user LED current vs R6 (PC13 low)")
    limit(ax, 3.0, "PC13 sink limit 3 mA")
    ax.axvline(best, color=INK2, lw=1, ls=":"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(R / "led_r6.png"); plt.close(fig)
    return "\n".join(out), best


# ---------------------------------------------------------------------------- 06 I2C
def i2c():
    out = ["| f | Cb | tr 30-70 % | tf 70-30 % | VOL | V at end of tHIGH | spec tr |", "|---|---|---|---|---|---|---|"]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    for name, rest in cases("06_i2c.log"):
        p = dict(kv.split("=") for kv in rest.split())
        cb, f = float(p["CB"]), float(p["F"])
        t, v = load(name)
        tl = 1.667e-6 if f > 2e5 else 4.7e-6
        period = 2.5e-6 if f > 2e5 else 10e-6
        t0 = 1e-6 + period + tl  # second rising edge (switch opens)
        tr = first_cross(t, v, 0.7 * 3.3, after=t0) - first_cross(t, v, 0.3 * 3.3, after=t0)
        t_fall = 1e-6 + 2 * period - 5e-9  # next falling edge (driver closes)
        tf = first_cross(t, v, 0.3 * 3.3, rising=False, after=t_fall) - first_cross(t, v, 0.7 * 3.3, rising=False, after=t_fall)
        vol = v[(t > 1e-6 + period + tl * 0.9) & (t < 1e-6 + period + tl * 0.99)].min()
        vend = float(np.interp(t_fall, t, v))
        spec = 300e-9 if f > 2e5 else 1000e-9
        out.append(f"| {f/1e3:.0f} kHz | {cb*1e12:.0f} pF | {tr*1e9:.0f} ns | {tf*1e9:.1f} ns | {vol:.3f} V | {vend:.2f} V | {spec*1e9:.0f} ns |")
        row("6 I2C", f"{f/1e3:.0f} kHz, 4.7 k, {cb*1e12:.0f} pF: tr <= {spec*1e9:.0f} ns", f"tr {tr*1e9:.0f} ns, tf {tf*1e9:.0f} ns",
            verdict(tr, lambda x: x <= 0.8 * spec, lambda x: x <= spec))
        if f > 2e5:
            m = (t > t0 - 0.3e-6) & (t < t0 + 1.2e-6)
            ax.plot((t[m] - t0) * 1e9, v[m], label=f"{cb*1e12:.0f} pF: tr {tr*1e9:.0f} ns")
    out.append(f"Max pull-up for 300 ns at Cb: R <= 300 ns / (0.847 Cb) -> 100 pF: {300e-9/(0.8473*100e-12)/1e3:.2f} k, "
               f"200 pF: {300e-9/(0.8473*200e-12)/1e3:.2f} k; min pull-up (3 mA, VOL 0.4 V): {(3.3-0.4)/3e-3:.0f} ohm")
    ax.set(xlabel="ns after SCL release", ylabel="V", title="I2C1 400 kHz rise, 4.7 k pull-up")
    limit(ax, 0.7 * 3.3, "0.7 VDD"); limit(ax, 0.3 * 3.3, "0.3 VDD", below=True); ax.legend(fontsize=8, loc="center right")
    fig.tight_layout(); fig.savefig(R / "i2c.png"); plt.close(fig)
    return "\n".join(out)


# ---------------------------------------------------------------------------- 07 crystal
def crystal():
    x = xtal.results()
    out = [f"gm_crit = {x['gm_crit_mA_V']:.3f} mA/V; gain margin {x['gain_margin']:.0f} (ESR 150 ohm), {x['gain_margin_180ohm']:.0f} (180 ohm); AN2867 needs >= 5",
           f"CL actual = 15p series + Cs(3..5 pF) = {x['cl_actual_pF'][0]:.1f}..{x['cl_actual_pF'][1]:.1f} pF vs 12 pF -> "
           f"{x['pull_ppm'][0]:+.0f}..{x['pull_ppm'][1]:+.0f} ppm (USB FS needs +-2500 ppm)",
           f"Drive level at ESR 150 ohm: {x['dl_uW_2vpp']:.0f} uW at 2 Vpp, {x['dl_uW_3v3pp']:.0f} uW at 3.3 Vpp (rail-to-rail) vs 100 uW max; "
           f"100 uW is reached at {x['vpp_at_100uW']:.2f} Vpp on OSC_IN. Rext start value 1/(2 pi f C) = {x['rext_start_ohm']:.0f} ohm"]
    row("7 Crystal", "AN2867 gain margin >= 5", f"{x['gain_margin']:.0f} (gm_crit {x['gm_crit_mA_V']:.2f} mA/V)", "PASS")
    row("7 Crystal", "Load capacitance / pulling", f"CL {x['cl_actual_pF'][0]:.1f}..{x['cl_actual_pF'][1]:.1f} pF, {x['pull_ppm'][1]:+.0f}..{x['pull_ppm'][0]:+.0f} ppm", "PASS")
    row("7 Crystal", "Drive level <= 100 uW (worst-case ESR, swing unknown)",
        f"{x['dl_uW_2vpp']:.0f} uW at 2 Vpp, {x['dl_uW_3v3pp']:.0f} uW at 3.3 Vpp; limit at {x['vpp_at_100uW']:.1f} Vpp", "MARGIN")
    return "\n".join(out)


# ---------------------------------------------------------------------------- 08 VDDA
def vdda():
    f, db = load("vdda_ac")
    fd, dbd = load("vdda_ac_damped")
    k, kd = int(np.argmax(db)), int(np.argmax(dbd))
    at = {fx: float(np.interp(fx, f, db)) for fx in (1e5, 1e6, 1e7, 1e8)}
    atd = {fx: float(np.interp(fx, fd, dbd)) for fx in (1e5, 1e6, 1e7, 1e8)}
    out = (f"As built: resonance {f[k]/1e3:.0f} kHz, +{db[k]:.1f} dB; " + ", ".join(f"{fx/1e6:g} MHz {v:.1f} dB" for fx, v in at.items())
           + f"\n+1 ohm in series with C7: peak +{dbd[kd]:.1f} dB @ {fd[kd]/1e3:.0f} kHz; " + ", ".join(f"{fx/1e6:g} MHz {v:.1f} dB" for fx, v in atd.items()))
    row("8 VDDA filter", "Attenuation above 10 MHz; LC resonance peak", f"{at[1e7]:.0f} dB @10 MHz, {at[1e8]:.0f} dB @100 MHz; peak +{db[k]:.1f} dB @ {f[k]/1e3:.0f} kHz",
        "PASS" if db[k] <= 6 and at[1e7] <= -20 else "MARGIN")
    row("8 VDDA filter", "Fix option: 1 ohm in series with C7", f"peak +{dbd[kd]:.1f} dB, {atd[1e7]:.0f} dB @10 MHz",
        "PASS" if dbd[kd] <= 6 and atd[1e7] <= -20 else "MARGIN", top=False)
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.semilogx(f, db, color=SERIES[0], label="v1.3 original / current (unchanged)"); ax.semilogx(fd, dbd, color=SERIES[1], label="+1 ohm in series with C7")
    ax.legend(fontsize=8); ax.set(xlabel="Hz", ylabel="VDDA / 3V3 (dB)", title="VDDA filter FB1 + C6 + C7 (derated)")
    limit(ax, 0, "0 dB"); fig.tight_layout(); fig.savefig(R / "vdda.png"); plt.close(fig)
    return out


def dq_for(c5, v=3.315, bank=None):
    """Charge the linear (fixed at 3.3 V) 3V3 caps undercount vs. C(V) = C0/(1+(V/V0)^2):
    Q_true = C0*V0*atan(V/V0), Q_sim = C(3.3)*V. Default bank = v1.3 original rail
    (C5, C8, C1-4, C14, C15, C6, C7); pass bank=[(C0, V0), ...] for another rail."""
    bank = bank or [(c5, 3.65), (1e-6, 4.04)] + [(100e-9, 6.6)] * 7 + [(1e-6, 4.04)]
    return sum(c0 * (v0 * np.arctan(v / v0) - v / (1 + (3.3 / v0) ** 2)) for c0, v0 in bank)


def compose_vectors(cir):
    unit = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3}
    num = lambda x: float(x[:-1]) * unit[x[-1]] if x[-1] in unit else float(x)
    return {m[0]: [num(x) for x in m[1].split()] for m in re.findall(r"^compose (\w+)\s+values (.*)$", cir, re.M)}


# ---------------------------------------------------------------------------- 09 hot-plug fixes
def hotplug_fixes():
    cir = (TB / "09_hotplug_fixes.cir").read_text()
    labels = dict(re.findall(r"^\* VARIANT (\d+): (.*)$", cir, re.M))
    vec = compose_vectors(cir)
    # Charge the linear (fixed-at-3.3 V) 3V3 caps undercount vs. C(V) = C0/(1+(V/V0)^2):
    # Q_true = C0*V0*atan(V/V0), Q_sim = C(3.3)*V. C5, C8, C1-4, C14, C15, C6, C7 (caps.lib values).
    dq = dq_for(10e-6)
    i_d, v_d = load("schottky_dc")
    by_var = {}
    for name, rest in cases("09_hotplug_fixes.log"):
        pr = dict(kv.split("=") for kv in rest.split())
        t, vb, vs, p3, i = load(name)
        by_var.setdefault(int(pr["variant"]), []).append(dict(vbus=vb.max(), vsys=vs.max(), ipk=i.max(), q=np.trapezoid(i - i[-1], t)))
    VDO, USBMIN = 0.238, 4.40  # TLV755 DRV max dropout at 500 mA (-40..125 C); USB 2.0 min at the device
    res = {}
    for k in sorted(by_var):
        cs = by_var[k]
        rs = vec["vfv"][k] + vec["vrs"][k]
        drop = {ma: float(np.interp(ma / 1e3, i_d, v_d)) + ma / 1e3 * rs for ma in (250, 500)}
        ldo_in = USBMIN - drop[500]
        res[k] = dict(vsys=max(c["vsys"] for c in cs), vbus=max(c["vbus"] for c in cs), ipk=max(c["ipk"] for c in cs),
                      q=max(c["q"] for c in cs), qc=max(c["q"] for c in cs) + dq_for(vec["vc5"][k]), drop=drop, ldo_in=ldo_in,
                      reg=ldo_in >= 3.3 + VDO, rs=rs)
        r = res[k]
        r["ok"] = r["vsys"] <= 5.8 and r["qc"] <= 50e-6 and r["reg"]
    lines = [f"Inrush 'full-bias' adds the charge the linear 3V3 caps undercount ({dq*1e6:.1f} uC with C5 10 uF, {dq_for(4.7e-6)*1e6:.1f} uC with 4.7 uF). Regulation check: LDO IN = 4.40 V - drop(500 mA) "
             f">= 3.3 V + {VDO*1e3:.0f} mV (TLV755 max dropout). VF from the fitted typ 1N5819WS model (25 C). VSYS is the LDO IN net.",
             "| Variant | worst VSYS = LDO IN peak | worst VBUS peak | I pk | inrush sim / full-bias | drop 250 / 500 mA | LDO IN @500 mA, USB 4.40 V | verdict |",
             "|---|---|---|---|---|---|---|---|"]
    for k, r in res.items():
        lines.append(f"| {k}: {labels[str(k)]} | {r['vsys']:.2f} V | {r['vbus']:.2f} V | {r['ipk']:.1f} A | {r['q']*1e6:.0f} / {r['qc']*1e6:.0f} uC | "
                     f"{r['drop'][250]:.2f} / {r['drop'][500]:.2f} V | {r['ldo_in']:.2f} V ({'regulates' if r['reg'] else 'DROPOUT'}) | {'PASS' if r['ok'] else 'FAIL'} |")
        row("9 Hot-plug fixes", labels[str(k)], f"LDO IN pk {r['vsys']:.2f} V, inrush {r['qc']*1e6:.0f} uC, drop@500mA {r['drop'][500]:.2f} V, "
            f"LDO IN {r['ldo_in']:.2f} V @USB 4.40 V", "PASS" if r["ok"] else "FAIL", top=False)
    # B is one design whose R is unit spread (0.1..0.6 ohm untripped): it must pass at every R.
    groups = [("A", [0]), ("D (C12 2.2 uF)", [6]), ("B (F1 on VBUS side, any R 0.1-0.6)", [1, 2, 3]),
              ("C 0.5 ohm", [4]), ("C 1.0 ohm", [5]), ("E (C12 4.7u 0603 + 0.75 ohm + C5 4.7u)", [7]),
              ("E' (C12 4.7u 0402 + 0.75 ohm + C5 4.7u)", [8]), ("E'' (C12 10u 0603 + 0.5 ohm + C5 4.7u)", [9])]
    best = next((g for g, ks in groups if all(res[k]["ok"] for k in ks)), None)
    lines.append(f"Smallest passing option (order A, D, B, C 0.5, C 1.0, then E candidates; B must pass at every PTC R): **{best or 'none'}**")
    lines.append("Series-R power at 500 mA (minimum package rating): 0.5 ohm 125 mW -> 0805 (0.125 W, no margin; 1206 preferred), "
                 "0.75 ohm 188 mW -> 1206 (0.25 W), 1.0 ohm 250 mW -> 1206 at its rating (1210/2010 0.5 W preferred).")
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    ks = list(res)
    ax.bar([str(k) for k in ks], [res[k]["vsys"] for k in ks], color=SERIES[0], width=0.6)
    ax.set(xlabel="variant (see table)", ylabel="worst LDO IN peak (V)", title="Hot-plug fix candidates: worst-case LDO IN peak")
    limit(ax, 5.8, "5.8 V target"); limit(ax, 6.0, "6.0 V abs max")
    fig.tight_layout(); fig.savefig(R / "hotplug_fixes.png"); plt.close(fig)
    return "\n".join(lines)


# ---------------------------------------------------------------------------- 10 RC snubber
def snubber():
    vec = compose_vectors((TB / "10_snubber_hotplug.cir").read_text())
    vl = compose_vectors((TB / "10_snubber_loadstep.cir").read_text())

    def label(k, vv=vec):
        if vv["vrs"][k] < 0.01:
            return "reference: C12 4.7u 0402 direct on VSYS, no Rs"
        c = vv["vcd"][k]
        cd = "no Cd" if c < 1e-9 else "Cd 100n" if c < 5e-7 else "Cd 1u"
        return f"Rs {vv['vrs'][k]:g} ohm, {cd}" + (", C5 4.7u" if vv["vc5"][k] < 5e-6 else "")
    hp = {}
    for name, rest in cases("10_snubber_hotplug.log"):
        k = int(dict(kv.split("=") for kv in rest.split())["variant"])
        t, vb, vs, vc, p3, i = load(name)
        rs = vec["vrs"][k]
        pw = (vs - vc) ** 2 / rs
        m50 = t <= 50e-6
        e = np.trapezoid(pw, t)
        hp.setdefault(k, []).append(dict(vsys=vs.max(), vbus=vb.max(), q=np.trapezoid(i - i[-1], t), ppk=pw.max(), e=e,
                                         p50=np.trapezoid(pw[m50], t[m50]) / 50e-6, irms=np.sqrt(np.trapezoid(pw[m50] / rs, t[m50]) / 50e-6)))
    ls = {}
    for name, rest in cases("10_snubber_loadstep.log"):
        k = int(rest.split("=")[1])
        t, vs, p3 = load(name)
        m = (t > 3e-3) & (t < 3.5e-3)
        seg = p3[(t >= 3e-3) & (t < 3.95e-3)]
        tt = t[(t >= 3e-3) & (t < 3.95e-3)]
        out_ = np.nonzero(np.abs(seg - seg[-50:].mean()) > 10e-3)[0]
        ls[k] = dict(v3min=p3[t > 1.5e-3].min(), v3max=p3[t > 1.5e-3].max(), vs_pp=vs[m].max() - vs[m].min(),
                     vs_min=vs[t > 1.5e-3].min(), settle=(tt[out_[-1]] - 3e-3) if len(out_) else 0.0)
    ceff = lambda c0, v0, v=5.0: c0 / (1 + (v / v0) ** 2)
    lines = ["Hot-plug: worst over the 8 corners of 01. Inrush = sim + the charge the linear 3V3 caps undercount. "
             "Rs power: peak instantaneous, energy per plug-in, mean over the first 50 us (steady-state Rs power is ~0: no DC flows). "
             "Load step: 1 uH / 0.1 ohm cable, 5.0 V, 0->50->250->50->0 mA. CIN at 5 V bias: direct = Cd, snubbed = C12 behind Rs.",
             "| Variant | VSYS = LDO IN peak | inrush | Rs P peak | Rs energy | Rs mean P (50 us) | 3V3 min / max on steps | VSYS p-p after 250 mA step | CIN direct / snubbed (eff. @5 V) | verdict |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    res = {}
    for k in sorted(hp):
        cs = hp[k]
        r = dict(vsys=max(c["vsys"] for c in cs), q=max(c["q"] for c in cs) + dq_for(vec["vc5"][k]), ppk=max(c["ppk"] for c in cs),
                 e=max(c["e"] for c in cs), p50=max(c["p50"] for c in cs))
        r["tpulse"] = r["e"] / r["ppk"]
        r["ok"] = r["vsys"] <= 5.8 and r["q"] <= 50e-6
        res[k] = r
        cdir = ceff(vec["vcd"][k], vec["vcd0"][k])
        l = ls[k]
        lines.append(f"| {k}: {label(k)} | {r['vsys']:.2f} V | {r['q']*1e6:.0f} uC | {r['ppk']:.1f} W | {r['e']*1e6:.0f} uJ | {r['p50']*1e3:.0f} mW | "
                     f"{l['v3min']:.3f} / {l['v3max']:.3f} V | {l['vs_pp']*1e3:.0f} mV | {cdir*1e6:.2f} / {ceff(4.7e-6, 3.1)*1e6:.2f} uF | {'PASS' if r['ok'] else 'FAIL'} |")
        row("10 RC snubber", label(k), f"VSYS pk {r['vsys']:.2f} V, inrush {r['q']*1e6:.0f} uC, Rs {r['ppk']:.1f} W pk / {r['e']*1e6:.0f} uJ",
            "PASS" if r["ok"] else "FAIL", top=False)
    ref = ls[max(ls)]
    lines.append(f"| {max(ls)}: {label(max(ls), vl)} (load step only) | - | - | - | - | - | {ref['v3min']:.3f} / {ref['v3max']:.3f} V | {ref['vs_pp']*1e3:.0f} mV | "
                 f"{ceff(4.7e-6, 3.1)*1e6:.2f} / - uF | - |")
    passing = [k for k in res if res[k]["ok"]]
    # prefer a direct cap at LDO IN (TI CIN rule), then the lowest inrush, then the lowest peak
    best = min(passing, key=lambda k: (vec["vcd"][k] < 1e-9, res[k]["q"], res[k]["vsys"])) if passing else None
    lines.append(f"Passing: {'; '.join(label(k) for k in passing) or 'none'}. Best: **{label(best) if best is not None else 'none'}**")
    if best is not None:
        b = res[best]
        lines.append(f"Rs sizing for the best option: {b['ppk']:.1f} W peak, {b['e']*1e6:.0f} uJ per plug-in, equivalent rectangular pulse "
                     f"{b['tpulse']*1e6:.1f} us (E / Ppk). The 0402's 62.5 mW continuous rating is irrelevant (no DC); check the vendor's "
                     "single-pulse curve at that duration, or use an anti-surge/pulse-rated 0603/0805 thick-film part.")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.8))
    for j, k in enumerate(sorted(hp)):
        a1.bar(j, res[k]["vsys"], color=SERIES[int(vec["vcd"][k] > 1e-9) + int(vec["vcd"][k] > 2e-7)], width=0.7)
    a1.set_xticks(range(len(hp)), [str(k) for k in sorted(hp)])
    a1.set(xlabel="variant", ylabel="worst VSYS peak (V)", title="Worst VSYS peak (blue: no Cd, orange: 100n, aqua: 1u)")
    limit(a1, 5.8, "5.8 V target")
    for j, k in enumerate((best if best is not None else 4, max(ls))):
        t, vs, p3 = load(f"snl_{k}")
        m = (t > 2.99e-3) & (t < 3.15e-3)
        a2.plot((t[m] - 3e-3) * 1e6, vs[m], color=SERIES[j], label=f"VSYS, {label(k, vl)}")
    a2.set(xlabel="us after 50 -> 250 mA step", ylabel="V", title="VSYS after the 250 mA load step (1 uH cable)"); a2.legend(fontsize=7)
    fig.tight_layout(); fig.savefig(R / "snubber.png"); plt.close(fig)
    return "\n".join(lines)


# ---------------------------------------------------------------------------- 11 current spec.py
def v13():
    vec = compose_vectors((TB / "11_hotplug_v13.cir").read_text())
    bank = [(4.7e-6, 3.1), (1e-6, 4.04)] + [(100e-9, 6.6)] * 6 + [(1e-6, 4.04)]  # C4, C8, C1-3/C14/C15/C6, C7
    dq = dq_for(None, bank=bank)
    i_d, v_d = load("schottky_dc")
    by = {}
    for name, rest in cases("11_hotplug_v13.log"):
        k = int(dict(kv.split("=") for kv in rest.split())["variant"])
        t, vb, vs, p3, i = load(name)
        by.setdefault(k, []).append(dict(vsys=vs.max(), vbus=vb.max(), q=np.trapezoid(i - i[-1], t), ipk=i.max()))
    RDO = 0.238 / 0.5  # TLV755 DRV max dropout 238 mV at 500 mA, as a resistance
    lines = [f"Current spec.py path: VBUS -> R12 -> D2 -> VSYS (C12 4.7u 0402) ; 3V3 bank C4 4.7u + C8 + 100 nF (no C5). "
             f"Inrush = sim + {dq*1e6:.1f} uC the linear 3V3 caps undercount. LDO IN = Vsrc - I*R12 - VF(I) (typ VF, 25 C); "
             "regulates if >= 3.3 V + 0.476 ohm * I (TLV755 max dropout).",
             "| R12 | LDO IN peak | VBUS peak | I pk | inrush | drop 250 / 500 mA | LDO IN @4.40 V: 250 / 500 mA | LDO IN @4.75 V: 250 / 500 mA | R12 P @300 / 500 mA | verdict |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for k in sorted(by):
        cs, r12 = by[k], vec["vrs"][k]
        pk, vbp, q = max(c["vsys"] for c in cs), max(c["vbus"] for c in cs), max(c["q"] for c in cs) + dq
        drop = {ma: ma / 1e3 * r12 + float(np.interp(ma / 1e3, i_d, v_d)) for ma in (250, 500)}
        cell, ok_reg = {}, True
        for vsrc in (4.40, 4.75):
            vals = []
            for ma in (250, 500):
                lin = vsrc - drop[ma]
                good = lin >= 3.3 + RDO * ma / 1e3
                ok_reg &= good if vsrc == 4.40 else True
                vals.append(f"{lin:.2f}{'' if good else ' (DROPOUT)'}")
            cell[vsrc] = " / ".join(vals)
        ok = pk <= 5.8 and q <= 50e-6
        vd = "PASS" if ok and ok_reg else ("PASS (hot-plug) / FAIL (500 mA @4.40 V)" if ok else "FAIL")
        lab = f"{r12:g} ohm" + (" (as built)" if k == 0 else "")
        lines.append(f"| {lab} | {pk:.2f} V | {vbp:.2f} V | {max(c['ipk'] for c in cs):.1f} A | {q*1e6:.0f} uC | {drop[250]:.2f} / {drop[500]:.2f} V | "
                     f"{cell[4.40]} V | {cell[4.75]} V | {0.09*r12*1e3:.0f} / {0.25*r12*1e3:.0f} mW | {vd} |")
        txt = f"LDO IN pk {pk:.2f} V, VBUS pk {vbp:.2f} V, inrush {q*1e6:.0f} uC, LDO IN @4.40 V/500 mA {4.40-drop[500]:.2f} V"
        if k == 0:
            row("1 Hot-plug", "As built (bench 11): R12 1 ohm, C12 4.7u 0402, C4 4.7u; LDO IN peak <= 5.8 V, inrush <= 50 uC",
                txt, "PASS" if ok else "FAIL", key=1.0)
            row("1 Hot-plug", "As built: 3V3 at 500 mA from USB 4.40 V (above the 250 mA thermal budget)",
                f"LDO IN {4.40-drop[500]:.2f} V vs {3.3 + RDO*0.5:.3f} V needed (max dropout); 3V3 ~{4.40-drop[500]-RDO*0.5:.2f} V",
                "PASS" if ok_reg else "MARGIN", key=1.0)
        row("11 Hot-plug v1.3 current", f"R12 = {lab}: LDO IN peak <= 5.8 V, inrush <= 50 uC, 500 mA @4.40 V", txt, vd, top=False)
    return "\n".join(lines)


# ---------------------------------------------------------------------------- 12 J1.1 hot-plug + long cables
def j11():
    """Bench 12: supply hot-plugged onto J1.1 (R12 not in that path) and 1.5-3 uH USB cables. U2 is passive
    (Iq only). The same peaks are scored against the old TLV755 6.0 V limit (not fitted) and the fitted
    TLV76733 (18 V; the table uses Q1's 12 V VGS). Do not label the 6.0 V score as as-built."""
    jc, uc = {}, {}
    for name, rest in cases("12_j11_hotplug.log"):
        p = dict(kv.split("=") for kv in rest.split())
        t, vb, vs, v5, vh, iu, ih = load(name)
        pk = max(vs.max(), v5.max())
        if p["src"] == "1":
            jc.setdefault((float(p["V"]), float(p["L"]), float(p["R"]), float(p["RF1"])), {})[int(p["CM"])] = pk
        else:
            k = (float(p["V"]), float(p["L"]), float(p["R"]))
            uc[k] = max(uc.get(k, 0), vs.max())
    vd = lambda v, lim: "PASS" if v <= lim else "FAIL"
    lines = ["J1.1 hot-plug, USB unplugged: stiff supply stepped onto J1.1 through leads L/R, then Q1 -> F1 -> VSYS "
             "(C12 4.7u 0402 + U2 IN/EN). Peak = max(VSYS, 5V_F). Bias = sim/ C12 fit (V0 3.1, extrapolated above 10 V); "
             "linear = 1.3 uF fixed. Limits: TLV755 VIN/EN 6.0 V (old part, not fitted); fitted TLV76733DRVR: Q1 VGS +-12 V (= -V(5V_F)), C12/F1 16 V. The 6.0 V column is not the current board.",
             "| Supply | Leads L / R | F1 | Peak, bias C12 | Peak, linear 1.3 uF | TLV755 6.0 V (not fitted) | Fitted TLV76733 (12 V gate) |",
             "|---|---|---|---|---|---|---|"]
    for (v, l, r, f), d in sorted(jc.items()):
        hi = max(d.values())
        lines.append(f"| {v:g} V | {l*1e6:g} uH / {r:g} ohm | {f:g} ohm | {d[0]:.2f} V | {d[1]:.2f} V | {vd(hi, 6.0)} | {vd(hi, 12.0)} |")
    lines += ["", "USB hot-plug with long cables (U3 BV 6 / 9 V, worst of the two), bias-dependent C12, J1.1 open:",
              "| VBUS source | Cable L / R | LDO IN peak | TLV755 6.0 V (not fitted) | Fitted TLV76733 (12 V gate) |", "|---|---|---|---|---|"]
    for (v, l, r), pk in sorted(uc.items()):
        lines.append(f"| {v:g} V | {l*1e6:g} uH / {r:g} ohm | {pk:.2f} V | {vd(pk, 6.0)} | {vd(pk, 12.0)} |")
    bias = [d[0] for d in jc.values()]; lin = [d[1] for d in jc.values()]
    n_ok = sum(max(d.values()) <= 6.0 for d in jc.values())
    row("12 J1.1 hot-plug", "Old TLV755 limit, not fitted: 5.0 / 5.5 V supply plugged onto J1.1 (leads 0.1-2 uH, F1 0.1 / 0.3 ohm); VSYS <= 6.0 V. Fitted part is the TLV76733 row in the second table (MARGIN)",
        f"VSYS pk {min(lin):.2f}..{max(lin):.2f} V (linear C12), up to {max(bias):.1f} V (bias C12); {n_ok} of {len(jc)} corners <= 6.0 V",
        "PASS" if n_ok == len(jc) else "FAIL (against 6.0 V only)", key=1.1)
    u525 = max(pk for (v, l, r), pk in uc.items() if v == 5.25 and l <= 2e-6)
    u_all = max(uc.values())
    row("12 J1.1 hot-plug", "Old TLV755 limit, not fitted: USB hot-plug, 1.5-3 uH cables (2-4 m), 5.25 / 5.5 V; LDO IN <= 6.0 V. Fitted TLV76733 score for this peak is PASS (<= 12 V)",
        f"<= 2 uH at 5.25 V: {u525:.2f} V; worst (3 uH, 5.5 V): {u_all:.2f} V",
        ("PASS" if u_all <= 5.8 else "MARGIN" if u525 <= 6.0 else "FAIL") + " (against 6.0 V only)", key=1.1)
    over = sum(b > 12.0 for b in bias)
    row("12 J1.1 hot-plug", "U2 -> TLV76733 (18 V) + C12 16 V: J1.1 hot-plug peak <= 12 V (Q1 VGS)",
        f"linear C12 max {max(lin):.2f} V; bias C12 max {max(bias):.2f} V ({over} of {len(bias)} corners > 12 V, all 1-2 uH with F1 at 0.1-0.3 ohm)",
        "PASS" if max(bias) <= 12 else "MARGIN" if max(lin) <= 12 else "FAIL", top=False, key=12.0)
    row("12 J1.1 hot-plug", "U2 -> TLV76733: USB hot-plug with 1.5-3 uH cables <= 12 V", f"worst {u_all:.2f} V",
        vd(u_all, 12.0), top=False, key=12.1)
    return "\n".join(lines)


def main():
    hp, hp_all = hotplug()
    sections = [("1 USB hot-plug (hotplug_variants.png, hotplug_base.png)", hp), ("2 LDO (ldo_steps.png)", ldo()),
                ("3 Brown-out (brownout.png)", brownout()), ("4 NRST / BOOT0 (nrst.png)", nrst())]
    led_txt, best = led()
    sections += [("5 LEDs (led_r6.png) - as built R6 = 330 ohm", led_txt), ("6 I2C (i2c.png)", i2c()),
                 ("7 Crystal (analytic, xtal.py)", crystal()), ("8 VDDA filter (vdda.png)", vdda()),
                 ("9 Hot-plug fix candidates (hotplug_fixes.png)", hotplug_fixes()),
                 ("10 C12 as RC snubber (snubber.png)", snubber()),
                 ("11 Hot-plug, current spec.py power path (R12 + C12 4.7u 0402, no C5)", v13()),
                 ("12 Hot-plug into J1.1 and long USB cables (U2 passive)", j11())]
    top = sorted((r for r in ROWS if r[4]), key=lambda r: r[5])
    other = sorted((r for r in ROWS if not r[4]), key=lambda r: r[5])
    table = ["| Test | Check | Result | Verdict |", "|---|---|---|---|"] + [f"| {a} | {b} | {c} | **{d}** |" for a, b, c, d, *_ in top]
    md = ["# NickLink v1.3 SPICE results", "", "Generated by `sim/run.sh` (ngspice 42 in Docker + analyze.py). Do not edit by hand.", "",
          "## As-built v1.3 board (current tools/spec.py)", "",
          "The rail in this table (R12 1 ohm, C12 4.7 µF 0402, R6 330 ohm) is the fitted board. "
          "Bench 12 rows that score VSYS against 6.0 V are the old TLV755 limit, not the fitted TLV76733DRVR (18 V). "
          "The fitted-part scores are in the second table: \"U2 -> TLV76733\" (J1.1 hot-plug **MARGIN**, long USB cables **PASS**). "
          "Peaks were not re-run.",
          ""] + table
    md += ["", "## Fix studies and v1.3-original comparisons", "", "| Test | Check | Result | Verdict |", "|---|---|---|---|"]
    md += [f"| {a} | {b} | {c} | **{d}** |" for a, b, c, d, *_ in other]
    for title, body in sections:
        md += ["", f"## {title}", ""]
        prev_tab = False
        for l in body.splitlines():
            tab = l.startswith("|")
            if tab != prev_tab and md[-1] != "":
                md.append("")
            md.append(l if tab else f"- {l}")
            prev_tab = tab
    md += ["", "## Hot-plug, every corner", "", hp_all, ""]
    (R / "summary.md").write_text("\n".join(md))
    # README headline table between markers
    readme = Path(__file__).parent / "README.md"
    txt = readme.read_text()
    a, b = "<!-- results:start -->", "<!-- results:end -->"
    if a in txt and b in txt:
        readme.write_text(txt[:txt.index(a) + len(a)] + "\n" + "\n".join(table) + "\n" + txt[txt.index(b):])
    for a, b, c, d, *_ in top + other:
        print(f"{d:7s} {a:14s} {b[:70]:70s} {c}")


if __name__ == "__main__":
    main()
