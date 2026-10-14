#!/usr/bin/env python3
"""NickLink IMU viewer: a live 3D model of the board that follows its LSM6DSV.

The test firmware's `stream` command sends raw accelerometer + gyro samples over the USB-C console.
This fuses them into an orientation (Madgwick filter: gyro, corrected by gravity) and draws the board.
There is no magnetometer, so tilt is absolute but heading slowly drifts; R zeroes it.

    python3 imu_viewer.py [PORT] [--rate 200]

PORT defaults to /dev/serial/by-id/usb-NickLink*. Needs PyQt6 and numpy (pip install PyQt6 numpy) and
a termios system (Linux, macOS). Keep the board still for a moment after it connects: that measures
the gyro's offset. Mouse drag orbits, the wheel zooms; R zeroes heading, C re-measures the gyro offset
(hold still), Space freezes, Q quits. `--selftest` checks the filter maths without a board.
"""
import argparse
import glob
import math
import os
import select
import sys
import termios
import threading
import time

import numpy as np
from PyQt6.QtCore import QPointF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QApplication, QWidget

ACC_G = 0.061e-3                      # g per LSB (+-2 g)
GYR_RAD = 70e-3 * math.pi / 180       # rad/s per LSB (+-2000 dps)

# Board frame: x toward J1 (KiCad +x), y toward the USB-C edge (KiCad -y), z out of the component side.
# Rows: board axes in IMU axes (board = IMU_TO_BOARD @ imu). The LSM6DSV (U4, 0 deg) is aligned with
# the board: measured on a v1.3 board, lying flat reads +1 g on IMU +Z, and USB-C pointing up on IMU +Y.
IMU_TO_BOARD = np.array([[1.0, 0, 0],
                         [0, 1.0, 0],
                         [0, 0, 1.0]])


# ---- serial ----------------------------------------------------------------------------------------
def find_port():
    ports = sorted(glob.glob("/dev/serial/by-id/usb-NickLink*")) or sorted(glob.glob("/dev/cu.usbmodem*"))
    return ports[0] if ports else None


class Stream(threading.Thread):
    """Keeps a `stream` running on the board's console and hands each sample to on_sample.
    Reconnects after a reset or replug."""

    def __init__(self, port, rate, on_sample):
        super().__init__(daemon=True)
        self.port, self.rate, self.on_sample = port, rate, on_sample
        self.status, self.name, self.fd, self.running = "connecting", "", None, True

    def run(self):
        while self.running:
            try:
                self.session()
            except OSError as e:
                self.status = f"disconnected ({e.strerror or e})"
            self.close()
            if self.running:
                time.sleep(1)

    def drain(self, quiet, cap):
        """Read until nothing has arrived for `quiet` s (at most `cap` s)."""
        t_quiet, t_end = time.time() + quiet, time.time() + cap
        while time.time() < min(t_quiet, t_end):
            if select.select([self.fd], [], [], 0.05)[0] and os.read(self.fd, 65536):
                t_quiet = time.time() + quiet

    def session(self):
        port = self.port or find_port()
        if not port:
            self.status = "no NickLink console found (plug in USB-C)"
            return
        self.fd = os.open(port, os.O_RDWR | os.O_NOCTTY)
        a = termios.tcgetattr(self.fd)
        a[0] = a[1] = a[3] = 0                              # raw, no echo
        a[2] |= termios.CLOCAL | termios.CREAD
        termios.tcsetattr(self.fd, termios.TCSANOW, a)
        self.name = os.path.basename(port)
        # Opening prints the banner, and the firmware ignores input until it is out: wait for quiet.
        self.drain(0.3, 2)
        os.write(self.fd, b"\r")                            # stops a stream left running
        self.drain(0.2, 1)
        termios.tcflush(self.fd, termios.TCIFLUSH)
        os.write(self.fd, f"stream {self.rate}\r".encode())
        self.status = "waiting for data"
        buf, t_last = b"", time.time()
        while self.running:
            if not select.select([self.fd], [], [], 0.25)[0]:
                if time.time() - t_last > 2:
                    self.status = "no data from the board"
                continue
            d = os.read(self.fd, 65536)
            if not d:
                raise OSError(0, "port closed")
            *lines, buf = (buf + d).split(b"\n")
            for line in lines:
                p = line.split()
                if len(p) != 8 or p[0] != b"S":
                    continue
                try:
                    v = [int(x) for x in p[1:]]
                except ValueError:
                    continue
                t_last = time.time()
                self.status = "streaming"
                self.on_sample(v[0], np.array(v[1:4]) * ACC_G, np.array(v[4:7]) * GYR_RAD)

    def close(self):
        if self.fd is not None:
            try:
                os.write(self.fd, b"\r")                    # any key ends the stream
            except OSError:
                pass
            os.close(self.fd)
            self.fd = None

    def stop(self):
        self.running = False
        self.join(1.5)


