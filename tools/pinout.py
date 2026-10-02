"""Write docs/pinout.csv from spec.py and print the README pinout table."""
import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import spec  # noqa: E402

# STM32F103x8 datasheet pin table: five-volt tolerant I/O
FT = {f"PA{i}" for i in range(8, 16)} | {"PB2", "PB3", "PB4"} | {f"PB{i}" for i in range(6, 16)}
# Pins that are FT on the MCU but not at board level: the IMU's SCL/SDA max is VDDIO + 0.3 V.
BOARD_3V3 = {"PB6", "PB7"} if "U4" in spec.PARTS else set()
POWER = {"+3.3V": "3V3 regulated output", "+5V": "5V (USB VBUS after Schottky; <=5.5 V input)", "GND": "GND", "NRST": "NRST (reset, active low)"}


def label(net):
    return {"+3.3V": "3V3", "+5V": "5V", "NRST": "RST"}.get(net, net[1:] if re.fullmatch(r"P[ABC]\d+", net) else net)


def describe(net):
    if net in POWER:
        return POWER[net]
    alias = spec.ALIASES.get(net)
    return f"{net} / {alias}" if alias else net


root = os.path.join(os.path.dirname(__file__), "..")
rows = []
for ref in ("J3", "J1"):
    for pin, net in sorted(spec.PARTS[ref][3].items(), key=lambda p: int(p[0])):
        ft = "" if net in POWER and net != "NRST" else ("FT" if net in FT - BOARD_3V3 else "3.3 V only")
        rows.append((ref, int(pin), net, label(net), describe(net), ft))
with open(os.path.join(root, "docs", "pinout.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Header", "Pin", "Net", "Front label", "Signal / function", "5 V tolerant"])
    w.writerows(rows)

j = {(r[0], r[1]): r for r in rows}
print("| Pin | J3 (left) | J1 (right) |\n|---:|---|---|")
for p in range(1, 21):
    cell = lambda ref: f"`{j[(ref, p)][3]}` {j[(ref, p)][4]}" + (" (3.3 V only)" if j[(ref, p)][5] == "3.3 V only" else "")
    print(f"| {p} | {cell('J3')} | {cell('J1')} |")
