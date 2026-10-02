#!/usr/bin/env bash
# Fabrication outputs for NickLink from the root nicklink.kicad_pcb/.kicad_sch:
#   fabrication/$REV/gerbers/   Gerbers + job file, PTH/NPTH Excellon + drill map PDFs
#   fabrication/$REV/nicklink_BOM.csv (with notes), nicklink_CPL.csv (Gerber coordinates)
#   fabrication/$REV/nicklink_gerbers.zip, nicklink_BOM_JLC.csv   (upload these + the CPL to JLC)
#   docs/assembly.pdf, docs/copper.pdf, docs/images/top.png, bottom.png
#   checks/final-drc.json, checks/final-erc.rpt
# Fails if DRC or ERC is not clean, or any output check fails.
# Usage: [REV=v<spec.REV>] tools/fab.sh
set -euo pipefail
cd "$(dirname "$0")/.."
REV=${REV:-v$(python3 -c "import sys; sys.path.insert(0, 'tools'); import spec; print(spec.REV)")}
OUT=fabrication/$REV
G=$OUT/gerbers
K=tools/kdock
TMP=$PWD/tools/_work/fab  # inside the repo so the kdock container sees it
rm -rf "$TMP"; mkdir -p "$TMP"
rm -rf "$G"; mkdir -p "$G" checks docs/images

# --- checks -------------------------------------------------------------------
tools/drc.sh nicklink.kicad_pcb | grep -v '^report:'
mv nicklink-drc.json checks/final-drc.json
# Same sym-lib-table trick as tools/sch.sh: image ships *.kicad_sym, repo table points at *.kicad_symdir.
sed 's/\.kicad_symdir/.kicad_sym/' sym-lib-table > "$TMP/sym-lib-table"
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD:/w" \
  -v "$TMP/sym-lib-table:/w/sym-lib-table:ro" -w /w "${KICAD_IMAGE:-kicad/kicad:10.0}" \
  kicad-cli sch erc --severity-all --exit-code-violations -o checks/final-erc.rpt nicklink.kicad_sch >/dev/null \
  || { cat checks/final-erc.rpt; exit 1; }
grep -q 'ERC messages: 0  Errors 0  Warnings 0' checks/final-erc.rpt
echo "ERC: 0 errors, 0 warnings"

# --- gerbers + drills ---------------------------------------------------------
$K kicad-cli pcb export gerbers -o "$G/" \
  -l F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts nicklink.kicad_pcb >/dev/null
$K kicad-cli pcb export drill -o "$G/" --format excellon --drill-origin absolute --excellon-units mm \
  --excellon-zeros-format decimal --excellon-separate-th --generate-map --map-format pdf nicklink.kicad_pcb >/dev/null

# --- BOM + CPL ----------------------------------------------------------------
$K kicad-cli sch export bom -o "$TMP/bom.csv" --fields 'Reference,Value,Footprint,LCSC,Note,MPN' \
  --labels 'Ref,Value,Footprint,LCSC,Note,MPN' --ref-range-delimiter '' nicklink.kicad_sch >/dev/null
$K kicad-cli pcb export pos -o "$TMP/pos_all.csv" --format csv --units mm --side both --exclude-dnp nicklink.kicad_pcb >/dev/null
$K kicad-cli pcb export pos -o "$TMP/pos_smd.csv" --format csv --units mm --side both --smd-only --exclude-dnp nicklink.kicad_pcb >/dev/null
python3 - "$TMP" "$G/nicklink-Edge_Cuts.gm1" "$OUT" <<'EOF'
import csv, math, os, re, sys, collections, zipfile
tmp, edge, out = sys.argv[1:]
rd = lambda f: list(csv.DictReader(open(f"{tmp}/{f}")))
refkey = lambda s: (re.sub(r"\d", "", s), int(re.sub(r"\D", "", s)))
pos = {r["Ref"]: r for r in rd("pos_all.csv")}
smd = {r["Ref"] for r in rd("pos_smd.csv")}
assert all(r["Side"] == "top" for r in pos.values()), "bottom-side parts: BOM/CPL are top-only"

