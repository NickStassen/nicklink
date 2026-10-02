#!/usr/bin/env bash
# Run every NickLink SPICE testbench headlessly, then build plots + results/summary.md.
# Usage: sim/run.sh [testbench-name-substring ...]   (no args = all)
# ngspice runs in a throwaway Docker image built from sim/Dockerfile (no host install).
set -euo pipefail
cd "$(dirname "$0")"
IMG=nicklink-ngspice
docker image inspect "$IMG" >/dev/null 2>&1 || docker build -q -t "$IMG" .
mkdir -p results
for cir in tb/*.cir; do
  name=$(basename "$cir" .cir)
  if [ $# -gt 0 ]; then match=0; for a in "$@"; do [[ $name == *$a* ]] && match=1; done; [ $match = 1 ] || continue; fi
  echo "== $name"
  docker run --rm -u "$(id -u):$(id -g)" -v "$PWD:/w" -w /w "$IMG" ngspice -b "$cir" >"results/$name.log" 2>"results/$name.err"
  if grep -qE "aborted|Timestep too small|^Error" "results/$name.log" "results/$name.err"; then
    echo "   ngspice reported errors, see results/$name.log / .err" >&2; exit 1
  fi
done
python3 xtal.py >results/07_xtal.log
python3 analyze.py
