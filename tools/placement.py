"""Component placement for NickLink. Local mm coords: origin = board top-left, X right, Y down.

Each header has a 1.4 mm silkscreen label strip on both sides (outer: along the
board edge, inner: between header and the middle component area).
"""
OX, OY = 100.0, 100.0          # board origin in KiCad coordinates
LBL = 1.4                      # label strip width: 1.0 mm text (JLC minimum) rotated + clearance
PIN_OUT = LBL + 1.27           # outer header pin column, from board edge
PIN_IN = PIN_OUT + 2.54        # inner header pin column
MID = PIN_IN + 1.27 + LBL      # middle component area starts here (from either edge)
W = round(2 * MID + 2.04 + 10.05 + 2.04 + 4.1, 2)   # hole + USB + hole across the top
H, CORNER = 25.5, 0.5
L, R, c = MID, W - MID, W / 2  # middle area left/right edges, centre
hy = (H - 22.86) / 2           # header pin-1 row
my = 16.2                      # MCU centre
X0 = 16.595                    # centre x the hand-tuned absolute x values below were made for
dx = lambda x: round(c - X0 + x, 3)
mx = c - 0.25                  # MCU centre: 0.25 mm left of the board centre, so fan-out vias fit
dxm = lambda x: round(mx - X0 + x, 3)   # hand-tuned x values tied to the MCU

FP_OVERRIDE = {h: "MountingHole:MountingHole_2.2mm_M2_ISO7380" for h in ("H1", "H2", "H3", "H4")}

PLACE = {
    # headers: pin 1 position
    "J3": (PIN_OUT, hy, 0),
    "J1": (W - PIN_IN, hy, 0),
    # mounting holes
    "H1": (L + 2.05, 2.05, 0), "H2": (R - 2.05, 2.05, 0),
    "H3": (L + 2.05, H - 2.05, 0), "H4": (R - 2.05, H - 2.05, 0),
    # USB (footprint origin = pad A1); row below it: ESD, CC, pull-up, diode
    "J2": (c + 2.975, 6.625, 180),
    "U3": (c - 0.6, 9.27, 270),
    "C13": (c + 1.1, 9.8, 90),
    "R5": (c - 3.2, 8.6, 0),
    "R2": (c - 3.2, 9.7, 0),
    "D2": (R - 2.06, 5.1, 0),
    # Schottky in the right pocket, LDO in the row below USB
    "U2": (c + 4.1, 9.3, 0),
    "C12": (R - 2.01, 6.9, 0),   # 10 uF 0603, right pocket under D2
    "R4": (R - 1.2, 10.73, 0),   # CC1 pull-down, above RESET
    # LED resistors in the left pocket, LEDs + labels below it
    "D1": (L + 3.6, 8.6, 0), "R3": (L + 1.13, 5.3, 0),
    "D3": (L + 3.6, 9.8, 0), "R6": (L + 3.13, 5.3, 0),
    # MCU + decoupling
    "U1": (mx, my, 90),
    "C3": (c - 4.5, 11.5, 90),
    "C2": (dxm(20.95), 12.0, 90),
    "C4": (L + 2.85, my + 2.75, 90),
    "C1": (dxm(12.3), 20.6, 90),
    "R12": (L + 2.0, 6.7, 180),  # hot-plug damping resistor, left pocket below R3/R6 (pad 1 = VBUS, right)
    "R8": (R - 2.71, 9.3, 90),
    # clock row under the MCU
    "Y1": (mx - 1.5, 23.2, 0),
    "C10": (mx - 4.2, 23.4, 90),
    "C11": (mx + 1.2, 23.2, 90),
    "C6": (mx + 2.3, 22.6, 90),
    "C7": (mx + 3.4, 22.6, 90),
    "C9": (mx + 4.5, 22.6, 90),
    "R10": (dxm(21.1), 20.4, 270),  # MCU courtyard bottom-right notch: IMU INT1 (top) -> PA0 (bottom)
    # BOOT0 button beside its pin (left), RESET on the right
    "SW2": (L + 1.7, 13.9, 90), "R1": (L + 1.4, 17.4, 90),
    "SW1": (R - 1.7, 13.7, 90),
}

