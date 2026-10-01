# NickLink build tools

NickLink v1.2 is generated, not hand-edited. Change the inputs below, then rebuild. Everything runs in the `kicad/kicad:10.0` Docker image, so no local KiCad install is needed. Freerouting runs in `eclipse-temurin:25-jre`.

## Inputs

| File | What it holds |
|---|---|
| `spec.py` | Parts, values, footprints, pin→net map, header pinout, LCSC numbers. Single source of truth. |
| `placement.py` | Board size, label-strip geometry, every part's position/rotation, front part labels. |
| `gen_sch.py` | Schematic layout (block positions in its `LAYOUT` table). |

## Pipeline

```sh
tools/build_all.sh   # sch -> place -> autoroute -> stitch -> DRC -> nicklink.kicad_pcb
tools/fab.sh         # gerbers, drills, BOM/CPL, PDFs, renders, checks/
```

| Script | Step |
|---|---|
| `sch.sh` | Runs `gen_sch.py`, ERC (must be 0/0), exports the netlist and checks it against `spec.py` (`check_netlist.py`); refreshes `docs/schematic.pdf` and `docs/images/schematic.png`. |
| `place.sh` | Runs `build_pcb.py`: footprints, nets and symbol links from the netlist, outline, GND pours, silkscreen (front pin labels, back cheat sheet). Also writes `_work/placed.png`, a placement preview with courtyard-overlap check and ratsnest length (`preview.py`). |
| `autoroute.sh` | Exports a Specctra DSN, runs Freerouting headless, imports the SES and refills the pours. Existing tracks are kept as fixed. |
| `stitch.py` | Adds GND stitching vias wherever both pours have room, then drops any via that ends up on isolated copper. |
| `drc.sh` | `kicad-cli pcb drc` with schematic parity; exits nonzero on any violation. |
| `render.sh` | 3D top/bottom renders plus 2D layer plots (`svg2png.py`). |
| `compare.py` | Any number of boards side by side at a fixed physical scale (px/mm), e.g. `docs/images/compare.png`. Outline-only entries are allowed for boards without files. |
| `pinout.py` | Writes `docs/pinout.csv` from `spec.py` and prints the README pinout table. |
| `netreport.py` | Per-net length per layer and via count (check USB/HSE routing). |
| `build_pcb.py --resilk` | Redraws only the silkscreen on an already-routed board. Use it for label tweaks without re-routing. |
| `nosilk.py` | Copies a library footprint into `nicklink.pretty` without its silkscreen. |
| `kdock` | Runs a command in the KiCad container with the repo and 3D models mounted. |

`_work/`, `3dmodels/` and the Freerouting jar are local caches, ignored by git. `get3d.sh` and `autoroute.sh` download them on first use.

## Routing notes

- `placement.py` `PREROUTE` holds locked tracks laid before autorouting (currently the crystal nets), so the critical nets don't depend on Freerouting.
- Freerouting's result is very sensitive to placement. If a placement change leaves nets unrouted, try `NICKLINK_SEED=<n> tools/place.sh tools/_work/s<n>` for a few seeds: it nudges small top-area parts by ±0.1 mm. Autoroute each candidate and bake the offsets of a clean one into `PLACE`.
- `build_all.sh` retries the route, stitch and DRC step (`TRIES`, default 3) because Freerouting's optimizer is time-limited.

## Typical edits

- **Swap a part or value:** edit `spec.py`, run `build_all.sh`.
- **Change only silkscreen text or labels:** edit `build_pcb.py` / `placement.py`, then run `tools/kdock python3 tools/build_pcb.py --resilk nicklink.kicad_pcb` and `tools/drc.sh nicklink.kicad_pcb`.
- **Move a part:** edit `placement.py`, run `place.sh` and look at `_work/placed.png` until there are no overlaps, then run `build_all.sh`.
- **Change the header pinout:** edit the `J1`/`J3` maps in `spec.py`. Labels, the schematic, `pinout.csv` and the routing all follow. Run `pinout.py` and update the README table.
