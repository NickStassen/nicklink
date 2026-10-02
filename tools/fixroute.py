"""Finish one leftover connection that Freerouting gave up on: a small two-layer grid router.

  tools/fixroute.sh board.kicad_pcb out.kicad_pcb NET PAD_A PAD_B [width_mm]

joins the copper cluster holding PAD_A (e.g. U4.6) to the one holding PAD_B with new tracks and vias.
Steps: `dump` (in the KiCad container) writes every other net's copper, holes and keep-outs as polygons
inflated by clearance, plus the two clusters' copper as targets; `search` (host, numpy + PIL) rasterises
them at 0.05 mm and runs Dijkstra on F.Cu/B.Cu with a via cost; `apply` (container) adds the path and
refills the pours. Run drc.sh afterwards.
ponytail: grid router, 0.05 mm cells and 45-degree moves; good for a short gap, not a general autorouter.
"""
import json
import sys

STEP, CLR, VIA_D, VIA_DRILL, VIA_COST = 0.05, 0.19, 0.6, 0.3, 40   # CLR: 0.13 rule + grid quantisation


def dump(board, net, pad_a, pad_b, width, out):
    import pcbnew
    sys.path.insert(0, __file__.rsplit("/", 1)[0])
    from gndnet import gnd_clusters
    mm, b = pcbnew.FromMM, pcbnew.LoadBoard(board)
    b.BuildConnectivity()
    layers = {"F": pcbnew.F_Cu, "B": pcbnew.B_Cu}
    pads = {f"{f.GetReference()}.{p.GetNumber()}": p for f in b.GetFootprints() for p in f.Pads()}

    def outlines(ps):
        return [[(pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)) for p in ps.Outline(i).CPoints()] for i in range(ps.OutlineCount())]

    def shape(item, layer, clr):
        ps = pcbnew.SHAPE_POLY_SET()
        item.TransformShapeToPolygon(ps, layer, mm(clr), mm(0.005), pcbnew.ERROR_OUTSIDE)
        return outlines(ps)

    # the two clusters (GND: per fill island, see gndnet.py; others: board connectivity)
    if net == "GND":
        cl = gnd_clusters(b)
        want = {k[1]: c for c in cl for k in c if k[0] == "pad"}
        ca, cb = want[pad_a], want[pad_b]
        uu = {t.m_Uuid.AsString(): t for t in b.GetTracks()}
        zones = [z for z in b.Zones() if z.GetNetname() == "GND"]
        polys = {l: [z.GetFilledPolysList(l) for z in zones if z.IsOnLayer(l)] for l in layers.values()}
        def members(c):
            out = {"F": [], "B": []}
            for k in c:
                if k[0] == "pad":
                    p = pads[k[1]]
                    for n, l in layers.items():
                        if p.IsOnLayer(l):
                            out[n] += shape(p, l, 0)
                elif k[0] in ("via", "trk"):
                    t = uu[k[1]]
                    for n, l in layers.items():
                        if t.IsOnLayer(l):
                            out[n] += shape(t, l, 0)
                else:
                    _, l, zi, i = k
                    n = "F" if l == pcbnew.F_Cu else "B"
                    out[n].append([(pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)) for p in polys[l][zi].Outline(i).CPoints()])
            return out
    else:
        conn = b.GetConnectivity()
        def cluster(p):
            seen, st = {}, [p]
            while st:
                it = st.pop()
                k = it.m_Uuid.AsString()
                if k not in seen:
                    seen[k] = it
                    st.extend(conn.GetConnectedItems(it))
            return seen.values()
        def members(c):
            out = {"F": [], "B": []}
            for it in c:
                for n, l in layers.items():
                    if it.IsOnLayer(l) and it.GetNetname() == net:
                        out[n] += shape(it, l, 0)
            return out
        ca, cb = cluster(pads[pad_a]), cluster(pads[pad_b])
    inflate = CLR + width / 2
    obst = {"F": [], "B": []}
    vobst = {"F": [], "B": []}           # same, for a via's pad radius
    for n, l in layers.items():
        items = [p for p in pads.values()] + list(b.GetTracks())
        for it in items:
            if it.IsOnLayer(l) and it.GetNetname() != net:
                obst[n] += shape(it, l, inflate)
                vobst[n] += shape(it, l, CLR + VIA_D / 2)
        for z in b.Zones():
            if z.GetIsRuleArea() and z.GetDoNotAllowTracks() and z.IsOnLayer(l):
                obst[n] += outlines(z.Outline()); vobst[n] += outlines(z.Outline())
    holes = []                           # every drill, for hole-to-hole spacing of new vias
    for p in pads.values():
        if p.HasHole():
            d = max(p.GetDrillSize().x, p.GetDrillSize().y)
            holes.append((pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y), pcbnew.ToMM(d) / 2))
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            holes.append((pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y), pcbnew.ToMM(t.GetDrillValue()) / 2))
    bb = b.GetBoardEdgesBoundingBox()
    edge = [pcbnew.ToMM(v) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())]
    json.dump({"obst": obst, "vobst": vobst, "holes": holes, "A": members(ca), "B": members(cb),
               "edge": edge, "width": width}, open(out, "w"))


