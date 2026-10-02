#!/bin/sh
# Full NickLink build: schematic -> placement -> autoroute -> GND stitching -> DRC.
# Result is written to nicklink.kicad_pcb at the repo root only if DRC is clean.
set -e
cd "$(dirname "$0")/.."
W=tools/_work
tools/sch.sh
tools/place.sh
PASSES=${PASSES:-60} tools/autoroute.sh $W/placed.kicad_pcb $W/ar/nicklink.kicad_pcb
mkdir -p $W/st
cp nicklink.kicad_pro nicklink.kicad_sch fp-lib-table $W/st/ && rm -rf $W/st/nicklink.pretty && cp -r nicklink.pretty $W/st/
tools/kdock python3 tools/stitch.py $W/ar/nicklink.kicad_pcb $W/st/nicklink.kicad_pcb 2>&1 | grep -v 'swig/python'
tools/drc.sh $W/st/nicklink.kicad_pcb
cp $W/st/nicklink.kicad_pcb nicklink.kicad_pcb
echo "OK: nicklink.kicad_pcb built, DRC clean"
