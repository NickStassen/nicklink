"""Build nicklink.kicad_pcb from spec.py + placement.py (runs inside the kicad docker image).

usage: python3 tools/build_pcb.py <template.kicad_pcb> <out.kicad_pcb> [netlist.net]
       python3 tools/build_pcb.py --resilk <routed.kicad_pcb>   # redraw silkscreen only

The template only supplies board setup (stackup, plot settings); all footprints,
tracks, zones and drawings are replaced. If a KiCad netlist is given, footprints
are linked to their schematic symbols (needed for DRC schematic parity).
"""
import json
import math
import os
import re
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(__file__))
import placement as P  # noqa: E402
import spec  # noqa: E402

LIBDIRS = {"nicklink": os.path.join(os.path.dirname(__file__), "..", "nicklink.pretty")}
mm = pcbnew.FromMM


def V(x, y):
    return pcbnew.VECTOR2I(mm(x + P.OX), mm(y + P.OY))


def load_fp(libid):
    lib, name = libid.split(":")
    fp = pcbnew.FootprintLoad(LIBDIRS.get(lib, f"/usr/share/kicad/footprints/{lib}.pretty"), name)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def sexpr(text):
    """Minimal S-expression parser -> nested lists of str."""
    toks = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', text)
    stack = [[]]
    for t in toks:
        if t == "(":
            stack.append([])
        elif t == ")":
            x = stack.pop()
            stack[-1].append(x)
        else:
            stack[-1].append(t[1:-1].replace('\\"', '"') if t.startswith('"') else t)
    return stack[0][0]


def kids(node, key):
    return [c for c in node[1:] if isinstance(c, list) and c and c[0] == key]


def kid(node, key):
    k = kids(node, key)
    return k[0] if k else None


def read_netlist(path):
    """-> ({ref: (uuid path, {field: value})}, {(ref, pin): net name})"""
    root = sexpr(open(path).read())
    comps = {}
    for comp in kids(kid(root, "components"), "comp"):
        ref = kid(comp, "ref")[1]
        fields = {f[1][1]: (f[2] if len(f) > 2 else "") for f in kids(kid(comp, "fields"), "field")}
        sheet = kid(kid(comp, "sheetpath"), "tstamps")[1]
        comps[ref] = (sheet + kid(comp, "tstamps")[1], fields)
    pins = {}
    for net in kids(kid(root, "nets"), "net"):
        name = kid(net, "name")[1]
        for node in kids(net, "node"):
            pins[(kid(node, "ref")[1], kid(node, "pin")[1])] = name
    return comps, pins


