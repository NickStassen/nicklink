#!/usr/bin/env python3
"""Assert a KiCad netlist (kicadsexpr) matches tools/spec.py exactly.

usage: check_netlist.py NETLIST
Checks: same set of parts; value, footprint and extra fields per part; every
spec pin on its spec net; every other pin unconnected.
"""
import sys

from gen_sch import find, findall, parse
import spec


def main(path):
    net = parse(open(path, encoding="utf-8").read())
    errs = []
    comps = {str(find(c, "ref")[1]): c for c in findall(find(net, "components"), "comp")
             if not str(find(c, "ref")[1]).startswith("#")}
    for ref in sorted(set(comps) ^ set(spec.PARTS)):
        errs.append(f"{ref}: {'missing from netlist' if ref in spec.PARTS else 'not in spec'}")
    for ref, c in comps.items():
        if ref not in spec.PARTS:
            continue
        _, value, fp, _, extra = spec.PARTS[ref]
        fields = {str(find(f, "name")[1]): str(f[2]) if len(f) > 2 else "" for f in findall(find(c, "fields") or [], "field")}
        got = {"value": str(find(c, "value")[1]), "footprint": str((find(c, "footprint") or [0, ""])[1])}
        for k, want in [("value", value), ("footprint", fp)]:
            if got[k] != want:
                errs.append(f"{ref}: {k} {got[k]!r} != spec {want!r}")
        for k, want in extra.items():
            if fields.get(k) != want:
                errs.append(f"{ref}: field {k} {fields.get(k)!r} != spec {want!r}")

    actual = {}
    nnets = 0
    for n in findall(find(net, "nets"), "net"):
        name = str(find(n, "name")[1])
        name = None if name.startswith("unconnected-") else name.lstrip("/")
        nnets += name is not None
        for node in findall(n, "node"):
            ref, pin = str(find(node, "ref")[1]), str(find(node, "pin")[1])
            if not ref.startswith("#"):
                actual[(ref, pin)] = name
    for ref, (_, _, _, pins, _) in spec.PARTS.items():
        for pin, want in pins.items():
            if (ref, pin) not in actual:
                errs.append(f"{ref}.{pin}: missing from netlist (spec {want})")
    for (ref, pin), got in sorted(actual.items()):
        want = spec.PARTS.get(ref, (0, 0, 0, {}))[3].get(pin)
        if got != want:
            errs.append(f"{ref}.{pin}: on {got or 'no net'}, spec says {want or 'unconnected'}")

    if errs:
        print("NETLIST MISMATCH:\n  " + "\n  ".join(errs))
        return 1
    print(f"netlist OK: {len(comps)} parts, {nnets} nets, {len(actual)} pins match spec.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
