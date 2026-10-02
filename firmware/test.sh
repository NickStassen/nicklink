#!/bin/sh
# Build the firmware and run the Renode emulation tests headlessly (docker: antmicro/renode).
# Prints PASS/FAIL per test; exit status is non-zero if any test failed.
set -e
cd "$(dirname "$0")"
make
REPO=$(cd .. && pwd)
mkdir -p build/home build/robot
set +e
docker run --rm -u "$(id -u):$(id -g)" -e HOME=/w/firmware/build/home -v "$REPO:/w" -w /w/firmware/build \
    antmicro/renode:latest renode-test -r /w/firmware/build/robot /w/firmware/renode/test.robot > build/robot/console.txt 2>&1
rc=$?
set -e
python3 - build/robot/robot_output.xml <<'PY'
import sys, xml.etree.ElementTree as ET
fails = 0
for t in ET.parse(sys.argv[1]).iter("test"):
    st = t.find("status")
    ok = st.get("status") == "PASS"
    fails += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {t.get('name')}" + ("" if ok else f"\n      {(st.text or '').strip()[:300]}"))
print(f"{'ALL PASSED' if not fails else f'{fails} FAILED'} (log: build/robot/log.html, console: build/robot/console.txt)")
PY
exit $rc