# BOM: one line per LCSC part. JLC unselects every line when two lines match the same part,
# so parts that differ only in value text (RESET/BOOT0) or footprint variant (_NoSilk) share a line.
# JLC assembles everything, THT (headers, USB-C) included.
groups = collections.OrderedDict()
for r in sorted(rd("bom.csv"), key=lambda r: (r["Value"], r["Footprint"])):
    for ref in r["Ref"].split(","):
        assert r["LCSC"], f"{ref} has no LCSC number"
        groups.setdefault(r["LCSC"], []).append(dict(r, Ref=ref.strip()))
rows = []
for lcsc, parts in groups.items():
    refs = sorted((p["Ref"] for p in parts), key=refkey)
    assert all(r in pos for r in refs), f"{refs} not on the board"
    fps = {p["Footprint"].split(":")[-1] for p in parts}
    assert len({f.replace("_NoSilk", "") for f in fps}) == 1, (refs, fps)
    tht = {r not in smd for r in refs}; assert len(tht) == 1, (refs, "mixed SMD/THT")
    notes = collections.defaultdict(list)  # note -> refs carrying it; tag it when not group-wide
    for p in parts:
        for n in (p["MPN"], p["Note"]):
            if n: notes[n].append(p["Ref"])
    notes = [n if len(r) == len(refs) else f"{','.join(r)}: {n}" for n, r in notes.items()]
    vals = sorted({p["Value"] for p in parts})
    rows.append(["/".join(vals), ",".join(refs), min(fps, key=len), lcsc, "; ".join(notes), "THT" if tht.pop() else "SMD"])
