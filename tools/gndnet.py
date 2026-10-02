"""GND connectivity per fill island (KiCad's connectivity treats a zone as one item).
gnd_clusters(board) -> list of clusters, each a set of node keys:
  ("isl", layer, zone_idx, outline_idx), ("pad", "U4.6"), ("via", uuid), ("trk", uuid).
Run as a script for a report: python3 tools/gndnet.py board.kicad_pcb
"""
import sys

import pcbnew


def gnd_clusters(b, net="GND", skip_vias=()):
    zones = [z for z in b.Zones() if z.GetNetname() == net]
    layers = (pcbnew.F_Cu, pcbnew.B_Cu)
    polys = {l: [z.GetFilledPolysList(l) for z in zones if z.IsOnLayer(l)] for l in layers}

    def islands(l, pos):
        return [("isl", l, zi, i) for zi, ps in enumerate(polys[l])
                for i in range(ps.OutlineCount()) if ps.Outline(i).PointInside(pos)]

    parent = {}
    def find(k):
        parent.setdefault(k, k)
        while parent[k] != k:
            parent[k] = parent[parent[k]]; k = parent[k]
        return k
    def union(a, c):
        parent[find(a)] = find(c)

    pads = [(f"{f.GetReference()}.{p.GetNumber()}", p) for f in b.GetFootprints() for p in f.Pads() if p.GetNetname() == net]
    tracks = [t for t in b.GetTracks() if t.GetNetname() == net and t.m_Uuid.AsString() not in skip_vias]
    vias = [t for t in tracks if t.Type() == pcbnew.PCB_VIA_T]
    segs = [t for t in tracks if t.Type() != pcbnew.PCB_VIA_T]
    for name, p in pads:
        find(("pad", name))
        for l in layers:
            if p.IsOnLayer(l):
                for k in islands(l, p.GetPosition()):
                    union(("pad", name), k)
    for v in vias:
        k = ("via", v.m_Uuid.AsString()); find(k)
        for l in layers:
            for i in islands(l, v.GetPosition()):
                union(k, i)
    for t in segs:
        k = ("trk", t.m_Uuid.AsString()); find(k); l = t.GetLayer()
        for pt in (t.GetStart(), t.GetEnd()):
            for i in islands(l, pt):
                union(k, i)
            for name, p in pads:
                if p.IsOnLayer(l) and (p.HitTest(pt) or t.HitTest(p.GetPosition())):
                    union(k, ("pad", name))
            for v in vias:
                if v.HitTest(pt):
                    union(k, ("via", v.m_Uuid.AsString()))
            for u in segs:
                if u is not t and u.GetLayer() == l and u.HitTest(pt):
                    union(k, ("trk", u.m_Uuid.AsString()))
    out = {}
    for k in list(parent):
        out.setdefault(find(k), set()).add(k)
    return sorted(out.values(), key=lambda c: -sum(1 for k in c if k[0] == "pad"))


if __name__ == "__main__":
    b = pcbnew.LoadBoard(sys.argv[1])
    cl = gnd_clusters(b)
    for c in cl:
        pads = sorted(k[1] for k in c if k[0] == "pad")
        print(f"cluster: {len(pads)} pads {pads[:8]}{'...' if len(pads) > 8 else ''}, "
              f"{sum(k[0] == 'via' for k in c)} vias, {sum(k[0] == 'isl' for k in c)} islands")
    print("clusters:", len(cl))
