#!/bin/sh
# Full NickLink build: schematic -> placement -> autoroute -> GND stitching -> DRC.
# Result is written to nicklink.kicad_pcb at the repo root only if DRC is clean.
# Freerouting's optimizer is time-limited, so a run can occasionally leave a
# connection open; the route/stitch/DRC step is retried up to TRIES times.
set -e
cd "$(dirname "$0")/.."
W=tools/_work
tools/sch.sh
tools/place.sh
mkdir -p $W/st
cp nicklink.kicad_pro nicklink.kicad_dru nicklink.kicad_sch fp-lib-table sym-lib-table nicklink.kicad_sym $W/st/ && rm -rf $W/st/nicklink.pretty && cp -r nicklink.pretty $W/st/
n=0
until
  n=$((n + 1))
  PASSES=${PASSES:-100} tools/autoroute.sh $W/placed.kicad_pcb $W/ar/nicklink.kicad_pcb &&
  tools/kdock python3 tools/stitch.py $W/ar/nicklink.kicad_pcb $W/st/nicklink.kicad_pcb 2>&1 | grep -v 'swig/python' &&
  tools/drc.sh $W/st/nicklink.kicad_pcb
do
  [ $n -ge "${TRIES:-3}" ] && { echo "FAILED: DRC not clean after $n autoroute attempts"; exit 1; }
  echo "--- autoroute attempt $n not clean, retrying"
done
cp $W/st/nicklink.kicad_pcb nicklink.kicad_pcb
echo "OK: nicklink.kicad_pcb built, DRC clean (attempt $n)"
