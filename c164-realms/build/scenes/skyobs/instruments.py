"""Models for the room under the dome: the astronomer's instruments and furniture.

Registered through props.py (SCALE, MODELS and GALLERY are merged into its lists).
"""
import math
import random

import numpy as np

from artkit import models as M
from artkit import pixelart as P

SCALE = {"orrery": 1.5, "star_globe": 1.5, "chart_desk": 1.0, "observer_steps": 1.0, "star_easel": 1.5,
         "book_pile": 1.0, "book_row": 1.0}


class Starry(P.Mat):
    """Night-blue surface with scattered gold stars."""

    def paint(self, w, h, grain="u", seed=0):
        out = super().paint(w, h, grain, seed)
        jj, ii = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
        r = P._hash(ii * 3 + 1, jj * 5 + 2, seed * 13 + 7)
        out[r > 0.972, :3] = P.hx("#c9a04a")
        out[r > 0.990, :3] = P.hx("#fff2b0")
        return out


NAVY = P.Mat("navy", ["#0d1433", "#141d47", "#1b275c", "#243373", "#30428c"], noise=0.25, bevel=0)
STARRY = Starry("starry", ["#0d1433", "#141d47", "#1b275c", "#243373", "#30428c"], noise=0.2, bevel=0)
PAPER = P.Mat("paper", ["#b79e6c", "#cbb482", "#dcc898", "#eadbb1", "#f4ead0"], noise=0.2, bevel=0, base=3)
WAX = P.Mat("wax", ["#cfc4a2", "#e4dbbc", "#f2ecd6"], noise=0.1, bevel=0)
SUN = P.Mat("orrery_sun", ["#f0a030", "#ffc65a", "#ffe08a", "#fff3c0", "#fffbe6"], noise=0.3, bevel=0, base=2)
INK = P.Mat("ink", ["#10131f"], kind="flat", bevel=0)
CUSHION = P.Mat("cushion", ["#5e1717", "#7c2020", "#9c2b2b", "#b83a36"], noise=0.25)
COVERS = [
    P.Mat("cover_red", ["#4a1414", "#651c1c", "#812626", "#9b3230"], noise=0.15),
    P.Mat("cover_green", ["#16301f", "#1f4229", "#2a5535", "#376a43"], noise=0.15),
    P.Mat("cover_blue", ["#161f3d", "#1e2a52", "#283868", "#35487f"], noise=0.15),
    P.Mat("cover_tan", ["#5a4022", "#73542d", "#8c693a", "#a37e4a"], noise=0.15),
    P.Mat("cover_plum", ["#35183a", "#48214e", "#5c2c63", "#713878"], noise=0.15),
]