def main(template, out, netfile=None):
    board = pcbnew.LoadBoard(template)

    nets = {}

    def net(name):
        if name not in nets:
            n = pcbnew.NETINFO_ITEM(board, name)
            board.Add(n)
            nets[name] = n
        return nets[name]

    comps, npins = read_netlist(netfile) if netfile else ({}, {})
    parts = {ref: (fpid, val, pins) for ref, (_, val, fpid, pins, _) in spec.PARTS.items()}
    parts.update({ref: (fpid, ref, {}) for ref, fpid in spec.BOARD_ONLY.items()})

    for ref, (fpid, val, pins) in parts.items():
        fp = load_fp(P.FP_OVERRIDE.get(ref, fpid))
        fp.SetReference(ref)
        fp.SetValue(val)
        if ref in spec.BOARD_ONLY:
            fp.SetBoardOnly(True)
        if ref in comps:
            path, fields = comps[ref]
            fp.SetPath(pcbnew.KIID_PATH(path))
            for k, v in fields.items():
                if k not in ("Footprint", "Reference", "Value"):
                    fp.SetField(k, v)
                    fp.GetField(k).SetVisible(False)
                    fp.GetField(k).SetLayer(pcbnew.F_Fab)
        x, y, rot = P.PLACE[ref][:3]
        fp.SetPosition(V(x, y))
        fp.SetOrientationDegrees(rot)
        board.Add(fp)
        for pad in fp.Pads():
            n = npins.get((ref, pad.GetNumber())) if npins else pins.get(pad.GetNumber())
            if n:
                pad.SetNet(net(n))
                if n == "GND" and ref in ("J1", "J3"):
                    pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
            elif pad.GetNumber() and fpid.split(":")[0] != "MountingHole":
                pad.SetNet(net(f"unconnected-({ref}-Pad{pad.GetNumber()})"))

    # Outline: rounded rectangle
    W, H, R = P.W, P.H, P.CORNER
    segs = [((R, 0), (W - R, 0)), ((W, R), (W, H - R)), ((W - R, H), (R, H)), ((0, H - R), (0, R))]
    for a, b in segs:
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(V(*a)); s.SetEnd(V(*b)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.05))
        board.Add(s)
    for cx, cy, a0 in ((R, R, 180), (W - R, R, 270), (W - R, H - R, 0), (R, H - R, 90)):
        pts = [(cx + R * math.cos(math.radians(a)), cy + R * math.sin(math.radians(a))) for a in (a0, a0 + 45, a0 + 90)]
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        s.SetArcGeometry(V(*pts[0]), V(*pts[1]), V(*pts[2]))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.05))
        board.Add(s)

    # GND pour on both layers (filled after routing)
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(net("GND"))
        z.SetLocalClearance(mm(0.2))
        z.SetMinThickness(mm(0.2))
        z.SetThermalReliefGap(mm(0.25))
        z.SetThermalReliefSpokeWidth(mm(0.3))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)  # solid SMD, relieved THT
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        o = z.Outline()
        o.NewOutline()
        for x, y in ((0, 0), (W, 0), (W, H), (0, H)):
            o.Append(mm(x + P.OX), mm(y + P.OY))
        board.Add(z)

    for name, w, pts in P.PREROUTE:
        for a, b in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(V(*a)); t.SetEnd(V(*b)); t.SetWidth(mm(w))
            t.SetLayer(pcbnew.F_Cu); t.SetNet(nets[name]); t.SetLocked(True)
            board.Add(t)

    # Keep-outs (no tracks, vias or pour), e.g. top copper under the IMU per ST TN0018
    for layer, (x0, y0, x1, y1) in P.KEEPOUTS:
        k = pcbnew.ZONE(board)
        k.SetIsRuleArea(True)
        k.SetLayer(layer)
        k.SetDoNotAllowTracks(True); k.SetDoNotAllowVias(True); k.SetDoNotAllowZoneFills(True)
        k.SetDoNotAllowPads(False); k.SetDoNotAllowFootprints(False)
        o = k.Outline(); o.NewOutline()
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            o.Append(mm(x + P.OX), mm(y + P.OY))
        board.Add(k)

    silk(board)
    board.Save(out)
    dump(board, out.replace(".kicad_pcb", ".geom.json"))


def text(board, s, x, y, layer, h=0.8, w=None, angle=0, th=0.15, just=0):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(w or h), mm(h)))
    t.SetTextThickness(mm(th))
    t.SetTextAngleDegrees(angle)
    t.SetHorizJustify({-1: pcbnew.GR_TEXT_H_ALIGN_LEFT, 0: pcbnew.GR_TEXT_H_ALIGN_CENTER, 1: pcbnew.GR_TEXT_H_ALIGN_RIGHT}[just])
    t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    t.SetPosition(V(x, y))
    board.Add(t)
    return t


def short(net):
    """Header pin label: PA9 -> A9, +3.3V -> 3V3."""
    return {"+3.3V": "3V3", "+5V": "5V", "NRST": "RST"}.get(net, net[1:] if re.fullmatch(r"P[ABC]\d+", net) else net)


def fab_refs(board):
    """References go on the fab layer (assembly drawing). Footprints that already
    carry a small ${REFERENCE} fab text keep only that one."""
    for fp in board.GetFootprints():
        fp.Reference().SetLayer(pcbnew.F_Fab)
        fp.Value().SetVisible(False)
        has_small = any(g.Type() == pcbnew.PCB_TEXT_T and g.GetText() == "${REFERENCE}" and g.GetLayer() == pcbnew.F_Fab
                        for g in fp.GraphicalItems())
        fp.Reference().SetVisible(not has_small)


