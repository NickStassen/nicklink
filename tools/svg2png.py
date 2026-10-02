#!/usr/bin/env python3
"""svg2png.py in.svg out.png [px_per_mm] -- rasterize a KiCad SVG on white using host librsvg (python3-gi + pycairo)."""
import sys

import cairo
import gi

gi.require_version("Rsvg", "2.0")
from gi.repository import Rsvg

src, dst = sys.argv[1], sys.argv[2]
pxmm = float(sys.argv[3]) if len(sys.argv) > 3 else 50.0
h = Rsvg.Handle.new_from_file(src)
h.set_dpi(pxmm * 25.4)
ok, w, hgt = h.get_intrinsic_size_in_pixels()
assert ok, "SVG has no absolute size"
surf = cairo.ImageSurface(cairo.FORMAT_RGB24, round(w), round(hgt))
ctx = cairo.Context(surf)
ctx.set_source_rgb(1, 1, 1)
ctx.paint()
vp = Rsvg.Rectangle()
vp.x, vp.y, vp.width, vp.height = 0, 0, w, hgt
h.render_document(ctx, vp)
surf.write_to_png(dst)
print(f"{dst}: {round(w)}x{round(hgt)} px")
