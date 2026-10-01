#!/usr/bin/env python3
"""Generate nicklink.kicad_sch from tools/spec.py.

Every symbol pin gets a short wire stub ending in a local label (or a power
symbol for POWER_NETS); unlisted pins get a no_connect marker. Symbol
placement lives in LAYOUT below; everything electrical comes from spec.py.

Run inside the kicad/kicad:10.0 container (needs the stock symbol libraries),
normally via tools/sch.sh.
"""
import copy
import os
import re
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import spec  # noqa: E402

SYMDIR = os.environ.get("KICAD_SYMBOL_DIR", "/usr/share/kicad/symbols")
OUT = os.path.join(HERE, "..", "nicklink.kicad_sch")
PROJECT = "nicklink"
ROOT_UUID = "40aeb617-1e9c-49dd-a464-61de3f0156c5"  # keep v1.1 root uuid
NS = uuid.UUID(ROOT_UUID)
G = 2.54   # grid
STUB = 2.54  # wire stub length
FONT = 1.27

TITLE = {"title": "NickLink", "date": "2026-10-01", "rev": spec.REV}

# Library pins renumbered to match the footprint (footprint calls the USB-C
# shield pads "SH"; stock symbol calls them "S1").
PIN_RENUMBER = {"Connector:USB_C_Receptacle_USB2.0_16P": {"S1": "SH"}}

# Blocks: title -> list of (ref, x, y[, rotation]) symbol anchors in mm.
# Parts are drawn net-label style, so only positions matter, not wiring.
LAYOUT = {
    "Clock (8 MHz HSE)": [("Y1", 33.02, 38.1), ("C10", 22.86, 55.88), ("C11", 43.18, 55.88)],
    "Reset / Boot": [
        ("SW1", 33.02, 91.44), ("C9", 58.42, 91.44),
        ("SW2", 33.02, 116.84), ("R1", 58.42, 116.84), ("R8", 58.42, 142.24),
    ],
    "MCU + decoupling": [
        ("U1", 114.3, 137.16),
        ("C1", 162.56, 121.92), ("C2", 175.26, 121.92), ("C3", 187.96, 121.92),
        ("C4", 200.66, 121.92), ("C5", 213.36, 121.92),
        ("FB1", 162.56, 149.86), ("C6", 187.96, 149.86), ("C7", 200.66, 149.86),
    ],
    "USB-C + ESD": [
        ("J2", 170.18, 45.72), ("R4", 208.28, 45.72, 180), ("R5", 218.44, 45.72, 180),
        ("R2", 228.6, 45.72), ("U3", 251.46, 45.72), ("C13", 241.3, 66.04),
    ],
    "Power": [
        ("D2", 292.1, 38.1, 180), ("C12", 309.88, 40.64), ("U2", 335.28, 40.64),
        ("C8", 355.6, 40.64), ("D1", 381.0, 38.1, 180), ("R3", 393.7, 60.96, 180),
    ],
    "User LED": [("D3", 292.1, 99.06, 180), ("R6", 332.74, 99.06, 270)],
    "Headers J1 / J3": [("J3", 299.72, 139.7), ("J1", 365.76, 139.7)],
    "IMU (I2C1 0x6A, INT1 -> PA0)": [
        ("U4", 309.88, 190.5), ("R7", 342.9, 187.96), ("R9", 355.6, 187.96),
        ("C14", 368.3, 187.96), ("C15", 381.0, 187.96),
    ],
}
FLAG_AREA = (284.48, 71.12)  # PWR_FLAG row (inside the Power block)
NOTE_AT = (20.32, 205.74)

NOTES = [
    "NOTES",
    "1. Every header pin is labelled beside it on the front silkscreen (A9 = PA9); the back has a function cheat sheet.",
    "2. CAN (PB8 RX / PB9 TX, remapped) is logic level only: it needs an external CAN transceiver.",
    "3. USB and CAN cannot run at the same time on the STM32F103 (they share the packet RAM).",
    "4. The 3V3 header pins are outputs of the on-board LDO (U2); do not back-drive them from another supply.",
    "5. The 5V header pin is USB VBUS after the Schottky D2; it can also be used as a 5 V input (max 5.5 V).",
]


# --------------------------------------------------------------------------
# S-expressions
class Q(str):
    """A quoted string atom."""


TOK = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+')


def _unq(s):
    return Q(re.sub(r'\\(.)', lambda m: {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)), s[1:-1]))