# ---- orientation -----------------------------------------------------------------------------------
def madgwick(q, g, a, beta, dt):
    """One Madgwick IMU step. q maps board vectors to world (w, x, y, z); g in rad/s, a in any unit."""
    q0, q1, q2, q3 = q
    gx, gy, gz = g
    d0 = 0.5 * (-q1 * gx - q2 * gy - q3 * gz)
    d1 = 0.5 * (q0 * gx + q2 * gz - q3 * gy)
    d2 = 0.5 * (q0 * gy - q1 * gz + q3 * gx)
    d3 = 0.5 * (q0 * gz + q1 * gy - q2 * gx)
    n = math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])
    if beta and n:
        ax, ay, az = a[0] / n, a[1] / n, a[2] / n
        s0 = 4 * q0 * q2 * q2 + 2 * q2 * ax + 4 * q0 * q1 * q1 - 2 * q1 * ay
        s1 = (4 * q1 * q3 * q3 - 2 * q3 * ax + 4 * q0 * q0 * q1 - 2 * q0 * ay - 4 * q1
              + 8 * q1 * q1 * q1 + 8 * q1 * q2 * q2 + 4 * q1 * az)
        s2 = (4 * q0 * q0 * q2 + 2 * q0 * ax + 4 * q2 * q3 * q3 - 2 * q3 * ay - 4 * q2
              + 8 * q2 * q1 * q1 + 8 * q2 * q2 * q2 + 4 * q2 * az)
        s3 = 4 * q1 * q1 * q3 - 2 * q1 * ax + 4 * q2 * q2 * q3 - 2 * q2 * ay
        sn = math.sqrt(s0 * s0 + s1 * s1 + s2 * s2 + s3 * s3)
        if sn:
            d0 -= beta * s0 / sn
            d1 -= beta * s1 / sn
            d2 -= beta * s2 / sn
            d3 -= beta * s3 / sn
    q = (q0 + d0 * dt, q1 + d1 * dt, q2 + d2 * dt, q3 + d3 * dt)
    n = math.sqrt(sum(c * c for c in q))
    return tuple(c / n for c in q)


