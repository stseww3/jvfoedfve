"""Somebody is at work behind two windows of the base storey (round two, A0 #85318: what stood
still is made to move, a lamp in a window goes on and off now and then; review #86134: the two
dark windows south of the entrance, a desk lamp, a half-drawn curtain, instruments on the sill).

A dark window is a painted block (materials/windows.py): nothing that stands behind it can be
seen. What the room shows is therefore painted on two sheets that lie on the glass, inside the
grille, one display entity to a window:

    the dark sheet   what is there when the room is dark: the curtain, the lamp, the instruments
                     on the sill, as shapes darker than the night in the glass. It takes the light
                     of the wall, as the glass does.
    the lit sheet    what the lamp shows when it burns: its shade and its mantle, the wall behind
                     it, the edge of the curtain and the side of each instrument that is turned to
                     it. At full emission, as the lit windows are, and a moving picture (artkit.
                     pixelart.Frames): in the frames in which the lamp is out the sheet is clear.

No command and no light source: the game runs the frames by itself in every client (plan/parts/
materials.md, section 2 D). The two windows share one cycle and take turns: the desk lamp burns
and goes out, the lamp on the bench next door comes on a moment later and goes out before the
first comes on again. Whoever works there is not seen (A0: no figures).

The sheets paint the glazing bars across what they show, in the net of the windows, so the net
runs on over a curtain as it does over the glass beside it. Nobody is to see a lit window in
this: the base storey stays the dark band it is (A0, 11-14), a lamp is a point in it.

    WORK        which windows, and what stands in each
    build(canvas, origin, windows)   one display entity to a window of WORK that is there
    models()    the models, "bld_facade_work_<name>"
    check(windows)                   what can be told without a picture, as lines
"""
import functools

import numpy as np

from artkit import models as M
from artkit import pixelart as PX

from ..common import blocks as B
from ..common import palette as P

MODEL = "bld_facade_work_"
# (front, bay, storey) -> what stands behind it. Both are dark windows of the south wing, the two
# that V3 and V4 see beside the entrance.
WORK = {("east", 12, "base"): "desk", ("east", 11, "base"): "bench"}

TILE = 16                   # pixels to a block
PANE = 8                    # the net of the windows, version a: a bar on every eighth column and row
BAR = ("iron", 1)           # the glazing bar, as materials/windows.py paints it
DARK_AT = 0.3               # pixels in front of the glass: the face of the dark sheet,
LIT_AT = 0.6                # and that of the lit sheet over it
NUDGE = 0.01                # blocks: the entity stands this far inside the grille's cell, which lights it
VIEW = M.MID                # seen from the upper terrace, not from the station
SHARE = 0.25                # of a window, at most, is lit by its lamp

FRAME = 40                  # ticks a frame lasts: two seconds
FRAMES = 16                 # a cycle of 32 seconds
# The frames in which each lamp burns. The first frame is what a still picture shows: the desk lamp.
BURNS = {"desk": range(0, 9), "bench": range(10, 15)}

# What a letter of a sketch is painted with. Small letters lie on the dark sheet, capitals on the
# lit one, over them.
DARK = {"c": ("dark_wood", 0), "f": ("dark_wood", 1), "k": ("iron", 0), "j": ("night_glass", 0)}
LIT = {"S": ("glow", 2), "E": ("glow", 3), "M": ("glow", 4), "P": ("glow", 1),
       "W": ("dark_wood", 4), "V": ("dark_wood", 3), "U": ("dark_wood", 2),
       "C": ("dark_wood", 3), "F": ("dark_wood", 4), "R": ("glow", 1), "B": ("brass", 3)}
# How the wall behind a lamp takes its light: rings of (radius in pixels, letter, share), from
# the lamp out. Share 2 is every second pixel, like the squares of a chess board: the light thins
# out into the night in the glass. And how cloth takes it, a curtain's edge beside the lamp.
WALL = ((2.3, "P", 1), (4.3, "W", 1), (6.4, "V", 1), (8.4, "U", 2))
CLOTH = ((7.5, "F", 1), (10.5, "C", 1), (12.5, "C", 2))


