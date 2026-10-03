#!/bin/sh
# Bring-up pictures (docs/images/bringup-*.png) from a fresh transparent 3D render of nicklink.kicad_pcb.
set -e
cd "$(dirname "$0")/.."
mkdir -p tools/_work
tools/kdock kicad-cli pcb render --side top --quality high --background transparent -w 2400 -h 2400 \
  -o tools/_work/bringup-top.png nicklink.kicad_pcb | grep -E "rror" || true
tools/kdock python3 tools/bringup_img.py dump nicklink.kicad_pcb tools/_work/bringup.json 2>&1 | grep -v "memory leak" || true
python3 tools/bringup_img.py draw tools/_work/bringup.json tools/_work/bringup-top.png docs/images
ls -la docs/images/bringup-*.png