PLACE.update({
    # IMU in the right channel below RESET; its caps in a row underneath
    "U4": (R - 2.0, 18.0, 0),
    "C14": (R - 2.95, 20.35, 0), "C15": (R - 1.0, 20.35, 0),
    # I2C1 pull-ups in the left channel, beside the PB6/PB7 pins
    "R7": (L + 1.2, 19.0, 0), "R9": (L + 1.2, 20.15, 0),
})

# Offsets found with NICKLINK_SEED=13 (see below): nudges of up to 0.1 mm that let Freerouting
# route 100% with short crystal/USB nets. Re-run the seed search if you move parts here.
PLACE.update({
    "R2": (dx(13.294), 9.658, 0), "R5": (dx(13.411), 8.601, 0), "D1": (dx(10.93), 8.25, 0),
    "D3": (dx(11.093), 9.62, 0), "R3": (dx(8.71), 5.17, 0), "R6": (dx(10.623), 5.198, 0),
    "C3": (dxm(11.989), 11.407, 90), "C13": (dx(17.706), 9.907, 90), "C8": (dx(18.764), 9.216, 270),  # beside U2 OUT (pin 1) / GND (pin 3)
    "R7": (dx(8.609), 19.074, 0), "R9": (dx(8.742), 20.211, 0), "FB1": (dx(21.165), 20.449, 90),
    "U4": (dx(23.8), 17.71, 0), "FB1": (dx(22.22), 20.45, 90), "C14": (dx(23.32), 20.45, 270), "C15": (dx(24.82), 20.45, 270),
    "SW1": (dx(24.023), 13.686, 90),
})

# Seed 3 of the post-review layout (2026-10-01): these nudges (<= 0.1 mm) route 100%.
PLACE.update({
    "R2": (dx(13.242), 9.667, 0), "R5": (dx(13.385), 8.622, 0), "D1": (dx(10.955), 8.163, 0),
    "C3": (dx(11.642), 11.474, 90), "C13": (dx(17.658), 9.854, 270), "C8": (dx(18.863), 9.21, 270),  # C13 VBUS pad up, toward J2.A4
    "R7": (dx(8.676), 19.069, 0), "R9": (dx(8.77), 20.141, 0), "SW1": (dx(24.05), 13.76, 90),
})

# v1.4 power fixes (tools/_work/fix_power/PROPOSAL.md). Right pocket, top to bottom:
# D2 (vertical, anode up) | Q1 (5V-pin P-FET); F1 (PTC); C12 (LDO input) and R8; R4 beside them.
PLACE.update({
    "D2": (R - 3.135, 5.845, 90), "Q1": (R - 1.08, 5.705, 90),
    "F1": (R - 1.835, 8.405, 0),
    "C12": (R - 2.71, 9.83, 0), "R8": (R - 2.71, 10.8, 0), "R4": (R - 0.51, 10.4, 90),
    "R11": (dx(13.2), 10.585, 0), # D+ divider bottom, between R2 and the MCU top-row pads (5 um courtyard gaps)
    "R2": (dx(13.242), 9.65, 0),  # 0.017 mm up (was 9.667) so R11 fits under it
})

# Seed 12 of the reliability-pass layout (2026-10-02), baked in (the board was then finished with
# tools/fixroute.sh: IMU/C2 3V3 feed and R5's GND via).
PLACE.update({
    "R5": (dx(13.38), 8.653, 0), "C3": (dx(11.675), 11.403, 90),
    "R7": (dx(8.578), 19.044, 0), "R9": (dx(8.725), 20.203, 0),
})

