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
    "R4": (c + 2.2, 9.2, 90),
    "R5": (c - 3.2, 8.6, 0),
    "R2": (c - 3.2, 9.7, 0),
    "D2": (R - 2.06, 5.1, 0),
    # Schottky in the right pocket, LDO in the row below USB
    "U2": (c + 4.1, 9.3, 0),
    "C12": (R - 3.11, 6.85, 0),
    "C8": (R - 1.06, 6.85, 0),
    # LED resistors in the left pocket, LEDs + labels below it
    "D1": (L + 3.6, 8.6, 0), "R3": (L + 1.13, 5.3, 0),
    "D3": (L + 3.6, 9.8, 0), "R6": (L + 3.13, 5.3, 0),
    # MCU + decoupling
    "U1": (c, my, 90),
    "C3": (c - 4.5, 11.5, 90),
    "C2": (dx(20.95), 12.0, 90),
    "C4": (L + 2.85, my + 2.75, 90),
    "C1": (dx(12.3), 20.6, 90),
    "C5": (L + 2.0, 6.75, 0),  # left pocket, below R3/R6
    "R8": (R - 2.71, 9.3, 90),
    # clock row under the MCU
    "Y1": (c - 1.5, 23.2, 0),
    "C10": (c - 4.2, 23.4, 90),
    "C11": (c + 1.2, 23.2, 90),
    "C9": (c + 2.3, 22.6, 90),
    "C6": (c + 3.4, 22.6, 90),
    "C7": (c + 4.5, 22.6, 90),
    "FB1": (dx(21.1), 20.4, 90),   # MCU courtyard bottom-right notch, beside VDDA
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
    "R2": (dx(13.294), 9.658, 0), "R5": (dx(13.411), 8.601, 0), "D1": (dx(10.93), 8.526, 0),
    "D3": (dx(11.093), 9.945, 0), "R3": (dx(8.71), 5.17, 0), "R6": (dx(10.623), 5.198, 0),
    "C3": (dx(11.989), 11.407, 90), "C13": (dx(17.706), 9.907, 90), "R4": (dx(18.764), 9.216, 90),
    "R7": (dx(8.609), 19.074, 0), "R9": (dx(8.742), 20.211, 0), "FB1": (dx(21.165), 20.449, 90),
    "U4": (dx(23.8), 18.059, 0), "C14": (dx(22.711), 20.42, 0), "C15": (dx(24.707), 20.401, 0),
    "SW1": (dx(24.023), 13.686, 90),
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
    for _r in ("R2", "R5", "D1", "D3", "R3", "R6", "C3", "C13", "R4", "R7", "R9", "FB1", "U4", "C14", "C15", "SW1"):
        _x, _y, _a = PLACE[_r]
        PLACE[_r] = (round(_x + _rng.uniform(-0.1, 0.1), 3), round(_y + _rng.uniform(-0.1, 0.1), 3), _a)

# Pre-routed, locked F.Cu tracks laid before autorouting: (net, width, [(x, y), ...]).
# Crystal nets stay short, top-layer only and via-free regardless of Freerouting.
# Coordinates follow the U1 / Y1 / C10 / C11 positions above; re-derive if those move.
PREROUTE = [
    ("/HSE_IN", 0.2, [(dx(15.845), 20.6), (dx(15.845), 21.35), (dx(13.0), 21.35), (dx(13.0), 24.05), (dx(13.995), 24.05)]),
    ("/HSE_IN", 0.2, [(dx(13.0), 23.88), (dx(12.395), 23.88)]),
    ("/HSE_OUT", 0.2, [(dx(16.345), 20.6), (dx(16.345), 22.35), (dx(16.195), 22.35)]),
    ("/HSE_OUT", 0.2, [(dx(16.195), 22.35), (dx(17.19), 22.35), (dx(17.19), 23.68), (dx(17.795), 23.68)]),
]

# Silkscreen pin-1 dots (x, y, radius) for footprints used without their own silk
SILK_DOTS = []

# Rule areas: (layer, (x0, y0, x1, y1)). pcbnew layer ids: F.Cu = 0.


# Front labels for parts: (text, x, y, angle, justify -1 left / 0 centre)
LABELS = [
    ("PWR", L + 0.15, 8.6, 0, -1),
    ("C13", L + 0.15, 10.0, 0, -1),
    ("BOOT", L + 3.57, 13.9, 90, 0),
    ("RST", R - 3.5, 13.7, 90, 0),
]

# IMU keep-out (inside its pad ring) and pin-1 dot, following its final position/rotation
_ux, _uy, _ur = PLACE["U4"]
_kx, _ky = (0.8, 0.55) if _ur % 180 == 0 else (0.55, 0.8)
KEEPOUTS = [(0, (_ux - _kx, _uy - _ky, _ux + _kx, _uy + _ky))]
_p1 = {0: (-1.45, -1.35), 90: (-1.35, 1.45), 180: (1.45, 1.35), 270: (1.35, -1.45)}[_ur % 360]  # pad 1 corner
SILK_DOTS.append((_ux + _p1[0], _uy + _p1[1], 0.15))
