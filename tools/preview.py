"""Placement preview: courtyards, pads, ratsnest, overlap report.  usage: preview.py geom.json out.png"""
import itertools
import json
import math
import sys

from PIL import Image, ImageDraw, ImageFont

g = json.load(open(sys.argv[1]))
S = 40  # px/mm
M = 3   # mm margin
W, H, OX, OY = g["W"], g["H"], g["OX"], g["OY"]
img = Image.new("RGB", (int((W + 2 * M) * S), int((H + 2 * M) * S)), "white")
d = ImageDraw.Draw(img)
font = ImageFont.load_default(size=13)
small = ImageFont.load_default(size=9)


def px(x, y):
    return ((x - OX + M) * S, (y - OY + M) * S)


def bbox(poly):
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


d.rectangle([px(OX, OY), px(OX + W, OY + H)], outline="black", width=2)
boxes = {f["ref"]: bbox(f["crtyd"]) for f in g["fps"] if f["crtyd"]}
import numpy as np
masks = {}
for f in g["fps"]:
    if f["crtyd"]:
        m = Image.new("1", img.size, 0)
        ImageDraw.Draw(m).polygon([px(*p) for p in f["crtyd"]], fill=1)
        masks[f["ref"]] = np.array(m)
bad = set()
issues = []
for a, b in itertools.combinations(masks, 2):
    A, B = boxes[a], boxes[b]
    if min(A[2], B[2]) <= max(A[0], B[0]) or min(A[3], B[3]) <= max(A[1], B[1]):
        continue
    n = int((masks[a] & masks[b]).sum())
    if n > 2:  # px; 1 px = 0.025 mm
        bad |= {a, b}
        issues.append(f"overlap {a}-{b} {n / S / S:.2f} mm2")
for f in g["fps"]:
    if f["ref"] in boxes and not f["ref"].startswith("J"):
        x0, y0, x1, y1 = boxes[f["ref"]]
        if x0 < OX - 0.01 or y0 < OY - 0.01 or x1 > OX + W + 0.01 or y1 > OY + H + 0.01:
            if f["ref"] != "J2":
                issues.append(f"{f['ref']} courtyard off board")

for f in g["fps"]:
    if f["crtyd"]:
        d.polygon([px(*p) for p in f["crtyd"]], outline="red" if f["ref"] in bad else "#00a0a0", width=2)
    for p in f["pads"]:
        x0, y0, x1, y1 = p["bb"]
        d.rectangle([px(x0, y0), px(x1, y1)], fill="#d9a400" if p["tht"] else "#c04040")
    for p in f["pads"]:
        if p["net"] and not p["net"].startswith("unconnected"):
            w = max(len(p["net"]) * 5, 1)
            d.text((px(p["x"], p["y"])[0] - w / 2, px(p["x"], p["y"])[1] - 5), p["net"], fill="black", font=small)
    if f["crtyd"]:
        x0, y0, x1, y1 = boxes[f["ref"]]
        d.text(px(x0 + 0.1, y0 + 0.05), f["ref"], fill="#0000c0", font=font)

# ratsnest: MST per net
nets = {}
for f in g["fps"]:
    for p in f["pads"]:
        if p["net"] and not p["net"].startswith("unconnected"):
            nets.setdefault(p["net"], []).append((p["x"], p["y"]))
total = 0
for n, pts in nets.items():
    pts = list(dict.fromkeys(pts))
    inside, rest = [pts[0]], pts[1:]
    while rest:
        a, b = min(((a, b) for a in inside for b in rest), key=lambda e: math.dist(*e))
        inside.append(b); rest.remove(b)
        if n != "GND":
            total += math.dist(a, b)
        d.line([px(*a), px(*b)], fill="#e0e0e0" if n == "GND" else ("#ff00ff" if n.startswith(("USB_D", "HSE")) else "#3080ff"), width=1)
img.save(sys.argv[2])
print(f"ratsnest (non-GND) {total:.1f} mm; board {W}x{H} = {W*H:.0f} mm2")
print("\n".join(issues) or "no courtyard issues")
