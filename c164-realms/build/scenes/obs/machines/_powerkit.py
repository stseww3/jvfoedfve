"""What the boilers and the switchboard of the power house share (machines/switchboard-boiler):
drawing a model in blocks, lighting a piece that looks at a wall's side of the sky, painting a
face pixel by pixel, and placing a piece.

The name starts with an underscore: the category does not take it for a package.
"""
import math

from artkit import models as M
from artkit.pixelart import Sprite

from ..common import palette as P

VIEW = 1.5          # view range of a piece: 96 blocks at the client's normal setting; the room is 19 across

# ---- how a piece is lit --------------------------------------------------------------------------------
# The game lights a face of an item model by the one of the model's six axes its normal lies nearest
# to, that axis turned with the display entity, under two fixed lamps high in the north-east and the
# south-west: a face filed under "up" is full bright, north and south 0.74, east and west 0.5, down
# 0.4 (see machines/mast.py, the lamp). A boiler front looks west and the board looks east: drawn
# upright, all that counts on them would be shown at half its tone, and iron at half its tone under a
# lamp of level 10 is black.
#
# So such a piece is drawn in a frame that leans towards the side it looks at: the entity is turned
# about the north-south axis by LEAN, the model is drawn turned back and stands upright, and its
# front is filed under the model's "up", which now points LEAN off the zenith: full bright, as its
# tops are (filed under the axis that leans the other way). Faces that look north and south keep
# 0.74, undersides and backs get 0.4. It is the light of a lamp that hangs before the piece, which
# is where the fire and the room's lamps are. LEAN is a degree past 45 so that no face lies on the
# line between two axes.
LEAN = 46.0
LEAN_WEST = (("z", LEAN),)      # for a piece that looks west
LEAN_EAST = (("z", -LEAN),)     # for a piece that looks east


class Draw:
    """A model drawn in blocks round the point `at`, where its entity stands, and shown at `scale`.

    artkit's unit is 1/16 block of a model shown at scale 1. A model shown at scale s is drawn s
    times smaller and gets s texels to the unit (px = scale): 16 texels to the block whatever the
    scale. A model may span 48 units: three blocks at scale 1, six at scale 2.

    frame = the turns the entity is given (LEAN_WEST, LEAN_EAST); everything is drawn turned back.
    """

    def __init__(self, name, at=(0.0, 0.0, 0.0), scale=2.0, frame=()):
        self.at = tuple(float(v) for v in at)
        self.scale = float(scale)
        self.u = 16.0 / self.scale
        self.m = M.Model(name, px=self.scale)
        self.frame = tuple(frame)
        if self.frame:
            self._upright = self.m.turned(*((axis, -deg) for axis, deg in reversed(self.frame)))
            self._upright.__enter__()

    def p(self, v):
        return tuple((v[i] - self.at[i]) * self.u for i in range(3))

    def _across(self, axis, c):
        k = M.AXES.index(axis)
        o1, o2 = [i for i in range(3) if i != k]
        return k, ((c[0] - self.at[o1]) * self.u, (c[1] - self.at[o2]) * self.u)

    def box(self, a, b, mat, rot=None, **kw):
        if rot is not None:
            rot = (rot[0], rot[1], self.p(rot[2]))
        self.m.box(self.p(a), self.p(b), mat, rot=rot, **kw)

    def tube(self, axis, c, a0, a1, radius, mat, **kw):
        """c: the two other coordinates of the centre line, in the order of the axes."""
        k, c = self._across(axis, c)
        self.m.tube(axis, c, (a0 - self.at[k]) * self.u, (a1 - self.at[k]) * self.u, radius * self.u, mat, **kw)

    def taper(self, axis, c, a0, a1, r0, r1, mat, **kw):
        k, c = self._across(axis, c)
        self.m.taper(axis, c, (a0 - self.at[k]) * self.u, (a1 - self.at[k]) * self.u, r0 * self.u, r1 * self.u,
                     mat, **kw)

    def ring(self, axis, centre, radius, thick, width, mat, **kw):
        self.m.ring(axis, self.p(centre), radius * self.u, thick * self.u, width * self.u, mat, **kw)

    def ball(self, centre, radius, mat, **kw):
        self.m.ball(self.p(centre), radius * self.u, mat, **kw)

    def rod(self, a, b, radius, mat, **kw):
        self.m.rod(self.p(a), self.p(b), radius * self.u, mat, **kw)

    def beam(self, a, b, width, height, mat, **kw):
        self.m.beam(self.p(a), self.p(b), width * self.u, height * self.u, mat, **kw)

    def hose(self, points, radius, mat, **kw):
        self.m.hose([self.p(v) for v in points], radius * self.u, mat, **kw)

    def turned(self, *turns, about=(0.0, 0.0, 0.0)):
        """`with d.turned(("z", 30), about=p):` turns what is drawn inside about the point p (blocks)."""
        return self.m.turned(*turns, about=self.p(about))

    def plate(self, face, at, w, h, sprite, lift=0.0, thick=1.0 / 64.0, **kw):
        """A picture standing by itself: a box as thin as paper that shows `sprite` on one face only.

        face   the letter of the face that carries it: "w" or "e" (the picture's plane is x = at[0]),
               "u" (y = at[1]), "n" or "s" (z = at[2])
        at     the middle of the picture, in blocks; w, h its size in texels
        lift   how far the picture stands off that plane, towards where it looks: a quarter texel
               keeps it clear of the face it lies on
        """
        k = {"w": 0, "e": 0, "u": 1, "d": 1, "n": 2, "s": 2}[face]
        out = 1.0 if face in "eus" else -1.0
        ua, va = M.FACE_AXES[face][1], M.FACE_AXES[face][2]
        lo, hi = list(at), list(at)
        lo[ua], hi[ua] = at[ua] - w / 32.0, at[ua] + w / 32.0
        lo[va], hi[va] = at[va] - h / 32.0, at[va] + h / 32.0
        front = at[k] + out * lift
        lo[k], hi[k] = sorted((front, front - out * thick))
        self.box(lo, hi, sprite, skip="".join(f for f in "nsewud" if f != face), **kw)


