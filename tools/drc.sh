#!/usr/bin/env bash
# DRC with schematic parity + all track errors; JSON report next to the board,
# summary to stdout. Exit 1 if any violation, unconnected item or parity issue.
# Usage: tools/drc.sh <board.kicad_pcb>
# Needs <base>.kicad_pro (rules/net classes) and <base>.kicad_sch (parity) beside the board.
set -euo pipefail
pcb=$(realpath "${1:?usage: drc.sh <board.kicad_pcb>}")
tools="$(cd "$(dirname "$0")" && pwd)"
base=${pcb%.kicad_pcb}
json=$base-drc.json
for ext in kicad_pro kicad_sch; do
  [[ -f $base.$ext ]] || echo "WARNING: $base.$ext missing (rules/parity will be wrong)" >&2
done
"$tools/kdock" kicad-cli pcb drc --schematic-parity --all-track-errors --severity-all \
  --format json -o "$json" "$pcb" >/dev/null
python3 - "$json" <<'EOF'
import collections, json, sys
r = json.load(open(sys.argv[1]))
groups = {"violations": r.get("violations", []),
          "unconnected_items": r.get("unconnected_items", []),
          "schematic_parity": r.get("schematic_parity", [])}
total = 0
for name, items in groups.items():
    total += len(items)
    counts = collections.Counter(f'{v["severity"]}:{v["type"]}' for v in items)
    print(f"{name}: {len(items)}" + "".join(f"\n  {n:4d}  {k}" for k, n in counts.most_common()))
for name, items in groups.items():
    for v in items:
        where = "; ".join(f'{i["description"]} @({i["pos"]["x"]:.2f},{i["pos"]["y"]:.2f})' for i in v.get("items", []))
        print(f'[{name}] {v["severity"]} {v["type"]}: {v["description"]} -- {where}')
print(f"report: {sys.argv[1]}")
sys.exit(1 if total else 0)
EOF