def star_rows(w, h, seed, frame=True):
    """A drawn star chart: constellation lines 'l' between stars '*', loose stars 'o', frame 'f'."""
    rng = random.Random(seed)
    g = [["." for _ in range(w)] for _ in range(h)]

    def put(x, y, ch):
        if 0 <= x < w and 0 <= y < h and g[y][x] != "*":
            g[y][x] = ch

    for _ in range(max(3, w * h // 100)):
        pts = [(rng.randint(4, w - 5), rng.randint(3, h - 4))]
        for _ in range(rng.randint(2, 4)):
            x, y = pts[-1]
            pts.append((min(w - 3, max(2, x + rng.randint(-6, 6))), min(h - 3, max(2, y + rng.randint(-4, 4)))))
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            n = max(abs(xb - xa), abs(yb - ya), 1)
            for i in range(n + 1):
                put(int(round(xa + (xb - xa) * i / n)), int(round(ya + (yb - ya) * i / n)), "l")
        for x, y in pts:
            put(x, y, "*")
    for _ in range(w * h // 28):
        x, y = rng.randint(1, w - 2), rng.randint(1, h - 2)
        if g[y][x] == ".":
            g[y][x] = "o"
    if frame:
        for x in range(w):
            g[0][x] = g[h - 1][x] = "f"
        for y in range(h):
            g[y][0] = g[y][w - 1] = "f"
    return ["".join(r) for r in g]


def book(m, x, y, z, length, thick, depth, cover, turn=0.0, seed=0):
    """One closed book lying flat with its spine towards -z; (x, y, z) is the middle of its underside."""
    with m.turned(("y", turn), about=(x, y, z)), m.moved((x, y, z)):
        m.box((-length / 2, 0, -depth / 2), (length / 2, thick, depth / 2), cover, skip="s", grain="x", seed=seed)
        m.box((-length / 2 + 0.3, 0.3, -depth / 2 + 0.3), (length / 2 - 0.3, thick - 0.3, depth / 2 - 0.05), PAPER,
              grain="x", seed=seed + 1)


def orrery():
    """Brass orrery: a glowing sun, six planets on their arms and a zodiac band. Anchor: underside of the foot."""
    m = M.Model("orrery", px=1.5)
    m.tube("y", (0, 0), 0, 0.9, 4.6, P.BRASS_DARK, sides=16)
    m.tube("y", (0, 0), 0.9, 1.6, 3.6, P.BRASS_DARK, sides=16)
    m.taper("y", (0, 0), 1.6, 4.0, 2.4, 1.0, P.BRASS, sides=12, steps=4)
    m.tube("y", (0, 0), 4.0, 15.0, 0.7, P.BRASS, sides=8)
    m.ball((0, 5.0, 0), 1.3, P.BRASS_DARK, sides=12, layers=4)
    m.tube("y", (0, 0), 9.4, 10.8, 2.8, P.IRON, sides=16)
    m.tube("y", (0, 0), 10.8, 11.4, 2.0, P.BRASS_DARK, sides=16)
    for k in range(12):   # teeth of the driving wheel
        with m.turned(("y", 30.0 * k), about=(0, 0, 0)):
            m.box((2.7, 9.7, -0.3), (3.3, 10.5, 0.3), P.IRON, seed=981)
    sun_y = 17.0
    m.ball((0, sun_y, 0), 2.4, SUN, sides=12, layers=8, emit=15, shade=False)
    # radius of the orbit, size, material, where it stands on its orbit (degrees)
    planets = [(3.9, 0.55, P.IRON, 40.0), (5.6, 0.8, PAPER, 150.0), (7.6, 0.9, P.VERDIGRIS, 265.0),
               (9.6, 0.7, P.COPPER, 330.0), (12.2, 1.5, P.BRASS, 95.0), (14.8, 1.2, PAPER, 205.0)]
    for i, (orbit, size, mat, where) in enumerate(planets):
        y = 11.6 + 0.55 * i
        m.tube("y", (0, 0), y - 0.2, y + 0.2, 1.0, P.BRASS_DARK, sides=8)
        with m.turned(("y", where), about=(0, 0, 0)):
            m.box((0.6, y - 0.15, -0.15), (orbit, y + 0.15, 0.15), P.BRASS_DARK, grain="x", seed=982)
            m.box((orbit - 0.15, y, -0.15), (orbit + 0.15, sun_y - size * 0.6, 0.15), P.BRASS_DARK, grain="y", seed=983)
            m.ball((orbit, sun_y, 0), size, mat, sides=8 if size < 1 else 12, layers=4 if size < 1 else 6)
            if i == 2:    # the moon
                m.rod((orbit, sun_y, 0), (orbit + 1.7, sun_y + 0.5, 0.6), 0.1, P.IRON, sides=4)
                m.ball((orbit + 1.8, sun_y + 0.55, 0.65), 0.35, PAPER, sides=8, layers=3)
            if i == 4:    # banded giant
                m.tube("y", (orbit, 0), sun_y - 0.25, sun_y + 0.25, size * 1.02, P.COPPER, sides=12)
            if i == 5:    # ringed
                with m.turned(("z", 20.0), about=(orbit, sun_y, 0)):
                    m.ring("y", (orbit, sun_y, 0), size + 0.9, 0.7, 0.12, P.BRASS, sides=16)
    # zodiac band on four curved brackets
    m.ring("y", (0, 12.6, 0), 17.4, 1.8, 0.5, P.BRASS, sides=40)
    m.ring("y", (0, 13.0, 0), 18.2, 0.4, 0.5, P.BRASS_DARK, sides=40)
    for k in range(4):
        with m.turned(("y", 45.0 + 90.0 * k), about=(0, 0, 0)):
            m.ring("z", (4.6, 12.4, 0), 12.0, 0.6, 0.6, P.BRASS_DARK, sides=48, arc=(270.0, 360.0))
            m.box((3.6, 0.2, -0.3), (5.2, 0.9, 0.3), P.BRASS_DARK, seed=984)
    for k in range(12):   # the twelve signs: studs on the band
        with m.turned(("y", 30.0 * k + 15.0), about=(0, 0, 0)):
            m.box((17.0, 12.85, -0.4), (17.8, 13.05, 0.4), P.COPPER, seed=985)
    return m


def star_globe():
    """Celestial globe in a four-legged stand, its axis tilted. Anchor: floor under the middle."""
    m = M.Model("star_globe", px=1.5)
    cy = 15.0
    with m.turned(("z", 23.5), about=(0, cy, 0)):
        m.ball((0, cy, 0), 6.4, STARRY, sides=16, layers=10, patchy=True)
        m.tube("y", (0, 0), cy + 6.3, cy + 7.6, 0.35, P.BRASS, sides=8)
        m.tube("y", (0, 0), cy - 7.6, cy - 6.3, 0.35, P.BRASS, sides=8)
        m.tube("y", (0, 0), cy - 0.25, cy + 0.25, 6.5, P.BRASS_DARK, sides=16)     # the ecliptic
    m.ring("z", (0, cy, 0), 7.5, 0.7, 0.7, P.BRASS, sides=32)
    m.ring("y", (0, cy, 0), 8.9, 1.7, 0.7, P.WOOD, sides=24)
    for k in range(4):
        with m.turned(("y", 45.0 + 90.0 * k), about=(0, 0, 0)):
            m.rod((8.6, cy - 0.3, 0), (7.4, 0.8, 0), 0.6, P.DARK_WOOD, sides=8, seed=990)
            m.ball((7.4, 0.7, 0), 0.9, P.DARK_WOOD, sides=8, layers=3)
            m.ball((8.25, cy - 4.0, 0), 0.95, P.DARK_WOOD, sides=8, layers=4)
            m.box((0.5, 4.4, -0.4), (7.8, 5.2, 0.4), P.DARK_WOOD, grain="x", seed=991)
    m.tube("y", (0, 0), 4.0, 5.6, 1.4, P.DARK_WOOD, sides=8)
    m.tube("y", (0, 0), 5.6, cy - 7.9, 0.35, P.BRASS_DARK, sides=8)
    m.ring("z", (0, cy, 0), 8.1, 0.5, 1.2, P.BRASS_DARK, sides=32, arc=(250.0, 290.0))
    return m


def chart_desk():
    """Writing desk with an unrolled star chart, dividers, books, ink and a candle. The front with
    the drawers looks to +z. Anchor: floor under the middle."""
    chart = P.Sprite("desk_chart", star_rows(22, 14, 4, frame=False),
                     {"l": "#b39566", "*": "#4a2f1a", "o": "#a58a5c"}, back=PAPER)
    m = M.Model("chart_desk")
    m.box((-20, 13.5, -10), (20, 15, 10), P.WOOD, grain="x")
    m.box((-18, 10.5, -8.5), (18, 13.5, 8.5), P.DARK_WOOD, grain="x")
    for sx in (-1, 1):
        for sz in (-1, 1):
            x, z = sx * 16.8, sz * 7.3
            m.taper("y", (x, z), 0, 9.3, 0.7, 1.25, P.DARK_WOOD, sides=8, steps=3, seed=1000)
            m.ball((x, 9.7, z), 1.3, P.DARK_WOOD, sides=8, layers=3, seed=1001)
            m.tube("y", (x, z), 10.0, 10.5, 1.3, P.DARK_WOOD, sides=8, seed=1002)
    m.box((-16.8, 3.0, -0.5), (16.8, 4.0, 0.5), P.DARK_WOOD, grain="x")
    for sx in (-1, 1):
        m.box((sx * 16.8 - 0.5, 3.0, -7.3), (sx * 16.8 + 0.5, 4.0, 7.3), P.DARK_WOOD, grain="z", seed=1003)
    for x in (-9.0, 9.0):   # drawers
        m.box((x - 7.5, 11.0, 8.5), (x + 7.5, 13.2, 8.8), P.WOOD, grain="x", skip="n", seed=1004)
        m.ball((x, 12.1, 9.2), 0.55, P.BRASS, sides=8, layers=3)
    top = 15.0
    # the chart: flat sheet, one end still rolled, held down by the dividers and the glass
    m.box((-17, top, -7), (5, top + 0.12, 7), PAPER, faces={"u": chart}, skip="d")
    m.tube("z", (6.0, top + 0.9), -7, 7, 0.9, PAPER, sides=8)
    m.tube("z", (6.0, top + 0.9), -7.15, 7.15, 0.45, P.WOOD, sides=8)
    hinge = (-7.0, top + 2.6, 1.5)
    m.rod(hinge, (-10.6, top + 0.15, 4.6), 0.2, P.BRASS, sides=4)
    m.rod(hinge, (-4.4, top + 0.15, 5.2), 0.2, P.BRASS, sides=4)
    m.ball(hinge, 0.45, P.BRASS_DARK, sides=8, layers=3)
    m.ring("y", (-12.5, top + 0.3, -3.0), 1.7, 0.45, 0.35, P.BRASS, sides=16)
    m.rod((-11.2, top + 0.3, -1.9), (-9.3, top + 0.3, -0.2), 0.3, P.DARK_WOOD, sides=4)
    # ink, quill, candle
    m.tube("y", (11.5, -6.0), top, top + 1.5, 1.0, NAVY, sides=8, cap=INK)
    m.tube("y", (11.5, -6.0), top + 1.5, top + 2.0, 0.55, NAVY, sides=8, cap=INK)
    m.beam((11.5, top + 1.8, -6.0), (14.6, top + 7.2, -8.4), 0.25, 0.25, WAX)
    m.beam((12.7, top + 3.9, -6.9), (14.9, top + 7.8, -8.6), 0.15, 1.5, WAX)
    m.tube("y", (-17.0, -7.0), top, top + 0.3, 1.7, P.BRASS_DARK, sides=12)
    m.tube("y", (-17.0, -7.0), top + 0.3, top + 3.6, 0.6, WAX, sides=8)
    m.box((-17.25, top + 3.6, -7.25), (-16.75, top + 4.6, -6.75), P.LAMP_GLOW, emit=15, shade=False)
    # a few books to hand
    book(m, 14.0, top, 3.5, 7.0, 1.6, 5.0, COVERS[0], turn=8.0, seed=1010)
    book(m, 13.6, top + 1.6, 3.2, 6.4, 1.3, 4.6, COVERS[2], turn=-12.0, seed=1012)
    book(m, 14.2, top + 2.9, 3.6, 5.6, 1.1, 4.2, COVERS[3], turn=27.0, seed=1014)
    return m


def observer_steps():
    """Rolling steps with a cushioned seat on top, for the observer at the eyepiece: climbed from
    -z, the seat looks to +z. Anchor: floor under the middle."""
    m = M.Model("observer_steps")
    for sx in (-1, 1):
        x = sx * 5.5
        m.beam((x, 1.5, -9.0), (x, 14.0, 3.0), 1.0, 2.2, P.DARK_WOOD, seed=1020)
        m.box((x - 0.5, 1.0, 2.5), (x + 0.5, 15.0, 3.7), P.DARK_WOOD, grain="y", seed=1021)
        m.box((x - 0.5, 1.0, -9.5), (x + 0.5, 2.0, 3.7), P.DARK_WOOD, grain="z", seed=1022)
        for z in (-8.0, 2.4):   # castors
            m.tube("x", (0.8, z), x - 0.35, x + 0.35, 0.8, P.IRON, sides=8, seed=1023)
    for k, (y, z) in enumerate(((4.5, -6.6), (8.5, -2.8), (12.5, 1.0))):
        m.box((-6.2, y, z - 1.9), (6.2, y + 0.9, z + 1.9), P.WOOD, grain="x", seed=1024 + k)
    m.box((-6.4, 15.0, -1.2), (6.4, 16.0, 5.4), P.WOOD, grain="x")
    m.box((-5.4, 16.0, -0.4), (5.4, 17.2, 4.6), CUSHION)
    # hand rail on the right
    m.rod((5.5, 15.0, 3.1), (5.5, 24.0, 3.1), 0.45, P.DARK_WOOD, sides=8)
    m.rod((5.5, 6.0, -7.6), (5.5, 15.5, -7.6), 0.45, P.DARK_WOOD, sides=8)
    m.rod((5.5, 15.2, -7.9), (5.5, 23.7, 3.4), 0.5, P.BRASS, sides=8)
    return m


def star_easel():
    """Standing frame with a large painted star map, leaning back a little; the map looks to +z.
    Anchor: floor under the middle of the front."""
    chart = P.Sprite("easel_chart", star_rows(36, 24, 9),
                     {"l": "#8a6f3c", "*": "#fff2b0", "o": "#c9b27a", "f": "#dcb650"}, back=NAVY)
    m = M.Model("star_easel", px=1.5)
    with m.turned(("x", -11.0), about=(0, 0, 0)):
        for sx in (-1, 1):
            m.box((sx * 10.0 - 0.6, 0, -0.6), (sx * 10.0 + 0.6, 30.0, 0.6), P.DARK_WOOD, grain="y", seed=1030)
        m.box((-12.6, 8.2, -0.2), (12.6, 9.4, 1.6), P.DARK_WOOD, grain="x")
        m.box((-12, 9.4, 0.4), (12, 25.4, 0.9), NAVY, faces={"s": chart}, grain="x")
        m.box((-12.6, 25.4, 0.1), (12.6, 26.4, 1.2), P.DARK_WOOD, grain="x")
        m.box((-10.6, 29.0, -0.5), (10.6, 30.0, 0.5), P.DARK_WOOD, grain="x")
    m.rod((0, 27.5, -5.2), (0, 0, -13.0), 0.6, P.DARK_WOOD, sides=4)
    return m


def book_pile():
    """Five books in an untidy pile. Anchor: under the middle."""
    m = M.Model("book_pile")
    y = 0.0
    for i, (length, thick, depth, turn) in enumerate(((7.5, 1.8, 5.4, -6.0), (7.0, 1.4, 5.0, 14.0), (6.6, 1.6, 4.8, 2.0),
                                                      (6.0, 1.2, 4.4, -22.0), (5.2, 1.0, 3.8, 9.0))):
        book(m, 0.3 * (i % 2), y, 0.2 * i, length, thick, depth, COVERS[(i * 2 + 1) % len(COVERS)], turn=turn,
             seed=1040 + 2 * i)
        y += thick
    return m


def book_row():
    """A row of standing books between two brass ends, one leaning. Anchor: under the middle; spines to +z."""
    m = M.Model("book_row")
    widths = (1.6, 1.2, 1.8, 1.3, 1.5, 1.1, 1.7)
    heights = (7.0, 6.2, 7.6, 6.6, 7.2, 5.8, 6.8)
    x = -sum(widths) / 2.0
    for i, (w, h) in enumerate(zip(widths, heights)):
        lean = 14.0 if i == len(widths) - 1 else 0.0
        with m.turned(("z", -lean), about=(x, 0, 0)):
            m.box((x, 0, -2.4), (x + w, h, 2.4), COVERS[(i * 3) % len(COVERS)], skip="n", grain="y", seed=1050 + i)
            m.box((x + 0.25, 0.25, -2.45), (x + w - 0.25, h - 0.25, 2.0), PAPER, grain="y", seed=1060 + i)
        x += w
    for ex in (-sum(widths) / 2.0 - 0.9, x + 1.3):
        m.box((ex, 0, -2.2), (ex + 0.6, 5.0, 2.2), P.BRASS_DARK, seed=1070)
        m.box((ex - 0.6, 0, -2.2), (ex + 1.2, 0.5, 2.2), P.BRASS_DARK, seed=1071)
    return m


GLOW_SIZES = [(2, 3), (2, 2), (1, 2)]


def window_glow(w, h):
    """Lamplight to stand behind a window of w by h blocks: a warm sheet with leaded lines, brightest
    in the middle, seen from +z only and always fully lit. Anchor: its middle."""
    tones = "abcde"
    rows = []
    for j in range(16 * h):
        row = ""
        for i in range(16 * w):
            u = (i + 0.5) / (16 * w) * 2.0 - 1.0
            v = (j + 0.5) / (16 * h) * 2.0 - 1.0
            level = 4.4 - 2.6 * (u * u + v * v) + 0.9 * (P._hash(i, j, 77 + w * 10 + h) - 0.5)
            if i % 8 == 0 or j % 8 == 0:
                level -= 1.0   # the leads between the small panes
            row += tones[max(0, min(4, int(level)))]
        rows.append(row)
    light = P.Sprite(f"window_light_{w}x{h}", rows,
                     {"a": "#b8611c", "b": "#dc8226", "c": "#f4a23a", "d": "#ffc45a", "e": "#ffe08a"})
    m = M.Model(f"glow_{w}x{h}")
    m.box((-8 * w, -8 * h, -0.05), (8 * w, 8 * h, 0.05), light, skip="newud", emit=15, shade=False)
    return m


MODELS = [orrery, star_globe, chart_desk, observer_steps, star_easel, book_pile, book_row]
MODELS += [(lambda w=w, h=h: window_glow(w, h)) for w, h in GLOW_SIZES]
SCALE.update({f"glow_{w}x{h}": 1.0 for w, h in GLOW_SIZES})

GALLERY = [
    ("orrery", [("orrery", None, {})], (2.4, 2.6, 3.4), (0, 1.3, 0)),
    ("globe", [("star_globe", None, {})], (1.8, 2.2, 2.6), (0, 1.3, 0)),
    ("desk", [("chart_desk", None, {})], (1.6, 2.2, 2.2), (0, 0.9, 0)),
    ("steps", [("observer_steps", None, {"yaw": 200.0})], (1.8, 1.8, 2.4), (0, 0.8, 0)),
    ("easel", [("star_easel", (0, 0, -1.0), {})], (1.8, 2.0, 3.2), (0, 1.5, -1.0)),
    ("books", [("book_pile", (-0.6, 0, 0), {}), ("book_row", (0.6, 0, 0), {})], (0.4, 1.0, 1.6), (0, 0.3, 0)),
]
