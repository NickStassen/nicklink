"""Swap a placed footprint for another library footprint with the same pads, keeping position,
rotation, nets, fields and symbol link (e.g. a NoSilk variant on an already-routed board).
usage (in container): python3 tools/swapfp.py board.kicad_pcb REF LIB:NAME [REF LIB:NAME ...]
"""
import sys

import pcbnew

b = pcbnew.LoadBoard(sys.argv[1])
for ref, lib in zip(sys.argv[2::2], sys.argv[3::2]):
    old = b.FindFootprintByReference(ref)
    nick, name = lib.split(":")
    new = pcbnew.FootprintLoad(f"{nick}.pretty" if nick == "nicklink" else f"/usr/share/kicad/footprints/{nick}.pretty", name)
    new.SetFPIDAsString(lib)
    new.SetParent(b)
    b.Add(new)
    new.SetPosition(old.GetPosition()); new.SetOrientation(old.GetOrientation())
    new.SetReference(old.GetReference()); new.SetValue(old.GetValue())
    new.SetPath(old.GetPath()); new.SetSheetname(old.GetSheetname()); new.SetSheetfile(old.GetSheetfile())
    for f in old.GetFields():
        if not new.HasField(f.GetName()):
            nf = pcbnew.PCB_FIELD(new, new.GetNextFieldOrdinal(), f.GetName()); nf.SetText(f.GetText()); nf.SetVisible(False); new.Add(nf)
        else:
            new.GetField(f.GetName()).SetText(f.GetText())
    for p in new.Pads():
        p.SetNet(old.FindPadByNumber(p.GetNumber()).GetNet())
    new.Reference().SetPosition(old.Reference().GetPosition()); new.Reference().SetVisible(old.Reference().IsVisible())
    new.Reference().SetLayer(old.Reference().GetLayer())
    new.Value().SetPosition(old.Value().GetPosition()); new.Value().SetVisible(old.Value().IsVisible())
    b.Remove(old)
    print(f"{ref}: -> {lib}")
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(sys.argv[1], b)
