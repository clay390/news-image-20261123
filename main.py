#!/usr/bin/env python3
"""news-image-20261123 — "The World in One Day", Monday 23 November 2026.

A one-day newspaper front page drawn programmatically with pure Python 3
standard library only: an embedded 5x7 bitmap font, a small canvas with
rect/frame/line/circle/polygon drawing, and a pure-stdlib PNG encoder
(zlib + struct). No network, no files read, deterministic: the same run
always writes the same bytes.

37 stories, 8 regions, every story happened or was first reported on
Monday 23 November 2026 (UTC). Press time 05:00 UTC.
"""

import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
PAPER = (253, 248, 238)
PAPER2 = (247, 240, 224)
INK = (20, 20, 20)
INK2 = (70, 70, 70)
RED = (193, 39, 45)
RED_D = (150, 25, 30)
NAVY = (15, 42, 74)
NAVY2 = (30, 68, 110)
TEAL = (14, 124, 123)
GOLD = (217, 164, 65)
GOLD_L = (240, 205, 120)
GREEN = (46, 125, 50)
SKY = (168, 205, 232)
SKY_D = (120, 170, 215)
GREY = (200, 200, 200)
GREY_D = (140, 140, 140)
WHITE = (255, 255, 255)
CREAM = (255, 246, 220)
ORANGE = (230, 120, 30)
FLAME = (245, 160, 40)
SMOKE = (120, 120, 125)
BROWN = (120, 85, 50)
PINK = (220, 120, 160)
PURPLE = (110, 80, 160)

REGION_COLORS = [
    ("CLIMATE", RED),
    ("UKRAINE WAR", ORANGE),
    ("MIDDLE EAST", PURPLE),
    ("ASIA-PACIFIC", TEAL),
    ("EUROPE", NAVY2),
    ("AMERICAS", GREEN),
    ("AFRICA", BROWN),
    ("UK", GOLD),
]