def quat_to_matrix(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def quat_from_gravity(a):
    """Tilt from one accelerometer reading, heading 0."""
    roll, pitch = math.atan2(a[1], a[2]), math.atan2(-a[0], math.hypot(a[1], a[2]))
    cr, sr, cp, sp = math.cos(roll / 2), math.sin(roll / 2), math.cos(pitch / 2), math.sin(pitch / 2)
    return (cr * cp, sr * cp, cr * sp, -sr * sp)


def euler_zyx(R):
    """(roll, pitch, yaw) in degrees."""
    return (math.degrees(math.atan2(R[2, 1], R[2, 2])),
            math.degrees(math.asin(max(-1.0, min(1.0, -R[2, 0])))),
            math.degrees(math.atan2(R[1, 0], R[0, 0])))


class Ahrs:
    CAL_MS, CAL_MOTION = 1500, 0.05       # still for 1.5 s, gyro within 0.05 rad/s (3 dps) of its mean
    BETA, BETA_FAST, FAST_MS = 0.04, 0.5, 1500

    def __init__(self):
        self.q = (1.0, 0.0, 0.0, 0.0)
        self.bias = np.zeros(3)
        self.t_prev = None
        self.recalibrate()
        self.rate, self._n, self._t_rate = 0.0, 0, time.time()
        self.acc_norm = 0.0

    def recalibrate(self):
        self.calibrating, self.cal, self.t_cal, self.fast_until = True, [], None, 0

    def update(self, t, acc, gyr):
        acc, gyr = IMU_TO_BOARD @ acc, IMU_TO_BOARD @ gyr
        self.acc_norm = float(np.linalg.norm(acc))
        self._n += 1
        if time.time() - self._t_rate >= 1:
            self.rate, self._n, self._t_rate = self._n / (time.time() - self._t_rate), 0, time.time()
        if self.t_prev is None:
            self.t_prev, self.q = t, quat_from_gravity(acc)
            return
        dt, self.t_prev = (t - self.t_prev) / 1000.0, t
        if not 0 < dt < 0.1:                                 # reset or pause: start again from gravity
            self.q = quat_from_gravity(acc)
            return
        if self.calibrating:
            still = abs(self.acc_norm - 1) < 0.1 and (not self.cal or
                                                       np.max(np.abs(gyr - np.mean(self.cal, axis=0))) < self.CAL_MOTION)
            if not still:
                self.cal, self.t_cal = [], None
            else:
                self.cal.append(gyr)
                self.t_cal = self.t_cal or t
                if t - self.t_cal >= self.CAL_MS:
                    self.bias = np.mean(self.cal, axis=0)
                    self.calibrating, self.fast_until = False, t + self.FAST_MS
        beta = self.BETA_FAST if self.calibrating or t < self.fast_until else self.BETA
        if abs(self.acc_norm - 1) > 0.25:                     # being shaken: gravity is unreliable
            beta = 0
        self.q = madgwick(self.q, gyr - self.bias, acc, beta, dt)


# ---- board model (mm, board frame; KiCad positions from nicklink.kicad_pcb) ------------------------
GREEN, FR4, GOLD, BLACK, IC, SILVER, WHITE = ((31, 111, 63), (196, 172, 120), (212, 175, 55), (28, 28, 30),
                                              (36, 36, 40), (184, 188, 194), (225, 225, 225))


def kicad(x, y):
    return x - 116.995, 112.75 - y


def box(c, size, z0, color, top=None, bottom=None, hide=()):
    """An axis-aligned box; `hide` drops the faces with those normals (shared with a neighbour)."""
    (cx, cy), (sx, sy, sz) = c, size
    x0, x1, y0, y1, z1 = cx - sx / 2, cx + sx / 2, cy - sy / 2, cy + sy / 2, z0 + sz
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    faces = [((4, 5, 6, 7), (0, 0, 1), top or color), ((3, 2, 1, 0), (0, 0, -1), bottom or color),
             ((0, 1, 5, 4), (0, -1, 0), color), ((1, 2, 6, 5), (1, 0, 0), color),
             ((2, 3, 7, 6), (0, 1, 0), color), ((3, 0, 4, 7), (-1, 0, 0), color)]
    return v, [f for f in faces if f[1] not in hide]


def board_model():
    parts = [box((0, 0), (33.99, 25.5, 1.6), -1.6, FR4, top=GREEN, bottom=GREEN)]
    parts.append(box(kicad(116.745, 116.2), (7, 7, 1.4), 0, IC))                    # U1 STM32F103 LQFP-48
    parts.append(box(kicad(124.2, 117.71), (3, 2.5, 0.83), 0, (60, 60, 70)))        # U4 LSM6DSV
    parts.append(box(kicad(115.245, 123.2), (3.2, 2.5, 0.8), 0, SILVER))            # Y1 8 MHz crystal
    parts.append(box(kicad(121.095, 109.3), (2, 2, 0.75), 0, IC))                   # U2 regulator
    parts.append(box(kicad(116.395, 109.27), (1.6, 1.6, 0.55), 0, IC))              # U3
    for x, y in ((124.45, 113.76), (109.58, 113.9)):                                # SW1/SW2 B3U buttons
        parts.append(box(kicad(x, y), (2.5, 3.0, 1.2), 0, WHITE))
        parts.append(box(kicad(x, y), (1.2, 1.6, 0.4), 1.2, (90, 90, 95)))
    parts.append(box(kicad(111.493, 109.62), (1.0, 0.5, 0.35), 0, (60, 220, 90)))   # D3
    parts.append(box(kicad(111.355, 108.163), (1.0, 0.5, 0.35), 0, (230, 50, 50)))  # D1
    ux, _ = kicad(119.97, 0)
    parts.append(box((ux, 12.75 - 3.55), (8.94, 7.3, 3.26), 0, SILVER))             # J2 USB-C, mouth at the edge
    # J3, J1: 2x10 headers. The plastic is one cell per pin (faces between cells left out), so every part
    # is small and sorting parts by depth stays right; one long strip got painted over its own pins.
    for x0 in (102.67, 128.78):
        for c, col in enumerate((0, 2.54)):
            for i in range(10):
                p = kicad(x0 + col, 101.32 + 2.54 * i)
                hide = {(1, 0, 0) if c == 0 else (-1, 0, 0)} | ({(0, -1, 0)} if i < 9 else set()) | ({(0, 1, 0)} if i else set())
                parts.append(box(p, (2.54, 2.54, 2.5), 0, BLACK, hide=hide))
                parts.append(box(p, (0.64, 0.64, 6.0), 2.5, GOLD))
                parts.append(box(p, (0.64, 0.64, 3.0), -4.6, GOLD))
    verts, faces = [], []
    for k, (v, fs) in enumerate(parts):
        base = len(verts)
        verts += v
        zs = [z for _, _, z in v]
        slab = 1 if k == 0 else 0 if max(zs) <= -1.6 else 3 if min(zs) >= 2.5 else 2
        faces += [(tuple(base + i for i in idx), n, col, slab, k) for idx, n, col in fs]
    return (np.array(verts, float), np.array([f[0] for f in faces]), np.array([f[1] for f in faces], float),
            [f[2] for f in faces], np.array([f[3] for f in faces]), np.array([f[4] for f in faces]))


# ---- window ----------------------------------------------------------------------------------------
class Viewer(QWidget):
    def __init__(self, port, rate):
        super().__init__()
        self.setWindowTitle("NickLink IMU viewer")
        self.resize(1100, 800)
        self.ahrs = Ahrs()
        self.stream = Stream(port, rate, self.ahrs.update)
        self.stream.start()
        self.V, self.F, self.N, self.C, self.slab, self.part = board_model()
        self.part_verts = [np.unique(self.F[self.part == k]) for k in range(self.part.max() + 1)]
        self.az, self.el, self.dist = -55.0, 28.0, 95.0
        self.yaw0, self.frozen, self.R, self.drag = 0.0, False, np.eye(3), None
        self.timer = QTimer(self, timeout=self.update, interval=16)
        self.timer.start()

    def camera(self):
        az, el = math.radians(self.az), math.radians(self.el)
        eye = self.dist * np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
        fwd = -eye / np.linalg.norm(eye)
        right = np.cross(fwd, (0, 0, 1.0))
        right /= np.linalg.norm(right)
        return eye, np.array([right, np.cross(right, fwd), fwd])

    def paintEvent(self, _):
        if not self.frozen:
            yaw0 = math.radians(self.yaw0)
            Rz = np.array([[math.cos(-yaw0), -math.sin(-yaw0), 0], [math.sin(-yaw0), math.cos(-yaw0), 0], [0, 0, 1]])
            self.R = Rz @ quat_to_matrix(self.ahrs.q)
        R = self.R
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(24, 26, 31))
        w, h = self.width(), self.height()
        f = 0.9 * min(w, h)
        eye, cam = self.camera()

        def project(pts):
            c = (pts - eye) @ cam.T
            z = np.maximum(c[:, 2], 1e-3)
            return np.stack([w / 2 + f * c[:, 0] / z, h / 2 - f * c[:, 1] / z], 1), c[:, 2]

        # floor grid
        if eye[2] > -30:
            p.setPen(QPen(QColor(70, 74, 82), 1))
            for t in range(-60, 61, 10):
                for a, b in (((t, -60, -30), (t, 60, -30)), ((-60, t, -30), (60, t, -30))):
                    s, _ = project(np.array([a, b], float))
                    p.drawLine(QPointF(*s[0]), QPointF(*s[1]))
        # board, painter's algorithm with back faces culled. The parts lie in slabs between planes parallel
        # to the PCB: pin tails | PCB | parts on the PCB (header plastic, ICs, USB-C) | header pins. Nothing
        # in a slab can hide anything in a slab beyond it as seen from the camera, so the slabs are drawn
        # farthest first, and inside a slab whole parts far to near (a box's visible faces never overlap).
        Vw, Nw = self.V @ R.T, self.N @ R.T
        S, depth = project(Vw)
        centers = Vw[self.F].mean(axis=1)
        vis = np.nonzero(np.einsum("ij,ij->i", Nw, eye - centers) > 0)[0]
        cam_h = float((R.T @ eye)[2])                               # camera height above the PCB's top
        lo, hi = np.array([-9e9, -1.6, 0.0, 2.5]), np.array([-1.6, 0.0, 2.5, 9e9])
        slab_dist = np.maximum(0, np.maximum(lo - cam_h, cam_h - hi))
        part_depth = np.array([depth[i].mean() for i in self.part_verts])
        order = vis[np.lexsort((-part_depth[self.part[vis]], -slab_dist[self.slab[vis]]))]
        light = cam[1] * 0.4 - cam[2] * 0.85 - cam[0] * 0.25         # mostly a headlight, from upper left
        light /= np.linalg.norm(light)
        for k in order:
            s = 0.32 + 0.68 * max(0.0, float(Nw[k] @ light))
            r, g, b = self.C[k]
            col = QColor(min(255, int(r * s)), min(255, int(g * s)), min(255, int(b * s)))
            p.setPen(QPen(col.darker(125), 0.6))
            p.setBrush(col)
            p.drawPolygon(QPolygonF([QPointF(*S[i]) for i in self.F[k]]))
        # board axes
        ends, _ = project(np.vstack([np.zeros(3), (R @ np.eye(3)).T * 28]))
        p.setFont(QFont("Sans", 11, QFont.Weight.Bold))
        for i, (name, col) in enumerate((("X", QColor(240, 80, 80)), ("Y", QColor(90, 220, 110)), ("Z", QColor(90, 150, 255)))):
            p.setPen(QPen(col, 2.5))
            p.drawLine(QPointF(*ends[0]), QPointF(*ends[i + 1]))
            p.drawText(QPointF(*ends[i + 1]) + QPointF(4, -4), name)
        # text
        roll, pitch, yaw = euler_zyx(R)
        a = self.ahrs
        state = ("hold still: measuring gyro offset" if a.calibrating and self.stream.status == "streaming"
                 else self.stream.status)
        lines = [f"NickLink IMU   {self.stream.name or '-'}",
                 f"roll {roll:+7.1f}   pitch {pitch:+7.1f}   yaw {yaw:+7.1f}  deg",
                 f"{a.rate:5.0f} Hz   |a| {a.acc_norm:4.2f} g   gyro offset "
                 + " ".join(f"{d:+.2f}" for d in np.degrees(a.bias)) + " dps",
                 state + ("   [frozen]" if self.frozen else "")]
        p.setFont(QFont("Monospace", 10))
        p.setPen(QColor(220, 222, 228))
        for i, t in enumerate(lines):
            p.drawText(14, 24 + 18 * i, t)
        p.setPen(QColor(140, 144, 152))
        p.drawText(14, h - 14, "drag: orbit   wheel: zoom   R: zero heading   C: re-measure gyro offset (hold still)"
                               "   Space: freeze   Q: quit")
        p.end()

    def mousePressEvent(self, e):
        self.drag = e.position()

    def mouseMoveEvent(self, e):
        if self.drag is not None:
            d = e.position() - self.drag
            self.drag = e.position()
            self.az -= d.x() * 0.4
            self.el = max(-85.0, min(85.0, self.el + d.y() * 0.4))

    def mouseReleaseEvent(self, _):
        self.drag = None

    def wheelEvent(self, e):
        self.dist = max(50.0, min(500.0, self.dist * 0.9 ** (e.angleDelta().y() / 120)))

    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key.Key_R:
            self.yaw0 += euler_zyx(self.R)[2]
        elif k == Qt.Key.Key_C:
            self.ahrs.recalibrate()
        elif k == Qt.Key.Key_Space:
            self.frozen = not self.frozen
        elif k in (Qt.Key.Key_Q, Qt.Key.Key_Escape):
            self.close()

    def closeEvent(self, e):
        self.stream.stop()
        e.accept()

