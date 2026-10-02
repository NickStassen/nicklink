"""Component placement for NickLink. Local mm coords: origin = board top-left, X right, Y down.

Each header has a 1.2 mm silkscreen label strip on both sides (outer: along the
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
    "C5": (L + 2.0, 6.75, 0),  # left pocket, below R3/R6
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
    "U4": (dx(23.8), 17.71, 0), "FB1": (dx(22.22), 20.45, 90), "C14": (dx(23.32), 20.45, 270), "C15": (dx(24.52), 20.45, 270),
    "SW1": (dx(24.023), 13.686, 90),
})

# Seed 3 of the post-review layout (2026-10-01): these nudges (<= 0.1 mm) route 100%.
PLACE.update({
    "R2": (dx(13.242), 9.667, 0), "R5": (dx(13.385), 8.622, 0), "D1": (dx(10.955), 8.163, 0),
    "C3": (dx(11.642), 11.474, 90), "C13": (dx(17.658), 9.854, 90), "C8": (dx(18.863), 9.21, 270),
    "R7": (dx(8.676), 19.069, 0), "R9": (dx(8.77), 20.141, 0), "SW1": (dx(24.05), 13.76, 90),
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
    for _r in ("R2", "R5", "D1", "C3", "C13", "C8", "R7", "R9", "SW1"):
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
