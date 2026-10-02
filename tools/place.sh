#!/bin/sh
# Build placement-only board + preview PNG.  usage: tools/place.sh [out_dir]
set -e
cd "$(dirname "$0")/.."
OUT=${1:-tools/_work}
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -e NICKLINK_SEED="${NICKLINK_SEED:-}" -e NICKLINK_IMU_ROT="${NICKLINK_IMU_ROT:-}" -v "$PWD":/w -w /w kicad/kicad:10.0 \
  python3 tools/build_pcb.py tools/board_template.kicad_pcb "$OUT/placed.kicad_pcb" ${NETLIST:-tools/_work/nicklink.net}
cp nicklink.kicad_pro "$OUT/placed.kicad_pro"; cp nicklink.kicad_dru "$OUT/placed.kicad_dru"; cp nicklink.kicad_sch "$OUT/placed.kicad_sch"
python3 tools/preview.py "$OUT/placed.geom.json" "$OUT/placed.png"
