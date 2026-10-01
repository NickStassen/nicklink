"""Copy a KiCad library footprint into nicklink.pretty without its F.SilkS graphics.
usage (in container): python3 tools/nosilk.py Lib:Name"""
import re
import sys

lib, name = sys.argv[1].split(":")
s = open(f"/usr/share/kicad/footprints/{lib}.pretty/{name}.kicad_mod").read()
out, k = [], 0
while k < len(s):
    if s[k] == "(" and k > 0:
        d, m = 0, k
        while True:
            d += {"(": 1, ")": -1}.get(s[m], 0)
            if d == 0:
                break
            m += 1
        blk = s[k:m + 1]
        if not (blk.startswith(("(fp_line", "(fp_rect", "(fp_poly", "(fp_circle", "(fp_arc")) and '"F.SilkS"' in blk):
            out.append(blk)
        k = m + 1
    else:
        out.append(s[k])
        k += 1
t = re.sub(r"\n\s*\n", "\n", "".join(out)).replace(f'(footprint "{name}"', f'(footprint "{name}_NoSilk"', 1)
t = re.sub(r'\(descr "', '(descr "Silkscreen removed for NickLink labels. ', t, count=1)
open(f"nicklink.pretty/{name}_NoSilk.kicad_mod", "w").write(t)
