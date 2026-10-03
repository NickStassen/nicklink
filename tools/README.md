# NickLink build tools

NickLink is generated, not hand-edited. Change the inputs below, then rebuild. Everything runs in the `kicad/kicad:10.0` Docker image, so no local KiCad install is needed. Freerouting runs in `eclipse-temurin:25-jre`.

## Inputs

| File | What it holds |
|---|---|
| `spec.py` | Parts, values, footprints, pin→net map, header pinout, LCSC numbers. Single source of truth. |
| `placement.py` | Board size, label-strip geometry, every part's position/rotation, front part labels. |
| `board_template.kicad_pcb` | Board setup only (stackup, solder-mask web, plot settings) for `build_pcb.py`. |
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
| `autoroute.sh` | Exports a Specctra DSN, runs Freerouting headless, imports the SES and refills the pours. Existing tracks are kept as fixed. With `RIPUP=1`, only locked pre-routes stay fixed, so a second pass may rip up and redo the first pass's tracks. |
| `stitch.py` | Adds GND stitching vias wherever both pours have room, then drops any via that ends up on isolated copper. |
| `drc.sh` | `kicad-cli pcb drc` with schematic parity; exits nonzero on any violation. JLCPCB limits come from the board setup plus `nicklink.kicad_dru`. |
| `route_try.sh` | One placement variant end to end (place, route, stitch, DRC) for the seed search. |
| `render.sh` | 3D top/bottom renders plus 2D layer plots (`svg2png.py`). |
| `compare.py` | Any number of boards side by side at a fixed physical scale (px/mm), e.g. `docs/images/compare-v1.1-v1.2-v1.3.png`. Outline-only entries are allowed for boards without files. |
| `pinout.py` | Writes `docs/pinout.csv` from `spec.py` and prints the README pinout table. |
| `netreport.py` | Per-net length per layer and via count (check USB/HSE routing). |
| `build_pcb.py --resilk` | Redraws only the silkscreen on an already-routed board. Use it for label tweaks without re-routing. |
| `fixroute.sh` | Finishes a connection Freerouting left open: a small two-layer grid router (`fixroute.py`) joins the copper cluster holding one pad to the cluster holding another, e.g. `tools/fixroute.sh in.kicad_pcb out.kicad_pcb GND R5.1 U1.23 0.25`. Run `drc.sh` afterwards. |
| `gndnet.py` | GND connectivity per pour island (KiCad treats a whole zone as one item), so floating island pairs show up. `stitch.py` uses the same idea. |
| `swapfp.py` | Swaps a placed footprint for a same-pad variant (e.g. NoSilk) on a routed board, keeping nets and the symbol link. |
| `bringup_img.sh` | Renders the board and draws the bring-up pictures (`docs/images/bringup-*.png`: ST-Link wiring, check points) from the real pad positions (`bringup_img.py`). |
| `nosilk.py` | Copies a library footprint into `nicklink.pretty` without its silkscreen. |
| `kdock` | Runs a command in the KiCad container with the repo and 3D models mounted. |

`_work/`, `3dmodels/` and the Freerouting jar are local caches, ignored by git. `get3d.sh` and `autoroute.sh` download them on first use.

## Routing notes

- `placement.py` `PREROUTE` holds locked tracks laid before autorouting (currently the crystal nets), so the critical nets don't depend on Freerouting.
- Freerouting's result is very sensitive to placement. If a placement change leaves nets unrouted, run a few `tools/route_try.sh s<n> "" <n>` in parallel (at most about 4, since each Freerouting JVM needs a few GB of RAM). Each one nudges small parts by up to ±0.1 mm (`NICKLINK_SEED`), then routes, stitches and runs DRC. Bake the offsets of a clean seed into `PLACE`. The current layout uses seed 3 (second review wave), which Freerouting routes fully on its own. If a seed leaves one or two items, `fixroute.sh` is usually faster than more seeds. Hand-routed nets live in `PREROUTE`, `PREROUTE_B` and `PREVIAS`: crystal, IMU fan-out and GND returns, the power path, the USB-C orientation ties, and GND vias for boxed-in pads.
- `build_all.sh` retries the route, stitch and DRC step (`TRIES`, default 3) because Freerouting's optimizer is time-limited.

## Typical edits

- **Swap a part or value:** edit `spec.py`, run `build_all.sh`.
- **Change only silkscreen text or labels:** edit `build_pcb.py` / `placement.py`, then run `tools/kdock python3 tools/build_pcb.py --resilk nicklink.kicad_pcb` and `tools/drc.sh nicklink.kicad_pcb`.
- **Move a part:** edit `placement.py`, run `place.sh` and look at `_work/placed.png` until there are no overlaps, then run `build_all.sh`.
- **Change the header pinout:** edit the `J1`/`J3` maps in `spec.py`. Labels, the schematic, `pinout.csv` and the routing all follow. Run `pinout.py` and update the README table.
