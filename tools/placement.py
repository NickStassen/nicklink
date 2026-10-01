"""Component placement for NickLink v1.2. Local mm coords: origin = board top-left, X right, Y down.

Each header has a 1.2 mm silkscreen label strip on both sides (outer: along the
board edge, inner: between header and the middle component area).
"""
OX, OY = 100.0, 100.0          # board origin in KiCad coordinates
LBL = 1.2                      # label strip width (0.8 mm text rotated + clearance)
PIN_OUT = LBL + 1.27           # outer header pin column, from board edge
PIN_IN = PIN_OUT + 2.54        # inner header pin column
MID = PIN_IN + 1.27 + LBL      # middle component area starts here (from either edge)
W = round(2 * MID + 2.04 + 10.05 + 2.04 + 4.1, 2)   # hole + USB + hole across the top
H, CORNER = 25.5, 0.5
L, R, c = MID, W - MID, W / 2  # middle area left/right edges, centre
hy = (H - 22.86) / 2           # header pin-1 row
my = 16.2                      # MCU centre

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
    "C2": (20.95, 12.0, 90),
    "C4": (L + 2.85, my + 2.75, 90),
    "C1": (12.3, 20.6, 90),
    "C5": (R - 1.3, 18.4, 90),
    "R8": (R - 2.71, 9.3, 90),
    # clock row under the MCU
    "Y1": (c - 1.5, 23.2, 0),
    "C10": (c - 4.2, 23.4, 90),
    "C11": (c + 1.2, 23.2, 90),
    "C9": (c + 2.3, 22.6, 90),
    "C6": (c + 3.4, 22.6, 90),
    "C7": (c + 4.5, 22.6, 90),
    "FB1": (R - 2.9, 17.6, 90),
    # BOOT0 button beside its pin (left), RESET on the right
    "SW2": (L + 1.76, 13.9, 90), "R1": (L + 1.4, 17.4, 90),
    "SW1": (R - 1.76, 13.7, 90),
}

# Front labels for parts: (text, x, y, angle, justify -1 left / 0 centre)
LABELS = [
    ("PWR", L + 0.15, 8.6, 0, -1),
    ("C13", L + 0.15, 9.8, 0, -1),
    ("BOOT", L + 3.57, 13.9, 90, 0),
    ("RST", R - 3.5, 13.7, 90, 0),
]