# Freerouting is deterministic but placement-sensitive. NICKLINK_SEED=<n> nudges a few
# small top-area parts by up to +-0.1 mm to search for a fully routed result; the winning
# offsets are then baked into PLACE above.
import os as _os
import random as _random
if _os.environ.get("NICKLINK_IMU_ROT"):
    _x, _y, _ = PLACE["U4"]
    PLACE["U4"] = (_x, _y, int(_os.environ["NICKLINK_IMU_ROT"]))
if _os.environ.get("NICKLINK_SEED"):
    _rng = _random.Random(int(_os.environ["NICKLINK_SEED"]))
    for _r in ("R5", "C3", "R7", "R9"):  # C13/C8/SW1/D1 not nudged: locked tracks, R4 / J2 clearance
        _x, _y, _a = PLACE[_r]
        PLACE[_r] = (round(_x + _rng.uniform(-0.1, 0.1), 3), round(_y + _rng.uniform(-0.1, 0.1), 3), _a)

# Pre-routed, locked F.Cu tracks laid before autorouting: (net, width, [(x, y), ...]).
# Crystal nets stay short, top-layer only and via-free regardless of Freerouting.
# Coordinates follow the U1 / Y1 / C10 / C11 positions above; re-derive if those move.
PREROUTE = [
    ("/HSE_IN", 0.2, [(dxm(15.845), 20.6), (dxm(15.845), 21.35), (dxm(13.0), 21.35), (dxm(13.0), 24.05), (dxm(13.995), 24.05)]),
    ("/HSE_IN", 0.2, [(dxm(13.0), 23.88), (dxm(12.395), 23.88)]),
    ("/HSE_OUT", 0.2, [(dxm(16.345), 20.6), (dxm(16.345), 22.35), (dxm(16.195), 22.35)]),
    ("/HSE_OUT", 0.2, [(dxm(16.195), 22.35), (dxm(17.19), 22.35), (dxm(17.19), 23.68), (dxm(17.795), 23.68)]),
]

# Silkscreen pin-1 dots (x, y, radius) for footprints used without their own silk
SILK_DOTS = []

# Rule areas: (layer, (x0, y0, x1, y1)). pcbnew layer ids: F.Cu = 0.


# Front labels for parts: (text, x, y, angle, justify -1 left / 0 centre)
LABELS = [
    ("PWR", L + 0.15, 8.25, 0, -1),
    ("C13", L + 0.15, 9.62, 0, -1),
    ("BOOT", L + 1.7, 11.0, 0, 0),
    ("RST", R - 3.5, 13.7, 90, 0),
]

# IMU keep-out (inside its pad ring) and pin-1 dot, following its final position/rotation
_ux, _uy, _ur = PLACE["U4"]
_kx, _ky = (0.8, 0.55) if _ur % 180 == 0 else (0.55, 0.8)
_bx, _by = (1.5, 1.25) if _ur % 180 == 0 else (1.25, 1.5)
KEEPOUTS = [(0, (_ux - _kx, _uy - _ky, _ux + _kx, _uy + _ky), "all"),
            (0, (_ux - _bx, _uy - _by, _ux + _bx, _uy + _by), "pour")]
_p1 = {0: (-1.75, -0.6), 90: (-1.35, 1.45), 180: (1.45, 1.35), 270: (1.35, -1.45)}[_ur % 360]  # pad 1 corner
SILK_DOTS.append((_ux + _p1[0], _uy + _p1[1], 0.15))

