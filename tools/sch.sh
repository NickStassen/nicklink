#!/bin/sh
# Regenerate nicklink.kicad_sch from tools/spec.py, then verify it:
# ERC must be clean and the exported netlist must match spec.py exactly.
# Also refreshes docs/schematic.pdf and docs/images/schematic.png.
set -e
cd "$(dirname "$0")/.."
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
# The repo's sym-lib-table points at *.kicad_symdir libraries; the kicad/kicad:10.0
# image ships *.kicad_sym files, so mount an adjusted copy over it (repo file untouched).
sed 's/\.kicad_symdir/.kicad_sym/' sym-lib-table > "$TMP/sym-lib-table"
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD:/w" -v "$TMP:/t" \
    -v "$TMP/sym-lib-table:/w/sym-lib-table:ro" -w /w kicad/kicad:10.0 sh -ec '
python3 tools/gen_sch.py
kicad-cli sch erc --severity-all --exit-code-violations -o /t/erc.rpt nicklink.kicad_sch \
    || { cat /t/erc.rpt; exit 1; }
sed -n "/ERC messages/p" /t/erc.rpt
kicad-cli sch export netlist -o /t/nicklink.net nicklink.kicad_sch >/dev/null; mkdir -p tools/_work; cp /t/nicklink.net tools/_work/nicklink.net
python3 tools/check_netlist.py /t/nicklink.net
kicad-cli sch export pdf -o docs/schematic.pdf nicklink.kicad_sch >/dev/null
'
pdftoppm -r 150 -png -singlefile docs/schematic.pdf docs/images/schematic
echo "OK: nicklink.kicad_sch regenerated and verified"