# ---------------------------------------------------------------- PNG
def _chunk(kind, data):
    c = struct.pack(">I", len(data)) + kind + data
    return c + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def encode_png(w, h, px):
    """px: bytearray of w*h*3 RGB. Deterministic, per-row filter pick 0/1/2."""
    raw = bytearray()
    stride = w * 3
    prev = bytes(stride)
    for y in range(h):
        row = bytes(px[y * stride:(y + 1) * stride])
        best = None
        best_score = None
        for f in (0, 1, 2):
            if f == 0:
                fb = row
            elif f == 1:
                b = bytearray(stride)
                for i in range(stride):
                    left = row[i - 3] if i >= 3 else 0
                    b[i] = (row[i] - left) & 0xFF
                fb = bytes(b)
            else:
                b = bytearray(stride)
                for i in range(stride):
                    b[i] = (row[i] - prev[i]) & 0xFF
                fb = bytes(b)
            score = sum(abs(v - 256 if v > 127 else v) for v in fb)
            if best_score is None or score < best_score:
                best_score = score
                best = bytes([f]) + fb
        raw += best
        prev = row
    comp = zlib.compress(bytes(raw), 9)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", comp) + _chunk(b"IEND", b""))


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def fill_rect(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def dither_rect(self, x, y, w, h, c1, c2):
        """Newsprint halftone: checkerboard of two close colours."""
        for yy in range(y, y + h):
            if yy < 0 or yy >= self.h:
                continue
            for xx in range(x, x + w):
                if xx < 0 or xx >= self.w:
                    continue
                self.set(xx, yy, c1 if ((xx + yy) & 1) == 0 else c2)

    def hline(self, x, y, w, c, t=1):
        self.fill_rect(x, y, w, t, c)

    def vline(self, x, y, h, c, t=1):
        self.fill_rect(x, y, t, h, c)

    def frame(self, x, y, w, h, c, t=1):
        self.hline(x, y, w, c, t)
        self.hline(x, y + h - t, w, c, t)
        self.vline(x, y, h, c, t)
        self.vline(x + w - t, y, h, c, t)

    def line(self, x0, y0, x1, y1, c):
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        x, y = x0, y0
        while True:
            self.set(x, y, c)
            if x == x1 and y == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def fill_circle(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            dx = int((r * r - (yy - cy) ** 2) ** 0.5) if abs(yy - cy) <= r else 0
            self.hline(cx - dx, yy, dx * 2 + 1, c)

    def circle(self, cx, cy, r, c):
        x = 0
        y = r
        d = 3 - 2 * r
        while x <= y:
            for px, py in ((cx + x, cy + y), (cx - x, cy + y), (cx + x, cy - y),
                           (cx - x, cy - y), (cx + y, cy + x), (cx - y, cy + x),
                           (cx + y, cy - x), (cx - y, cy - x)):
                self.set(px, py, c)
            if d < 0:
                d += 4 * x + 6
            else:
                d += 4 * (x - y) + 10
                y -= 1
            x += 1

    def fill_poly(self, pts, c):
        """Scanline polygon fill. pts: list of (x, y)."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(max(0, min(ys)), min(self.h, max(ys) + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    if y1 != y0:
                        xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.hline(int(xs[i]), y, max(1, int(xs[i + 1]) - int(xs[i])), c)

    def poly_line(self, pts, c):
        for i in range(len(pts)):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % len(pts)]
            self.line(x0, y0, x1, y1, c)


# ---------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows of 5 chars, '#' = ink. Written fresh for this entry.
FONT = {
    'A': (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'B': ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    'C': (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    'D': ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    'E': ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    'F': ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    'G': (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    'H': ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'I': (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    'J': ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    'K': ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    'L': ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    'M': ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    'N': ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    'O': (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'P': ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    'Q': (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    'R': ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    'S': (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    'T': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'V': ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'W': ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    'X': ("#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"),
    'Y': ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    'Z': ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    'a': (".....", ".....", ".####", "....#", ".####", "#...#", ".####"),
    'b': ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    'c': (".....", ".....", ".####", "#....", "#....", "#....", ".####"),
    'd': ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"),
    'e': (".....", ".....", ".###.", "#...#", "#####", "#....", ".###."),
    'f': ("..##.", ".#...", ".#...", "####.", ".#...", ".#...", ".#..."),
    'g': (".....", ".####", "#...#", "#...#", ".####", "....#", ".###."),
    'h': ("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"),
    'i': (".....", "..#..", ".....", ".##..", "..#..", "..#..", ".###."),
    'j': (".....", "...#.", ".....", "..##.", "...#.", "...#.", "##..."),
    'k': ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    'l': (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    'm': (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"),
    'n': (".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"),
    'o': (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    'p': (".....", "####.", "#...#", "#...#", "####.", "#....", "#...."),
    'q': (".....", ".####", "#...#", "#...#", ".####", "....#", "....#"),
    'r': (".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."),
    's': (".....", ".....", ".####", "#....", ".###.", "....#", "####."),
    't': (".#...", ".#...", "####.", ".#...", ".#...", ".#...", "..##."),
    'u': (".....", ".....", "#...#", "#...#", "#...#", "#..##", ".##.#"),
    'v': (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'w': (".....", ".....", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."),
    'x': (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    'y': (".....", "#...#", "#...#", "#..##", ".##.#", "....#", ".###."),
    'z': (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"),
    '0': (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    '1': ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    '2': (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    '3': ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    '4': ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    '5': ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    '6': (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    '7': ("#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."),
    '8': (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    '9': (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    ' ': (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    '.': (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ',': (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    ':': (".....", ".....", ".##..", ".....", ".....", ".##..", "....."),
    ';': (".....", ".....", ".##..", ".....", ".##..", ".##..", ".#..."),
    '!': ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    '?': (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    '-': (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    '(': ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ')': (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    '/': ("....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."),
    '%': ("#...#", "#..#.", "...#.", "..#..", ".#...", "#..#.", "#...#"),
    '&': (".###.", "#...#", "#...#", ".#...", "#.#.#", "#..#.", ".##.#"),
    '+': (".....", ".....", "..#..", ".###.", "..#..", ".....", "....."),
    '=': (".....", ".....", "#####", ".....", "#####", ".....", "....."),
    '*': (".....", ".#.#.", "..#..", "#####", "..#..", ".#.#.", "....."),
    '°': (".##..", "#..#.", ".##..", ".....", ".....", ".....", "....."),
    '•': (".....", ".....", ".....", ".##..", ".##..", ".....", "....."),
    '…': (".....", ".....", ".....", ".....", ".....", "#.#.#", "....."),
    '×': (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    '£': ("..##.", ".#...", ".#...", "####.", ".#...", "#####", "....."),
    '€': (".###.", "#....", "#....", "#####", "#....", "#....", ".###."),
    '$': ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    '<': ("...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."),
    '>': (".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."),
    '[': (".###.", ".#...", ".#...", ".#...", ".#...", ".#...", ".###."),
    ']': (".###.", "...#.", "...#.", "...#.", "...#.", "...#.", ".###."),
    '_': (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
    '@': (".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."),
    '#': (".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."),
    '~': (".....", ".....", ".##.#", "#.#.#", ".....", ".....", "....."),
    '^': ("..#..", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    '\\': ("#....", ".#...", ".#...", "..#..", "...#.", "...#.", "....#"),
    '|': ("..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    '→': (".....", ".....", "..#..", "...#.", "#####", "...#.", "..#.."),
    '←': (".....", ".....", "..#..", ".#...", "#####", ".#...", "..#.."),
    '↑': ("..#..", ".#.#.", "..#..", "..#..", "..#..", "..#..", "....."),
    '↓': ("..#..", "..#..", "..#..", "..#..", "..#..", ".#.#.", "..#.."),
}

_NORMALIZE = {
    '‘': "'", '’': "'", '“': '"', '”': '"', '–': '-', '—': '-', '´': "'",
}


def norm_char(ch):
    return _NORMALIZE.get(ch, ch)


def text_width(text, scale):
    return len(text) * 6 * scale


def draw_text(cv, x, y, text, scale, color, align="left"):
    text = "".join(norm_char(ch) for ch in text)
    w = text_width(text, scale)
    if align == "center":
        x -= w // 2
    elif align == "right":
        x -= w
    for ch in text:
        g = FONT.get(ch, FONT['?'])
        for r in range(7):
            row = g[r]
            for c in range(5):
                if row[c] == '#':
                    cv.fill_rect(x + c * scale, y + r * scale, scale, scale, color)
        x += 6 * scale
    return w


def wrap_text(text, max_w, scale):
    """Word-wrap to lines fitting max_w pixels at the given scale."""
    words = text.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_para(cv, x, y, text, max_w, scale, color, lh=None):
    """Draw wrapped paragraph, return y after last line."""
    if lh is None:
        lh = 7 * scale + 2 * scale
    for line in wrap_text(text, max_w, scale):
        draw_text(cv, x, y, line, scale, color)
        y += lh
    return y


# ---------------------------------------------------------------- scenes
def draw_chip(cv, x, y, text, fg, bg):
    """Small coloured tag chip with white text, scale 1."""
    w = text_width(text, 1) + 10
    cv.fill_rect(x, y, w, 13, bg)
    draw_text(cv, x + 5, y + 3, text, 1, fg)
    return w


def _star(cv, cx, cy, r, c):
    """Tiny 5-point star as lines."""
    import math
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((int(cx + rr * math.cos(ang)), int(cy + rr * math.sin(ang))))
    cv.fill_poly(pts, c)


def draw_scene(cv, x, y, w, h, kind):
    """Draw a small pictogram scene inside box (x, y, w, h)."""
    u = w / 100.0
    v = h / 100.0
    X = lambda f: int(x + f * u)
    Y = lambda f: int(y + f * v)

    if kind == "fire_refinery":
        cv.dither_rect(x, y, w, h, (28, 32, 48), (38, 44, 66))
        # stars in the night sky
        for sx, sy in ((6, 8), (18, 4), (30, 10), (44, 5), (62, 9), (74, 4),
                       (88, 10), (94, 20), (10, 22), (52, 16), (82, 24)):
            cv.fill_circle(X(sx), Y(sy), max(1, int(1.2 * u)), (220, 220, 200))
        cv.fill_rect(X(0), Y(72), w, int(28 * v) + 1, (50, 45, 40))
        # road
        cv.fill_rect(X(0), Y(88), w, int(12 * v), (30, 30, 32))
        cv.hline(X(0), Y(93), w, (200, 180, 60), 1)
        # refinery towers with windows
        cv.fill_rect(X(8), Y(38), int(14 * u), int(34 * v), (90, 95, 105))
        cv.fill_rect(X(30), Y(28), int(12 * u), int(44 * v), (80, 85, 95))
        cv.fill_rect(X(55), Y(45), int(16 * u), int(27 * v), (90, 95, 105))
        cv.fill_rect(X(76), Y(34), int(10 * u), int(38 * v), (80, 85, 95))
        for wx in (11, 17, 33, 37, 59, 66, 79, 83):
            for wy in (44, 52, 60):
                cv.fill_rect(X(wx), Y(wy), int(2 * u), int(3 * v), (255, 220, 100))
        # chimney + smoke
        cv.fill_rect(X(46), Y(18), int(6 * u), int(54 * v), (70, 70, 75))
        cv.fill_circle(X(49), Y(12), int(5 * u), SMOKE)
        cv.fill_circle(X(56), Y(6), int(4 * u), SMOKE)
        cv.fill_circle(X(64), Y(10), int(3 * u), SMOKE)
        # flames
        cv.fill_poly([(X(14), Y(40)), (X(20), Y(14)), (X(26), Y(40))], FLAME)
        cv.fill_poly([(X(34), Y(30)), (X(39), Y(10)), (X(44), Y(30))], ORANGE)
        cv.fill_poly([(X(60), Y(46)), (X(66), Y(26)), (X(72), Y(46))], FLAME)
        cv.fill_circle(X(20), Y(36), int(4 * u), (255, 220, 100))
        cv.fill_circle(X(39), Y(26), int(3 * u), (255, 220, 100))
        # glow line
        cv.hline(X(0), Y(70), w, ORANGE, 2)

    elif kind == "chart_down":
        cv.fill_rect(x, y, w, h, WHITE)
        cv.dither_rect(x, y, w, int(6 * v), (235, 240, 245), WHITE)
        for gy in (25, 50, 75):
            cv.hline(X(6), Y(gy), int(88 * u), (225, 225, 225))
        for gx in (22, 38, 54, 70, 86):
            cv.vline(X(gx), Y(10), int(78 * v), (232, 232, 232))
        for i, bh in enumerate((30, 44, 26, 52, 38)):
            bx = X(12 + i * 16)
            cv.fill_rect(bx, Y(88 - bh), int(9 * u), int(bh * v),
                         GREEN if i % 2 == 0 else RED)
        # second, steadier line (another index)
        pts2 = [(X(10), Y(44)), (X(28), Y(40)), (X(46), Y(44)), (X(64), Y(38)),
                (X(82), Y(42)), (X(92), Y(40))]
        for i in range(len(pts2) - 1):
            cv.line(pts2[i][0], pts2[i][1], pts2[i + 1][0], pts2[i + 1][1], TEAL)
        pts = [(X(10), Y(20)), (X(28), Y(34)), (X(46), Y(30)), (X(64), Y(52)),
               (X(82), Y(66)), (X(92), Y(78))]
        for i in range(len(pts) - 1):
            cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], RED)
            cv.fill_circle(pts[i][0], pts[i][1], max(2, int(2.5 * u)), RED)
        cv.fill_circle(pts[-1][0], pts[-1][1], max(2, int(2.5 * u)), RED)
        cv.line(X(6), Y(88), X(94), Y(88), INK)
        cv.line(X(6), Y(10), X(6), Y(88), INK)

    elif kind == "capitol":
        cv.dither_rect(x, y, w, h, (200, 222, 240), (214, 232, 246))
        # clouds
        for cx, cy, r in ((16, 14, 6), (24, 12, 5), (78, 10, 6), (86, 13, 4)):
            cv.fill_circle(X(cx), Y(cy), int(r * u), WHITE)
            cv.fill_circle(X(cx + 6), Y(cy + 2), int((r - 1) * u), WHITE)
        # birds
        for bx, by in ((30, 8), (38, 6), (60, 12)):
            cv.line(X(bx), Y(by), X(bx + 3), Y(by - 2), INK)
            cv.line(X(bx + 3), Y(by - 2), X(bx + 6), Y(by), INK)
        # dome
        cv.fill_circle(X(50), Y(52), int(26 * u), WHITE)
        cv.fill_rect(X(24), Y(52), int(52 * u), int(8 * v), WHITE)
        cv.fill_rect(X(47), Y(18), int(6 * u), int(10 * v), WHITE)
        cv.fill_circle(X(50), Y(16), int(4 * u), GOLD)
        # dome windows
        for wx in (34, 44, 54):
            cv.fill_rect(X(wx), Y(42), int(3 * u), int(6 * v), NAVY2)
        # columns
        for cx in (28, 40, 52, 64):
            cv.fill_rect(X(cx), Y(60), int(5 * u), int(28 * v), WHITE)
        cv.fill_rect(X(20), Y(88), int(60 * u), int(6 * v), WHITE)
        cv.fill_rect(X(14), Y(94), int(72 * u), int(4 * v), (180, 180, 180))
        # trees
        cv.fill_circle(X(10), Y(80), int(7 * u), GREEN)
        cv.fill_rect(X(9), Y(84), int(2 * u), int(10 * v), BROWN)
        cv.fill_circle(X(92), Y(80), int(7 * u), GREEN)
        cv.fill_rect(X(91), Y(84), int(2 * u), int(10 * v), BROWN)
        # flag
        cv.vline(X(84), Y(20), int(34 * v), INK)
        cv.fill_rect(X(84), Y(20), int(14 * u), int(9 * v), RED)
        cv.fill_rect(X(84), Y(29), int(14 * u), int(9 * v), WHITE)
        cv.fill_rect(X(84), Y(38), int(14 * u), int(9 * v), NAVY2)

    elif kind == "quake":
        cv.fill_rect(x, y, w, h, WHITE)
        cv.fill_rect(X(0), Y(62), w, int(38 * v) + 1, (150, 125, 90))
        cv.fill_rect(X(0), Y(62), w, 2, (110, 85, 55))
        # crack
        pts = [(X(50), Y(62)), (X(42), Y(72)), (X(56), Y(80)), (X(44), Y(88)),
               (X(58), Y(96))]
        for i in range(len(pts) - 1):
            cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], (60, 40, 20))
        # seismograph panel
        cv.fill_rect(X(8), Y(10), int(84 * u), int(42 * v), WHITE)
        cv.frame(X(8), Y(10), int(84 * u), int(42 * v), INK)
        pts = [(X(12), Y(31)), (X(22), Y(31)), (X(28), Y(18)), (X(34), Y(44)),
               (X(40), Y(24)), (X(46), Y(38)), (X(52), Y(20)), (X(58), Y(42)),
               (X(64), Y(28)), (X(70), Y(36)), (X(78), Y(31)), (X(88), Y(31))]
        for i in range(len(pts) - 1):
            cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], RED)
        # shaking building
        cv.fill_rect(X(72), Y(48), int(16 * u), int(14 * v), (120, 120, 125))
        cv.line(X(70), Y(48), X(74), Y(44), INK)
        cv.line(X(86), Y(48), X(82), Y(44), INK)

    elif kind == "football":
        cv.dither_rect(x, y, w, h, (90, 170, 100), (110, 185, 115))
        cv.hline(X(0), Y(50), w, WHITE, 2)
        # ball
        cv.fill_circle(X(34), Y(62), int(20 * u), WHITE)
        cv.circle(X(34), Y(62), int(20 * u), INK)
        cv.fill_circle(X(34), Y(62), int(6 * u), INK)
        for dx, dy in ((-12, -8), (12, -8), (-12, 8), (12, 8), (0, -14)):
            cv.fill_circle(X(34) + int(dx * u), Y(62) + int(dy * v), int(3 * u), INK)
        # trophy
        cv.fill_poly([(X(66), Y(30)), (X(90), Y(30)), (X(86), Y(52)), (X(70), Y(52))], GOLD)
        cv.fill_rect(X(74), Y(52), int(8 * u), int(10 * v), GOLD)
        cv.fill_rect(X(68), Y(62), int(20 * u), int(6 * v), GOLD)
        cv.circle(X(64), Y(38), int(6 * u), GOLD)
        cv.circle(X(92), Y(38), int(6 * u), GOLD)

    elif kind == "flags_in_np":
        cv.dither_rect(x, y, w, h, SKY, (190, 220, 240))
        # India flag
        cv.vline(X(22), Y(14), int(70 * v), INK)
        cv.fill_rect(X(24), Y(16), int(26 * u), int(10 * v), (255, 153, 51))
        cv.fill_rect(X(24), Y(26), int(26 * u), int(10 * v), WHITE)
        cv.fill_rect(X(24), Y(36), int(26 * u), int(10 * v), (19, 136, 8))
        cv.circle(X(37), Y(31), int(4 * u), NAVY2)
        # Nepal flag (double pennon, simplified)
        cv.vline(X(62), Y(14), int(70 * v), INK)
        cv.fill_poly([(X(64), Y(16)), (X(88), Y(26)), (X(64), Y(34))], (220, 20, 60))
        cv.fill_poly([(X(64), Y(34)), (X(84), Y(42)), (X(64), Y(50))], (220, 20, 60))
        cv.fill_circle(X(70), Y(24), int(2 * u), WHITE)
        cv.fill_circle(X(70), Y(41), int(2 * u), WHITE)
        cv.fill_rect(X(0), Y(86), w, int(14 * v), (90, 140, 90))

    elif kind == "flags_in_cn":
        cv.dither_rect(x, y, w, h, SKY, (190, 220, 240))
        # India flag
        cv.vline(X(22), Y(14), int(70 * v), INK)
        cv.fill_rect(X(24), Y(16), int(26 * u), int(10 * v), (255, 153, 51))
        cv.fill_rect(X(24), Y(26), int(26 * u), int(10 * v), WHITE)
        cv.fill_rect(X(24), Y(36), int(26 * u), int(10 * v), (19, 136, 8))
        cv.circle(X(37), Y(31), int(4 * u), NAVY2)
        # China flag
        cv.vline(X(62), Y(14), int(70 * v), INK)
        cv.fill_rect(X(64), Y(16), int(26 * u), int(30 * v), (222, 41, 16))
        _star(cv, X(71), Y(25), int(4 * u), (255, 222, 0))
        _star(cv, X(82), Y(21), int(2 * u), (255, 222, 0))
        _star(cv, X(85), Y(28), int(2 * u), (255, 222, 0))
        _star(cv, X(82), Y(36), int(2 * u), (255, 222, 0))
        cv.fill_rect(X(0), Y(86), w, int(14 * v), (90, 140, 90))

    elif kind == "warning":
        cv.fill_rect(x, y, w, h, WHITE)
        cv.fill_poly([(X(50), Y(8)), (X(92), Y(84)), (X(8), Y(84))], (255, 210, 0))
        cv.poly_line([(X(50), Y(8)), (X(92), Y(84)), (X(8), Y(84))], INK)
        cv.fill_rect(X(47), Y(34), int(6 * u), int(26 * v), INK)
        cv.fill_circle(X(50), Y(70), int(4 * u), INK)

    elif kind == "gaza":
        cv.dither_rect(x, y, w, h, (210, 200, 180), (225, 215, 195))
        # broken building
        cv.fill_poly([(X(14), Y(88)), (X(14), Y(34)), (X(24), Y(26)), (X(30), Y(36)),
                      (X(38), Y(24)), (X(48), Y(34)), (X(48), Y(88))], (150, 150, 150))
        cv.fill_rect(X(18), Y(44), int(6 * u), int(8 * v), (60, 60, 60))
        cv.fill_rect(X(32), Y(52), int(6 * u), int(8 * v), (60, 60, 60))
        # rubble
        cv.fill_poly([(X(52), Y(88)), (X(62), Y(70)), (X(74), Y(88))], (120, 110, 95))
        cv.fill_poly([(X(70), Y(88)), (X(82), Y(76)), (X(92), Y(88))], (100, 92, 80))
        # dust
        cv.fill_circle(X(60), Y(60), int(6 * u), (200, 190, 170))
        cv.fill_circle(X(70), Y(52), int(4 * u), (200, 190, 170))

    elif kind == "arson":
        cv.dither_rect(x, y, w, h, (40, 40, 55), (55, 55, 70))
        # house
        cv.fill_rect(X(18), Y(48), int(52 * u), int(40 * v), (200, 180, 140))
        cv.fill_poly([(X(12), Y(50)), (X(44), Y(24)), (X(76), Y(50))], (150, 60, 50))
        cv.fill_rect(X(38), Y(66), int(12 * u), int(22 * v), (90, 60, 40))
        # flame on roof
        cv.fill_poly([(X(38), Y(28)), (X(44), Y(6)), (X(50), Y(28))], FLAME)
        cv.fill_poly([(X(56), Y(34)), (X(62), Y(16)), (X(68), Y(34))], ORANGE)
        cv.fill_circle(X(72), Y(14), int(4 * u), SMOKE)
        cv.fill_circle(X(80), Y(8), int(3 * u), SMOKE)

    elif kind == "nhs_ai":
        cv.fill_rect(x, y, w, h, WHITE)
        # screen with scan
        cv.fill_rect(X(10), Y(14), int(80 * u), int(56 * v), (20, 60, 90))
        cv.frame(X(10), Y(14), int(80 * u), int(56 * v), INK)
        pts = [(X(14), Y(46)), (X(26), Y(46)), (X(34), Y(28)), (X(42), Y(58)),
               (X(50), Y(38)), (X(62), Y(46)), (X(74), Y(46)), (X(86), Y(46))]
        for i in range(len(pts) - 1):
            cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], (80, 220, 160))
        # pink cross
        cv.fill_rect(X(66), Y(76), int(10 * u), int(8 * v), PINK)
        cv.fill_rect(X(20), Y(76), int(8 * u), int(8 * v), PINK)
        cv.fill_rect(X(20), Y(76), int(24 * u), int(8 * v), PINK)
        cv.fill_rect(X(46), Y(72), int(8 * u), int(16 * v), PINK)

    elif kind == "drone":
        cv.dither_rect(x, y, w, h, (60, 70, 90), (75, 85, 105))
        # building
        cv.fill_rect(X(10), Y(52), int(34 * u), int(36 * v), (110, 115, 125))
        cv.fill_rect(X(14), Y(58), int(6 * u), int(6 * v), (255, 220, 100))
        cv.fill_rect(X(28), Y(58), int(6 * u), int(6 * v), (255, 220, 100))
        cv.fill_rect(X(14), Y(70), int(6 * u), int(6 * v), (255, 220, 100))
        # quadcopter
        cx, cy = X(68), Y(30)
        cv.line(cx - int(14 * u), cy - int(10 * v), cx + int(14 * u), cy + int(10 * v), WHITE)
        cv.line(cx - int(14 * u), cy + int(10 * v), cx + int(14 * u), cy - int(10 * v), WHITE)
        cv.fill_circle(cx, cy, int(5 * u), WHITE)
        for dx, dy in ((-14, -10), (14, -10), (-14, 10), (14, 10)):
            cv.fill_circle(cx + int(dx * u), cy + int(dy * v), int(4 * u), (200, 200, 200))
        # dotted path
        for i in range(6):
            cv.fill_circle(X(56 + i * 6), Y(52 + i * 3), 2, (255, 220, 100))

    elif kind == "eu_stars":
        cv.fill_rect(x, y, w, h, (0, 51, 153))
        for i in range(12):
            import math
            ang = -math.pi / 2 + i * math.pi / 6
            _star(cv, X(50) + int(30 * u * math.cos(ang)),
                  Y(50) + int(30 * v * math.sin(ang)), int(4 * u), (255, 204, 0))
        cv.fill_rect(X(44), Y(44), int(12 * u), int(12 * v), (255, 204, 0))

    elif kind == "globe":
        cv.fill_rect(x, y, w, h, (10, 40, 80))
        cv.fill_circle(X(50), Y(50), int(38 * u), (70, 160, 220))
        cv.circle(X(50), Y(50), int(38 * u), WHITE)
        cv.fill_poly([(X(30), Y(28)), (X(44), Y(24)), (X(48), Y(36)), (X(36), Y(42))], (90, 180, 110))
        cv.fill_poly([(X(56), Y(56)), (X(72), Y(52)), (X(76), Y(66)), (X(60), Y(70))], (90, 180, 110))
        cv.fill_poly([(X(28), Y(62)), (X(38), Y(60)), (X(36), Y(72)), (X(26), Y(70))], (90, 180, 110))
        # meridians
        cv.circle(X(50), Y(50), int(20 * u), (200, 230, 245))
        cv.hline(X(12), Y(50), int(76 * u), (200, 230, 245))

    elif kind == "cop31":
        # globe + factory with crossed-out smoke
        cv.fill_rect(x, y, w, h, (10, 40, 80))
        cv.fill_circle(X(32), Y(50), int(30 * u), (70, 160, 220))
        cv.fill_poly([(X(18), Y(38)), (X(30), Y(32)), (X(36), Y(44)), (X(24), Y(50))], (90, 180, 110))
        cv.fill_poly([(X(34), Y(58)), (X(46), Y(54)), (X(48), Y(66)), (X(36), Y(68))], (90, 180, 110))
        # factory
        cv.fill_rect(X(58), Y(56), int(30 * u), int(26 * v), (160, 165, 170))
        cv.fill_rect(X(60), Y(38), int(6 * u), int(18 * v), (140, 145, 150))
        cv.fill_rect(X(70), Y(30), int(6 * u), int(26 * v), (140, 145, 150))
        cv.fill_circle(X(63), Y(30), int(4 * u), SMOKE)
        cv.fill_circle(X(73), Y(22), int(4 * u), SMOKE)
        # red cross over smoke
        cv.line(X(56), Y(14), X(80), Y(38), RED)
        cv.line(X(80), Y(14), X(56), Y(38), RED)


# ---------------------------------------------------------------- pin map
def draw_pin_map(cv, x, y, w, h, pins):
    """Simplified world map with numbered pins. pins: list of (fx, fy, n)."""
    cv.fill_rect(x, y, w, h, (185, 220, 240))
    cv.frame(x, y, w, h, INK)
    # graticule: latitude / longitude lines
    for gx in (0.25, 0.5, 0.75):
        cv.vline(x + int(gx * w), y, h, (160, 200, 225))
    for gy in (0.25, 0.5, 0.75):
        cv.hline(x, y + int(gy * h), w, (160, 200, 225))
    land = (150, 190, 130)
    # North America (with Alaska, Hudson Bay notch, Central America tail)
    cv.fill_poly([(x + int(0.04 * w), y + int(0.18 * h)),
                  (x + int(0.10 * w), y + int(0.08 * h)),
                  (x + int(0.20 * w), y + int(0.07 * h)),
                  (x + int(0.30 * w), y + int(0.10 * h)),
                  (x + int(0.32 * w), y + int(0.20 * h)),
                  (x + int(0.28 * w), y + int(0.26 * h)),
                  (x + int(0.30 * w), y + int(0.32 * h)),
                  (x + int(0.24 * w), y + int(0.34 * h)),
                  (x + int(0.20 * w), y + int(0.40 * h)),
                  (x + int(0.16 * w), y + int(0.38 * h)),
                  (x + int(0.12 * w), y + int(0.36 * h)),
                  (x + int(0.05 * w), y + int(0.26 * h))], land)
    # South America
    cv.fill_poly([(x + int(0.27 * w), y + int(0.44 * h)),
                  (x + int(0.33 * w), y + int(0.42 * h)),
                  (x + int(0.37 * w), y + int(0.48 * h)),
                  (x + int(0.38 * w), y + int(0.58 * h)),
                  (x + int(0.34 * w), y + int(0.68 * h)),
                  (x + int(0.31 * w), y + int(0.74 * h)),
                  (x + int(0.28 * w), y + int(0.60 * h))], land)
    # Europe (with Scandinavia, Iberia, Italy boot)
    cv.fill_poly([(x + int(0.47 * w), y + int(0.14 * h)),
                  (x + int(0.50 * w), y + int(0.08 * h)),
                  (x + int(0.55 * w), y + int(0.10 * h)),
                  (x + int(0.58 * w), y + int(0.16 * h)),
                  (x + int(0.56 * w), y + int(0.22 * h)),
                  (x + int(0.58 * w), y + int(0.26 * h)),
                  (x + int(0.54 * w), y + int(0.28 * h)),
                  (x + int(0.52 * w), y + int(0.24 * h)),
                  (x + int(0.48 * w), y + int(0.26 * h)),
                  (x + int(0.46 * w), y + int(0.20 * h))], land)
    # Africa (with the horn)
    cv.fill_poly([(x + int(0.48 * w), y + int(0.32 * h)),
                  (x + int(0.54 * w), y + int(0.30 * h)),
                  (x + int(0.60 * w), y + int(0.32 * h)),
                  (x + int(0.64 * w), y + int(0.38 * h)),
                  (x + int(0.62 * w), y + int(0.44 * h)),
                  (x + int(0.58 * w), y + int(0.52 * h)),
                  (x + int(0.56 * w), y + int(0.62 * h)),
                  (x + int(0.52 * w), y + int(0.60 * h)),
                  (x + int(0.50 * w), y + int(0.52 * h)),
                  (x + int(0.47 * w), y + int(0.42 * h))], land)
    # Asia (with India, SE Asia, Siberia)
    cv.fill_poly([(x + int(0.60 * w), y + int(0.08 * h)),
                  (x + int(0.72 * w), y + int(0.05 * h)),
                  (x + int(0.86 * w), y + int(0.06 * h)),
                  (x + int(0.93 * w), y + int(0.14 * h)),
                  (x + int(0.92 * w), y + int(0.22 * h)),
                  (x + int(0.88 * w), y + int(0.30 * h)),
                  (x + int(0.84 * w), y + int(0.36 * h)),
                  (x + int(0.78 * w), y + int(0.40 * h)),
                  (x + int(0.74 * w), y + int(0.36 * h)),
                  (x + int(0.70 * w), y + int(0.40 * h)),
                  (x + int(0.66 * w), y + int(0.32 * h)),
                  (x + int(0.62 * w), y + int(0.24 * h)),
                  (x + int(0.60 * w), y + int(0.16 * h))], land)
    # Oceania
    cv.fill_poly([(x + int(0.82 * w), y + int(0.62 * h)),
                  (x + int(0.88 * w), y + int(0.60 * h)),
                  (x + int(0.92 * w), y + int(0.64 * h)),
                  (x + int(0.90 * w), y + int(0.70 * h)),
                  (x + int(0.85 * w), y + int(0.70 * h))], land)
    # UK + Japan dots
    cv.fill_circle(x + int(0.485 * w), y + int(0.13 * h), 2, land)
    cv.fill_circle(x + int(0.90 * w), y + int(0.26 * h), 2, land)
    for fx, fy, n in pins:
        px = x + int(fx * w)
        py = y + int(fy * h)
        cv.fill_circle(px, py, 8, RED)
        cv.circle(px, py, 8, WHITE)
        draw_text(cv, px - 3, py - 3, str(n), 1, WHITE)


# ---------------------------------------------------------------- stories
# All 37 happened or were first reported on Monday 23 November 2026 (UTC).
LEAD = {
    "headline": "COP31 COLLAPSES - NO DEAL IN ANTALYA",
    "sub": ("Antalya talks end with no deal after record overtime; the EU rejects "
            "a text that never names fossil fuels. Albanese, on Monday: a sign "
            "of difficult times."),
    "tag": "LEAD - CLIMATE",
}

HEROES = [
    {
        "scene": "fire_refinery", "tag": "UKRAINE WAR", "color": ORANGE,
        "headline": "Drones hit Rostov refinery - fire burns",
        "sub": ("Novoshakhtinsk hit 02:22 UTC; boy, 7, pulled alive from Dymer "
                "rubble after a Russian strike."),
    },
    {
        "scene": "chart_down", "tag": "MARKETS", "color": RED,
        "headline": "Asia markets tumble on AI-bubble fears",
        "sub": ("Kospi -3.74%, Taiex -0.93%; Taiwan curbs short-selling after "
                "its worst week in 35 years."),
    },
    {
        "scene": "capitol", "tag": "AMERICAS", "color": GREEN,
        "headline": "Democrats win biggest House majority since 1992",
        "sub": ("North Carolina seat flips; the result is read as a rebuke of "
                "the Iran war and backing for Israel."),
    },
]

MIDS = [
    ("quake", "M6.5 quake shakes Vanuatu region, 598 km deep",
     "02:40 UTC; PAGER green - no tsunami threat, no damage reported yet."),
    ("football", "FIFA to confirm UK as 2035 Women's World Cup host",
     "First World Cup in the UK since 1966; decision due on Monday."),
    ("flags_in_np", "Nepal PM Shah holds talks with Modi in Delhi",
     "Ayodhya-Janakpur Express flagged off as the visit continues."),
    ("flags_in_cn", "India, China open 10 days of talks to ease LAC tensions",
     "Talks run for 10 days; easing tensions along the Line of Actual Control."),
    ("warning", "IDF warns Netanyahu: Iran strike could widen the war",
     "Military intelligence sees 'multiple fronts' - Lebanon, Syria, Gaza."),
    ("gaza", "Oxfam: 99% of Gaza is contaminated by the war",
     "Strip called a 'toxic wasteland' three years after the war began."),
    ("arson", "Israeli leaders denounce 'Jewish terrorism' in West Bank",
     "Eisenkot condemns settler arson in Palestinian villages at the weekend."),
    ("nhs_ai", "NHS launches world's largest AI breast-cancer trial",
     "700,000 women invited; scans read by AI to catch cancer earlier."),
    ("drone", "Drones hit Rosgvardiya HQ in Krasnodar, Russia",
     "Attack on the National Guard base reported on Monday morning."),
    ("eu_stars", "Burnham: 'landmark' EU deal could make decade 'better'",
     "Manchester mayor to tell MPs; Tories vow to scrap the deal."),
]

ALSO = [
    ("Boy, 7, pulled alive from Dymer rubble (BBC 02:37 UTC)", ORANGE),
    ("South Sudan: 24 civilians, incl. 7 children, killed in Warrap attack", BROWN),
    ("Zelensky: bridge strikes 'fair response' as he meets UK's Streeting", ORANGE),
    ("Trump keeps trying to reach Kim Jong Un - North has ghosted him", GREEN),
    ("San Francisco AI boom, but crash worries are growing", GREEN),
    ("US Army to detonate bomb-making chemicals in Iowa", GREEN),
    ("US intel chief trusts Trump's 'my friend' line on Putin", GREEN),
    ("Shuri Castle main hall opens to public, 7 years after fire", TEAL),
    ("Bulgari funeral held in Rome on Monday; jeweller died at 89", NAVY2),
    ("Smart buoys let wind-farm vessels charge at sea, trialled", GOLD),
    ("FSSAI orders prosecution of Bisleri over water quality", TEAL),
    ("West Bengal BJP protests attacks on Hindus in Bangladesh", TEAL),
    ("US hawks urge Trump to strike Iran; Trump says no rush", PURPLE),
    ("Long-lost Chevalier landscape found in a charity shop", GOLD),
    ("Theresa May's blast from the past calls Tories back", GOLD),
    ("Is Meghan using ChatGPT to promote As Ever?", GOLD),
    ("Patients may miss NHS weight-loss jabs as GP funding ends", GOLD),
    ("Man lured to villa, held 15 hours, rescued after being tied up", GOLD),
    ("Congress MLA writes letter in blood to Haryana CM", TEAL),
    ("Camara to race for Haas in final two Grands Prix", GREEN),
    ("Araghchi: Iran ready for talks on reopening Hormuz strait", PURPLE),
    ("Pezeshkian: Iran is in a 'silent' economic war", PURPLE),
    ("Likud demands keeping security zones in Gaza, Lebanon, Syria", PURPLE),
]

LEFT_OUT = ("Alcaraz wins ATP Finals (Sun 22)  •  Dymer flat strike, 2 killed "
            "(Sun 22)  •  Russian warship sunk off Benghazi (Sun 22)  •  "
            "Liverpool beat Man Utd (Sun 22)  •  Thitikul wins LPGA title "
            "(Sun 22)  •  Gaza: 4 killed on Saturday (Sat 21)")

PINS = [
    (0.56, 0.20, 1),  # Antalya - COP31
    (0.60, 0.13, 2),  # Rostov
    (0.92, 0.62, 3),  # Vanuatu
    (0.72, 0.28, 4),  # Delhi
    (0.49, 0.14, 5),  # London
    (0.18, 0.22, 6),  # Washington
    (0.55, 0.48, 7),  # Juba
    (0.83, 0.30, 8),  # Taipei
]

TIMELINE_1 = ("OVERNIGHT (UTC)   02:22  Drones hit Novoshakhtinsk refinery, "
              "Rostov   •   02:37  Boy, 7, found alive in Dymer rubble   •   "
              "02:40  M6.5 quake, Vanuatu")
TIMELINE_2 = ("MONDAY   Markets tumble at the open   •   FIFA confirms UK 2035   "
              "•   Modi-Shah talks in Delhi   •   NHS AI trial   •   "
              "Burnham's EU pitch to MPs")

NUMBERS = [
    ("37", "DATED STORIES"),
    ("8", "REGIONS"),
    ("M6.5", "VANUATU QUAKE"),
    ("-3.74%", "KOSPI ON MONDAY"),
    ("700,000", "WOMEN, NHS AI TRIAL"),
]


# ---------------------------------------------------------------- layout
def build():
    cv = Canvas(W, H, PAPER)
    mx = 16
    cw = W - 2 * mx  # 992

    # ---- masthead
    draw_text(cv, W // 2, 8, "THE WORLD IN ONE DAY", 4, INK, "center")
    draw_text(cv, W // 2, 44, "MONDAY 23 NOVEMBER 2026", 3, RED, "center")
    draw_text(cv, W // 2, 72,
              "37 DATED STORIES  •  8 REGIONS  •  EVERY STORY HAPPENED OR "
              "FIRST REPORTED 23 NOV 2026 (UTC)", 1, INK2, "center")
    cv.hline(mx, 92, cw, INK, 2)
    cv.hline(mx, 96, cw, INK, 1)

    # ---- lead strip
    draw_scene(cv, mx, 100, 56, 56, "cop31")
    cv.frame(mx, 100, 56, 56, INK)
    draw_text(cv, mx + 66, 102, LEAD["headline"], 3, INK)
    draw_para(cv, mx + 66, 130, LEAD["sub"], cw - 66, 1, INK2, lh=11)
    draw_chip(cv, mx + 66 + text_width(LEAD["headline"], 3) + 14, 104,
              LEAD["tag"], WHITE, RED)
    cv.hline(mx, 160, cw, INK, 1)

    # ---- UTC timeline strip
    draw_text(cv, mx, 166, "OVERNIGHT (UTC)", 1, RED)
    draw_text(cv, mx + text_width("OVERNIGHT (UTC)   ", 1), 166,
              TIMELINE_1[len("OVERNIGHT (UTC)   "):], 1, INK)
    draw_text(cv, mx, 178, "MONDAY", 1, RED)
    draw_text(cv, mx + text_width("MONDAY   ", 1), 178,
              TIMELINE_2[len("MONDAY   "):], 1, INK)
    cv.hline(mx, 190, cw, INK, 1)

    # ---- day in numbers
    bw = 194
    for i, (num, lab) in enumerate(NUMBERS):
        bx = mx + i * (bw + 5)
        cv.fill_rect(bx, 194, bw, 34, WHITE)
        cv.frame(bx, 194, bw, 34, GREY_D)
        draw_text(cv, bx + bw // 2, 198, num, 3, NAVY, "center")
        draw_text(cv, bx + bw // 2, 220, lab, 1, INK2, "center")

    # ---- region bar
    sw = cw // 8
    for i, (name, col) in enumerate(REGION_COLORS):
        sx = mx + i * sw
        cv.fill_rect(sx, 232, sw - 1, 15, col)
        draw_text(cv, sx + (sw - 1) // 2, 235, name, 1, WHITE, "center")

    # ---- heroes
    hw = 322
    for i, hero in enumerate(HEROES):
        hx = mx + i * (hw + 13)
        hy = 250
        cv.fill_rect(hx, hy, hw, 198, WHITE)
        cv.frame(hx, hy, hw, 198, INK)
        draw_scene(cv, hx + 1, hy + 1, hw - 2, 108, hero["scene"])
        draw_text(cv, hx + 8, hy + 116,
                  wrap_text(hero["headline"], hw - 16, 2)[0], 2, INK)
        lines = wrap_text(hero["headline"], hw - 16, 2)
        if len(lines) > 1:
            draw_text(cv, hx + 8, hy + 134, lines[1], 2, INK)
        sy = draw_para(cv, hx + 8, hy + 156, hero["sub"], hw - 16, 1, INK2, lh=10)
        draw_chip(cv, hx + 8, hy + 180, hero["tag"], WHITE, hero["color"])

    # ---- mid cards (stories 5-14)
    mw = 489
    mh = 44
    for i, (scene, head, sub) in enumerate(MIDS):
        cx = mx + (i % 2) * (mw + 14)
        cy = 452 + (i // 2) * (mh + 6)
        cv.fill_rect(cx, cy, mw, mh, WHITE)
        cv.frame(cx, cy, mw, mh, GREY_D)
        draw_scene(cv, cx + 2, cy + 2, 40, 40, scene)
        draw_text(cv, cx + 48, cy + 5, head, 1, INK)
        draw_text(cv, cx + 48, cy + 22, sub, 1, INK2)

    # ---- also list (stories 15-37)
    ay = 700
    draw_text(cv, mx, ay, "ALSO ON MONDAY 23 NOVEMBER", 2, INK)
    cv.hline(mx, ay + 18, cw, INK, 1)
    for i, (item, rcol) in enumerate(ALSO):
        col = 0 if i < 12 else 1
        row = i if i < 12 else i - 12
        ix = mx + col * (mw + 14)
        iy = ay + 24 + row * 13
        draw_text(cv, ix, iy, "%d." % (15 + i), 1, RED)
        cv.fill_rect(ix + 20, iy + 1, 7, 7, rcol)
        draw_text(cv, ix + 30, iy, item, 1, INK)

    # ---- date check + pin map
    dy = 882
    cv.fill_rect(mx, dy, 560, 80, WHITE)
    cv.frame(mx, dy, 560, 80, RED, 2)
    draw_text(cv, mx + 8, dy + 5, "DATE CHECK", 2, RED)
    draw_text(cv, mx + 8, dy + 22,
              "Every story here happened or was first reported", 1, INK)
    draw_text(cv, mx + 8, dy + 32,
              "Mon 23 Nov 2026 (UTC). Press time 05:00 UTC.", 1, INK)
    draw_text(cv, mx + 8, dy + 44,
              "LEFT OUT - THEY BELONG TO ANOTHER DAY:", 1, RED)
    draw_para(cv, mx + 8, dy + 55, LEFT_OUT, 544, 1, INK2, lh=8)
    draw_pin_map(cv, mx + 576, dy, 416, 80, PINS)

    # ---- footer
    cv.hline(mx, 968, cw, INK, 1)
    draw_text(cv, mx, 974,
              "Sources: BBC - Reuters - AP - AFP - Hindu BusinessLine - Times "
              "of Israel - RFE/RL - Oxfam - NHS - FIFA.", 1, INK2)
    draw_text(cv, mx, 986,
              "Map: 1 Antalya (COP31)  2 Rostov  3 Vanuatu  4 Delhi  5 London  "
              "6 Washington  7 Juba  8 Taipei.", 1, INK2)
    draw_text(cv, mx, 998,
              "Press time 05:00 UTC, Mon 23 Nov 2026. Drawn by hand; no photos. "
              "THE WORLD IN ONE DAY.", 1, INK2)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv = build()
    data = encode_png(W, H, cv.px)
    with open(os.path.join(out_dir, "entry.png"), "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes)" % (os.path.join(out_dir, "entry.png"), len(data)))


if __name__ == "__main__":
    main()
