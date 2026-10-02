"""07 HSE crystal: AN2867 gain margin, load capacitance, pulling and drive level (analytic).

The F103 HSE oscillator can't be meaningfully SPICEd without ST's transistor-level model,
so this follows ST AN2867. Inputs: YXC X32258MOB4SI (8 MHz, CL 12 pF, ESR <= 150 ohm,
C0 <= 3 pF, C1 (motional) <= 5 fF, drive level <= 100 uW), C10/C11 = 15 pF C0G,
stray Cs = 3..5 pF (assumed), STM32F103 HSE gm >= 25 mA/V (DS5319, start-up).
Run directly for a printout; analyze.py imports results().
"""
from math import pi, sqrt

F, ESR, C0, CM, CL_SPEC, DL_MAX = 8e6, 150.0, 3e-12, 5e-15, 12e-12, 100e-6
C_EXT, CS, GM = 15e-12, (3e-12, 5e-12), 25e-3


def gm_crit(esr=ESR, f=F, c0=C0, cl=CL_SPEC):
    return 4 * esr * (2 * pi * f) ** 2 * (c0 + cl) ** 2


def cl_actual(cs):
    return C_EXT * C_EXT / (2 * C_EXT) + cs


def pulling_ppm(cl):
    """Frequency offset vs. the CL the crystal was cut for (positive = runs fast)."""
    return CM / 2 * (1 / (C0 + cl) - 1 / (C0 + CL_SPEC)) * 1e6


def drive_level(vpp, cs=4e-12, esr=ESR):
    """AN2867: DL = ESR * I_rms^2, I_rms = pi*F*Vpp*Ctot/sqrt(2), Ctot = C_ext + Cs/2."""
    ctot = C_EXT + cs / 2
    return esr * (pi * F * vpp * ctot) ** 2 / 2


def vpp_for_dl(dl=DL_MAX, cs=4e-12, esr=ESR):
    return sqrt(2 * dl / esr) / (pi * F * (C_EXT + cs / 2))


def results():
    g = gm_crit()
    return {
        "gm_crit_mA_V": g * 1e3,
        "gain_margin": GM / g,
        "gain_margin_180ohm": GM / gm_crit(esr=180),
        "cl_actual_pF": [cl_actual(c) * 1e12 for c in CS],
        "pull_ppm": [pulling_ppm(cl_actual(c)) for c in CS],
        "dl_uW_3v3pp": drive_level(3.3) * 1e6,
        "dl_uW_2vpp": drive_level(2.0) * 1e6,
        "vpp_at_100uW": vpp_for_dl(),
        "rext_start_ohm": 1 / (2 * pi * F * C_EXT),
    }


if __name__ == "__main__":
    r = results()
    # self-check against the hand calculation in tools/parts_research.md (0.34 mA/V, margin ~73)
    assert abs(r["gm_crit_mA_V"] - 0.341) < 0.005 and 70 < r["gain_margin"] < 76, r
    assert abs(drive_level(r["vpp_at_100uW"]) - DL_MAX) < 1e-9
    for k, v in r.items():
        print(f"{k:20s} {v}")
