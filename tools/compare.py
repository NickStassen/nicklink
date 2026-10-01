"""Side-by-side v1.1 / v1.2 comparison at a fixed physical scale.

usage: compare.py <px_per_mm> <out.png> v11-top.png v11-bottom.png v12-top.png v12-bottom.png
Inputs are transparent kicad-cli renders; scale is taken from the opaque board
width (nothing protrudes sideways on either board).
"""
import sys

from PIL import Image, ImageDraw, ImageFont

pxmm = float(sys.argv[1])
out = sys.argv[2]
boards = [("NickLink v1.1", 34.0, 33.0, sys.argv[3], sys.argv[4]), ("NickLink v1.2", 33.19, 25.5, sys.argv[5], sys.argv[6])]


def board_img(path, w_mm):
    im = Image.open(path).convert("RGBA")
    solid = im.getchannel("A").point(lambda v: 255 if v >= 250 else 0)
    x0, y0, x1, y1 = solid.getbbox()
    s = pxmm * w_mm / (x1 - x0)
    pad = 0  # crop to the board + protruding USB, keep soft shadow out
    crop = im.crop((x0 - pad, y0 - pad, x1 + pad, y1 + pad))
    return crop.resize((max(1, round(crop.width * s)), max(1, round(crop.height * s))), Image.LANCZOS)


fs = max(11, round(pxmm * 2.2))
font = ImageFont.load_default(size=fs)
small = ImageFont.load_default(size=max(10, round(fs * 0.75)))
gap = round(pxmm * 8)
imgs = [(t, w, h, board_img(top, w), board_img(bot, w)) for t, w, h, top, bot in boards]
col_w = max(max(a.width, b.width) for *_, a, b in imgs)
row_h = max(max(a.height, b.height) for *_, a, b in imgs)
W = gap + len(imgs) * (col_w + gap)
H = gap + fs * 3 + 2 * (row_h + fs * 2) + gap + fs * 3
canvas = Image.new("RGB", (W, H), (32, 34, 38))
d = ImageDraw.Draw(canvas)
for i, (title, w, h, top, bot) in enumerate(imgs):
    x = gap + i * (col_w + gap)
    d.text((x, gap), title, fill="white", font=font)
    d.text((x, gap + fs * 1.3), f"{w:g} x {h:g} mm = {w * h:.0f} mm²", fill=(190, 190, 190), font=small)
    y = gap + fs * 3
    for label, im in (("top", top), ("bottom", bot)):
        canvas.paste(im, (x + (col_w - im.width) // 2, int(y)), im)
        d.text((x, y + im.height + fs * 0.3), label, fill=(150, 150, 150), font=small)
        y += row_h + fs * 2
# 10 mm scale bar
y = H - gap - fs
d.line([(gap, y), (gap + 10 * pxmm, y)], fill="white", width=max(1, round(pxmm * 0.3)))
d.text((gap + 10 * pxmm + fs * 0.5, y - fs * 0.6), "10 mm", fill="white", font=small)
canvas.save(out)
print(out, canvas.size)
