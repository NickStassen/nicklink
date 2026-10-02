"""Per-net routing summary: length per layer and via count.  usage: netreport.py board.kicad_pcb [net ...]"""
import sys
from collections import defaultdict

import pcbnew

b = pcbnew.LoadBoard(sys.argv[1])
want = set(sys.argv[2:])
rep = defaultdict(lambda: {"F": 0.0, "B": 0.0, "vias": 0})
for t in b.GetTracks():
    n = t.GetNetname()
    if want and n not in want:
        continue
    if t.Type() == pcbnew.PCB_VIA_T:
        rep[n]["vias"] += 1
    else:
        rep[n]["F" if t.GetLayer() == pcbnew.F_Cu else "B"] += pcbnew.ToMM(t.GetLength())
for n, r in sorted(rep.items()):
    print(f"{n:22s} F {r['F']:6.1f}  B {r['B']:6.1f}  vias {r['vias']}")