def parse(text, pos=0):
    """Parse the first complete expression at/after pos."""
    stack = [[]]
    for m in TOK.finditer(text, pos):
        t = m.group()
        if t == "(":
            stack.append([])
        elif t == ")":
            x = stack.pop()
            stack[-1].append(x)
            if len(stack) == 1:
                return x
        else:
            stack[-1].append(_unq(t) if t[0] == '"' else t)
    raise ValueError("unbalanced")


def num(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def atom(a):
    if isinstance(a, Q):
        return '"' + a.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if isinstance(a, float):
        return num(a)
    return str(a)


def dump(x, ind=0):
    if not any(isinstance(c, list) for c in x):
        return "(" + " ".join(atom(c) for c in x) + ")"
    head = [atom(c) for c in x if not isinstance(c, list)]
    out = "(" + " ".join(head)
    for c in x:
        if isinstance(c, list):
            out += "\n" + "  " * (ind + 1) + dump(c, ind + 1)
    return out + ")"


def find(x, key):
    return next((c for c in x if isinstance(c, list) and c and c[0] == key), None)


def findall(x, key):
    return [c for c in x if isinstance(c, list) and c and c[0] == key]


# --------------------------------------------------------------------------
# Library symbols
_libtext = {}


def lib_raw(lib, name):
    if lib not in _libtext:
        path = os.path.join(os.path.dirname(__file__), "..", "nicklink.kicad_sym") if lib == "nicklink" else os.path.join(SYMDIR, lib + ".kicad_sym")
        with open(path, encoding="utf-8") as f:
            _libtext[lib] = f.read()
    m = re.search(r'^\t\(symbol "%s"\s*$' % re.escape(name), _libtext[lib], re.M)
    if not m:
        sys.exit(f"symbol {lib}:{name} not found in {SYMDIR}")
    return parse(_libtext[lib], m.start())


def lib_flat(lib, name):
    """Symbol definition with `extends` resolved, as KiCad embeds it."""
    s = lib_raw(lib, name)
    ext = find(s, "extends")
    if not ext:
        return s
    parent = lib_flat(lib, ext[1])
    out = [c for c in parent if not (isinstance(c, list) and c[0] == "property")]
    out[1] = Q(name)
    for c in out:
        if isinstance(c, list) and c[0] == "symbol":
            c[1] = Q(name + c[1][len(ext[1]):])
    props = [c for c in s if isinstance(c, list) and c[0] == "property"]
    names = {p[1] for p in props}
    props += [p for p in findall(parent, "property") if p[1] not in names]
    i = next(i for i, c in enumerate(out) if isinstance(c, list) and c[0] == "symbol")
    return out[:i] + props + out[i:]


class Sym:
    def __init__(self, lib_id):
        lib, name = lib_id.split(":")
        d = copy.deepcopy(lib_flat(lib, name))
        d[1] = Q(lib_id)
        ren = PIN_RENUMBER.get(lib_id, {})
        self.lib_id, self.d, self.pins, self.gfx = lib_id, d, [], []
        for u in findall(d, "symbol"):
            unit, style = map(int, u[1].rsplit("_", 2)[1:])
            if unit not in (0, 1) or style not in (0, 1):
                continue
            for c in u[2:]:
                if not isinstance(c, list):
                    continue
                if c[0] == "pin":
                    n = find(c, "number")
                    if n[1] in ren:
                        n[1] = Q(ren[n[1]])
                    at = find(c, "at")
                    self.pins.append({"num": str(n[1]), "name": str(find(c, "name")[1]), "type": c[1],
                                      "x": float(at[1]), "y": float(at[2]), "a": int(float(at[3])),
                                      "len": float(find(c, "length")[1])})
                elif c[0] in ("rectangle", "polyline", "circle", "arc", "bezier"):
                    for k in ("start", "end", "center", "mid"):
                        p = find(c, k)
                        if p:
                            self.gfx.append((float(p[1]), float(p[2])))
                    if find(c, "radius"):
                        r = float(find(c, "radius")[1])
                        cx, cy = self.gfx[-1]
                        self.gfx += [(cx - r, cy - r), (cx + r, cy + r)]
                    pts = find(c, "pts")
                    for p in findall(pts or [], "xy"):
                        self.gfx.append((float(p[1]), float(p[2])))
        self.is_power = find(d, "power") is not None
        pts = self.gfx + [(p["x"], p["y"]) for p in self.pins]
        self.body = (min(p[0] for p in pts), min(p[1] for p in pts),
                     max(p[0] for p in pts), max(p[1] for p in pts))  # symbol space, Y up

    def prop(self, name):
        return next((p for p in findall(self.d, "property") if p[1] == name), None)




# --------------------------------------------------------------------------
# Geometry helpers (schematic space, mm, Y down)
OUTWARD = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}  # lib pin angle -> away from body


