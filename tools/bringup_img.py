"""Bring-up pictures for docs/BRINGUP.md, drawn on a real 3D render of the board.

  tools/bringup_img.sh            (renders, dumps positions, writes docs/images/bringup-*.png)

`dump` runs in the KiCad container (pad/part positions from the board); `draw` runs on the host
(PIL) and overlays the ST-Link wiring and the bring-up check points onto the transparent render.
"""
import json
import sys

W_MM, H_MM, OX, OY = 33.99, 25.5, 100.0, 100.0
REFS = ("D1", "D3", "SW1", "SW2", "U4", "Y1", "J2", "U1", "U2", "J1", "J3")

# STDC14 (STLINK-V3MINIE CN4, UM2910 Table 4) -> NickLink J3; colour; label
WIRES = [
    (3, "T_VCC", 1, "3V3 (sense only)", (220, 40, 40)),
    (5, "GND", 2, "GND", (150, 150, 155)),
    (4, "SWDIO", 7, "PA13 SWDIO", (245, 150, 20)),
    (6, "SWCLK", 8, "PA14 SWCLK", (40, 170, 70)),
    (8, "SWO", 9, "PB3 SWO (optional)", (150, 80, 200)),
    (12, "T_NRST", 10, "NRST", (40, 110, 230)),
    (13, "T_VCP_RX", 4, "PA10 USART1 RX", (0, 175, 190)),
    (14, "T_VCP_TX", 3, "PA9 USART1 TX", (215, 50, 160)),
]
STDC = {1: "reserved", 2: "reserved", 3: "T_VCC", 4: "SWDIO", 5: "GND", 6: "SWCLK", 7: "GND",
        8: "SWO", 9: "JRCLK", 10: "JTDI", 11: "GNDDETECT", 12: "T_NRST", 13: "T_VCP_RX", 14: "T_VCP_TX"}


def dump(board, out):
    import pcbnew
    b = pcbnew.LoadBoard(board)
    mm = lambda v: round(pcbnew.ToMM(v), 3)
    d = {"pads": {}, "parts": {}}
    for f in b.GetFootprints():
        r = f.GetReference()
        if r in REFS:
            p = f.GetPosition()
            d["parts"][r] = (mm(p.x) - OX, mm(p.y) - OY)
        if r in ("J1", "J3"):
            for pad in f.Pads():
                p = pad.GetPosition()
                d["pads"][f"{r}.{pad.GetNumber()}"] = (mm(p.x) - OX, mm(p.y) - OY)
    json.dump(d, open(out, "w"))