# IMU local fan-out, pre-routed and locked (the LGA's perimeter pin order G G G INT1 VDDIO G G
# VDD INT2 x x CS SCL SDA can't fan out on one layer). Topology:
#  - left GND pads 1-3 go up-left to a GND via above the package;
#  - bottom GND pads 6-7 drop into a GND via just below them;
#  - one 3V3 rail runs under that via, joining VDDIO (5), VDD (8, via CS/OCS/SDO_Aux around INT2)
#    and the 3V3 pads of FB1, C14, C15, which sit on the rail in a row (their GND pads face down);
#  - INT1 (4) runs diagonally down-left to R10 in the MCU courtyard notch.
# Pad centres relative to U4 at 0 deg: 1-4 left (-1.163, -0.75..0.75), 5-7 bottom (-0.5..0.5, 0.912),
# 8-11 right (1.163, 0.75..-0.75), 12-14 top (0.5..-0.5, -0.912).
_p = lambda x, y: (round(_ux + x, 3), round(_uy + y, 3))
_rail = round(_uy + 2.22, 3)                       # 3V3 rail y
_gvia = _p(0.25, 1.54)                             # GND via under pads 6/7
_fbx, _c14x, _c15x = PLACE["FB1"][0], PLACE["C14"][0], PLACE["C15"][0]
_r10x, _r10y = PLACE["R10"][0], PLACE["R10"][1]
PREROUTE += [
    ("GND", 0.25, [_p(-1.163, 0.25), _p(-1.163, -0.75), _p(-1.6, -1.6)]),     # pads 3-2-1 -> via above-left
    ("GND", 0.25, [_p(0, 0.912), _gvia, _p(0.5, 0.912)]),                     # pads 6, 7 -> via below
    ("+3.3V", 0.25, [_p(-0.5, 0.912), (_ux - 0.5, _rail)]),                   # VDDIO down to the rail
    ("+3.3V", 0.25, [_p(0.5, -0.912), _p(1.163, -0.75), _p(1.163, -0.25),     # CS -> 11 -> 10
                     _p(1.75, -0.25), _p(1.75, 0.75), _p(1.163, 0.75)]),      # around INT2 (9) -> VDD (8)
    ("+3.3V", 0.25, [_p(1.163, 0.75), _p(1.35, 0.94), (_ux + 1.35, _rail)]),  # VDD down to the rail
    ("+3.3V", 0.25, [(_fbx, _rail), (_ux + 1.35, _rail)]),                    # the rail
    ("/IMU_INT1", 0.2, [_p(-1.163, 0.75), (_r10x, _r10y - 0.48)]),            # INT1 -> R10 (in the notch)
]
PREVIAS = [("GND", _p(-1.6, -1.6)), ("GND", _gvia)]
# B.Cu GND link from the IMU's left GND via in under the MCU body (solid GND on both layers);
# the MCU's right-side fan-out vias all sit to the right of this path.
PREROUTE_B = [("GND", 0.3, [_p(-1.6, -1.6), (round(mx + 1.5, 3), _p(-1.6, -1.6)[1])])]
PREVIAS += [("GND", (round(mx + 1.5, 3), _p(-1.6, -1.6)[1]))]  # ties the link into the MCU's inner F.Cu GND