class _Sketch:
    """A window's two sheets as letters, x from the left hand of whoever stands before the window,
    y from its head. A letter put down takes the place of what its sheet had there."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.dark, self.lit = {}, {}

    def dot(self, x, y, ch):
        if 0 <= x < self.w and 0 <= y < self.h:
            (self.dark if ch.islower() else self.lit)[(x, y)] = ch

    def box(self, x0, y0, x1, y1, ch):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.dot(x, y, ch)

    def line(self, x0, y0, x1, y1, ch):
        n = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(n + 1):
            self.dot(round(x0 + (x1 - x0) * i / n), round(y0 + (y1 - y0) * i / n), ch)

    def disc(self, cx, cy, ch):
        """A ball five pixels across, its middle at (cx, cy)."""
        for dy, half in ((-2, 1), (-1, 2), (0, 2), (1, 2), (2, 1)):
            self.box(cx - half, cy + dy, cx + half, cy + dy, ch)

    def shine(self, cx, cy):
        """What a lamp whose mantle is at (cx, cy) lights, on the lit sheet: the wall behind it,
        where nothing stands on either sheet, and the cloth that hangs near it."""
        for y in range(self.h):
            for x in range(self.w):
                if (x, y) in self.lit:
                    continue
                on = self.dark.get((x, y))
                if on is not None and on not in "cf":
                    continue
                d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                for radius, ch, share in (WALL if on is None else CLOTH):
                    if d <= radius:
                        if (x + y) % share == 0:
                            self.dot(x, y, ch)
                        break

    def sheet(self, cells, tones):
        """The pixels of one sheet, (h, w, 4); a bar of the net over whatever of it lies on a
        bar's column or row. The rest is clear."""
        px = np.zeros((self.h, self.w, 4), np.uint8)
        for (x, y), ch in cells.items():
            bar = x % PANE == 0 or y % PANE == 0
            px[y, x, :3] = P.colour(*(BAR if bar else tones[ch]))
            px[y, x, 3] = 255
        return px


def _lamp(s, x, foot, high=3):
    """A desk lamp: a foot, a stem, a shade of opal glass on it. Dark: its shape, the glass in the
    darkest tone of the night. Lit: the shade, paler along its lip, and the mantle under it.
    Returns where the mantle is."""
    top = foot - high - 3
    s.box(x - 1, foot, x + 1, foot, "k")
    s.box(x, foot - high, x, foot - 1, "k")
    for y, half, dark, lit in ((top, 1, "j", "S"), (top + 1, 2, "j", "E"), (top + 2, 1, "j", "M")):
        s.box(x - half, y, x + half, y, dark)
        s.box(x - half, y, x + half, y, lit)
    return x, top + 2


def _desk():
    """The desk by the window: a curtain drawn half across from the left, the lamp, a globe on its
    stand, a small transit on a tripod."""
    s = _Sketch(3 * TILE, 2 * TILE)
    foot = s.h - 1
    # the curtain: cloth in folds over the two lights on the left, from the head to the sill
    s.box(1, 1, 15, foot, "c")
    for x in (3, 6, 10, 13):
        s.box(x, 1, x, foot, "f")
    lamp = _lamp(s, 21, foot)
    # the globe
    s.disc(29, foot - 6, "k")
    s.box(29, foot - 3, 29, foot - 1, "k")
    s.box(28, foot, 30, foot, "k")
    for y in (foot - 7, foot - 6, foot - 5):
        s.dot(27, y, "R")                           # the side that is turned to the lamp
    # the transit: two legs and the column, the tube aimed up and out
    s.line(37, foot, 40, foot - 5, "k")
    s.line(43, foot, 40, foot - 5, "k")
    s.box(40, foot - 4, 40, foot, "k")
    s.line(36, foot - 4, 44, foot - 10, "k")
    s.line(36, foot - 5, 44, foot - 11, "k")
    s.line(36, foot - 5, 39, foot - 7, "B")         # the brass of the tube catches the lamp
    s.shine(*lamp)
    return s


def _bench():
    """The bench next door: a blind let half down, a balance under it, three bottles, the lamp."""
    s = _Sketch(3 * TILE, 2 * TILE)
    foot = s.h - 1
    # the blind: slats over the upper half, its rail under them
    s.box(1, 1, s.w - 1, 12, "c")
    for y in (3, 6, 9, 12):
        s.box(1, y, s.w - 1, y, "f")
    s.box(1, 13, s.w - 1, 13, "k")
    # the balance: column, beam, two pans on their threads, the foot
    s.box(12, foot - 9, 12, foot - 1, "k")
    s.box(6, foot - 9, 18, foot - 9, "k")
    for x in (6, 18):
        s.box(x, foot - 8, x, foot - 5, "k")
        s.box(x - 2, foot - 4, x + 2, foot - 4, "k")
    s.box(10, foot, 14, foot, "k")
    s.dot(20, foot - 4, "B")                        # the lip of the pan nearer the lamp
    # the bottles, the tall one stoppered
    for x, high in ((26, 3), (28, 6), (30, 4)):
        s.box(x, foot - high, x, foot, "k")
    s.dot(28, foot - 7, "k")
    s.box(29, foot - 5, 29, foot - 3, "R")
    s.box(31, foot - 3, 31, foot - 1, "R")
    lamp = _lamp(s, 36, foot)
    s.shine(*lamp)
    return s