def draw(dumpf, render, outdir):
    from PIL import Image, ImageDraw, ImageFont
    d = json.load(open(dumpf))
    im = Image.open(render).convert("RGBA")
    solid = im.getchannel("A").point(lambda v: 255 if v >= 250 else 0)
    x0, y0, x1, y1 = solid.getbbox()
    pxmm = 30.0                                   # output scale
    s = (x1 - x0) / W_MM
    k = pxmm / s
    board = im.crop((x0, y0, x1, y1)).resize((round((x1 - x0) * k), round((y1 - y0) * k)), Image.LANCZOS)
    bh = board.height                             # board bottom = image bottom (USB-C sticks out at the top)
    font = lambda n: ImageFont.load_default(size=n)
    BG, FG, DIM = (30, 32, 36), (235, 235, 235), (160, 160, 165)

    def to_px(pt, bx, by):                        # board mm -> canvas px (board pasted at bx, by)
        return bx + pt[0] * pxmm, by + bh - (H_MM - pt[1]) * pxmm

    # ---------------- 1. ST-Link wiring ----------------
    Wc, Hc = 1900, 1110
    c = Image.new("RGB", (Wc, Hc), BG)
    bx, by = 860, 70
    c.paste(board, (bx, by), board)
    dr = ImageDraw.Draw(c)
    dr.text((40, 24), "STLINK-V3MINIE  ->  NickLink J3 (left header)", fill=FG, font=font(34))
    colour = {w[0]: w[4] for w in WIRES}
    # STDC14 pinout (odd pins left column, pin 1 at the top), used pins in their wire colour
    cx, cy, pitch = 190, 150, 64
    dr.rounded_rectangle([cx - 46, cy - 44, cx + pitch + 46, cy + 6 * pitch + 44], 14, fill=(20, 20, 22), outline=(120, 120, 120), width=3)
    dr.polygon([(cx - 40, cy - 38), (cx - 20, cy - 38), (cx - 40, cy - 18)], fill=(250, 210, 60))
    for n in range(1, 15):
        col, row = (n - 1) % 2, (n - 1) // 2
        x, y = cx + col * pitch, cy + row * pitch
        fill = colour.get(n, (85, 85, 85))
        dr.ellipse([x - 19, y - 19, x + 19, y + 19], fill=fill)
        dr.text((x, y), str(n), fill=(255, 255, 255), font=font(18), anchor="mm")
        lx = x - 58 if col == 0 else x + 58
        dr.text((lx, y), STDC[n], fill=FG if n in colour else (110, 110, 110), font=font(18), anchor="rm" if col == 0 else "lm")
    dr.text((cx + pitch / 2, cy + 6 * pitch + 64), "STDC14 on the probe (CN4)\npin 1 is marked on the probe\nand on the flat cable", fill=DIM, font=font(19), anchor="ma", align="center")
    # one straight wire per signal: odd J3 pins (outer column) at pad height, even pins (inner column)
    # along the gap above their row, then down into the pad
    for sp, sname, jp, jname, col in WIRES:
        tx, ty = to_px(d["pads"][f"J3.{jp}"], bx, by)
        wy = ty if jp % 2 else ty - 1.27 * pxmm
        x_start = 560
        pts = [(x_start, wy), (tx, wy)] + ([] if jp % 2 else [(tx, ty)])
        if sname == "SWO":
            for xx in range(x_start, int(tx), 28):
                dr.line([(xx, wy), (min(xx + 16, tx), wy)], fill=col, width=7)
            if not jp % 2:
                dr.line([(tx, wy), (tx, ty)], fill=col, width=7)
        else:
            dr.line(pts, fill=col, width=7, joint="curve")
        dr.ellipse([tx - 17, ty - 17, tx + 17, ty + 17], outline=col, width=6)
        dr.ellipse([x_start - 9, wy - 9, x_start + 9, wy + 9], fill=col)
        dr.text((x_start - 18, wy), f"pin {sp} {sname}", fill=FG, font=font(20), anchor="rm")
        dr.text((x_start + 14, wy - 6), f"J3.{jp} {jname}", fill=col, font=font(17), anchor="ld")
    note = ("Power the board from USB-C (computer or charger): the probe does NOT power it,\n"
            "T_VCC only senses 3V3.  TX/RX look crossed on purpose: T_VCP_RX (pin 13) is the\n"
            "probe's output and feeds the MCU's RX (PA10); T_VCP_TX (pin 14) reads the MCU's TX (PA9).")
    dr.text((bx - 820, by + bh + 50), note, fill=DIM, font=font(22), spacing=8)
    c.save(f"{outdir}/bringup-stlink-wiring.png", optimize=True)

    # ---------------- 2. Check points ----------------
    Wc, Hc = 2000, 1150
    c = Image.new("RGB", (Wc, Hc), BG)
    bx, by = (Wc - board.width) // 2, 110
    c.paste(board, (bx, by), board)
    dr = ImageDraw.Draw(c)
    dr.text((40, 24), "NickLink v1.3 bring-up check points", fill=FG, font=font(34))
    P, pad = d["parts"], d["pads"]
    calls = [  # (target mm, label, side)
        (P["J2"], "USB-C: power (and USB data)", "top"),
        (P["D1"], "PWR LED (red): on with power", "left"),
        (P["D3"], "C13 LED (green): blinks 1 Hz\nwith the test firmware", "left"),
        (P["SW2"], "BOOT button\n(hold + tap RESET = bootloader)", "left"),
        (P["SW1"], "RESET button", "right"),
        (P["U4"], "IMU (LSM6DSV, I2C 0x6A)\ntap it: firmware prints 'tap'", "right"),
        (P["Y1"], "8 MHz crystal\n('mco' -> 8 MHz on J3.5)", "bottom"),
        (P["U2"], "3.3 V regulator", "right"),
        (pad["J1.1"], "J1.1 5V (~4.7 V out)", "right"),
        (pad["J1.20"], "J1.20 3V3", "right"),
        (pad["J3.1"], "J3.1 3V3", "left"),
        (pad["J3.5"], "J3.5 PA8 = MCO", "left"),
    ]
    side_y = {"left": [], "right": []}
    for pt, label, side in sorted(calls, key=lambda t: t[0][1]):
        tx, ty = to_px(pt, bx, by)
        if side in ("left", "right"):
            lx = bx - 60 if side == "left" else bx + board.width + 60
            ly_ = ty
            for prev in side_y[side]:               # keep labels from overlapping
                if abs(prev - ly_) < 62:
                    ly_ = prev + 62
            side_y[side].append(ly_)
            dr.line([(tx, ty), (lx, ly_)], fill=(250, 210, 60), width=4)
            dr.text((lx - 12 if side == "left" else lx + 12, ly_), label, fill=FG, font=font(22),
                    anchor="rm" if side == "left" else "lm", align="right" if side == "left" else "left")
        else:
            ly_ = by - 40 if side == "top" else by + bh + 60
            dr.line([(tx, ty), (tx, ly_)], fill=(250, 210, 60), width=4)
            dr.text((tx, ly_ - 8 if side == "top" else ly_ + 8), label, fill=FG, font=font(22),
                    anchor="md" if side == "top" else "ma", align="center")
        dr.ellipse([tx - 9, ty - 9, tx + 9, ty + 9], fill=(250, 210, 60))
    c.save(f"{outdir}/bringup-checkpoints.png", optimize=True)


if __name__ == "__main__":
    if sys.argv[1] == "dump":
        dump(sys.argv[2], sys.argv[3])
    else:
        draw(sys.argv[2], sys.argv[3], sys.argv[4])