# --- v1.4 power pre-routes (PROPOSAL.md items 1, 2, 6); all derived from the positions above ---
_d2x, _d2y, _ = PLACE["D2"]; _q1x, _q1y, _ = PLACE["Q1"]; _f1x, _f1y, _ = PLACE["F1"]
_c12x, _c12y, _ = PLACE["C12"]; _r8x, _r8y, _ = PLACE["R8"]
_jx, _jy, _ = PLACE["J2"]; _j1x, _j1y, _ = PLACE["J1"]; _u2x, _u2y, _ = PLACE["U2"]
_r12x, _r12y, _ = PLACE["R12"]
_r = lambda *p: tuple(round(v, 3) for v in p)
_d2a, _d2k = _r(_d2x, _d2y - 1.05), _r(_d2x, _d2y + 1.05)          # SOD-323 at 90: anode up
_qg, _qs, _qd = _r(_q1x - 0.65, _q1y + 0.887), _r(_q1x + 0.65, _q1y + 0.887), _r(_q1x, _q1y - 0.887)
_f11, _f12 = _r(_f1x - 0.938, _f1y), _r(_f1x + 0.938, _f1y)
_trunk = round(_u2x + 1.365, 3)                                      # VSYS trunk, 0.14 mm off U2 NC pad 5
_gq, _gc = _r(_f11[0] + 0.513, _f1y - 1.155), _r(_c12x + 1.25, _c12y + 0.52)   # GND vias: Q1 gate; C12/R8
PREROUTE += [
    # VBUS (J2.A9, left end) -> R12 -> VBUS_D, which runs up the pocket's left edge and under the USB
    # body at y = 4.0 (between the shield slots) to D2's anode.
    ("VBUS", 0.3, [_r(_jx - 5.1, _jy), _r(_jx - 5.1, 7.4), _r(_r12x + 1.15, 7.4), _r(_r12x + 0.9125, _r12y)]),
    ("VBUS", 0.2, [_r(PLACE["R2"][0] - 1.062, 7.4), _r(PLACE["R2"][0] - 1.062, PLACE["R2"][1]), _r(PLACE["R2"][0] - 0.51, PLACE["R2"][1])]),  # -> R2.1 (D+ pull-up), between D1/D3 and R5
    ("/VBUS_D", 0.25, [_r(_r12x - 0.9125, _r12y), _r(L + 0.12, _r12y), _r(L + 0.12, 3.65), _r(_d2x, 3.65), _d2a]),
    ("/VSYS", 0.3, [_d2k, _r(_d2x, _d2k[1] + 0.448), _r(_f11[0], _d2k[1] + 0.81), _f11]),     # D2.K -> F1.1
    ("/VSYS", 0.3, [_r(_d2x, _d2k[1] + 0.448), _r(_trunk, _d2k[1] + 0.963), _r(_trunk, _u2y + 0.65), _r(_u2x + 0.888, _u2y + 0.65)]),  # -> U2 EN (4)
    ("/VSYS", 0.3, [_r(_trunk, _u2y - 0.65), _r(_u2x + 0.888, _u2y - 0.65)]),                  # -> U2 IN (6)
    ("/VSYS", 0.3, [_r(_trunk, _c12y), _r(_c12x - 0.48, _c12y)]),                              # -> C12.1
    ("/5V_F", 0.3, [_f12, _r(_f12[0], _f1y - 0.895), _r(_qs[0], _f1y - 1.347), _qs]),          # F1.2 -> Q1.S
    ("+5V", 0.3, [_qd, _r(_q1x, 4.15), _r(_q1x + 2.83, _j1y), (_j1x, _j1y)]),                 # Q1.D -> J1.1 (45 deg past H2)
    ("GND", 0.25, [_qg, _gq]),                                                                 # Q1 gate -> GND via
    ("GND", 0.25, [_r(_c12x + 0.48, _c12y), _gc]), ("GND", 0.25, [_r(_r8x + 0.51, _r8y), _gc]),
]
PREVIAS += [("GND", _gq), ("GND", _gc)]

# Item 2: USBLC6 (U3) GND pin 2 gets a via; VBUS pin 5 -> C13.1 (top) -> J2.A4 locked; C13 GND -> C8 GND.
_u3x, _u3y, _ = PLACE["U3"]; _c13x, _c13y, _ = PLACE["C13"]; _c8x, _c8y, _ = PLACE["C8"]
_gu3 = _r(_u3x - 0.245, _u3y - 1.72)
PREROUTE += [
    ("GND", 0.25, [_r(_u3x, _u3y - 0.925), _gu3]),
    ("GND", 0.25, [_r(_c13x, _c13y + 0.48), _r(_c13x + 0.55, _c13y + 0.48), _r(_c8x, _c8y + 0.48)]),
    ("VBUS", 0.3, [_r(_c13x, _c13y - 0.48), _r(_c13x, _c13y - 1.25), _r(_jx - 0.85, _c13y - 2.31), _r(_jx - 0.85, _jy)]),
    ("VBUS", 0.3, [_r(_u3x, _u3y + 0.925), _r(_u3x, _u3y + 0.532), _r(_u3x + 0.217, _u3y + 0.315),
                   _r(_u3x + 0.914, _u3y + 0.315), _r(_c13x, _c13y - 0.48)]),
]
PREVIAS += [("GND", _gu3)]