def rot(v, r):
    """Rotate a screen vector the way KiCad rotates a symbol by r degrees."""
    x, y = v
    for _ in range(r // 90 % 4):
        x, y = y, -x
    return round(x, 4), round(y, 4)


def xf(x, y, r, px, py):
    """Symbol-space point -> schematic point for a symbol at (x, y, r)."""
    dx, dy = rot((px, -py), r)
    return round(x + dx, 4), round(y + dy, 4)


def tw(s, size=FONT):
    return 1.0 * size * max(len(line) for line in s.split("\n"))


def trect(x, y, s, justify="", size=FONT):
    w, h = tw(s, size), size * 1.3 * (s.count("\n") + 1)
    j = justify.split()
    x0 = x if "left" in j else x - w if "right" in j else x - w / 2
    y0 = y - h if "bottom" in j else y if "top" in j else y - h / 2
    return (x0, y0, x0 + w, y0 + h)


def bbox_of(points):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys))


uid = lambda *k: Q(str(uuid.uuid5(NS, "/".join(map(str, k)))))  # noqa: E731


# --------------------------------------------------------------------------
class Sheet:
    def __init__(self):
        self.syms = {}      # lib_id -> Sym
        self.items = []     # top-level schematic items
        self.rects = []     # (rect, owner, block, what) for the overlap check
        self.npwr = 0
        self.nflg = 0
        self.block = None

    def sym(self, lib_id):
        if lib_id not in self.syms:
            self.syms[lib_id] = Sym(lib_id)
        return self.syms[lib_id]

    def note(self, rect, owner, what):
        self.rects.append((rect, owner, self.block, what))

    # ---- primitives
    def wire(self, a, b, owner):
        self.items.append(["wire", ["pts", ["xy", a[0], a[1]], ["xy", b[0], b[1]]],
                           ["stroke", ["width", 0], ["type", "default"]], ["uuid", uid("w", a, b)]])
        self.note((min(a[0], b[0]) - 0.1, min(a[1], b[1]) - 0.1, max(a[0], b[0]) + 0.1, max(a[1], b[1]) + 0.1),
                  owner, "wire")

    def junction(self, p):
        self.items.append(["junction", ["at", p[0], p[1]], ["diameter", 0], ["color", 0, 0, 0, 0], ["uuid", uid("j", p)]])

    def no_connect(self, p):
        self.items.append(["no_connect", ["at", p[0], p[1]], ["uuid", uid("nc", p)]])

    def label(self, net, p, d, owner):
        a = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[d]
        j = "left bottom" if a in (0, 90) else "right bottom"
        self.items.append(["label", Q(net), ["at", p[0], p[1], a],
                           ["effects", ["font", ["size", FONT, FONT]], ["justify", *j.split()]], ["uuid", uid("l", net, p)]])
        w, h = tw(net) + 0.5, 1.9
        r = {0: (p[0], p[1] - h, p[0] + w, p[1]), 180: (p[0] - w, p[1] - h, p[0], p[1]),
             90: (p[0] - h, p[1] - w, p[0], p[1]), 270: (p[0] - h, p[1], p[0], p[1] + w)}[a]
        self.note(r, owner, f"label {net}")

    def text(self, s, p, size=FONT, bold=False, justify="left top"):
        font = ["font", ["size", size, size]] + ([["bold", "yes"]] if bold else [])
        self.items.append(["text", Q(s), ["exclude_from_sim", "no"], ["at", p[0], p[1], 0],
                           ["effects", font, ["justify", *justify.split()]], ["uuid", uid("t", s)]])
        self.note(trect(p[0], p[1], s, justify, size), ("text", s), "text")

    def place(self, lib_id, ref, value, at, r=0, footprint=None, extra=None, fields=None, owner=None, key=None):
        """Place a symbol. fields: {name: (x, y, angle, justify)} for visible fields."""
        s = self.sym(lib_id)
        x, y = at
        props = []
        for p in findall(s.d, "property"):
            name = str(p[1])
            if name.startswith("ki_"):
                continue
            val = {"Reference": ref, "Value": value}.get(name, str(p[2]))
            if name == "Footprint" and footprint is not None:
                val = footprint
            hide = find(p, "hide") is not None
            fx, fy, fa, fj = (fields or {}).get(name, (x, y, 0, ""))
            # Field angle/justify are stored relative to the symbol: undo its rotation
            # so the text displays as requested (horizontal, justified as given).
            sa = (fa + 90) % 180 if r in (90, 270) else fa
            sj = fj
            if r in (180, 270):
                flip = {"left": "right", "right": "left", "top": "bottom", "bottom": "top"}
                sj = " ".join(flip.get(w, w) for w in fj.split())
            props.append(self._prop(name, val, fx, fy, sa, hide, sj))
            if not hide and name in (fields or {}):
                self.note(trect(fx, fy, val, fj), owner or (ref, "fields"), f"{name} {val}")
        for k, v in (extra or {}).items():
            props.append(self._prop(k, v, x, y, 0, True, ""))
        flag = lambda k: find(s.d, k)[1] if find(s.d, k) else "yes"  # noqa: E731
        self.items.append(
            ["symbol", ["lib_id", Q(lib_id)], ["at", x, y, r], ["unit", 1], ["body_style", 1],
             ["exclude_from_sim", "no"], ["in_bom", flag("in_bom")], ["on_board", flag("on_board")],
             ["in_pos_files", flag("in_pos_files")], ["dnp", "no"], ["uuid", uid("s", key or ref)], *props,
             *[["pin", Q(n), ["uuid", uid("p", ref, n)]] for n in dict.fromkeys(p["num"] for p in s.pins)],
             ["instances", ["project", Q(PROJECT), ["path", Q("/" + ROOT_UUID),
                                                    ["reference", Q(ref)], ["unit", 1]]]]])
        if s.gfx:
            self.note(bbox_of([xf(x, y, r, *g) for g in s.gfx]), owner or (ref, "body"), f"body {ref}")
        return s

    @staticmethod
    def _prop(name, val, x, y, a, hide, justify):
        e = ["effects", ["font", ["size", FONT, FONT]]] + ([["justify", *justify.split()]] if justify else [])
        return ["property", Q(name), Q(val), ["at", x, y, a]] + ([["hide", "yes"]] if hide else []) + \
               [["show_name", "no"], ["do_not_autoplace", "no"], e]

    def power(self, net, p, d, owner, key):
        """Power symbol at p with its graphic pointing in screen direction d."""
        lib_id = "power:" + net
        s = self.sym(lib_id)
        base = (0, 1) if sum(g[1] for g in s.gfx) < 0 else (0, -1)
        r = next(r for r in (0, 90, 180, 270) if rot(base, r) == d)
        ln = max(max(abs(g[0]), abs(g[1])) for g in s.gfx)
        if d[0]:  # horizontal: text beyond the tip, kept horizontal
            vx, vy = p[0] + d[0] * (ln + 0.6 + tw(net) / 2), p[1]
        else:
            vx, vy = p[0], p[1] + d[1] * (ln + 1.4)
        self.npwr += 1
        ref = f"#PWR{self.npwr:02d}"
        self.place(lib_id, ref, net, p, r, fields={"Value": (vx, vy, 0, "")},
                   owner=owner, key=("pwr", key))  # uuid stable across renumbering
        return ref

    def flag(self, p, owner, key):
        self.nflg += 1
        self.place("power:PWR_FLAG", f"#FLG{self.nflg:02d}", "PWR_FLAG", p,
                   fields={"Value": (p[0], p[1] - 3.81, 0, "")}, owner=owner, key=("flg", key))


