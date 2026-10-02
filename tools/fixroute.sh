#!/bin/sh
# Join two copper clusters of one net that the autorouter left apart (see fixroute.py).
# usage: tools/fixroute.sh in.kicad_pcb out.kicad_pcb NET PAD_A PAD_B [width_mm]
set -e
cd "$(dirname "$0")/.."
w=${6:-0.2}; t=$(mktemp -d tools/_work/fix.XXXX)
tools/kdock python3 tools/fixroute.py dump "$1" "$3" "$4" "$5" $w $t/dump.json 2>&1 | grep -v "memory leak" || true
python3 tools/fixroute.py search $t/dump.json $t/path.json
tools/kdock python3 tools/fixroute.py apply "$1" "$2" "$3" $t/path.json $w 2>&1 | grep -v "memory leak" || true
