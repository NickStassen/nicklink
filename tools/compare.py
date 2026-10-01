"""Side-by-side board comparison at a fixed physical scale.

usage: compare.py <px_per_mm> <out.png> BOARD [BOARD ...]
  BOARD = "Title|W_mm|H_mm|top.png|bottom.png"   (transparent kicad-cli renders)
        | "Title|W_mm|H_mm|outline"              (no files: dimensioned outline only)
Render scale is taken from the opaque board width (nothing protrudes sideways).
"""
import sys

from PIL import Image, ImageDraw, ImageFont

pxmm = float(sys.argv[1])
out = sys.argv[2]
boards = [a.split("|") for a in sys.argv[3:]]


def board_img(path, w_mm):
    im = Image.open(path).convert("RGBA")
    solid = im.getchannel("A").point(lambda v: 255 if v >= 250 else 0)
    x0, y0, x1, y1 = solid.getbbox()
    s = pxmm * w_mm / (x1 - x0)
    crop = im.crop((x0, y0, x1, y1))
    return crop.resize((max(1, round(crop.width * s)), max(1, round(crop.height * s))), Image.LANCZOS)


def outline_img(w_mm, h_mm, note):
    im = Image.new("RGBA", (round(w_mm * pxmm), round(h_mm * pxmm)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lw = max(1, round(pxmm * 0.25))
    d.rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=round(1.5 * pxmm), outline=(150, 150, 150), width=lw)
    f = ImageFont.load_default(size=max(9, round(pxmm * 1.6)))
    d.text((im.width / 2, im.height / 2), note, fill=(150, 150, 150), font=f, anchor="mm", align="center")
    return im


fs = max(11, round(pxmm * 2.2))
font = ImageFont.load_default(size=fs)
small = ImageFont.load_default(size=max(10, round(fs * 0.75)))
gap = round(pxmm * 8)
imgs = []
for b in boards:
    title, w, h = b[0], float(b[1]), float(b[2])
    if b[3] == "outline":
        top = outline_img(w, h, "outline only\n(design files\nnot available)")
        imgs.append((title, w, h, top, None))
    else:
        imgs.append((title, w, h, board_img(b[3], w), board_img(b[4], w)))
col_w = max(max(a.width, b.width if b else 0) for *_, a, b in imgs)
row_h = max(max(a.height, b.height if b else 0) for *_, a, b in imgs)
W = gap + len(imgs) * (col_w + gap)
H = gap + fs * 3 + 2 * (row_h + fs * 2) + gap + fs * 3
canvas = Image.new("RGB", (W, H), (32, 34, 38))
d = ImageDraw.Draw(canvas)
for i, (title, w, h, top, bot) in enumerate(imgs):
    x = gap + i * (col_w + gap)
    d.text((x, gap), title, fill="white", font=font)
    d.text((x, gap + fs * 1.3), f"{w:g} x {h:g} mm = {w * h:.0f} sq mm", fill=(190, 190, 190), font=small)
    y = gap + fs * 3
    for label, im in (("top", top), ("bottom", bot)):
        if im is None:
            continue
        canvas.paste(im, (x + (col_w - im.width) // 2, int(y)), im)
        d.text((x, y + im.height + fs * 0.3), label, fill=(150, 150, 150), font=small)
        y += row_h + fs * 2
y = H - gap - fs  # 10 mm scale bar
d.line([(gap, y), (gap + 10 * pxmm, y)], fill="white", width=max(1, round(pxmm * 0.3)))
d.text((gap + 10 * pxmm + fs * 0.5, y - fs * 0.6), "10 mm", fill="white", font=small)
canvas.save(out)
print(out, canvas.size)