# J2 orientation ties: VBUS B4-A9 / B9-A4 straight on F.Cu plus a B.Cu cross-link above the B row;
# D+ B6-A6 on B.Cu and D- A7-B7 on F.Cu, crossing between the pin rows.
_jb = round(_jy - 1.35, 3)
PREROUTE += [
    ("VBUS", 0.3, [_r(_jx - 5.1, _jb), _r(_jx - 5.1, _jy)]),
    ("VBUS", 0.3, [_r(_jx - 0.85, _jb), _r(_jx - 0.85, _jy)]),
    ("/USB_D-", 0.2, [_r(_jx - 3.4, _jy), _r(_jx - 2.55, _jb)]),
]
PREROUTE_B += [
    ("VBUS", 0.3, [_r(_jx - 5.1, _jb), _r(_jx - 5.1, 4.2), _r(_jx - 0.85, 4.2), _r(_jx - 0.85, _jb)]),
    ("/USB_D+", 0.2, [_r(_jx - 3.4, _jb), _r(_jx - 2.55, _jy)]),
]

# GND vias for two pads the v1.4 parts boxed in: R3.1 (VBUS_D above/left, R12 below) and VSS_2 (pin 35,
# R11 above it), the latter into the MCU's inner area.
_r3x, _r3y, _ = PLACE["R3"]
_gr3, _g35 = _r(_r3x - 0.51, _r3y - 0.82), _r(mx - 2.25, my - 2.7)
PREROUTE += [("GND", 0.25, [_r(_r3x - 0.51, _r3y), _gr3]), ("GND", 0.25, [_r(mx - 2.25, my - 3.5), _g35])]
PREVIAS += [("GND", _gr3), ("GND", _g35)]


# Item 6: C2 (VDD pin 24) GND straight to VSS pin 23 round the end of pin 24; C2.1's 3V3 feed moves to a
# via in the MCU corner (the old feed from the right is what cut C2's GND off from pin 23).
_c2x, _c2y, _ = PLACE["C2"]
_p24, _p23 = _r(mx + 4.162, my - 2.75), _r(mx + 4.162, my - 2.25)
_v33 = _r(_c2x - 0.75, _c2y + 0.8)
PREROUTE += [
    ("GND", 0.25, [_r(_c2x, _c2y - 0.48), _r(_c2x + 0.65, _c2y - 0.48), _r(_c2x + 0.82, _c2y - 0.31),
                   _r(_c2x + 0.82, _p23[1]), _r(_p23[0] + 0.593, _p23[1])]),
    ("+3.3V", 0.3, [_r(_c2x, _c2y + 0.48), _r(_c2x, _p24[1] - 0.193), _p24]),
    ("+3.3V", 0.3, [_v33, _r(_c2x - 0.43, _c2y + 0.48), _r(_c2x, _c2y + 0.48)]),
]
PREVIAS += [("+3.3V", _v33)]

# IMU bottom GND (pads 6/7 via) -> B.Cu -> via between C14/C15 GND pads: short decoupling return.
_c14y = PLACE["C14"][1]
_gcap = _r((PLACE["C14"][0] + PLACE["C15"][0]) / 2, _c14y + 0.48)
PREROUTE += [("GND", 0.25, [_r(PLACE["C14"][0], _c14y + 0.48), _gcap, _r(PLACE["C15"][0], _c14y + 0.48)])]
PREROUTE_B += [("GND", 0.3, [_gvia, _gcap])]
PREVIAS += [("GND", _gcap)]

