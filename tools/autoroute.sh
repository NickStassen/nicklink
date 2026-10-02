#!/usr/bin/env bash
# Autoroute the unrouted connections of a KiCad 10 board with Freerouting.
# Existing tracks/vias are kept as fixed; widths/clearances/vias come from the
# board's net classes (KiCad writes them into the DSN as (class ... (rule ...))).
#
# Usage: [PASSES=30] [SKIP_NETS=GND,...] [FR_ARGS="..."] tools/autoroute.sh <in.kicad_pcb> <out.kicad_pcb>
#   SKIP_NETS  nets Freerouting must not route (e.g. pour-only nets; you stitch them).
#   FR_ARGS    extra Freerouting flags, e.g. "--router.optimizer.enabled=false".
set -euo pipefail
in=$(realpath "${1:?usage: autoroute.sh <in.kicad_pcb> <out.kicad_pcb>}")
out=$(realpath -m "${2:?usage: autoroute.sh <in.kicad_pcb> <out.kicad_pcb>}")
tools="$(cd "$(dirname "$0")" && pwd)"
jar=$tools/freerouting-2.4.1.jar
[[ -s $jar ]] || curl -fL -o "$jar" https://github.com/freerouting/freerouting/releases/download/v2.4.1/freerouting-2.4.1.jar
mkdir -p "$(dirname "$out")"
work=${out%.kicad_pcb}
# Net classes/rules live in the .kicad_pro, parity needs the .kicad_sch, DRC's
# footprint-lib checks need the lib tables: give the output its own copies so it
# can be opened / DRC'd on its own.
for ext in kicad_pro kicad_dru kicad_sch; do
  [[ -f ${in%.kicad_pcb}.$ext && ! -f $work.$ext ]] && cp "${in%.kicad_pcb}.$ext" "$work.$ext"
done
for f in "$(dirname "$in")"/{fp-lib-table,sym-lib-table,*.pretty}; do
  [[ -e $f && ! -e $(dirname "$out")/$(basename "$f") ]] && cp -r "$f" "$(dirname "$out")/"
done
quiet() { grep -v 'swig/python detected a memory leak' || true; }  # pcbnew SWIG noise

t0=$SECONDS
"$tools/kdock" python3 "$tools/autoroute.py" export "$in" "$work.dsn" --skip-nets "${SKIP_NETS:-}" 2>&1 | quiet
# Freerouting 2.4.1 is built for Java 25 (class file 69); run it in a JRE 25 container.
# --gui.enabled=false: headless (otherwise it tries to open a window).
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$tools:$tools:ro" -v "$(dirname "$out"):$(dirname "$out")" \
  eclipse-temurin:25-jre java -jar "$jar" -de "$work.dsn" -do "$work.ses" -mp "${PASSES:-30}" \
  --gui.enabled=false ${FR_ARGS:-} >"$work.freerouting.log" 2>&1 \
  || { tail -20 "$work.freerouting.log"; exit 1; }
grep -E 'Auto-routing stage completed|Optimization stage completed' "$work.freerouting.log" | sed 's/.*\] //' | cut -c1-160
"$tools/kdock" python3 "$tools/autoroute.py" import "$in" "$work.ses" "$out" "$work.dsn" 2>&1 | quiet
echo "autoroute: $((SECONDS - t0)) s total; log $work.freerouting.log"
