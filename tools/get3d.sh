#!/usr/bin/env bash
# Download only the KiCad 3D models a board references into tools/3dmodels/.
# Usage: tools/get3d.sh <board.kicad_pcb>
set -euo pipefail
pcb=${1:?usage: get3d.sh <board.kicad_pcb>}
dst="$(cd "$(dirname "$0")" && pwd)/3dmodels"
base=https://gitlab.com/kicad/libraries/kicad-packages3D/-/raw/master
mkdir -p "$dst"
# Models referenced by footprints placed on the board, e.g. ${KICAD10_3DMODEL_DIR}/Package_QFP.3dshapes/X.step
grep -o '(model "\${KICAD[0-9]*_3DMODEL_DIR}/[^"]*"' "$pcb" | sed 's/.*_3DMODEL_DIR}\///; s/"$//' | sort -u |
while read -r rel; do
  [[ -s "$dst/$rel" ]] && { echo "have $rel"; continue; }
  mkdir -p "$dst/$(dirname "$rel")"
  # Fall back to .wrl if the .step is missing upstream.
  for f in "$rel" "${rel%.*}.wrl"; do
    if curl -fsSL "$base/$f" -o "$dst/$f"; then echo "got  $f"; continue 2; fi
    rm -f "$dst/$f"
  done
  echo "MISSING $rel" >&2
done