# --------------------------------------------------------------------------
def field_pos(s, x, y, r, name):
    """Visible Reference/Value placement: beside 2-pin vertical parts, above/below
    horizontal ones, library position otherwise (text kept horizontal)."""
    x0, y0, x1, y1 = bbox_of([xf(x, y, r, *g) for g in s.gfx])
    sides = {rot(OUTWARD[p["a"]], r) for p in s.pins}
    first = name == "Reference"
    if sides <= {(0, 1), (0, -1)}:
        return (x1 + 1.27, y + (-1.27 if first else 1.27), 0, "left")
    if sides <= {(1, 0), (-1, 0)}:
        return (x, y0 - 1.9, 0, "") if first else (x, y1 + 1.9, 0, "")
    p = s.prop(name)
    at, j = find(p, "at"), find(find(p, "effects"), "justify")
    fx, fy = xf(x, y, r, float(at[1]), float(at[2]))
    return (fx, fy, 0, " ".join(j[1:]) if j else "")


def place_part(sh, ref, at, r):
    lib_id, value, fp, nets, extra = spec.PARTS[ref]
    s = sh.sym(lib_id)
    missing = set(nets) - {p["num"] for p in s.pins}
    if missing:
        sys.exit(f"{ref}: spec pins {sorted(missing)} not in symbol {lib_id}")
    x, y = at
    sh.place(lib_id, ref, value, at, r, footprint=fp, extra=extra,
             fields={n: field_pos(s, x, y, r, n) for n in ("Reference", "Value")})
    locs = {}
    for p in s.pins:
        locs.setdefault((p["x"], p["y"]), []).append(p)
    # Sideways power symbols go in a column beyond the longest label on that side,
    # so their artwork never crowds the neighbouring pins' labels (headers etc).
    side_lbl = {}
    for p in s.pins:
        n = nets.get(p["num"])
        d = rot(OUTWARD[p["a"]], r)
        if n and d[0] and n not in spec.POWER_NETS:
            side_lbl[d] = max(side_lbl.get(d, 0), tw(n) + 1.27)
    ends = []
    for (px, py), ps in locs.items():
        got = {nets.get(p["num"]) for p in ps if p["type"] != "no_connect" or p["num"] in nets}
        if not got:
            continue  # library no_connect pins need no marker
        if len(got) > 1:
            sys.exit(f"{ref}: stacked pins {[p['num'] for p in ps]} map to different nets {got}")
        net = got.pop()
        pt = xf(x, y, r, px, py)
        if net is None:
            sh.no_connect(pt)
            continue
        d = rot(OUTWARD[ps[0]["a"]], r)
        ln = STUB
        if net in spec.POWER_NETS and d in side_lbl:
            ln += -(-side_lbl[d] // G) * G
        e = (round(pt[0] + d[0] * ln, 4), round(pt[1] + d[1] * ln, 4))
        key = (ref, ps[0]["num"])
        sh.wire(pt, e, key)
        for p in ps:  # pin line from body to connection point
            sh.note(bbox_of([pt, (pt[0] - d[0] * p["len"], pt[1] - d[1] * p["len"])]), key, "pin")
        ends.append((d, e, net, key))
    # Adjacent same-side pins on the same net share one label / power symbol.
    along = lambda e: e[1][1] if e[0][0] else e[1][0]  # noqa: E731
    perp = lambda e: e[1][0] if e[0][0] else e[1][1]  # noqa: E731
    ends.sort(key=lambda e: (e[0], perp(e), along(e)))
    groups = []
    for e in ends:
        g = groups[-1] if groups else None
        if g and g[-1][0] == e[0] and perp(g[-1]) == perp(e) and g[-1][2] == e[2] \
                and abs(along(e) - along(g[-1]) - G) < 1e-3:
            g.append(e)
        else:
            groups.append([e])
    for g in groups:
        d, e, net, key = g[0]
        for a, b in zip(g, g[1:]):
            sh.wire(a[1], b[1], key)
        for m in g[1:-1]:
            sh.junction(m[1])
        if net in spec.POWER_NETS:
            sh.power(net, e, d, key, key)
        else:
            sh.label(net, e, d, key)


def net_types(sh):
    types = {}
    for lib_id, _, _, nets, _ in spec.PARTS.values():
        pins = {p["num"]: p["type"] for p in sh.sym(lib_id).pins}
        for n, net in nets.items():
            types.setdefault(net, set()).add(pins[n])
    return types


def overlaps(rects, eps=0.1):
    bad = []
    for i, (a, oa, _, wa) in enumerate(rects):
        for b, ob, _, wb in rects[i + 1:]:
            if oa == ob or (wa == "wire" and wb == "wire"):
                continue
            if oa[0] == ob[0] and {wa, wb} & {"pin", "wire"}:
                continue  # a symbol's own pins/stubs may cross its own artwork
            if a[0] + eps < b[2] - eps and b[0] + eps < a[2] - eps and a[1] + eps < b[3] - eps and b[1] + eps < a[3] - eps:
                bad.append(f"{wa} ({oa}) overlaps {wb} ({ob})")
    return bad


def main():
    sh = Sheet()
    placed = set()
    layout = dict(LAYOUT)
    extra = [r for r in spec.PARTS if not any(r == e[0] for v in LAYOUT.values() for e in v)]
    if extra:  # new parts nobody has laid out yet: park them in a row so the sheet still works
        print("WARNING: no LAYOUT entry for", extra, "- placed in 'Unplaced'")
        layout["Unplaced"] = [(r, 30.48 + 30.48 * i, 254.0) for i, r in enumerate(extra)]
    for block, entries in layout.items():
        sh.block = block
        for ref, x, y, *r in entries:
            if ref in spec.PARTS:
                place_part(sh, ref, (x, y), r[0] if r else 0)
                placed.add(ref)

    # PWR_FLAG for every net that has nothing driving it.
    sh.block = "Power"
    types = net_types(sh)
    need = sorted(n for n, t in types.items()
                  if "power_out" not in t and (n in spec.POWER_NETS or "power_in" in t))
    fx, fy = FLAG_AREA
    for i, net in enumerate(need):
        x = fx + 22.86 * i
        key = ("flag", net)
        if net in spec.POWER_NETS:
            sh.power(net, (x, fy), (0, 1) if sum(g[1] for g in sh.sym("power:" + net).gfx) < 0 else (0, -1), key, key)
        else:
            sh.label(net, (x, fy), (-1, 0), key)
        sh.wire((x, fy), (x + 10.16, fy), key)
        sh.flag((x + 10.16, fy), ("flagsym", net), net)

    # Block frames + titles, sized to their contents.
    frames = []
    for block in layout:
        rs = [r for r, _, b, _ in sh.rects if b == block]
        if not rs:
            continue
        x0, y0, x1, y1 = bbox_of([(r[0], r[1]) for r in rs] + [(r[2], r[3]) for r in rs])
        x0, y0, x1, y1 = x0 - 2.54, y0 - 6.35, x1 + 2.54, y1 + 2.54
        frames.append(((x0, y0, x1, y1), block))
        sh.items.append(["rectangle", ["start", round(x0, 2), round(y0, 2)], ["end", round(x1, 2), round(y1, 2)],
                         ["stroke", ["width", 0.1524], ["type", "dash"]], ["fill", ["type", "none"]],
                         ["uuid", uid("frame", block)]])
        sh.block = None
        sh.text(block.upper(), (x0 + 1.27, y0 + 1.27), size=1.778, bold=True)
    sh.block = None
    sh.text("\n".join(NOTES), NOTE_AT, size=1.524)

    problems = overlaps(sh.rects)
    problems += [f"frames overlap: {a[1]} / {b[1]}" for i, a in enumerate(frames) for b in frames[i + 1:]
                 if a[0][0] < b[0][2] and b[0][0] < a[0][2] and a[0][1] < b[0][3] and b[0][1] < a[0][3]]
    note_r = [r for r, o, _, _ in sh.rects if o == ("text", "\n".join(NOTES))][0]
    problems += [f"notes overlap frame {b}" for f, b in frames
                 if note_r[0] < f[2] and f[0] < note_r[2] and note_r[1] < f[3] and f[1] < note_r[3]]
    allr = [r for r, *_ in sh.rects] + [f for f, _ in frames]
    x0, y0, x1, y1 = bbox_of([(r[0], r[1]) for r in allr] + [(r[2], r[3]) for r in allr])
    if x0 < 12 or y0 < 12 or x1 > 408 or y1 > 285:
        problems.append(f"content outside sheet border: {(x0, y0, x1, y1)}")

    doc = ["kicad_sch", ["version", 20260306], ["generator", Q("eeschema")], ["generator_version", Q("10.0")],
           ["uuid", Q(ROOT_UUID)], ["paper", Q("A3")],
           ["title_block", *[[k, Q(v)] for k, v in TITLE.items()]],
           ["lib_symbols", *[s.d for _, s in sorted(sh.syms.items())]],
           *sh.items,
           ["sheet_instances", ["path", Q("/"), ["page", Q("1")]]], ["embedded_fonts", "no"]]
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(dump(doc) + "\n")
    print(f"wrote {os.path.normpath(OUT)}: {len(placed)} parts, {sh.npwr} power symbols, "
          f"{sh.nflg} PWR_FLAGs ({', '.join(need)})")
    if problems:
        print("LAYOUT PROBLEMS (edit LAYOUT in tools/gen_sch.py):\n  " + "\n  ".join(problems))
        sys.exit(1)


if __name__ == "__main__":
    main()