def run_viewer(port, rate):
    app = QApplication(sys.argv[:1])
    v = Viewer(port, rate)
    v.show()
    return app.exec()


def selftest():
    """Integrate known motions through the filter and check where the board axes end up."""
    def ok(name, cond):
        print(("PASS " if cond else "FAIL ") + name)
        return cond

    dt, good = 1 / 200, True
    q = quat_from_gravity((0, 0, 1))
    for _ in range(400):
        q = madgwick(q, (0, 0, 0), (0, 0, 1), 0.04, dt)
    good &= ok("flat and still stays level", np.allclose(quat_to_matrix(q), np.eye(3), atol=1e-6))
    # +90 deg about board X in 1 s; accelerometer sees gravity in the board frame as it turns
    q, true = (1.0, 0, 0, 0), 0.0
    for _ in range(200):
        true += math.pi / 2 * dt
        grav = (0, math.sin(true), math.cos(true))
        q = madgwick(q, (math.pi / 2, 0, 0), grav, 0.04, dt)
    R = quat_to_matrix(q)
    good &= ok("roll +90 about X puts board +Y up", np.allclose(R[:, 1], (0, 0, 1), atol=0.02))
    good &= ok("euler roll reads +90", abs(euler_zyx(R)[0] - 90) < 1.5)
    # gravity alone pulls a wrong start to the right tilt (board standing on its -Y edge, +Y up)
    q = (1.0, 0, 0, 0)
    for _ in range(2000):
        q = madgwick(q, (0, 0, 0), (0, 1, 0), 0.5, dt)
    good &= ok("gravity correction converges", quat_to_matrix(q)[2, 1] > 0.99)
    good &= ok("start from gravity", np.allclose(quat_to_matrix(quat_from_gravity((0, 1, 0)))[:, 1], (0, 0, 1), atol=1e-6))
    V, F, N, C, slab, part = board_model()
    good &= ok(f"board model: {len(F)} faces, {part.max() + 1} parts",
               len(F) == len(C) == len(N) == len(slab) == len(part) and F.max() < len(V))
    return 0 if good else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("port", nargs="?", help="console port (default /dev/serial/by-id/usb-NickLink*)")
    ap.add_argument("--rate", type=int, default=200, help="samples per second (default 200)")
    ap.add_argument("--selftest", action="store_true", help="check the filter maths, no board needed")
    args = ap.parse_args()
    sys.exit(selftest() if args.selftest else run_viewer(args.port, args.rate))