_ROOMS = {"desk": _desk, "bench": _bench}


@functools.lru_cache(maxsize=None)
def sheets(name):
    """The two sheets of a window as pixels: (dark, lit)."""
    s = _ROOMS[name]()
    return s.sheet(s.dark, DARK), s.sheet(s.lit, LIT)


def model_name(name):
    return MODEL + name


@functools.lru_cache(maxsize=None)
def _models():
    out = {}
    plain = P.mat("iron_flat")
    for name in _ROOMS:
        dark, lit = sheets(name)
        h, w = dark.shape[:2]
        burning = PX.Picture(f"{MODEL}{name}_lit", lit)
        out_ = PX.Picture(f"{MODEL}{name}_out", np.zeros_like(lit))
        shots = [burning if k in BURNS[name] else out_ for k in range(FRAMES)]
        m = M.Model(model_name(name))
        # The anchor is the middle of the foot of the back, which lies on the glass; the pictures
        # are on the faces that look out, the model's +z; +x is the right hand of whoever stands
        # before the window.
        m.box((-w / 2.0, 0.0, 0.0), (w / 2.0, float(h), DARK_AT), plain, skip="neuwd",
              faces={"s": PX.Picture(f"{MODEL}{name}_dark", dark)})
        m.box((-w / 2.0, 0.0, DARK_AT), (w / 2.0, float(h), LIT_AT), plain, skip="neuwd", emit=15, shade=False,
              faces={"s": PX.Frames(f"{MODEL}{name}_lamp", shots, frametime=FRAME)})
        out[m.name] = m
    return out


def models():
    return dict(_models())


_YAW = {(0, 1): 0.0, (-1, 0): 90.0, (0, -1): 180.0, (1, 0): -90.0}     # by the way the sheets look


def places(windows):
    """Where the sheets stand: [(name, (x, y, z), yaw, window)] for the windows of WORK that are in
    `windows` (main/facade.py's windows()). The entity stands just before the outer face of the
    glass, at the middle of the window's foot."""
    out = []
    for w in windows:
        name = WORK.get((w["front"], w["bay"], w["storey"]))
        if name is None:
            continue
        dx, dz = -w["inward"][0], -w["inward"][1]              # the step from the glass outwards
        xs = [c[0] for c in w["cells"]]
        zs = [c[1] for c in w["cells"]]
        x = (min(xs) + max(xs) + 1) / 2.0 + dx * (0.5 + NUDGE)
        z = (min(zs) + max(zs) + 1) / 2.0 + dz * (0.5 + NUDGE)
        out.append((name, (x, float(w["y"][0]), z), _YAW[(dx, dz)], w))
    return out


def build(canvas, origin=(0, 0, 0), windows=()):
    """One display entity to a window of WORK. Returns the entities placed."""
    kit = _models()
    ox, oy, oz = origin
    n = 0
    for name, (x, y, z), yaw, _ in places(windows):
        canvas.add_entity(ox + x, oy + y, oz + z, M.display(kit[model_name(name)], yaw=yaw, view=VIEW))
        n += 1
    return n


def check(windows):
    """What can be told without a picture; the findings as lines (none is good)."""
    out = []
    found = places(windows)
    if len(found) != len(WORK):
        out.append(f"nightwork: {len(found)} of the {len(WORK)} windows of WORK are in the shell")
    for name, _, _, w in found:
        if w["glass"] != B.WINDOW_DARK.block:
            out.append(f"nightwork: the {name} stands in a window of {w['glass']}; it is painted for dark glass")
        wide, high = len(w["cells"]), w["y"][1] - w["y"][0] + 1
        dark, lit = sheets(name)
        if dark.shape[:2] != (high * TILE, wide * TILE):
            out.append(f"nightwork: the {name} is painted {dark.shape[1]}x{dark.shape[0]} "
                       f"for a window of {wide}x{high} blocks")
        share = float((lit[..., 3] > 0).mean())
        if share > SHARE:
            out.append(f"nightwork: the {name}: the lamp lights {share:.0%} of the window, {SHARE:.0%} at most: "
                       f"the base storey is a dark band")
    for name, burns in BURNS.items():
        if not 0 < len(burns) < FRAMES or min(burns) < 0 or max(burns) >= FRAMES:
            out.append(f"nightwork: the {name} burns in the frames {list(burns)} of {FRAMES}")
    if 0 not in BURNS["desk"]:
        out.append("nightwork: the first frame, the one a still picture shows, has no lamp burning")
    if set(BURNS["desk"]) & set(BURNS["bench"]):
        out.append("nightwork: the two lamps burn at once")
    return out
