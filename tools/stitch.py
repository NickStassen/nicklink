"""Add GND stitching vias wherever both GND pours have room, then refill.
usage (in container): python3 tools/stitch.py in.kicad_pcb out.kicad_pcb [pitch_mm]
"""
import math
import sys

import pcbnew

mm = pcbnew.FromMM
inp, out = sys.argv[1], sys.argv[2]
pitch = float(sys.argv[3]) if len(sys.argv) > 3 else 1.27
b = pcbnew.LoadBoard(inp)
gnd = b.GetNetInfo().GetNetItem("GND")
zones = [z for z in b.Zones() if z.GetNetname() == "GND"]

# Fill with islands kept, so vias can rescue islands on one layer.
modes = [(z, z.GetIslandRemovalMode()) for z in zones]
for z in zones:
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_NEVER)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())

VIA_D, VIA_DRILL = 0.6, 0.3
inner = {}
for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
    polys = pcbnew.SHAPE_POLY_SET()
    for z in zones:
        if z.IsOnLayer(layer):
            polys.Append(z.GetFilledPolysList(layer))
    polys.Deflate(mm(VIA_D / 2 + 0.05), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, mm(0.005))
    inner[layer] = polys

holes = []  # (x, y, r) of every drilled thing, mm
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.HasHole():
            pos = p.GetPosition()
            holes.append((pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y), pcbnew.ToMM(max(p.GetSize(pcbnew.F_Cu).x, p.GetSize(pcbnew.F_Cu).y, p.GetDrillSize().x, p.GetDrillSize().y)) / 2))  # oval slots: long axis
# keep vias off silkscreen text so labels stay readable
texts = []
for item in list(b.GetDrawings()) + [g for fp in b.GetFootprints() for g in fp.GraphicalItems()]:
    if item.Type() == pcbnew.PCB_TEXT_T and item.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
        bb = item.GetBoundingBox()
        texts.append(tuple(pcbnew.ToMM(v) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())))
placed = [(pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)) for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]

bb = b.GetBoardEdgesBoundingBox()
x0, y0, x1, y1 = (pcbnew.ToMM(v) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom()))
added, new = 0, []
y = y0 + 0.8
while y < y1 - 0.8:
    x = x0 + 0.8
    while x < x1 - 0.8:
        pt = pcbnew.VECTOR2I(mm(x), mm(y))
        ok = all(inner[l].Contains(pt) for l in inner)
        ok = ok and all(math.dist((x, y), (hx, hy)) > hr + VIA_D / 2 + 0.35 for hx, hy, hr in holes)
        ok = ok and all(math.dist((x, y), v) > 1.1 for v in placed)
        ok = ok and not any(tx0 - 0.35 < x < tx1 + 0.35 and ty0 - 0.35 < y < ty1 + 0.35 for tx0, ty0, tx1, ty1 in texts)
        if ok:
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pt)
            v.SetWidth(mm(VIA_D))
            v.SetDrill(mm(VIA_DRILL))
            v.SetNet(gnd)
            b.Add(v)
            new.append(v)
            placed.append((x, y))
            added += 1
        x += pitch
    y += pitch

for z, m in modes:
    z.SetIslandRemovalMode(m)
removed = 0
while True:
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    # A stitching via is kept only if it joins fill islands anchored to real GND copper: islands holding a
    # GND pad or a pre-existing GND via, extended through the kept vias. (Board connectivity treats each
    # zone as one item, so it can't see a floating island pair held together only by stitching vias.)
    isl = {l: [z.GetFilledPolysList(l) for z in zones if z.IsOnLayer(l)] for l in (pcbnew.F_Cu, pcbnew.B_Cu)}
    def where(l, pos):
        for zi, ps in enumerate(isl[l]):
            for i in range(ps.OutlineCount()):
                if ps.Outline(i).PointInside(pos):
                    return (l, zi, i)
    anchored = set()
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() == "GND":
                for l in (pcbnew.F_Cu, pcbnew.B_Cu):
                    if p.IsOnLayer(l):
                        anchored.add(where(l, p.GetPosition()))
    ids = {v.m_Uuid.AsString() for v in new}
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == "GND" and t.m_Uuid.AsString() not in ids:
            anchored |= {where(l, t.GetPosition()) for l in (pcbnew.F_Cu, pcbnew.B_Cu)}
    anchored.discard(None)
    ends = {v.m_Uuid.AsString(): (where(pcbnew.F_Cu, v.GetPosition()), where(pcbnew.B_Cu, v.GetPosition())) for v in new}
    grew = True
    while grew:
        grew = False
        for a, c in ends.values():
            if a and c and (a in anchored) != (c in anchored):
                anchored |= {a, c}; grew = True
    keep, bad = [], []
    for v in new:
        a, c = ends[v.m_Uuid.AsString()]
        (keep if a in anchored and c in anchored else bad).append(v)
    if not bad:
        break
    for v in bad:
        b.Delete(v)
        removed += 1
    new = keep
pcbnew.SaveBoard(out, b)
print(f"added {added - removed} GND stitching vias ({removed} dropped: isolated copper)")