def place(canvas, drawn, pos, origin, yaw=0.0, brightness=None):
    """One drawn model with its point `at` on pos; returns 1, the entity it takes."""
    x, y, z = (pos[i] + origin[i] for i in range(3))
    canvas.add_entity(x, y, z, M.display(drawn.m, yaw=yaw, scale=drawn.scale, turns=drawn.frame, brightness=brightness,
                                         view=VIEW))
    return 1


# ---- painting a face pixel by pixel ----------------------------------------------------------------------
# One letter for every tone of the ramps the set uses; "." is see-through.
LETTERS = {"iron": "0123456", "brass": "abcdef", "slate": "ABCDEFG", "cream": "pqrs", "porcelain": "PQRST",
           "glow": "uvwxy", "phosphor": "hijkl", "signal": "JKLM", "dark_wood": "VWXYZ"}
TONES = {c: P.RAMPS[ramp][i] for ramp, letters in LETTERS.items() for i, c in enumerate(letters)}


def tone(ramp, step):
    """The letter of a ramp's step, kept inside the ramp."""
    letters = LETTERS[ramp]
    return letters[int(min(len(letters) - 1, max(0, step)))]


def flat(ramp, step):
    """One flat tone of a ramp, as a material."""
    return P.mat(ramp, kind="flat", base=step, bevel=0)


def _hash(i, j, seed):
    h = (i * 374761393 + j * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(1 << 24)


class Pix:
    """A small picture drawn in the letters of TONES; x runs right, y down, (0, 0) is the top left
    texel. Circles are measured from texel middles: disc(24, 24, 24) fills a 48 x 48 picture's
    inscribed circle."""

    def __init__(self, w, h, fill="."):
        self.w, self.h = int(w), int(h)
        self.g = [[fill] * self.w for _ in range(self.h)]

    def get(self, x, y):
        return self.g[y][x] if 0 <= x < self.w and 0 <= y < self.h else "."

    def set(self, x, y, ch, only=None):
        if 0 <= x < self.w and 0 <= y < self.h and (only is None or self.g[y][x] in only):
            self.g[y][x] = ch

    def rect(self, x0, y0, x1, y1, ch, only=None):
        """Both corners are filled."""
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, ch, only)

    def frame(self, x0, y0, x1, y1, ch, only=None):
        for x in range(x0, x1 + 1):
            self.set(x, y0, ch, only)
            self.set(x, y1, ch, only)
        for y in range(y0, y1 + 1):
            self.set(x0, y, ch, only)
            self.set(x1, y, ch, only)

    def disc(self, cx, cy, r, ch, only=None, inner=0.0):
        """Texels whose middle lies within r of (cx, cy), and not within `inner`."""
        for y in range(self.h):
            for x in range(self.w):
                d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
                if inner <= d <= r and not (inner and d == inner):
                    self.set(x, y, ch, only)

    def dots(self, cx, cy, r, n, ch, start=0.0, only=None):
        """n texels on the circle of radius r, the first `start` degrees from the top, clockwise."""
        for k in range(n):
            a = math.radians(start + 360.0 * k / n)
            self.set(int(math.floor(cx + r * math.sin(a))), int(math.floor(cy - r * math.cos(a))), ch, only)

    def line(self, x0, y0, x1, y1, ch, only=None):
        n = max(abs(x1 - x0), abs(y1 - y0), 1)
        for k in range(n + 1):
            self.set(int(round(x0 + (x1 - x0) * k / n)), int(round(y0 + (y1 - y0) * k / n)), ch, only)

    def streaks(self, on, light, dark, seed, share=0.10, run=5):
        """Short brushed runs along x, one step up or down, on the texels that are `on`."""
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] != on:
                    continue
                r = _hash(y, x // run + (y * 7) % run, seed)
                if r > 1.0 - share / 2.0:
                    self.g[y][x] = light
                elif r < share / 2.0:
                    self.g[y][x] = dark

    def specks(self, on, light, dark, seed, share=0.10):
        """Single texels one step up or down, on the texels that are `on`."""
        for y in range(self.h):
            for x in range(self.w):
                if self.g[y][x] != on:
                    continue
                r = _hash(x, y, seed)
                if r > 1.0 - share / 2.0:
                    self.g[y][x] = light
                elif r < share / 2.0:
                    self.g[y][x] = dark

    def paste(self, other, x0, y0):
        for y in range(other.h):
            for x in range(other.w):
                if other.g[y][x] != ".":
                    self.set(x0 + x, y0 + y, other.g[y][x])

    def text(self, x0, y0, rows, key):
        """Rows of a small drawing: the letters of `key` are replaced by its tones, the rest is left."""
        for j, row in enumerate(rows):
            for i, c in enumerate(row):
                if c in key:
                    self.set(x0 + i, y0 + j, key[c])

    def rows(self):
        return ["".join(r) for r in self.g]

    def sprite(self, name):
        return Sprite(name, self.rows(), TONES)

    def save(self, path, k=8):
        """A picture file of it, k times enlarged: for looking at while drawing, never for the pack."""
        from PIL import Image
        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        for y in range(self.h):
            for x in range(self.w):
                c = self.g[y][x]
                if c in TONES:
                    v = TONES[c].lstrip("#")
                    img.putpixel((x, y), (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16), 255))
        img.resize((self.w * k, self.h * k), Image.NEAREST).save(path)
