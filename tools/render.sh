#!/usr/bin/env bash
# Renders for review: <outprefix>-top.png / -bottom.png (3D, orthographic, with
# 3D models) and <outprefix>-front-2d.png / -back-2d.png (Cu+silk+courtyard+fab+edge).
# Usage: [PXMM=60] [SIZE=1600] tools/render.sh <board.kicad_pcb> <outprefix>
# 2D PNGs are rasterized on the host with python3-gi (librsvg) + pycairo.
set -euo pipefail
pcb=$(realpath "${1:?usage: render.sh <board.kicad_pcb> <outprefix>}")
out=$(realpath -m "${2:?usage: render.sh <board.kicad_pcb> <outprefix>}")
tools="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$(dirname "$out")"
"$tools/get3d.sh" "$pcb" | { grep -v '^have ' || true; }
for side in top bottom; do
  "$tools/kdock" kicad-cli pcb render --side $side --quality high --background opaque \
    -w "${SIZE:-1600}" -h "${SIZE:-1600}" -o "$out-$side.png" "$pcb" | grep -E 'Success|rror' || true
done
plot() {  # name mirror layers
  "$tools/kdock" kicad-cli pcb export svg --mode-single --page-size-mode 2 --exclude-drawing-sheet \
    $2 --layers "$3" -o "$out-$1.svg" "$pcb" >/dev/null
  python3 "$tools/svg2png.py" "$out-$1.svg" "$out-$1.png" "${PXMM:-60}"
  rm "$out-$1.svg"
}
plot front-2d "" F.Cu,F.Silkscreen,F.Courtyard,F.Fab,Edge.Cuts
plot back-2d --mirror B.Cu,B.Silkscreen,B.Courtyard,B.Fab,Edge.Cuts
ls -1 "$out"-*.png