def search(dumpf, pathf):
    import heapq
    import numpy as np
    from PIL import Image, ImageDraw
    d = json.load(open(dumpf))
    x0, y0, x1, y1 = d["edge"]
    W, H = int((x1 - x0) / STEP) + 1, int((y1 - y0) / STEP) + 1
    px = lambda pts: [((x - x0) / STEP, (y - y0) / STEP) for x, y in pts]

    def mask(polys, base=0):
        im = Image.new("1", (W, H), base)
        dr = ImageDraw.Draw(im)
        for p in polys:
            if len(p) > 2:
                dr.polygon(px(p), fill=1)
        return np.array(im, dtype=bool)
    e = 0.3 + d["width"] / 2             # copper-to-edge
    ev = 0.3 + VIA_D / 2
    yy, xx = np.mgrid[0:H, 0:W]
    X, Y = x0 + xx * STEP, y0 + yy * STEP
    def inside(m):
        return (X > x0 + m) & (X < x1 - m) & (Y > y0 + m) & (Y < y1 - m)
    blocked = {n: mask(d["obst"][n]) | ~inside(e) for n in "FB"}
    vblock = mask(d["vobst"]["F"]) | mask(d["vobst"]["B"]) | ~inside(ev)
    for hx, hy, hr in d["holes"]:
        for n in "FB":                   # track copper to any hole edge: 0.25 mm
            blocked[n] |= np.hypot(X - hx, Y - hy) < hr + d["width"] / 2 + 0.3
        vblock |= np.hypot(X - hx, Y - hy) < hr + VIA_D / 2 + 0.3   # hole clearance 0.25
    tA = {n: mask(d["A"][n]) for n in "FB"}
    tB = {n: mask(d["B"][n]) for n in "FB"}
    L = {"F": 0, "B": 1}
    dist, prev, pq = {}, {}, []
    for n in "FB":
        for y, x in zip(*np.nonzero(tA[n])):
            k = (L[n], y, x)
            dist[k] = 0
            pq.append((0, k))
    heapq.heapify(pq)
    moves = [(dy, dx, 1.0 if dy == 0 or dx == 0 else 1.414) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]
    goal = None
    while pq:
        c, k = heapq.heappop(pq)
        if c > dist.get(k, 1e18):
            continue
        l, y, x = k
        n = "FB"[l]
        if tB[n][y, x]:
            goal = k
            break
        nb = [((l, y + dy, x + dx), c + w) for dy, dx, w in moves]
        if not vblock[y, x]:
            nb.append(((1 - l, y, x), c + VIA_COST))
        for k2, c2 in nb:
            l2, y2, x2 = k2
            if not (0 <= y2 < H and 0 <= x2 < W):
                continue
            n2 = "FB"[l2]
            if blocked[n2][y2, x2] and not (tA[n2][y2, x2] or tB[n2][y2, x2]):
                continue
            if c2 < dist.get(k2, 1e18):
                dist[k2], prev[k2] = c2, k
                heapq.heappush(pq, (c2, k2))
    if goal is None:
        sys.exit("no path")
    path = [goal]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path.reverse()
    # cells -> polyline segments per layer + vias, dropping collinear points
    segs, vias, cur = [], [], [path[0]]
    for a, c in zip(path, path[1:]):
        if a[0] != c[0]:
            segs.append(cur); vias.append((x0 + a[2] * STEP, y0 + a[1] * STEP)); cur = [c]
        else:
            cur.append(c)
    segs.append(cur)
    out = []
    for s in segs:
        pts = [s[0]]
        for a, c in zip(s[1:], s[2:]):
            d1 = (a[1] - pts[-1][1], a[2] - pts[-1][2]); d2 = (c[1] - a[1], c[2] - a[2])
            if d1[0] * d2[1] != d1[1] * d2[0]:   # direction changes at a
                pts.append(a)
        pts.append(s[-1])
        if len(pts) > 1:
            out.append({"layer": "FB"[s[0][0]], "pts": [(x0 + p[2] * STEP, y0 + p[1] * STEP) for p in pts]})
    json.dump({"segs": out, "vias": vias}, open(pathf, "w"))
    print(f"path: {sum(len(s['pts']) - 1 for s in out)} segments, {len(vias)} vias, cost {dist[goal]:.0f}")


def apply(board, out, net, pathf, width):
    import pcbnew
    mm, b = pcbnew.FromMM, pcbnew.LoadBoard(board)
    ni = b.GetNetInfo().GetNetItem(net)
    p = json.load(open(pathf))
    for s in p["segs"]:
        for (xa, ya), (xb, yb) in zip(s["pts"], s["pts"][1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(mm(xa), mm(ya))); t.SetEnd(pcbnew.VECTOR2I(mm(xb), mm(yb)))
            t.SetWidth(mm(width)); t.SetLayer(pcbnew.F_Cu if s["layer"] == "F" else pcbnew.B_Cu); t.SetNet(ni)
            b.Add(t)
    for x, y in p["vias"]:
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y))); v.SetWidth(mm(VIA_D)); v.SetDrill(mm(VIA_DRILL)); v.SetNet(ni)
        b.Add(v)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(out, b)
    print(f"added {sum(len(s['pts']) - 1 for s in p['segs'])} track segments, {len(p['vias'])} vias on {net}")


if __name__ == "__main__":
    cmd, *a = sys.argv[1:]
    if cmd == "dump":
        dump(a[0], a[1], a[2], a[3], float(a[4]), a[5])
    elif cmd == "search":
        search(a[0], a[1])
    else:
        apply(a[0], a[1], a[2], a[3], float(a[4]))