rows.sort(key=lambda r: refkey(r[1].split(",")[0]))
with open(f"{out}/nicklink_BOM.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #", "Notes", "Assembly"]); w.writerows(rows)
# JLC upload set: the BOM's four JLC columns, gerbers + drills zipped
with open(f"{out}/nicklink_BOM_JLC.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"]); w.writerows(r[:4] for r in rows)
with zipfile.ZipFile(f"{out}/nicklink_gerbers.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for n in sorted(os.listdir(f"{out}/gerbers")):
        if not n.endswith(".pdf"):
            z.write(f"{out}/gerbers/{n}", n)

# CPL in the Gerber frame: kicad pos X/Y (Y = -page Y) are already Gerber coordinates. JLC aligns the
# CPL to the Gerbers by coordinate, so a board-relative origin shows every part offset off the board.
pts = [(int(x) / 1e6, int(y) / 1e6) for x, y in re.findall(r"^X(-?\d+)Y(-?\d+)", open(edge).read(), re.M)]
x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
w_mm, h_mm = max(p[0] for p in pts) - x0, max(p[1] for p in pts) - y0
# JLC places its own (EasyEDA) footprint for each LCSC part at the CPL angle and position. Checked
# 2026-10-02 against easyeda.com/api/products/<C>/components:
#   rotation: add the angle between JLC's pin 1 and KiCad's at 0 deg (the footprint name says where it is)
#     C8734    LQFP-48 "-BL"  pin 1 bottom-left            = KiCad at 90  -> -90
#     C15999   SOT-666 "-BR"  pin 1 bottom-right           = KiCad at 180 -> +180
#     C388477  SOT-323 "-BR"  pin 1 bottom-right           = KiCad at 180 -> +180
#     C5383109 2x10 header    drawn horizontal, pin 1 low-left = KiCad at 90 -> -90
#     C41785564 LGA-14 "-TL"  pin 1 top-left, as KiCad -> 0 (the earlier C5267406 was "-BR": +180)
#     all other parts (passives, SOD-323, LEDs, 3225 crystal, WSON-6, B3U, PTC, USB4085) match KiCad.
#   position: JLC's origin, in KiCad footprint coordinates (mm, y down), where it isn't KiCad's origin:
#     C5383109 header: pad-array centre (KiCad's origin is pin 1); C7095263 USB4085: 2.975 / 2.180 from A1.
JLC_ROT = {"C8734": -90, "C15999": 180, "C388477": 180, "C5383109": -90}
JLC_OFS = {"C5383109": (1.27, 11.43), "C7095263": (2.975, 2.18)}
lcsc_of = {ref: r[3] for r in rows for ref in r[1].split(",")}
with open(f"{out}/nicklink_CPL.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for ref in sorted(pos, key=refkey):
        r, c = pos[ref], lcsc_of[ref]
        a = math.radians(float(r["Rot"])); dx, dy = JLC_OFS.get(c, (0, 0))
        x = float(r["PosX"]) + dx * math.cos(a) + dy * math.sin(a)
        y = float(r["PosY"]) + dx * math.sin(a) - dy * math.cos(a)
        assert x0 < x < x0 + w_mm and y0 < y < y0 + h_mm, f"{ref} placed off the board at ({x:.3f}, {y:.3f})"
        w.writerow([ref, f"{x:.4f}mm", f"{y:.4f}mm", "Top", f"{(float(r['Rot']) + JLC_ROT.get(c, 0)) % 360:g}"])
sys.path.insert(0, "tools"); import placement as P
assert abs(w_mm - P.W) < 0.01 and abs(h_mm - P.H) < 0.01, f"Edge.Cuts {w_mm:.2f} x {h_mm:.2f} mm, expected {P.W} x {P.H}"
n_tht = sum(len(r[1].split(",")) for r in rows if r[5] == "THT")
print(f"BOM: {len(rows)} lines, {sum(len(r[1].split(',')) for r in rows)} parts ({n_tht} THT); CPL: {len(pos)} parts; board {w_mm:.2f} x {h_mm:.2f} mm")
EOF

# --- docs ---------------------------------------------------------------------
$K kicad-cli pcb export pdf --mode-single --scale 0 -l F.Fab,F.Silkscreen,Edge.Cuts -o docs/assembly.pdf nicklink.kicad_pcb >/dev/null
$K kicad-cli pcb export pdf --mode-multipage --scale 0 -l F.Cu,B.Cu --cl Edge.Cuts -o docs/copper.pdf nicklink.kicad_pcb >/dev/null
tools/get3d.sh nicklink.kicad_pcb | { grep -v '^have ' || true; }
for side in top bottom; do  # zoom < 1 so the USB-C shell overhanging the top edge isn't clipped
  $K kicad-cli pcb render --side $side --quality high --background transparent --zoom 0.9 \
    -w 1600 -h 1600 -o docs/images/$side.png nicklink.kicad_pcb | grep -q Success
done
# The high-quality raytracer leaves a blown-up ~30%-alpha ghost of the board in the background
# (and paints it into --background opaque too). Drop alpha below ~110, then flatten onto white.
python3 - docs/images/top.png docs/images/bottom.png <<'EOF'
import sys
from PIL import Image
for f in sys.argv[1:]:
    im = Image.open(f).convert("RGBA")
    im.putalpha(im.getchannel("A").point(lambda a: max(0, min(255, (a - 110) * 255 // 145))))
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im); bg.convert("RGB").save(f)
EOF

# --- verify -------------------------------------------------------------------
for l in F_Cu.gtl B_Cu.gbl F_Mask.gts B_Mask.gbs F_Paste.gtp B_Paste.gbp F_Silkscreen.gto B_Silkscreen.gbo \
         Edge_Cuts.gm1 job.gbrjob PTH.drl NPTH.drl PTH-drl_map.pdf NPTH-drl_map.pdf; do
  [[ -s $G/nicklink-$l ]] || { echo "MISSING $G/nicklink-$l"; exit 1; }
done
[[ $(ls "$G" | wc -l) -eq 14 ]] || { echo "unexpected files in $G:"; ls "$G"; exit 1; }
for f in docs/assembly.pdf docs/copper.pdf docs/images/top.png docs/images/bottom.png; do [[ -s $f ]] || { echo "MISSING $f"; exit 1; }; done
echo "OK: $OUT, docs and checks written"
ls -1 "$G" "$OUT"/*.csv
