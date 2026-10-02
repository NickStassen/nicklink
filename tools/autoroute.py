#!/usr/bin/env python3
"""Specctra round-trip helper, run inside the kicad/kicad container (needs pcbnew).

  autoroute.py export <board.kicad_pcb> <out.dsn> [--skip-nets A,B]
      Locks every existing track/via (so Freerouting treats it as fixed and
      KiCad's SES import keeps it), writes the DSN, and records which items
      were originally unlocked in <out.dsn>.unlock.
      --skip-nets drops those nets from the DSN network so they are not routed
      (e.g. GND that is handled by pours).
  autoroute.py import <board.kicad_pcb> <in.ses> <out.kicad_pcb> <dsn>
      Imports the SES, restores the original lock flags, refills zones, saves.
With RIPUP=1 (second pass on a routed board) only the already-locked pre-routes stay fixed:
earlier autorouted tracks go to Freerouting as movable wiring it may rip up, and the SES replaces them.
"""
import os
import re
import sys

import pcbnew


RIPUP = os.environ.get("RIPUP") == "1"


def drop(text, head):
    """Remove every balanced s-expression whose start matches regex `head`."""
    n = 0
    while m := re.search(head, text):
        i, depth, q = m.start(), 0, False
        for j in range(i, len(text)):
            c = text[j]
            if c == '"':
                q = not q
            elif not q and c in "()":
                depth += 1 if c == "(" else -1
                if depth == 0:
                    break
        text = text[:i] + text[j + 1 :]
        n += 1
    return text, n


def export(pcb, dsn, skip):
    board = pcbnew.LoadBoard(pcb)
    unlocked = [t.m_Uuid.AsString() for t in board.GetTracks() if not t.IsLocked()]
    for t in board.GetTracks():
        t.SetLocked(t.IsLocked() or not RIPUP)
    # Pour-only rule areas (tracks allowed) only matter to the zone filler, but KiCad
    # exports every rule area as a DSN keepout; drop them so Freerouting can route there.
    for z in list(board.Zones()):
        if z.GetIsRuleArea() and not z.GetDoNotAllowTracks():
            board.Delete(z)
    assert pcbnew.ExportSpecctraDSN(board, dsn), "ExportSpecctraDSN failed"
    open(dsn + ".unlock", "w").write("\n".join(unlocked))
    text = open(dsn).read()
    # KiCad exports pours as (plane ...). Freerouting then treats every pin on
    # that layer as connected to the plane, but the real pour gets split into
    # islands by the new tracks -> unconnected GND after refill. Drop the planes
    # so pour nets are routed with real tracks; the pour is refilled on import.
    text, n = drop(text, r"\(plane\s")
    print(f"dropped {n} plane(s) from DSN")
    for net in skip:
        # The (net X (pins ...)) block in (network ...): without it the pins are
        # netless to Freerouting, so it neither routes them nor rips them up.
        text, n = drop(text, r'\(net\s+("?)%s\1\s+\(pins' % re.escape(net))
        # ...and the name in its (class ...) net list.
        text = re.sub(r'(\(class\s(?:[^()"]|"[^"]*")*?)\s"?%s"?(?=[\s)])' % re.escape(net), r"\1", text)
        print(f"skip-net {net}: removed {n} net block(s)")
    open(dsn, "w").write(text)
    print(f"exported {dsn}: {len(board.GetTracks())} existing tracks/vias locked as fixed")


def import_(pcb, ses, out, dsn):
    board = pcbnew.LoadBoard(pcb)
    for t in board.GetTracks():  # same locking as export, so SES import keeps them
        t.SetLocked(t.IsLocked() or not RIPUP)
    assert pcbnew.ImportSpecctraSES(board, ses), "ImportSpecctraSES failed"
    unlock = set(filter(None, open(dsn + ".unlock").read().split("\n")))
    # Freerouting 2.4.1 necks tracks down to 0.75x at small pads and its job
    # ("API") settings override --router.automatic_neckdown=false, so clamp
    # imported tracks up to the board's minimum track width instead.
    wmin, widened = board.GetDesignSettings().m_TrackMinWidth, 0
    for t in board.GetTracks():
        if t.m_Uuid.AsString() in unlock:
            t.SetLocked(False)
        elif not t.IsLocked() and t.Type() == pcbnew.PCB_TRACE_T and t.GetWidth() < wmin:
            t.SetWidth(wmin)
            widened += 1
    print(f"widened {widened} necked-down track(s) to min width {wmin / 1e6} mm")
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.BuildConnectivity()
    assert pcbnew.SaveBoard(out, board), "SaveBoard failed"
    n_unrouted = board.GetConnectivity().GetUnconnectedCount(False)
    print(f"saved {out}: {len(board.GetTracks())} tracks/vias, {n_unrouted} unconnected")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "export":
        skip = []
        if "--skip-nets" in a:
            i = a.index("--skip-nets")
            skip = [s for s in a[i + 1].split(",") if s]
            del a[i : i + 2]
        export(a[1], a[2], skip)
    elif a[0] == "import":
        import_(*a[1:5])
    else:
        sys.exit(__doc__)