def silk(board):
    # References live on the fab layer (assembly drawing), as in v1.1.
    fab_refs(board)

    # Front pin labels: rotated text in the strips either side of each header column.
    off = 1.27 + P.LBL / 2 - 0.06  # nudge outer/inner labels toward the header body for edge clearance
    for ref, outer_odd in (("J3", True), ("J1", False)):
        x0, y0 = P.PLACE[ref][:2]
        for pin, net in spec.PARTS[ref][3].items():
            n = int(pin)
            col, row = (n - 1) % 2, (n - 1) // 2
            px = x0 + 2.54 * col
            is_outer = (col == 0) == outer_odd
            side = -1 if (ref == "J3") == is_outer else 1
            text(board, short(net), px + side * off, y0 + 2.54 * row, pcbnew.F_SilkS, h=0.8, w=0.7, angle=90)

    for s, x, y, a, j in P.LABELS:
        text(board, s, x, y, pcbnew.F_SilkS, h=0.8, w=0.62 if a == 0 else 0.7, angle=a, just=j)
    for x, y, r in P.SILK_DOTS:
        d = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_CIRCLE)
        d.SetCenter(V(x, y)); d.SetEnd(V(x + r / 2, y))
        d.SetWidth(mm(r)); d.SetFilled(True); d.SetLayer(pcbnew.F_SilkS)
        board.Add(d)

    # Back: function cheat sheet + name.
    lines = [
        "STM32F103C8 8MHz",
        "A9 TX1   A10 RX1", "A13 SWDIO A14 SWCLK", "B3 SWO   RST NRST",
        "B6 SCL1  B7 SDA1", "A5 SCK1  A6 MISO1", "A7 MOSI1 B2 BOOT1", "B8 CANRX B9 CANTX",
        "C13 LED (low=on)", "5V: USB out/<=5.5V in", "3V3 out: 250 mA max",
    ] + [f"IMU {spec.PARTS['U4'][1]} 0x6A", "I2C1 B6/B7, INT1 A0"] * ("U4" in spec.PARTS)
    for i, s in enumerate(lines):
        text(board, s, P.c, 8.3 + 1.25 * i, pcbnew.B_SilkS, h=0.8, w=0.7)
    text(board, f"NickLink v{spec.REV}", P.c, P.H - 2.0, pcbnew.B_SilkS, h=1.0, w=0.8)


def dump(board, path):
    """Geometry for tools/preview.py."""
    g = {"W": P.W, "H": P.H, "OX": P.OX, "OY": P.OY, "fps": []}
    for fp in board.GetFootprints():
        cy = fp.GetCourtyard(pcbnew.F_CrtYd)
        poly = []
        if cy.OutlineCount():
            o = cy.Outline(0)
            poly = [(pcbnew.ToMM(o.CPoint(i).x), pcbnew.ToMM(o.CPoint(i).y)) for i in range(o.PointCount())]
        pads = []
        for p in fp.Pads():
            bb = p.GetBoundingBox()
            pads.append({"num": p.GetNumber(), "net": p.GetNetname(), "x": pcbnew.ToMM(p.GetPosition().x), "y": pcbnew.ToMM(p.GetPosition().y),
                         "bb": [pcbnew.ToMM(v) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())],
                         "tht": p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)})
        g["fps"].append({"ref": fp.GetReference(), "x": pcbnew.ToMM(fp.GetPosition().x), "y": pcbnew.ToMM(fp.GetPosition().y),
                         "rot": fp.GetOrientationDegrees(), "crtyd": poly, "pads": pads})
    json.dump(g, open(path, "w"), indent=0)


def resilk(path):
    """Redraw all board-level silkscreen on an already-routed board (copper untouched)."""
    board = pcbnew.LoadBoard(path)
    for d in list(board.GetDrawings()):
        if d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
            board.Delete(d)
    silk(board)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(path, board)


if __name__ == "__main__":
    if sys.argv[1] == "--resilk":
        resilk(sys.argv[2])
    else:
        main(*sys.argv[1:])
