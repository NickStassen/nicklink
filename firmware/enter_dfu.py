#!/usr/bin/env python3
"""Ask a running NickLink test console to reboot into its USB DFU bootloader (`make dfu` runs this).

Linux: finds /dev/serial/by-id/usb-NickLink*. Otherwise pass the port, e.g. /dev/cu.usbmodem1234.
If no console is found, double-tap RESET instead (green LED solid on = bootloader).
Prints the board's USB serial on stdout when it can find it (the bootloader uses the same one), so
`dfu-util -S` flashes that board and no other; messages go to stderr."""
import glob
import os
import re
import select
import sys
import termios
import time


def say(msg):
    print(msg, file=sys.stderr)


def usb_serial(port):  # Linux sysfs; None elsewhere
    try:
        tty = os.path.basename(os.path.realpath(port))
        with open(f"/sys/class/tty/{tty}/device/../serial") as f:
            return f.read().strip()
    except OSError:
        return None


ports = sys.argv[1:] or sorted(glob.glob("/dev/serial/by-id/usb-NickLink*"))
if not ports:
    say("no NickLink console found: if the board isn't already in the bootloader, double-tap RESET")
    sys.exit(0)
if len(ports) > 1:
    say("several NickLink boards are connected; pick one with CONSOLE=<port>:")
    for p in ports:
        say(f"  {p}")
    sys.exit(1)
port = ports[0]
if not os.path.exists(port):
    # e.g. the board is still in the bootloader after a failed download; its serial is in the by-id name
    m = re.search(r"_([0-9A-F]{24})-if\d+$", port)
    say(f"{port} not found: assuming that board is already in the bootloader")
    if m:
        print(m.group(1))
    sys.exit(0)
try:
    fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    a = termios.tcgetattr(fd)
    a[0] = a[1] = a[3] = 0                  # raw, no echo: don't bounce the banner back as input
    termios.tcsetattr(fd, termios.TCSANOW, a)
    # Opening the port prints the banner after 100 ms, and the firmware ignores input until 150 ms after
    # it has gone out: wait for 0.3 s of silence (at most 2 s) before sending anything.
    t_end, t_quiet = time.time() + 2, time.time() + 0.3
    while time.time() < min(t_end, t_quiet):
        if select.select([fd], [], [], 0.05)[0] and os.read(fd, 4096):
            t_quiet = time.time() + 0.3
    termios.tcflush(fd, termios.TCIFLUSH)
    serial = usb_serial(port)               # read it before the board leaves
    os.write(fd, b"\rdfu\r")
    time.sleep(0.1)
    os.close(fd)
except OSError as e:
    say(f"{port}: {e}")
    sys.exit(1)
say(f"asked {os.path.basename(port)} to reboot into the DFU bootloader")
if serial:
    print(serial)
