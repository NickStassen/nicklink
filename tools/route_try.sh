#!/bin/sh
# Place + autoroute + stitch + DRC one placement variant into tools/_work/t_<name>/.
# usage: tools/route_try.sh <name> <imu_rot or ""> <seed or "">
# Run up to ~4 in parallel (each Freerouting JVM needs a few GB of RAM).
cd "$(dirname "$0")/.."
D=tools/_work/t_$1; rm -rf $D; mkdir -p $D/st
NICKLINK_IMU_ROT=$2 NICKLINK_SEED=$3 tools/place.sh $D > $D/place.log 2>&1
grep -q "no courtyard issues" $D/place.log || { echo "$1: overlap"; exit; }
PASSES=100 tools/autoroute.sh $D/placed.kicad_pcb $D/ar/nicklink.kicad_pcb > $D/ar.log 2>&1
cp nicklink.kicad_pro nicklink.kicad_dru nicklink.kicad_sch fp-lib-table sym-lib-table nicklink.kicad_sym $D/st/; cp -r nicklink.pretty $D/st/
tools/kdock python3 tools/stitch.py $D/ar/nicklink.kicad_pcb $D/st/nicklink.kicad_pcb > /dev/null 2>&1
tools/drc.sh $D/st/nicklink.kicad_pcb > $D/drc.log 2>&1
echo "$1: $(head -1 $D/drc.log) $(sed -n 2p $D/drc.log) $(grep '^schematic' $D/drc.log)"
